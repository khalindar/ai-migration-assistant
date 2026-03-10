"""
State persistence service — local file or S3 backend.

Configure via environment variables:
  STATE_BACKEND    = local (default) | s3
  STATE_LOCAL_DIR  = .sessions (default)
  STATE_S3_BUCKET  = <bucket name>          (required for s3)
  STATE_S3_PREFIX  = sessions (default)
  AWS_REGION       = us-east-1 (default)
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Optional

from models.platform_state import PlatformState


# ── Helpers ──────────────────────────────────────────────────────────────────

def _repo_key(repo_url: str) -> str:
    """Deterministic filename key from repo URL."""
    slug = repo_url.rstrip("/").split("/")[-1]
    h = hashlib.sha1(repo_url.encode()).hexdigest()[:8]
    return f"{slug}-{h}"


def _session_meta(state: PlatformState, key: str) -> dict:
    completed = sum(1 for s in state.step_statuses.values() if s == "COMPLETED")
    return {
        "key": key,
        "repo_url": state.repo_url,
        "repo_name": state.repo_url.rstrip("/").split("/")[-1],
        "cloud_provider": state.cloud_provider,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "steps_completed": completed,
        "workflow_complete": state.workflow_complete,
    }


def format_saved_at(saved_at: str) -> str:
    """Return human-readable relative time string."""
    try:
        dt = datetime.fromisoformat(saved_at)
        now = datetime.now(timezone.utc)
        diff = now - dt
        if diff.days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                mins = diff.seconds // 60
                return f"{mins}m ago" if mins > 0 else "just now"
            return f"{hours}h ago"
        elif diff.days == 1:
            return "yesterday"
        elif diff.days < 7:
            return f"{diff.days}d ago"
        else:
            return dt.strftime("%b %d, %Y")
    except Exception:
        return saved_at[:10] if saved_at else ""


# ── Local backend ─────────────────────────────────────────────────────────────

class LocalStateStore:
    def __init__(self, sessions_dir: str):
        self._dir = sessions_dir
        os.makedirs(self._dir, exist_ok=True)

    def _index_path(self) -> str:
        return os.path.join(self._dir, "index.json")

    def _state_path(self, key: str) -> str:
        return os.path.join(self._dir, f"{key}.json")

    def _read_index(self) -> list:
        path = self._index_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return []

    def _write_index(self, entries: list):
        with open(self._index_path(), "w") as f:
            json.dump(entries, f, indent=2)

    def save(self, state: PlatformState):
        if not state.repo_url:
            return
        key = _repo_key(state.repo_url)
        data = state.model_dump()
        data["workflow_running"] = False  # never persist a running state
        with open(self._state_path(key), "w") as f:
            json.dump(data, f, indent=2)
        meta = _session_meta(state, key)
        entries = [e for e in self._read_index() if e.get("key") != key]
        entries.insert(0, meta)  # newest first
        self._write_index(entries)

    def load(self, repo_url: str) -> Optional[PlatformState]:
        key = _repo_key(repo_url)
        path = self._state_path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            data["workflow_running"] = False
            data["loaded_from_cache"] = True
            return PlatformState(**data)
        except Exception:
            return None

    def list_sessions(self) -> list:
        return self._read_index()

    def find_by_url(self, repo_url: str) -> Optional[dict]:
        key = _repo_key(repo_url)
        for entry in self._read_index():
            if entry.get("key") == key:
                return entry
        return None


# ── S3 backend ────────────────────────────────────────────────────────────────

class S3StateStore:
    def __init__(self, bucket: str, prefix: str, region: str):
        import boto3  # only imported when S3 backend is used
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")
        self._s3 = boto3.client("s3", region_name=region)

    def _state_key(self, key: str) -> str:
        return f"{self._prefix}/{key}.json"

    def _index_key(self) -> str:
        return f"{self._prefix}/index.json"

    def _read_index(self) -> list:
        try:
            resp = self._s3.get_object(Bucket=self._bucket, Key=self._index_key())
            return json.loads(resp["Body"].read())
        except Exception:
            return []

    def _write_index(self, entries: list):
        self._s3.put_object(
            Bucket=self._bucket,
            Key=self._index_key(),
            Body=json.dumps(entries, indent=2).encode(),
            ContentType="application/json",
        )

    def save(self, state: PlatformState):
        if not state.repo_url:
            return
        key = _repo_key(state.repo_url)
        data = state.model_dump()
        data["workflow_running"] = False
        self._s3.put_object(
            Bucket=self._bucket,
            Key=self._state_key(key),
            Body=json.dumps(data, indent=2).encode(),
            ContentType="application/json",
        )
        meta = _session_meta(state, key)
        entries = [e for e in self._read_index() if e.get("key") != key]
        entries.insert(0, meta)
        self._write_index(entries)

    def load(self, repo_url: str) -> Optional[PlatformState]:
        key = _repo_key(repo_url)
        try:
            resp = self._s3.get_object(Bucket=self._bucket, Key=self._state_key(key))
            data = json.loads(resp["Body"].read())
            data["workflow_running"] = False
            data["loaded_from_cache"] = True
            return PlatformState(**data)
        except Exception:
            return None

    def list_sessions(self) -> list:
        return self._read_index()

    def find_by_url(self, repo_url: str) -> Optional[dict]:
        key = _repo_key(repo_url)
        for entry in self._read_index():
            if entry.get("key") == key:
                return entry
        return None


# ── Factory ───────────────────────────────────────────────────────────────────

_store_instance = None


def get_store():
    """Return the configured state store (singleton per process)."""
    global _store_instance
    if _store_instance is not None:
        return _store_instance

    from dotenv import load_dotenv
    load_dotenv()

    backend = os.getenv("STATE_BACKEND", "local").lower()

    if backend == "s3":
        bucket = os.getenv("STATE_S3_BUCKET", "")
        if not bucket:
            raise ValueError("STATE_S3_BUCKET must be set when STATE_BACKEND=s3")
        prefix = os.getenv("STATE_S3_PREFIX", "sessions")
        region = os.getenv("AWS_REGION", "us-east-1")
        _store_instance = S3StateStore(bucket, prefix, region)
    else:
        sessions_dir = os.getenv("STATE_LOCAL_DIR", ".sessions")
        _store_instance = LocalStateStore(sessions_dir)

    return _store_instance
