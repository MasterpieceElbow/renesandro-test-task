from pydantic import BaseModel


class LogSchema(BaseModel):
    task_name: str
    timestamp: float
    total_time: float | None = None
    level: str
    message: str
    details: dict | None = None
    error_details: str | None = None
