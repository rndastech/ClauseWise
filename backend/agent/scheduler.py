import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
from ..database import SessionLocal
from ..models import Task, Obligation, AuditLog

logger = logging.getLogger("clausewise.scheduler")
scheduler = BackgroundScheduler()

def check_pending_obligations_job():
    """Periodic job running in the background to monitor scheduled obligations."""
    db = SessionLocal()
    try:
        now_str = datetime.utcnow().strftime("%Y-%m-%d")
        tasks = db.query(Task).filter(Task.status == "ready").all()
        for t in tasks:
            if t.due_at and t.due_at <= now_str:
                logger.info(f"Task {t.id} due reached ({t.due_at}). Updating to action_required.")
                t.status = "action_required"
                if t.obligation:
                    t.obligation.status = "action_required"
                
                # Log audit
                audit = AuditLog(
                    obligation_id=t.obligation_id,
                    task_id=t.id,
                    tool="apscheduler_monitor",
                    input_summary=f"Automated check at {now_str}",
                    result=f"Obligation reached scheduled deadline ({t.due_at}). Marked action_required.",
                    status="success"
                )
                db.add(audit)
        db.commit()
    except Exception as e:
        logger.error(f"Error in scheduler check: {e}")
        db.rollback()
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            check_pending_obligations_job,
            'interval',
            seconds=30,
            id='check_obligations_timer',
            replace_existing=True
        )
        scheduler.start()
        logger.info("APScheduler background engine started successfully.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler background engine stopped.")
