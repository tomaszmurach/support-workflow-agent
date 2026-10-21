from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="AI Support Workflow Agent")


class HealthResponse(BaseModel):
    status: Literal["ok"]


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
