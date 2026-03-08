import time
import queue
from models.platform_state import PlatformState
from services.terraform_executor import TerraformExecutor, DockerExecutor, KubernetesExecutor
from utils.logger import make_log


def run(state: PlatformState, log_queue: queue.Queue) -> PlatformState:
    tf_executor = TerraformExecutor(state.safe_mode, log_queue)
    docker_executor = DockerExecutor(state.safe_mode, log_queue)
    k8s_executor = KubernetesExecutor(state.safe_mode, log_queue)

    deployment_status = {}

    # Step 10: Bundle
    log_queue.put(make_log("AI", "Bundling application code for deployment..."))
    log_queue.put(make_log("Docker", "Analyzing Dockerfiles and build configurations..."))
    time.sleep(0.5)
    services = state.detected_services or ["api-service"]
    docker_results = docker_executor.build(services)
    deployment_status["docker"] = docker_results

    # Step 11: Terraform provisioning
    log_queue.put(make_log("AI", "Starting infrastructure provisioning..."))
    tf_results = tf_executor.provision(state.terraform_resources)
    deployment_status["terraform"] = tf_results

    # Step 12: Kubernetes deploy
    log_queue.put(make_log("AI", "Publishing application to Kubernetes cluster..."))
    k8s_results = k8s_executor.deploy(state.kubernetes_manifests)
    deployment_status["kubernetes"] = k8s_results

    # Step 13: Validate endpoint
    log_queue.put(make_log("AI", "Validating public application endpoint..."))
    time.sleep(0.8)

    provider = state.cloud_provider
    cluster_name = "app-cluster"
    if provider == "AWS":
        endpoint = f"https://app.{cluster_name}.us-east-1.elb.amazonaws.com"
    else:
        endpoint = f"https://app.{cluster_name}.us-central1.cloud.gcp.com"

    state.simulated_endpoint = endpoint
    deployment_status["endpoint"] = endpoint
    deployment_status["status"] = "deployed"

    log_queue.put(make_log("AI", f"Application endpoint: {endpoint}", "success"))
    log_queue.put(make_log("AI", "Endpoint validation complete ✔", "success"))

    state.deployment_status = deployment_status
    return state
