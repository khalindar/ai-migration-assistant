import queue
import threading
import traceback
from models.platform_state import PlatformState, StepStatus, WORKFLOW_STEPS
from utils.logger import make_log, LogEvent, StepStatusEvent

import agents.repo_scanner_agent as repo_scanner_agent
import agents.repo_analysis_agent as repo_analysis_agent
import agents.repo_summary_agent as repo_summary_agent
import agents.dependency_agent as dependency_agent
import agents.infrastructure_agent as infrastructure_agent
import agents.modernization_agent as modernization_agent
import agents.cloud_selection_agent as cloud_selection_agent
import agents.kubernetes_agent as kubernetes_agent
import agents.terraform_agent as terraform_agent
import agents.deployment_agent as deployment_agent
import agents.cost_estimation_agent as cost_estimation_agent


STEP_AGENTS = [
    ("scan",           repo_scanner_agent),
    ("analyze",        repo_analysis_agent),
    ("summarize",      repo_summary_agent),
    ("dependencies",   dependency_agent),
    ("infrastructure", infrastructure_agent),
    ("modernization",  modernization_agent),
    ("cloud",          cloud_selection_agent),
    ("kubernetes",     kubernetes_agent),
    ("terraform",      terraform_agent),
    ("bundle",         None),
    ("provision",      None),
    ("deploy",         None),
    ("validate",       None),
    ("cost",           cost_estimation_agent),
]

DEPLOYMENT_STEPS = {"bundle", "provision", "deploy", "validate"}


class _StepQueue:
    """Wraps the main queue and tags all LogEvents with the current step_id."""
    def __init__(self, main_queue: queue.Queue, step_id: str):
        self._q = main_queue
        self._step_id = step_id

    def put(self, event):
        if isinstance(event, LogEvent) and event.step_id is None:
            event.step_id = self._step_id
        self._q.put(event)

    def empty(self):
        return self._q.empty()

    def get_nowait(self):
        return self._q.get_nowait()


class WorkflowEngine:
    def __init__(self):
        self.log_queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread = None
        self._store = None

    def _get_store(self):
        if self._store is None:
            try:
                from services.state_store import get_store
                self._store = get_store()
            except Exception:
                pass
        return self._store

    def _save(self, state: PlatformState):
        try:
            store = self._get_store()
            if store:
                store.save(state)
        except Exception:
            pass  # storage failure must never break the workflow

    def start(self, state: PlatformState) -> PlatformState:
        state.workflow_running = True
        state.workflow_complete = False
        state.workflow_error = None
        self._thread = threading.Thread(
            target=self._run,
            args=(state,),
            daemon=True,
        )
        self._thread.start()
        return state

    def _run(self, state: PlatformState):
        deployment_done = False

        for step_id, agent in STEP_AGENTS:
            step_q = _StepQueue(self.log_queue, step_id)
            try:
                if step_id in DEPLOYMENT_STEPS:
                    # All 4 deployment steps are executed together when "bundle" is reached.
                    # Steps 11-13 (provision/deploy/validate) are skipped here — their
                    # statuses are already set to COMPLETED by the "bundle" handler.
                    if not deployment_done:
                        for ds in ["bundle", "provision", "deploy", "validate"]:
                            state.step_statuses[ds] = StepStatus.RUNNING
                            self.log_queue.put(StepStatusEvent(step_id=ds, status=StepStatus.RUNNING))

                        deploy_q = _StepQueue(self.log_queue, "bundle")
                        state = deployment_agent.run(state, deploy_q)
                        deployment_done = True

                        # Bundle completes; provision/deploy/validate remain RUNNING
                        # to simulate ongoing cloud infrastructure activity during the demo
                        state.step_statuses["bundle"] = StepStatus.COMPLETED
                        self.log_queue.put(StepStatusEvent(step_id="bundle", status=StepStatus.COMPLETED))
                        self._save(state)
                    continue

                state.step_statuses[step_id] = StepStatus.RUNNING
                self.log_queue.put(StepStatusEvent(step_id=step_id, status=StepStatus.RUNNING))

                if agent is not None:
                    state = agent.run(state, step_q)

                state.step_statuses[step_id] = StepStatus.COMPLETED
                self.log_queue.put(StepStatusEvent(step_id=step_id, status=StepStatus.COMPLETED))
                self._save(state)

            except Exception as e:
                error_msg = traceback.format_exc()
                state.step_statuses[step_id] = StepStatus.FAILED
                self.log_queue.put(StepStatusEvent(step_id=step_id, status=StepStatus.FAILED))
                step_q.put(make_log("System", f"ERROR: {str(e)}", "error"))
                step_q.put(make_log("System", error_msg[:1000], "error"))
                state.workflow_error = error_msg
                break

        state.workflow_running = False
        state.workflow_complete = True
        self._save(state)
        self.log_queue.put(make_log("System", "Workflow complete ✔", "success"))


_engine_instance: WorkflowEngine = None


def get_engine() -> WorkflowEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = WorkflowEngine()
    return _engine_instance


def reset_engine():
    global _engine_instance
    _engine_instance = WorkflowEngine()
    return _engine_instance
