import os
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

from .database import engine, Base, get_db
from .models import Document, Clause, Obligation, Task, Event, Approval, AuditLog
from .agent.orchestrator import ClauseWiseOrchestrator
from .agent.scheduler import start_scheduler, shutdown_scheduler
from .agent.tools import record_audit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clausewise.api")

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: start background scheduler
    start_scheduler()
    logger.info("ClauseWise backend engine initialized.")
    yield
    # Shutdown: stop scheduler
    shutdown_scheduler()
    logger.info("ClauseWise backend engine shut down.")

app = FastAPI(
    title="ClauseWise Contract Obligation Agent",
    description="Persistent, event-driven contract obligation agent powered by Sarvam AI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_contracts")
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

# Health Check
@app.get("/api/health")
def health_check():
    api_key_set = bool(os.environ.get("SARVAM_API_KEY"))
    return {
        "status": "healthy",
        "agent": "ClauseWise Persistent Event-Driven Agent",
        "sarvam_ai_connected": api_key_set,
        "scheduler": "APScheduler active",
        "database": "SQLite persistent ledger"
    }

# Dashboard Metrics
@app.get("/api/dashboard/metrics")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    total_docs = db.query(Document).count()
    obligations = db.query(Obligation).all()
    pending_approvals = db.query(Approval).filter(Approval.decision == "pending").count()
    total_audit_events = db.query(AuditLog).count()

    status_counts = {}
    risk_counts = {"high": 0, "medium": 0, "low": 0}
    for ob in obligations:
        status_counts[ob.status] = status_counts.get(ob.status, 0) + 1
        r = ob.risk_level or "medium"
        risk_counts[r] = risk_counts.get(r, 0) + 1

    return {
        "total_documents": total_docs,
        "total_obligations": len(obligations),
        "active_obligations": len([o for o in obligations if o.status in ["scheduled", "action_required", "awaiting_approval"]]),
        "completed_obligations": len([o for o in obligations if o.status == "completed"]),
        "pending_approvals": pending_approvals,
        "total_audit_events": total_audit_events,
        "status_distribution": status_counts,
        "risk_distribution": risk_counts,
        "monitored_bonus_value": "₹5,00,000"
    }

# Documents
@app.get("/api/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [d.to_dict() for d in docs]

@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    res = doc.to_dict()
    res["clauses"] = [c.to_dict() for c in doc.clauses]
    res["obligations"] = [o.to_dict() for o in doc.obligations]
    return res

@app.post("/api/documents/upload")
async def upload_document(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    filename: Optional[str] = Form(None),
    auto_process: bool = Form(True),
    db: Session = Depends(get_db)
):
    content = ""
    resolved_filename = filename or "document.txt"

    if file:
        resolved_filename = file.filename
        bytes_data = await file.read()
        try:
            content = bytes_data.decode("utf-8")
        except UnicodeDecodeError:
            # Handle PDF extraction if uploaded as pdf
            try:
                import fitz
                pdf_doc = fitz.open(stream=bytes_data, filetype="pdf")
                pages_text = [page.get_text() for page in pdf_doc]
                content = "\n\n".join(pages_text)
            except Exception as e:
                content = f"[Extracted document content: {resolved_filename}]"
    elif raw_text:
        content = raw_text

    doc = Document(
        id=str(uuid.uuid4()),
        filename=resolved_filename,
        raw_text=content,
        status="uploaded"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    if auto_process:
        process_res = ClauseWiseOrchestrator.process_new_document(db, doc.id)
        return {
            "document": doc.to_dict(),
            "pipeline_result": process_res
        }

    return {"document": doc.to_dict()}

@app.post("/api/documents/load-sample")
def load_sample_document(db: Session = Depends(get_db)):
    sample_path = os.path.join(SAMPLE_DIR, "employment_bonus_agreement.txt")
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Sample contract file missing.")

    with open(sample_path, "r", encoding="utf-8") as f:
        text = f.read()

    doc = Document(
        id=str(uuid.uuid4()),
        filename="Executive_Employment_Agreement_AaravSharma.txt",
        raw_text=text,
        status="uploaded"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Run orchestrator pipeline
    pipeline_res = ClauseWiseOrchestrator.process_new_document(db, doc.id)
    return {
        "message": "Sample employment agreement loaded and processed into persistent ledger.",
        "document": doc.to_dict(),
        "pipeline_result": pipeline_res
    }

# Obligations
@app.get("/api/obligations")
def list_obligations(
    status: Optional[str] = Query(None),
    risk: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Obligation)
    if status and status != "all":
        query = query.filter(Obligation.status == status)
    if risk and risk != "all":
        query = query.filter(Obligation.risk_level == risk)
    obs = query.order_by(Obligation.created_at.desc()).all()
    return [o.to_dict() for o in obs]

@app.get("/api/obligations/{ob_id}")
def get_obligation(ob_id: str, db: Session = Depends(get_db)):
    ob = db.query(Obligation).filter(Obligation.id == ob_id).first()
    if not ob:
        raise HTTPException(status_code=404, detail="Obligation not found")
    data = ob.to_dict()
    data["tasks"] = [t.to_dict() for t in ob.tasks]
    return data

# Events & Simulation
@app.post("/api/events/simulate")
def simulate_event(
    event_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Simulate a future event: e.g. resignation notice, milestone, or amendment.
    Triggers: Retrieve affected obligations -> Sarvam-105B reassessment -> Prepare Action -> Approval Inbox
    """
    event_type = event_data.get("event_type", "resignation_submitted")
    payload = event_data.get("payload", {
        "employee_name": "Aarav Sharma",
        "resignation_date": "2026-10-24",
        "effective_joining_date": "2025-11-15",
        "reason": "Found alternative career opportunity",
        "requested_last_working_day": "2026-11-23"
    })

    result = ClauseWiseOrchestrator.handle_event(db, event_type, payload)
    return result

@app.get("/api/events")
def list_events(db: Session = Depends(get_db)):
    events = db.query(Event).order_by(Event.created_at.desc()).all()
    return [e.to_dict() for e in events]

# Approvals (Human-in-the-loop)
@app.get("/api/approvals")
def list_approvals(db: Session = Depends(get_db)):
    approvals = db.query(Approval).order_by(Approval.id.desc()).all()
    return [a.to_dict() for a in approvals]

@app.post("/api/approvals/{approval_id}/decide")
def decide_approval(
    approval_id: str,
    decision_payload: Dict[str, str],
    db: Session = Depends(get_db)
):
    decision = decision_payload.get("decision", "approved")
    decided_by = decision_payload.get("decided_by", "VP_HR_Director")
    result = ClauseWiseOrchestrator.approve_and_execute(
        db,
        approval_id=approval_id,
        decision=decision,
        decided_by=decided_by
    )
    return result

# Audit Logs
@app.get("/api/audit-logs")
def list_audit_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [l.to_dict() for l in logs]

# Reset Demo
@app.post("/api/reset-demo")
def reset_demo(db: Session = Depends(get_db)):
    db.query(AuditLog).delete()
    db.query(Approval).delete()
    db.query(Task).delete()
    db.query(Event).delete()
    db.query(Obligation).delete()
    db.query(Clause).delete()
    db.query(Document).delete()
    db.commit()
    record_audit(db, "system_reset", "Database reset for clean demo run", "All ledger tables initialized", "success")
    return {"message": "Demo database successfully reset to clean state."}

# Serve frontend static assets if available
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({
        "message": "ClauseWise Backend is running. Please access frontend.",
        "docs_url": "/docs"
    })
