import queue
from models.platform_state import PlatformState
from utils.logger import make_log


def run(state: PlatformState, log_queue: queue.Queue) -> PlatformState:
    log_queue.put(make_log("AI", "Evaluating cloud provider selection..."))

    if state.lumi_dependency:
        state.cloud_provider = "GCP"
        log_queue.put(make_log("AI", "LUMI dependency detected — selecting GCP as cloud provider", "info"))
        log_queue.put(make_log("AI", "Cloud provider confirmed: Google Cloud Platform (GCP) ✔", "success"))
    else:
        state.cloud_provider = "AWS"
        log_queue.put(make_log("AI", "No LUMI dependency — selecting AWS as cloud provider", "info"))
        log_queue.put(make_log("AI", "Cloud provider confirmed: Amazon Web Services (AWS) ✔", "success"))

    log_queue.put(make_log("AI", f"All downstream resources will target {state.cloud_provider}", "info"))
    return state
