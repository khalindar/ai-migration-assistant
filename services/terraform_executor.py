import time
import queue
from utils.logger import make_log


class TerraformExecutor:
    def __init__(self, safe_mode: bool, log_queue: queue.Queue):
        self.safe_mode = safe_mode
        self.log_queue = log_queue

    def provision(self, resources: list) -> dict:
        if self.safe_mode:
            return self._simulate(resources)
        return self._real(resources)

    def _simulate(self, resources: list) -> dict:
        results = {}
        self.log_queue.put(make_log("Terraform", "Initializing Terraform...", "info"))
        time.sleep(0.5)
        self.log_queue.put(make_log("Terraform", "Planning infrastructure changes...", "info"))
        time.sleep(0.5)
        self.log_queue.put(make_log("Terraform", "Applying infrastructure...", "info"))
        time.sleep(0.3)

        for resource in resources:
            name = resource.get("name", resource.get("type", "resource"))
            time.sleep(0.4)
            self.log_queue.put(make_log("Terraform", f"Creating {name}...", "info"))
            time.sleep(0.6)
            self.log_queue.put(make_log("Terraform", f"{name} created successfully ✔", "success"))
            results[name] = "created"

        self.log_queue.put(make_log("Terraform", "Apply complete! All resources provisioned.", "success"))
        return results

    def _real(self, resources: list) -> dict:
        self.log_queue.put(make_log("Terraform", "Real Terraform execution not enabled in prototype.", "warning"))
        return {}


class DockerExecutor:
    def __init__(self, safe_mode: bool, log_queue: queue.Queue):
        self.safe_mode = safe_mode
        self.log_queue = log_queue

    def build(self, services: list) -> dict:
        if self.safe_mode:
            return self._simulate(services)
        return self._real(services)

    def _simulate(self, services: list) -> dict:
        results = {}
        for service in services:
            name = service if isinstance(service, str) else service.get("name", "service")
            self.log_queue.put(make_log("Docker", f"Building image for {name}...", "info"))
            time.sleep(0.5)
            self.log_queue.put(make_log("Docker", f"Image {name}:latest built successfully ✔", "success"))
            results[name] = f"{name}:latest"
        return results

    def _real(self, services: list) -> dict:
        self.log_queue.put(make_log("Docker", "Real Docker build not enabled in prototype.", "warning"))
        return {}


class KubernetesExecutor:
    def __init__(self, safe_mode: bool, log_queue: queue.Queue):
        self.safe_mode = safe_mode
        self.log_queue = log_queue

    def deploy(self, manifests: dict) -> dict:
        if self.safe_mode:
            return self._simulate(manifests)
        return self._real(manifests)

    def _simulate(self, manifests: dict) -> dict:
        results = {}
        self.log_queue.put(make_log("Kubernetes", "Applying manifests to cluster...", "info"))
        time.sleep(0.3)

        services = manifests.get("services", [])
        if not services:
            services = list(manifests.keys())

        for svc in services:
            name = svc if isinstance(svc, str) else svc.get("name", "service")
            time.sleep(0.4)
            self.log_queue.put(make_log("Kubernetes", f"Deploying {name}...", "info"))
            time.sleep(0.5)
            self.log_queue.put(make_log("Kubernetes", f"{name} running (1/1 pods ready) ✔", "success"))
            results[name] = "running"

        self.log_queue.put(make_log("Kubernetes", "All services deployed successfully ✔", "success"))
        return results

    def _real(self, manifests: dict) -> dict:
        self.log_queue.put(make_log("Kubernetes", "Real kubectl execution not enabled in prototype.", "warning"))
        return {}
