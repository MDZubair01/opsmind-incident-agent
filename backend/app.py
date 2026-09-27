from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os

# Ensure backend directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import diagnose_incident, retain_incident_resolution

app = FastAPI(title="OpsMind Incident Agent API", version="1.0.0")

class IncidentRequest(BaseModel):
    service_name: str
    error_message: str
    stack_trace: str

class PostMortemRequest(BaseModel):
    service_name: str
    error_message: str
    root_cause: str
    fix_applied: str
    runbook_cmd: str

@app.get("/")
def health_check():
    return {"status": "ok", "service": "OpsMind Agent API"}

@app.post("/triage")
def triage_incident(req: IncidentRequest):
    try:
        result = diagnose_incident(
            service_name=req.service_name,
            error_message=req.error_message,
            stack_trace=req.stack_trace
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resolve")
def resolve_incident(req: PostMortemRequest):
    try:
        res = retain_incident_resolution(
            service_name=req.service_name,
            error_message=req.error_message,
            root_cause=req.root_cause,
            fix_applied=req.fix_applied,
            runbook_cmd=req.runbook_cmd
        )
        return {"status": "retained", "response": str(res)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))