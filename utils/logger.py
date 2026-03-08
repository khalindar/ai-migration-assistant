from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class LogEvent(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    source: str  # "AI" | "Terraform" | "Docker" | "Kubernetes" | "System"
    message: str
    level: str = "info"  # "info" | "success" | "warning" | "error"
    step_id: Optional[str] = None


class StepStatusEvent(BaseModel):
    step_id: str
    status: str  # "RUNNING" | "COMPLETED" | "FAILED"


def make_log(source: str, message: str, level: str = "info") -> LogEvent:
    return LogEvent(source=source, message=message, level=level)


SOURCE_ICONS = {
    "AI": "🤖",
    "Terraform": "🏗️",
    "Docker": "🐳",
    "Kubernetes": "☸️",
    "System": "⚙️",
}

LEVEL_COLORS = {
    "info": "#a0aec0",
    "success": "#68d391",
    "warning": "#f6e05e",
    "error": "#fc8181",
}
