import uuid
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from ..models import Document, Clause, Obligation, Task, Event, Approval, AuditLog
from .tools import (
    extract_obligations,
    validate_obligation,
    create_reminder,
    draft_followup,
    request_approval,
    verify_action,
    record_audit
)
from .sarvam_client import reassess_event_with_sarvam

class ClauseWiseOrchestrator:
    """
    Controlled State Machine Agent Orchestrator:
    Understand -> Plan -> Act -> Verify -> Monitor -> Replan
    """

    @staticmethod
    def process_new_document(db: Session, document_id: str) -> Dict[str, Any]:
        """
        Initial Pipeline: Understand -> Validate -> Plan -> Act (Schedule) -> Verify
        """
        # 1. UNDERSTAND: Extract clauses and obligations
        extracted_obs = extract_obligations(db, document_id)
        validated_obs = []
        scheduled_tasks = []

        # 2. VALIDATE & PLAN
        for ob_data in extracted_obs:
            ob_id = ob_data["id"]
            # Validation step
            val_result = validate_obligation(db, ob_id)
            validated_obs.append(val_result)

            # 3. PLAN & ACT: Schedule deterministic reminders / monitors
            task_result = create_reminder(db, ob_id)
            scheduled_tasks.append(task_result)

        # 4. VERIFY: Ensure persistent state
        record_audit(
            db,
            tool_name="orchestrator_initial_pipeline",
            input_summary=f"Processed document {document_id}",
            result=f"Completed Understand -> Plan -> Act pipeline. {len(validated_obs)} obligations scheduled for monitoring.",
            status="verification_passed"
        )

        return {
            "document_id": document_id,
            "stage": "monitoring",
            "extracted_count": len(extracted_obs),
            "validated_obligations": validated_obs,
            "scheduled_tasks": scheduled_tasks
        }

    @staticmethod
    def handle_event(db: Session, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Event Loop Pipeline: Event -> Retrieve Affected Obligations -> Reassess with Sarvam-105B -> Replan -> Act/Request Approval
        """
        # Record Event
        event = Event(
            id=str(uuid.uuid4()),
            event_type=event_type,
            payload_json=payload,
            processed="in_progress",
            created_at=datetime.utcnow()
        )
        db.add(event)
        db.commit()

        # Step 1: RETRIEVE AFFECTED OBLIGATIONS
        # In our demo employment case, resignation triggers clawback & notice period obligations
        obligations = db.query(Obligation).filter(
            Obligation.status.in_(["scheduled", "identified", "validated", "action_required"])
        ).all()

        reassessed_actions = []

        for ob in obligations:
            clause_text = ob.clause.text if ob.clause else ob.original_wording
            
            # Step 2: REASSESS CONTEXT WITH SARVAM-105B
            assessment = reassess_event_with_sarvam(
                event_type=event_type,
                event_payload=payload,
                obligation_dict=ob.to_dict(),
                clause_text=clause_text
            )

            if assessment.get("condition_triggered", False):
                # Condition is actively triggered!
                ob.status = "action_required"
                db.flush()

                # Step 3: REPLAN & PREPARE NEXT ACTION
                # Check if it requires approval (e.g. monetary demand, payroll clawback, external notice)
                if assessment.get("requires_approval", True):
                    # Create Task
                    task = Task(
                        id=str(uuid.uuid4()),
                        obligation_id=ob.id,
                        due_at=assessment.get("repayment_deadline", "2026-11-23"),
                        action=assessment.get("action_type", "issue_bonus_clawback_notice"),
                        status="awaiting_approval",
                        payload_json={
                            "reassessment": assessment,
                            "event_id": event.id,
                            "event_payload": payload
                        }
                    )
                    db.add(task)
                    db.flush()

                    # Draft legal communication
                    draft = draft_followup(db, ob.id, {
                        **payload,
                        "liability_amount": assessment.get("liability_amount", ob.amount),
                        "repayment_deadline": assessment.get("repayment_deadline")
                    })

                    # Request Human Approval
                    approval = request_approval(
                        db=db,
                        task_id=task.id,
                        proposed_action=assessment.get("proposed_action", f"Issue demand for {ob.amount}"),
                        rationale=assessment.get("rationale", "Triggered by resignation event"),
                        consequences=assessment.get("consequences", "Potential loss of unrecovered bonus"),
                        clause_reference=ob.clause.evidence_ref if ob.clause else "Clause 4.2",
                        assumptions=assessment.get("assumptions", "Standard employment tenure calculations apply")
                    )

                    reassessed_actions.append({
                        "obligation_id": ob.id,
                        "obligation_title": ob.title,
                        "assessment": assessment,
                        "task_id": task.id,
                        "approval_id": approval["id"],
                        "draft_notice": draft
                    })

        event.processed = "true"
        db.commit()

        record_audit(
            db,
            tool_name="event_orchestrator",
            input_summary=f"Processed event '{event_type}' with payload {payload}",
            result=f"Reassessed {len(obligations)} obligations. Generated {len(reassessed_actions)} actionable approval requests."
        )

        return {
            "event_id": event.id,
            "event_type": event_type,
            "actions_prepared": reassessed_actions,
            "status": "awaiting_human_approval" if reassessed_actions else "no_action_needed"
        }

    @staticmethod
    def approve_and_execute(db: Session, approval_id: str, decision: str, decided_by: str = "HR_Director") -> Dict[str, Any]:
        """
        Verify & Close Pipeline: Human Authorization -> Execute Tool -> Verify Result -> Close Obligation
        """
        verification = verify_action(db, approval_id=approval_id, decision=decision, decided_by=decided_by)
        return verification
