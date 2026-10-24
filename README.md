# ClauseWise — Persistent Event-Driven Contract Obligation Agent

> **Autonomous contract obligation monitoring, grounded clause reasoning, and event-driven workflow execution powered by Sarvam AI.**

ClauseWise is a persistent, event-driven contract obligation agent designed to understand legal documents, remember obligations, monitor future milestones, and execute follow-up workflows until each obligation is resolved.

---

## 🔄 Core Agent Loop

$$\text{Understand} \longrightarrow \text{Plan} \longrightarrow \text{Act} \longrightarrow \text{Verify} \longrightarrow \text{Monitor} \longrightarrow \text{Replan}$$

1. **Understand**: Sarvam Vision & Document AI parses contract text, identifies obligations, conditions, deadlines, monetary figures, and exact page/passage evidence.
2. **Plan**: Sarvam-105B checks that dates and conditions are valid, then deterministic tools schedule monitoring tasks.
3. **Act**: The agent executes deterministic tools (APScheduler timers, reminder dispatch, legal draft generator).
4. **Verify**: Confirms tool execution and state persistence in the relational ledger.
5. **Monitor**: Survives beyond the initial chat session, listening for approaching deadlines, calendar triggers, or incoming events.
6. **Replan**: Upon receiving a real-world event (e.g., an employee resignation or lease termination notice), Sarvam-105B reassesses active obligations, evaluates date math, drafts follow-ups, and routes sensitive actions to the **Human Authorization Inbox**.

---

## 🏗️ System Architecture

```
                                  +---------------------------------------------+
                                  |            React 18 Frontend UI             |
                                  |  Upload Studio · Risk Dashboard · Inbox     |
                                  +----------------------+----------------------+
                                                         |
                                                         v
                                  +---------------------------------------------+
                                  |              FastAPI Backend                |
                                  |     REST Endpoints · Event Ingestion        |
                                  +----------------------+----------------------+
                                                         |
                   +-------------------------------------+-------------------------------------+
                   |                                                                           |
                   v                                                                           v
+--------------------------------------+                                    +--------------------------------------+
|       State Machine Orchestrator     |                                    |       APScheduler Background Engine  |
|  Understand -> Plan -> Act -> Replan |                                    |      Persistent Deadline Monitoring  |
+------------------+-------------------+                                    +------------------+-------------------+
                   |                                                                           |
                   v                                                                           v
+--------------------------------------+                                    +--------------------------------------+
|      Sarvam AI Reasoning Engine      |                                    |        Persistent Relational Ledger  |
|   Sarvam-105B & Document AI          |                                    |   Documents · Clauses · Obligations  |
|   Clawback Reassessment & Drafting   |                                    |   Tasks · Events · Approvals · Audits|
+--------------------------------------+                                    +--------------------------------------+
```

- **Frontend**: React 18 Single-Page Application with glassmorphic dark design system, Risk Dashboard, Obligation Ledger, and Human Authorization Inbox.
- **Backend API**: Python + FastAPI serving REST endpoints, document upload, and event ingestion.
- **Reasoning Engine**: **Sarvam-105B** for grounded clause extraction, audit validation, and event reassessment.
- **Persistence**: SQLite (production-ready PostgreSQL compatibility via SQLAlchemy).
- **Background Scheduler**: APScheduler background monitor for persistent task monitoring.

---

## 🛠️ The 8 Typed Deterministic Tools

| Tool | Input | Output | Purpose |
| :--- | :--- | :--- | :--- |
| `extract_obligations` | Document text & page refs | Structured obligations | Identifies clauses and grounded obligations with Sarvam AI |
| `validate_obligation` | Obligation & supporting clause | Validated / Uncertain | Audits whether obligation terms are supported by source text |
| `create_reminder` | Obligation ID & due date | Reminder ID & scheduled time | Schedules persistent timer in background engine |
| `get_due_obligations` | User ID & as-of time | Pending active obligations | Retrieves active items requiring attention |
| `compare_document_versions`| Two document IDs | Changed clauses & evidence | Audits contract amendments and revisions |
| `draft_followup` | Obligation & context | Legal draft notice & rationale | Drafts formal demand communications |
| `request_approval` | Action, consequences, assumptions| Approval request ID | Enforces human-in-the-loop authorization for sensitive actions |
| `verify_action` | Approval ID & decision | Verification status & audit log| Confirms execution and transitions obligation to completed |

---

## 🚀 End-to-End Walkthrough Flow

Using the bundled **Executive Employment Agreement (*Aarav Sharma — Lead Distributed Systems Architect*)**:

1. **Upload Contract**:
   - Agent ingests agreement containing Clause 4.2:
     > *"Employee receives INR 5,00,000 joining bonus. If employee resigns within 12 months (on or before November 14, 2026), 100% must be repaid within 30 days of notice."*
   - Status moves: `identified` $\to$ `validated` $\to$ `scheduled`.

2. **Trigger Real-World Event**:
   - External event arrives: Employee submits resignation on **October 24, 2026** (tenure: 11.3 months).
   - Agent awakens, loads affected obligations, and passes context to Sarvam-105B.

3. **Sarvam-105B Reassessment**:
   - Evaluates tenure math: $11.3 \text{ months} < 12 \text{ months}$ threshold.
   - Triggers 100% clawback liability: **₹5,00,000**.
   - Calculates hard settlement deadline: **November 23, 2026** (30 calendar days).
   - Generates formal Bonus Repayment Demand Notice.
   - Detects external/financial action $\to$ queues into **Approval Inbox**.

4. **Human Authorization & Audit**:
   - Executive inspects rationale, evidence citation, and generated draft in the **Approval Inbox**.
   - Clicks **Approve & Execute** $\to$ `verify_action` confirms execution, resolves obligation to `completed`, and records tamper-evident log in the **Audit Trail**.

---

## ⚡ Quickstart

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/rndastech/ClauseWise.git
cd ClauseWise
pip install fastapi uvicorn sarvamai sqlalchemy apscheduler python-dotenv pydantic pymupdf python-multipart
```

### 2. Configure Environment
Create a `.env` file in the root directory:
```env
SARVAM_API_KEY=your_sarvam_api_key_here
```

### 3. Run the Application
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser at **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.
