import os
import shutil
import tempfile
from pathlib import Path
from git import Repo, GitCommandError

EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".nuxt", "vendor"}
INCLUDE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".rs",
    ".yaml", ".yml", ".json", ".toml", ".tf", ".hcl", ".dockerfile",
    ".sh", ".env.example", ".md", ".xml", ".gradle", ".pom",
}
MAX_FILE_SIZE = 50_000  # bytes


def clone_repo(repo_url: str, target_dir: str = None) -> tuple[str, dict]:
    """
    Clone a GitHub repo into a temp directory.
    Returns (clone_path, file_tree)
    """
    if target_dir is None:
        target_dir = tempfile.mkdtemp(prefix="aipa_")

    try:
        Repo.clone_from(repo_url, target_dir, depth=1)
    except GitCommandError as e:
        raise RuntimeError(f"Failed to clone repository: {e}")

    file_tree = build_file_tree(target_dir)
    return target_dir, file_tree


def build_file_tree(root_path: str) -> dict:
    """
    Walk the repo and return a structured file tree with content for key files.
    """
    tree = {
        "root": root_path,
        "files": [],
        "directories": [],
        "key_files": {},
        "file_count": 0,
        "total_size": 0,
    }

    root = Path(root_path)

    for path in root.rglob("*"):
        # Skip excluded directories
        if any(excl in path.parts for excl in EXCLUDE_DIRS):
            continue

        relative = str(path.relative_to(root))

        if path.is_dir():
            tree["directories"].append(relative)
        elif path.is_file():
            size = path.stat().st_size
            tree["files"].append({"path": relative, "size": size, "ext": path.suffix})
            tree["file_count"] += 1
            tree["total_size"] += size

            # Read content for key files
            if path.suffix in INCLUDE_EXTENSIONS and size <= MAX_FILE_SIZE:
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                    tree["key_files"][relative] = content
                except Exception:
                    pass

    return tree


def cleanup_repo(clone_path: str):
    if clone_path and os.path.exists(clone_path):
        shutil.rmtree(clone_path, ignore_errors=True)


def get_directory_summary(file_tree: dict) -> str:
    """Return a compact string summary of the repo structure for prompts."""
    dirs = sorted(file_tree.get("directories", []))[:50]
    files = [f["path"] for f in file_tree.get("files", [])[:100]]
    lines = ["DIRECTORIES:"] + dirs + ["\nFILES:"] + files
    return "\n".join(lines)
