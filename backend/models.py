import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from .database import Base

def gen_id():
    return str(uuid.uuid4())

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=gen_id)
    user_id = Column(String(64), default="default_user", index=True)
    filename = Column(String(255), nullable=False)
    doc_type = Column(String(64), default="employment_agreement")
    version = Column(String(32), default="1.0")
    status = Column(String(32), default="uploaded")  # uploaded, processed, error
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    clauses = relationship("Clause", back_populates="document", cascade="all, delete-orphan")
    obligations = relationship("Obligation", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "doc_type": self.doc_type,
            "version": self.version,
            "status": self.status,
            "raw_text_preview": (self.raw_text[:200] + "...") if self.raw_text else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "clause_count": len(self.clauses) if self.clauses else 0,
            "obligation_count": len(self.obligations) if self.obligations else 0
        }

class Clause(Base):
    __tablename__ = "clauses"

    id = Column(String(36), primary_key=True, default=gen_id)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    page = Column(String(32), default="1")
    clause_title = Column(String(255), nullable=True)
    clause_type = Column(String(64), nullable=False)  # clawback, non_compete, confidentiality, payment, etc.
    text = Column(Text, nullable=False)
    confidence = Column(Float, default=0.95)
    evidence_ref = Column(String(255), nullable=True)  # Section or paragraph tag
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="clauses")
    obligations = relationship("Obligation", back_populates="clause")

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "page": self.page,
            "clause_title": self.clause_title,
            "clause_type": self.clause_type,
            "text": self.text,
            "confidence": self.confidence,
            "evidence_ref": self.evidence_ref,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Obligation(Base):
    __tablename__ = "obligations"

    id = Column(String(36), primary_key=True, default=gen_id)
    clause_id = Column(String(36), ForeignKey("clauses.id"), nullable=True, index=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    original_wording = Column(Text, nullable=False)  # Exact contractual quote
    condition = Column(Text, nullable=False)          # Trigger condition
    interpreted_deadline = Column(String(128), nullable=True)  # Computed or conditional deadline
    
    # Statuses: identified, validated, scheduled, action_required, awaiting_approval, completed, uncertain, cancelled, overdue
    status = Column(String(32), default="identified", index=True)
    confidence = Column(Float, default=0.90)
    
    party_obligated = Column(String(128), default="Employee")
    party_beneficiary = Column(String(128), default="Employer")
    amount = Column(String(64), nullable=True)       # e.g., "₹5,00,000"
    currency = Column(String(16), default="INR")
    risk_level = Column(String(16), default="medium") # low, medium, high
    metadata_json = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    clause = relationship("Clause", back_populates="obligations")
    document = relationship("Document", back_populates="obligations")
    tasks = relationship("Task", back_populates="obligation", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "clause_id": self.clause_id,
            "document_id": self.document_id,
            "title": self.title,
            "original_wording": self.original_wording,
            "condition": self.condition,
            "interpreted_deadline": self.interpreted_deadline,
            "status": self.status,
            "confidence": self.confidence,
            "party_obligated": self.party_obligated,
            "party_beneficiary": self.party_beneficiary,
            "amount": self.amount,
            "currency": self.currency,
            "risk_level": self.risk_level,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "clause": self.clause.to_dict() if self.clause else None
        }

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=gen_id)
    obligation_id = Column(String(36), ForeignKey("obligations.id"), nullable=False, index=True)
    due_at = Column(String(64), nullable=True)
    action = Column(String(128), nullable=False)     # e.g., "schedule_reminder", "draft_demand_notice", "request_clawback_approval"
    status = Column(String(32), default="pending")   # pending, ready, awaiting_approval, completed, failed
    payload_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    obligation = relationship("Obligation", back_populates="tasks")
    approvals = relationship("Approval", back_populates="task", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "obligation_id": self.obligation_id,
            "due_at": self.due_at,
            "action": self.action,
            "status": self.status,
            "payload_json": self.payload_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "approvals": [a.to_dict() for a in self.approvals] if self.approvals else []
        }

class Event(Base):
    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=gen_id)
    event_type = Column(String(64), nullable=False, index=True) # e.g. "resignation_submitted", "amendment_uploaded", "date_advance"
    payload_json = Column(JSON, default=dict)
    processed = Column(String(16), default="false") # "true", "false", "failed"
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "event_type": self.event_type,
            "payload_json": self.payload_json or {},
            "processed": self.processed,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True, default=gen_id)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    action_type = Column(String(64), nullable=False) # e.g., "send_recovery_notice", "payroll_deduction"
    proposed_action = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)
    consequences = Column(Text, nullable=True)
    clause_reference = Column(Text, nullable=True)
    assumptions = Column(Text, nullable=True)
    decision = Column(String(32), default="pending") # pending, approved, rejected
    decided_at = Column(DateTime, nullable=True)
    decided_by = Column(String(64), nullable=True)

    task = relationship("Task", back_populates="approvals")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "action_type": self.action_type,
            "proposed_action": self.proposed_action,
            "rationale": self.rationale,
            "consequences": self.consequences,
            "clause_reference": self.clause_reference,
            "assumptions": self.assumptions,
            "decision": self.decision,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "decided_by": self.decided_by
        }

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=gen_id)
    obligation_id = Column(String(36), nullable=True, index=True)
    task_id = Column(String(36), nullable=True, index=True)
    tool = Column(String(64), nullable=False)
    input_summary = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    status = Column(String(32), default="success") # success, failed, verification_passed
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "obligation_id": self.obligation_id,
            "task_id": self.task_id,
            "tool": self.tool,
            "input_summary": self.input_summary,
            "result": self.result,
            "status": self.status,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
