"""
FastAPI REST API Server for Kaplan Meier Estimator.
"""
from typing import Dict, Any, List
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from kaplan_meier import kaplan_meier, log_rank_test
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Kaplan Meier Estimator API",
    description="Survival analysis API with legacy demonstration audit endpoints",
    version="3.0.0",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "kaplan-meier-estimator", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}


class SurvivalRequest(BaseModel):
    times: List[float]
    events: List[int]


class LogRankRequest(BaseModel):
    times1: List[float]
    events1: List[int]
    times2: List[float]
    events2: List[int]


@app.post("/api/kaplan-meier")
def api_kaplan_meier(request: SurvivalRequest):
    """Compute product-limit survival estimates from numerical observations."""
    try:
        return kaplan_meier(request.times, request.events)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/log-rank")
def api_log_rank(request: LogRankRequest):
    """Compare two independent groups using the log-rank test."""
    try:
        return log_rank_test(request.times1, request.events1, request.times2, request.events2)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# Static front end is also served by FastAPI when running from a checkout or Docker.
_web_dir = Path(__file__).resolve().parent.parent / "web"
if _web_dir.is_dir():
    app.mount("/", StaticFiles(directory=_web_dir, html=True), name="browser-app")
