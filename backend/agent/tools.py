import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from ..models import Document, Clause, Obligation, Task, Approval, AuditLog
from .sarvam_client import (
    analyze_document_with_sarvam,
    validate_obligation_with_sarvam,
    reassess_event_with_sarvam
)

def record_audit(db: Session, tool_name: str, input_summary: str, result: str, status: str = "success", obligation_id: str = None, task_id: str = None):
    audit = AuditLog(
        id=str(uuid.uuid4()),
        obligation_id=obligation_id,
        task_id=task_id,
        tool=tool_name,
        input_summary=input_summary,
        result=result,
        status=status,
        timestamp=datetime.utcnow()
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit

# Tool 1: extract_obligations
def extract_obligations(db: Session, document_id: str) -> List[Dict[str, Any]]:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document with id {document_id} not found.")

    raw_extractions = analyze_document_with_sarvam(doc.raw_text or "")
    created_obligations = []

    for item in raw_extractions:
        # Create or link clause
        clause = Clause(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            page=str(item.get("page", "1")),
            clause_title=item.get("clause_title", "Contractual Term"),
            clause_type=item.get("clause_type", "general"),
            text=item.get("verbatim_text", item.get("original_wording", "")),
            confidence=float(item.get("confidence", 0.95)),
            evidence_ref=item.get("evidence_ref", "Section 1")
        )
        db.add(clause)
        db.flush()

        # Create obligation
        obligation = Obligation(
            id=str(uuid.uuid4()),
            clause_id=clause.id,
            document_id=doc.id,
            title=item.get("obligation_title", "Contract Obligation"),
            original_wording=item.get("original_wording", clause.text),
            condition=item.get("condition", "Standard contractual fulfillment"),
            interpreted_deadline=item.get("interpreted_deadline"),
            status="identified",
            confidence=float(item.get("confidence", 0.95)),
            party_obligated=item.get("party_obligated", "Employee"),
            party_beneficiary=item.get("party_beneficiary", "Employer"),
            amount=item.get("amount"),
            currency=item.get("currency", "INR"),
            risk_level=item.get("risk_level", "medium"),
            metadata_json={"raw_extraction": item}
        )
        db.add(obligation)
        db.flush()
        created_obligations.append(obligation)

    doc.status = "processed"
    db.commit()

    record_audit(
        db,
        tool_name="extract_obligations",
        input_summary=f"Extracted from document '{doc.filename}' ({len(doc.raw_text or '')} chars)",
        result=f"Identified {len(created_obligations)} clauses and obligations using Sarvam AI"
    )
    return [ob.to_dict() for ob in created_obligations]

# Tool 2: validate_obligation
def validate_obligation(db: Session, obligation_id: str) -> Dict[str, Any]:
    ob = db.query(Obligation).filter(Obligation.id == obligation_id).first()
    if not ob:
        raise ValueError(f"Obligation {obligation_id} not found.")

    clause_text = ob.clause.text if ob.clause else ob.original_wording
    val_res = validate_obligation_with_sarvam(ob.to_dict(), clause_text)

    if val_res.get("is_valid", False):
        ob.status = "validated"
        ob.confidence = float(val_res.get("confidence", 0.98))
    else:
        ob.status = "uncertain"

    meta = ob.metadata_json or {}
    meta["validation"] = val_res
    ob.metadata_json = meta
    db.commit()

    record_audit(
        db,
        tool_name="validate_obligation",
        input_summary=f"Validated obligation: '{ob.title}'",
        result=f"Status: {ob.status}, Confidence: {ob.confidence:.2f}. Rationale: {val_res.get('explanation')}",
        obligation_id=ob.id
    )
    return ob.to_dict()

# Tool 3: create_reminder
def create_reminder(db: Session, obligation_id: str, due_date: Optional[str] = None) -> Dict[str, Any]:
    ob = db.query(Obligation).filter(Obligation.id == obligation_id).first()
    if not ob:
        raise ValueError(f"Obligation {obligation_id} not found.")

    calculated_due = due_date or ob.interpreted_deadline or "2026-11-15"
    task = Task(
        id=str(uuid.uuid4()),
        obligation_id=ob.id,
        due_at=str(calculated_due),
        action="schedule_reminder",
        status="ready",
        payload_json={
            "reminder_type": "obligation_milestone_check",
            "obligation_title": ob.title,
            "trigger_condition": ob.condition,
            "monitored_amount": ob.amount
        }
    )
    db.add(task)
    ob.status = "scheduled"
    db.commit()

    record_audit(
        db,
        tool_name="create_reminder",
        input_summary=f"Set monitoring schedule for '{ob.title}'",
        result=f"Created Task {task.id} with due target '{calculated_due}'",
        obligation_id=ob.id,
        task_id=task.id
    )
    return task.to_dict()

# Tool 4: get_due_obligations
def get_due_obligations(db: Session, user_id: str = "default_user", as_of_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
    # Retrieve active obligations needing attention
    query = db.query(Obligation).join(Document).filter(
        Document.user_id == user_id,
        Obligation.status.in_(["scheduled", "action_required", "awaiting_approval", "uncertain"])
    )
    results = query.all()
    record_audit(
        db,
        tool_name="get_due_obligations",
        input_summary=f"Query obligations for user '{user_id}'",
        result=f"Found {len(results)} active obligations in ledger"
    )
    return [r.to_dict() for r in results]

# Tool 5: compare_document_versions
def compare_document_versions(db: Session, doc_id_1: str, doc_id_2: str) -> Dict[str, Any]:
    doc1 = db.query(Document).filter(Document.id == doc_id_1).first()
    doc2 = db.query(Document).filter(Document.id == doc_id_2).first()
    if not doc1 or not doc2:
        raise ValueError("Both document versions must exist for comparison.")

    clauses1 = {c.clause_type: c.text for c in doc1.clauses}
    clauses2 = {c.clause_type: c.text for c in doc2.clauses}

    diffs = []
    all_keys = set(clauses1.keys()).union(set(clauses2.keys()))
    for k in all_keys:
        t1 = clauses1.get(k)
        t2 = clauses2.get(k)
        if t1 != t2:
            diffs.append({
                "clause_type": k,
                "version_1_text": t1,
                "version_2_text": t2,
                "change_detected": "modified" if (t1 and t2) else ("added" if t2 else "removed")
            })

    result = {
        "doc_id_1": doc_id_1,
        "doc_id_2": doc_id_2,
        "total_differences": len(diffs),
        "differences": diffs
    }

    record_audit(
        db,
        tool_name="compare_document_versions",
        input_summary=f"Compared {doc1.filename} v{doc1.version} against {doc2.filename} v{doc2.version}",
        result=f"Detected {len(diffs)} clause differences"
    )
    return result

# Tool 6: draft_followup
def draft_followup(db: Session, obligation_id: str, current_context: Dict[str, Any]) -> Dict[str, Any]:
    ob = db.query(Obligation).filter(Obligation.id == obligation_id).first()
    if not ob:
        raise ValueError(f"Obligation {obligation_id} not found.")

    subject = f"ACTION REQUIRED: {ob.title} - Formal Notice"
    deadline = current_context.get("repayment_deadline", ob.interpreted_deadline or "Within 30 Days")
    amount = current_context.get("liability_amount", ob.amount or "₹5,00,000")
    party = ob.party_obligated

    body = f"""Dear {party},

This official notice pertains to your employment agreement dated November 15, 2025 with TechNova Solutions Pvt Ltd.

As per Clause 4.2 ('Joining Bonus & Clawback Terms'):
"{ob.original_wording}"

Following receipt of your resignation notice on {current_context.get('resignation_date', 'October 24, 2026')}, your departure falls within the initial 12-month tenure period. Consequently, 100% of the sign-on bonus is subject to immediate recovery.

Total Repayment Due: {amount}
Settlement Due Date: {deadline}

Please arrange wire transfer to the corporate escrow account or coordinate with HR/Finance prior to your full and final settlement.

Sincerely,
People Operations & Legal Operations Team
TechNova Solutions Pvt Ltd"""

    draft = {
        "obligation_id": ob.id,
        "subject": subject,
        "recipient": party,
        "body": body,
        "amount_demanded": amount,
        "deadline": deadline,
        "clause_ref": ob.clause.evidence_ref if ob.clause else "Clause 4.2"
    }

    record_audit(
        db,
        tool_name="draft_followup",
        input_summary=f"Drafted legal recovery notice for obligation '{ob.title}'",
        result=f"Generated draft demand notice for {amount} due on {deadline}",
        obligation_id=ob.id
    )
    return draft

# Tool 7: request_approval
def request_approval(db: Session, task_id: str, proposed_action: str, rationale: str, consequences: str, clause_reference: str, assumptions: str) -> Dict[str, Any]:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"Task {task_id} not found.")

    approval = Approval(
        id=str(uuid.uuid4()),
        task_id=task.id,
        action_type="sensitive_legal_demand",
        proposed_action=proposed_action,
        rationale=rationale,
        consequences=consequences,
        clause_reference=clause_reference,
        assumptions=assumptions,
        decision="pending"
    )
    db.add(approval)
    task.status = "awaiting_approval"
    if task.obligation:
        task.obligation.status = "awaiting_approval"
    db.commit()

    record_audit(
        db,
        tool_name="request_approval",
        input_summary=f"Submitted human approval request for Task {task.id}",
        result=f"Approval ID {approval.id} created. Awaiting HR/Legal executive authorization.",
        obligation_id=task.obligation_id,
        task_id=task.id
    )
    return approval.to_dict()

# Tool 8: verify_action
def verify_action(db: Session, approval_id: str, decision: str, decided_by: str = "HR_Director") -> Dict[str, Any]:
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise ValueError(f"Approval {approval_id} not found.")

    approval.decision = decision
    approval.decided_at = datetime.utcnow()
    approval.decided_by = decided_by

    task = approval.task
    if decision == "approved":
        task.status = "completed"
        if task.obligation:
            task.obligation.status = "completed"
        audit_status = "verification_passed"
        audit_result = f"Action '{approval.proposed_action}' authorized by {decided_by}. Execution verified and obligation marked resolved."
    else:
        task.status = "rejected"
        if task.obligation:
            task.obligation.status = "action_required"
        audit_status = "rejected_by_human"
        audit_result = f"Action rejected by {decided_by}. Obligation remanded back to action_required for alternative resolution."

    db.commit()

    record_audit(
        db,
        tool_name="verify_action",
        input_summary=f"Decision '{decision}' recorded for Approval {approval_id}",
        result=audit_result,
        status=audit_status,
        obligation_id=task.obligation_id,
        task_id=task.id
    )

    return {
        "approval_id": approval.id,
        "decision": approval.decision,
        "task_status": task.status,
        "obligation_status": task.obligation.status if task.obligation else None,
        "verified": decision == "approved"
    }
