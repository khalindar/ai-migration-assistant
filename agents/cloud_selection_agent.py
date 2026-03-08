import queue
from models.platform_state import PlatformState
from utils.logger import make_log


def run(state: PlatformState, log_queue: queue.Queue) -> PlatformState:
    log_queue.put(make_log("AI", "Confirming cloud provider selection..."))
    log_queue.put(make_log("AI", f"Target platform: {state.cloud_provider}", "info"))
    log_queue.put(make_log("AI", f"Cloud provider confirmed: {state.cloud_provider} ✔", "success"))
    log_queue.put(make_log("AI", f"All downstream resources will target {state.cloud_provider}", "info"))
    return state
