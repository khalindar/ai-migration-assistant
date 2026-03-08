import queue
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.platform_state import PlatformState
from services.repo_cloner import clone_repo, get_directory_summary
from utils.logger import make_log


def run(state: PlatformState, log_queue: queue.Queue) -> PlatformState:
    log_queue.put(make_log("AI", "Initializing repository scanner..."))
    log_queue.put(make_log("AI", f"Cloning repository: {state.repo_url}"))
    log_queue.put(make_log("System", "Connecting to GitHub..."))

    clone_path, file_tree = clone_repo(state.repo_url)

    log_queue.put(make_log("System", f"Repository cloned — {file_tree['file_count']} files detected", "success"))
    log_queue.put(make_log("AI", f"Identified {len(file_tree['directories'])} directories"))
    log_queue.put(make_log("AI", "Building file index..."))

    # Detect languages from extensions
    ext_counts = {}
    for f in file_tree["files"]:
        ext = f["ext"]
        if ext:
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

    top_exts = sorted(ext_counts.items(), key=lambda x: -x[1])[:10]
    log_queue.put(make_log("AI", f"Top file types: {', '.join(e for e, _ in top_exts)}", "info"))

    state.repo_structure = {
        "clone_path": clone_path,
        "file_tree": file_tree,
        "directory_summary": get_directory_summary(file_tree),
        "extension_counts": dict(top_exts),
        "file_count": file_tree["file_count"],
    }

    log_queue.put(make_log("AI", "Repository scan complete ✔", "success"))
    return state
