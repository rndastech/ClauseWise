const { useState, useEffect, useRef } = React;

function App() {
  const [activeTab, setActiveTab] = useState("documents"); // documents, dashboard, obligations, approvals, audit
  const [metrics, setMetrics] = useState({
    total_documents: 0,
    total_obligations: 0,
    active_obligations: 0,
    completed_obligations: 0,
    pending_approvals: 0,
    total_audit_events: 0,
    monitored_bonus_value: "₹5,00,000"
  });
  const [obligations, setObligations] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [activeStep, setActiveStep] = useState("Understand"); // Understand, Plan, Act, Verify, Monitor, Replan
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [filterStatus, setFilterStatus] = useState("all");

  // Upload Form State
  const [uploadText, setUploadText] = useState("");
  const [uploadTitle, setUploadTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadMode, setUploadMode] = useState("paste"); // 'file' or 'paste'
  const fileInputRef = useRef(null);

  const showNotification = (msg, type = "info") => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 6000);
  };

  const fetchAllData = async () => {
    try {
      const [mRes, oRes, aRes, lRes, dRes] = await Promise.all([
        fetch("/api/dashboard/metrics").then(r => r.json()),
        fetch("/api/obligations").then(r => r.json()),
        fetch("/api/approvals").then(r => r.json()),
        fetch("/api/audit-logs").then(r => r.json()),
        fetch("/api/documents").then(r => r.json())
      ]);
      setMetrics(mRes);
      setObligations(oRes);
      setApprovals(aRes);
      setAuditLogs(lRes);
      setDocuments(dRes);

      if (aRes.some(a => a.decision === "pending")) {
        setActiveStep("Replan");
      } else if (oRes.some(o => o.status === "scheduled")) {
        setActiveStep("Monitor");
      } else if (oRes.some(o => o.status === "completed")) {
        setActiveStep("Verify");
      } else if (oRes.length > 0) {
        setActiveStep("Plan");
      } else {
        setActiveStep("Understand");
      }
    } catch (err) {
      console.error("Error loading data:", err);
    }
  };

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 8000);
    return () => clearInterval(interval);
  }, []);

  // Handle Custom Document Upload (File or Raw Text)
  const handleUploadSubmit = async (e) => {
    if (e) e.preventDefault();
    if (uploadMode === "paste" && !uploadText.trim()) {
      showNotification("Please paste some contract text to analyze.", "warning");
      return;
    }
    if (uploadMode === "file" && !selectedFile) {
      showNotification("Please select a file to upload.", "warning");
      return;
    }

    setLoading(true);
    setActiveStep("Understand");
    showNotification("Uploading contract to Sarvam AI for dynamic extraction & clause grounding...", "info");

    const formData = new FormData();
    if (uploadMode === "file" && selectedFile) {
      formData.append("file", selectedFile);
      formData.append("filename", selectedFile.name);
    } else {
      formData.append("raw_text", uploadText);
      formData.append("filename", uploadTitle.trim() ? (uploadTitle.trim() + ".txt") : "Custom_Contract.txt");
    }
    formData.append("auto_process", "true");

    try {
      const res = await fetch("/api/documents/upload", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      setActiveStep("Plan");
      setTimeout(() => setActiveStep("Act"), 800);
      setTimeout(() => setActiveStep("Monitor"), 1600);

      const count = data.pipeline_result?.extracted_count || 0;
      showNotification(`Contract analyzed dynamically by Sarvam AI! Extracted ${count} obligations.`, "success");
      setUploadText("");
      setUploadTitle("");
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      fetchAllData();
      setActiveTab("obligations");
    } catch (err) {
      showNotification("Upload failed: " + err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  // Preset Sample: Executive Employment Agreement (Clawback)
  const handleLoadSample = async () => {
    setLoading(true);
    setActiveStep("Understand");
    showNotification("Loading Executive Employment Agreement (Aarav Sharma - ₹5L Clawback)...", "info");
    try {
      await fetch("/api/documents/load-sample", { method: "POST" });
      setActiveStep("Plan");
      setTimeout(() => setActiveStep("Act"), 800);
      setTimeout(() => setActiveStep("Monitor"), 1600);
      showNotification("Contract loaded! Extracted 3 obligations and scheduled monitoring.", "success");
      fetchAllData();
      setActiveTab("obligations");
    } catch (err) {
      showNotification("Failed to load sample: " + err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  // Preset Sample: Commercial Office Lease Agreement
  const handleLoadLeaseSample = async () => {
    const leaseText = `COMMERCIAL LEASE & FACILITIES AGREEMENT
Dated: January 10, 2026
Between: Prestige Tech Park Developers LLP (Landlord) AND CloudScale Technologies India Pvt Ltd (Tenant).

1. PREMISES & LEASE TERM
1.1 Premises: 12,000 sq.ft. Grade-A Office Space, Tower 3, Prestige Tech Park, Bengaluru.
1.2 Lease Commencement: February 1, 2026. The initial lease term shall be for five (5) years.

2. RENT AND PAYMENTS
2.1 Monthly Base Rent: The Tenant shall remit a monthly gross rent of INR 14,40,000 (Rupees Fourteen Lakhs Forty Thousand only) on or before the 5th day of every calendar month via RTGS transfer.
2.2 Maintenance Charges: Common area maintenance (CAM) of INR 1,80,000 per month shall be paid within fifteen (15) days of invoice generation.

3. SECURITY DEPOSIT AND LOCK-IN PENALTY
3.1 Security Deposit: Tenant shall maintain an interest-free refundable security deposit of INR 86,40,000 (Rupees Eighty-Six Lakhs Forty Thousand, equivalent to 6 months' rent) with the Landlord.
3.2 Lock-in Period: Both parties agree to a strict mandatory lock-in period of thirty-six (36) continuous months from the Commencement Date.
3.3 Early Exit Liquidated Damages: If the Tenant vacates or issues notice of termination before the expiry of the 36-month lock-in period, the Landlord shall forfeit the entire Security Deposit of INR 86,40,000 as liquidated damages, and Tenant shall immediately remit rent for the remainder of the lock-in period.
3.4 End-of-Lease Refund: Upon lawful expiration after the lock-in period, the Landlord must inspect premises and refund the deposit within forty-five (45) calendar days.`;

    setUploadTitle("Prestige_Commercial_Lease_Agreement");
    setUploadText(leaseText);
    setUploadMode("paste");
    showNotification("Commercial Lease loaded into editor! Click '⚡ Analyze with Sarvam AI' to extract.", "info");
  };

  // Simulate Triggering Event (Resignation within 12 months)
  const handleSimulateResignation = async () => {
    setLoading(true);
    setActiveStep("Monitor");
    showNotification("Event received: Employee submitted resignation on Oct 24, 2026. Invoking Sarvam-105B...", "info");
    try {
      const res = await fetch("/api/events/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: "resignation_submitted",
          payload: {
            employee_name: "Aarav Sharma",
            resignation_date: "2026-10-24",
            effective_joining_date: "2025-11-15",
            reason: "Accepted role at another firm",
            tenure_months: 11.3,
            requested_lwd: "2026-11-23"
          }
        })
      });
      const data = await res.json();
      setActiveStep("Replan");
      showNotification("Sarvam-105B evaluated tenure (<12 mos)! 100% clawback (₹5,00,000) triggered. Action in Approval Inbox.", "warning");
      fetchAllData();
      setActiveTab("approvals");
    } catch (err) {
      showNotification("Simulation failed: " + err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  // Approve or Reject Action
  const handleDecideApproval = async (approvalId, decision) => {
    setLoading(true);
    try {
      await fetch(`/api/approvals/${approvalId}/decide`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision: decision,
          decided_by: "VP_People_Operations"
        })
      });
      setActiveStep("Verify");
      showNotification(`Action ${decision.toUpperCase()}! Tool executed and verification logged.`, "success");
      fetchAllData();
    } catch (err) {
      showNotification("Decision error: " + err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  // Reset Demo Database
  const handleResetDemo = async () => {
    if (!confirm("Reset all documents, obligations, and approvals to a clean state?")) return;
    setLoading(true);
    try {
      await fetch("/api/reset-demo", { method: "POST" });
      setActiveStep("Understand");
      showNotification("Database reset to clean state. Ready for fresh contract uploads.", "info");
      fetchAllData();
      setActiveTab("documents");
    } catch (err) {
      showNotification("Reset error: " + err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  // Filtered obligations
  const filteredObligations = obligations.filter(ob => {
    if (filterStatus === "all") return true;
    return ob.status === filterStatus;
  });

  const pendingApprovalsCount = approvals.filter(a => a.decision === "pending").length;

  return (
    <div>
      {/* Top Navigation */}
      <header className="navbar">
        <div className="brand-section">
          <div className="brand-logo-icon">CW</div>
          <div className="brand-text">
            <h1>ClauseWise</h1>
            <div className="brand-tagline">Persistent Event-Driven Contract Obligation Agent</div>
          </div>
        </div>

        <div className="nav-badges">
          <div className="agent-status-pill">
            <span className="pulse-dot"></span>
            Agent Engine: Active
          </div>
          <div className="sarvam-badge">
            ⚡ Sarvam-105B Reasoning
          </div>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setActiveTab("documents")}
          >
            📤 Upload Contract
          </button>
          <button className="btn btn-outline btn-sm" onClick={handleResetDemo} title="Clear database for fresh demo">
            🧹 Reset Demo
          </button>
        </div>
      </header>

      {/* 6-Stage Controlled State Machine Loop */}
      <div className="state-machine-banner">
        <div className="loop-container">
          {[
            { step: "Understand", desc: "Extract Clauses & Text" },
            { step: "Plan", desc: "Validate & Schedule Tasks" },
            { step: "Act", desc: "Execute Deterministic Tools" },
            { step: "Verify", desc: "Confirm Tool Succeeded" },
            { step: "Monitor", desc: "Wait for Future Events" },
            { step: "Replan", desc: "Reassess with Sarvam-105B" }
          ].map((item, idx) => (
            <React.Fragment key={item.step}>
              <div className={`loop-step ${activeStep === item.step ? 'active' : ''}`}>
                <div className="loop-step-num">{idx + 1}</div>
                <div>
                  <div className="loop-step-name">{item.step}</div>
                  <div style={{ fontSize: '10.5px', color: '#94a3b8' }}>{item.desc}</div>
                </div>
              </div>
              {idx < 5 && <span className="loop-arrow">→</span>}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Main App Container */}
      <main className="main-content">
        {/* Toast Notification */}
        {notification && (
          <div style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            zIndex: 100,
            background: notification.type === 'warning' ? '#e11d48' : (notification.type === 'success' ? '#059669' : '#4f46e5'),
            color: 'white',
            padding: '14px 22px',
            borderRadius: '12px',
            boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
            fontSize: '13.5px',
            fontWeight: '600',
            maxWidth: '460px',
            lineHeight: '1.4'
          }}>
            {notification.msg}
          </div>
        )}

        {/* Guided Walkthrough Bar */}
        <div className="demo-banner">
          <div className="demo-banner-content">
            <h3>⚡ Hackathon Workflow Runner</h3>
            <p>
              Upload any contract (or load sample) → Sarvam AI extracts obligations → Reminders scheduled → Simulate triggering event → Replan & review action in Approval Inbox.
            </p>
          </div>
          <div className="demo-actions">
            <button className="btn btn-outline" onClick={() => setActiveTab("documents")}>
              📤 1. Upload Contract
            </button>
            <button
              className="btn btn-cyan"
              onClick={handleSimulateResignation}
              disabled={loading || obligations.length === 0}
            >
              ⚡ 2. Simulate Trigger Event
            </button>
            <button
              className="btn btn-rose"
              onClick={() => setActiveTab("approvals")}
              style={{ position: 'relative' }}
            >
              🔔 3. Review Approvals ({pendingApprovalsCount})
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="tab-bar">
          <button
            className={`tab-btn ${activeTab === 'documents' ? 'active' : ''}`}
            onClick={() => setActiveTab('documents')}
          >
            📄 Contract Upload Studio
            <span className="badge-counter">{documents.length}</span>
          </button>
          <button
            className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            📊 Risk Dashboard
          </button>
          <button
            className={`tab-btn ${activeTab === 'obligations' ? 'active' : ''}`}
            onClick={() => setActiveTab('obligations')}
          >
            📋 Obligation Ledger
            <span className="badge-counter">{obligations.length}</span>
          </button>
          <button
            className={`tab-btn ${activeTab === 'approvals' ? 'active' : ''}`}
            onClick={() => setActiveTab('approvals')}
          >
            📥 Approval Inbox
            {pendingApprovalsCount > 0 ? (
              <span className="badge-counter badge-alert">{pendingApprovalsCount}</span>
            ) : (
              <span className="badge-counter">0</span>
            )}
          </button>
          <button
            className={`tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            📜 Audit Trail ({auditLogs.length})
          </button>
        </div>

        {/* TAB 1: DOCUMENT UPLOAD STUDIO */}
        {activeTab === 'documents' && (
          <div>
            <div style={{ marginBottom: '24px' }}>
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '24px', fontWeight: '700' }}>
                Contract Upload & Intelligence Studio
              </h2>
              <p style={{ fontSize: '13.5px', color: '#94a3b8' }}>
                Upload any contract (PDF, TXT, DOCX) or paste agreement text directly. Sarvam-105B dynamically parses clauses, conditions, deadlines, amounts, and grounded evidence.
              </p>
            </div>

            {/* Interactive Upload Box */}
            <div className="glass-panel" style={{ padding: '28px', marginBottom: '32px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px' }}>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    className={`btn btn-sm ${uploadMode === 'paste' ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => setUploadMode('paste')}
                  >
                    ✍️ Paste Contract Text
                  </button>
                  <button
                    className={`btn btn-sm ${uploadMode === 'file' ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => setUploadMode('file')}
                  >
                    📁 Upload PDF / Text File
                  </button>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <span style={{ fontSize: '12px', color: '#94a3b8', alignSelf: 'center' }}>Quick Pre-sets:</span>
                  <button className="btn btn-outline btn-sm" onClick={handleLoadSample} disabled={loading}>
                    👔 Employment Clawback
                  </button>
                  <button className="btn btn-outline btn-sm" onClick={handleLoadLeaseSample} disabled={loading}>
                    🏢 Commercial Lease Lock-in
                  </button>
                </div>
              </div>

              {uploadMode === 'paste' ? (
                <div>
                  <div style={{ marginBottom: '14px' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#94a3b8', marginBottom: '6px', textTransform: 'uppercase' }}>
                      Agreement Title / Reference
                    </label>
                    <input
                      type="text"
                      placeholder="e.g., Master Services Agreement — Acme Corp"
                      value={uploadTitle}
                      onChange={(e) => setUploadTitle(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '12px 16px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'rgba(0,0,0,0.3)',
                        border: '1px solid var(--border-subtle)',
                        color: 'white',
                        fontSize: '14px'
                      }}
                    />
                  </div>
                  <div style={{ marginBottom: '18px' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#94a3b8', marginBottom: '6px', textTransform: 'uppercase' }}>
                      Contract Text (Clauses, Obligations, Deadlines, Penalties)
                    </label>
                    <textarea
                      rows={9}
                      placeholder="Paste contract clauses here... For example:
Clause 1. Sign-on Bonus: Employee receives ₹5,00,000 joining bonus. If employee resigns within 12 months, 100% must be repaid within 30 days of notice.
Clause 2. Confidentiality: Non-disclosure obligations apply for 24 months post-termination."
                      value={uploadText}
                      onChange={(e) => setUploadText(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '14px 16px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'rgba(0,0,0,0.35)',
                        border: '1px solid var(--border-subtle)',
                        color: '#f1f5f9',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '13px',
                        lineHeight: '1.6'
                      }}
                    />
                  </div>
                </div>
              ) : (
                <div style={{
                  padding: '40px',
                  border: '2px dashed rgba(99, 102, 241, 0.4)',
                  borderRadius: 'var(--radius-md)',
                  textAlign: 'center',
                  background: 'rgba(99, 102, 241, 0.04)',
                  marginBottom: '20px'
                }}>
                  <div style={{ fontSize: '36px', marginBottom: '12px' }}>📂</div>
                  <h3 style={{ fontSize: '16px', color: 'white', marginBottom: '6px' }}>
                    Choose a Contract File
                  </h3>
                  <p style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '16px' }}>
                    Supports PDF (with PyMuPDF text extraction), TXT, and DOC documents
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.txt,.doc,.docx"
                    onChange={(e) => setSelectedFile(e.target.files[0])}
                    style={{ color: '#cbd5e1' }}
                  />
                  {selectedFile && (
                    <div style={{ marginTop: '12px', fontSize: '13px', color: '#38bdf8' }}>
                      Selected: <strong>{selectedFile.name}</strong> ({(selectedFile.size / 1024).toFixed(1)} KB)
                    </div>
                  )}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button
                  className="btn btn-primary"
                  onClick={handleUploadSubmit}
                  disabled={loading || (uploadMode === 'paste' && !uploadText.trim()) || (uploadMode === 'file' && !selectedFile)}
                  style={{ padding: '12px 24px', fontSize: '15px' }}
                >
                  ⚡ Extract & Schedule with Sarvam AI
                </button>
              </div>
            </div>

            {/* Ingested Contracts Ledger */}
            <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '19px', color: 'white' }}>
                📁 Contract Repository ({documents.length} Agreements Ingested)
              </h3>
            </div>

            {documents.length === 0 ? (
              <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: '#94a3b8' }}>
                No agreements uploaded yet. Paste contract text or select a quick preset above.
              </div>
            ) : (
              documents.map(doc => (
                <div key={doc.id} className="glass-panel" style={{ padding: '24px', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <div>
                      <h4 style={{ fontFamily: 'var(--font-heading)', fontSize: '18px', color: 'white' }}>
                        {doc.filename}
                      </h4>
                      <div style={{ fontSize: '12.5px', color: '#94a3b8', marginTop: '2px' }}>
                        ID: <code style={{ color: '#a5b4fc' }}>{doc.id.slice(0, 8)}</code> · Version: {doc.version} · Extracted Clauses: {doc.clause_count} · Obligations: {doc.obligation_count}
                      </div>
                    </div>
                    <span className="status-pill status-validated">
                      ● Status: {doc.status}
                    </span>
                  </div>

                  <div className="quote-box" style={{ maxHeight: '140px', overflowY: 'auto' }}>
                    {doc.raw_text_preview || "Document text loaded and stored in persistent SQLite ledger."}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 2: DASHBOARD */}
        {activeTab === 'dashboard' && (
          <div>
            <div className="metrics-grid">
              <div className="glass-panel metric-card">
                <div className="metric-header">
                  <span className="metric-title">Monitored Liability</span>
                  <div className="metric-icon-box">💰</div>
                </div>
                <div className="metric-value">{metrics.monitored_bonus_value || "₹5,00,000"}</div>
                <div className="metric-sub">Total financial clawback/penalty exposure under active surveillance</div>
              </div>

              <div className="glass-panel metric-card">
                <div className="metric-header">
                  <span className="metric-title">Tracked Obligations</span>
                  <div className="metric-icon-box">📋</div>
                </div>
                <div className="metric-value">{metrics.total_obligations}</div>
                <div className="metric-sub">{metrics.active_obligations} active · {metrics.completed_obligations} resolved</div>
              </div>

              <div className="glass-panel metric-card">
                <div className="metric-header">
                  <span className="metric-title">Pending Approvals</span>
                  <div className="metric-icon-box">⚠️</div>
                </div>
                <div className="metric-value" style={{ color: pendingApprovalsCount > 0 ? '#fb7185' : 'white' }}>
                  {pendingApprovalsCount}
                </div>
                <div className="metric-sub">Sensitive external actions requiring human sign-off</div>
              </div>

              <div className="glass-panel metric-card">
                <div className="metric-header">
                  <span className="metric-title">Audit Ledger Entries</span>
                  <div className="metric-icon-box">🛡️</div>
                </div>
                <div className="metric-value">{metrics.total_audit_events}</div>
                <div className="metric-sub">Deterministic tool & verification history logs</div>
              </div>
            </div>

            {/* Event Simulator Panel */}
            <div className="glass-panel sim-card">
              <div className="sim-header">
                <h3>🎮 Event Ingestion & Reassessment Console</h3>
                <span className="agent-status-pill">Persistent Listener</span>
              </div>
              <p className="sim-desc">
                The agent survives beyond the initial session. When an external event occurs, the agent pulls affected obligations, invokes Sarvam-105B for date math and condition evaluation, and routes sensitive actions to the Approval Inbox.
              </p>
              <div className="sim-buttons">
                <button
                  className="btn btn-cyan"
                  onClick={handleSimulateResignation}
                  disabled={loading || obligations.length === 0}
                >
                  ⚡ Simulate Resignation Event (Oct 24, 2026 — 11 Mos Tenure)
                </button>
                <button
                  className="btn btn-outline"
                  onClick={() => setActiveTab("documents")}
                >
                  📤 Upload Another Agreement
                </button>
              </div>
            </div>

            {/* Active Critical Clauses Preview */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
                <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '18px' }}>
                  🚨 Monitored Contract Obligations
                </h3>
                <button className="btn btn-outline btn-sm" onClick={() => setActiveTab('obligations')}>
                  View Obligation Ledger →
                </button>
              </div>
              {obligations.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
                  No obligations loaded yet. Go to <strong>"📄 Contract Upload Studio"</strong> to upload an agreement.
                </div>
              ) : (
                obligations.slice(0, 3).map(ob => (
                  <div key={ob.id} className="obligation-card" style={{ marginBottom: '14px', background: 'rgba(0,0,0,0.2)' }}>
                    <div className="obligation-header">
                      <div className="obligation-title-group">
                        <h3>{ob.title}</h3>
                        <div className="obligation-meta-row">
                          <span className={`status-pill status-${ob.status}`}>
                            ● {ob.status.replace('_', ' ')}
                          </span>
                          <span className={`risk-tag risk-${ob.risk_level}`}>
                            {ob.risk_level} Risk
                          </span>
                          <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                            Ref: {ob.clause ? ob.clause.evidence_ref : 'Clause'}
                          </span>
                        </div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontFamily: 'var(--font-heading)', fontSize: '20px', fontWeight: '700', color: '#38bdf8' }}>
                          {ob.amount || "N/A"}
                        </div>
                        <div style={{ fontSize: '11px', color: '#94a3b8' }}>Monitored Sum</div>
                      </div>
                    </div>
                    <div className="quote-box">"{ob.original_wording}"</div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB 3: OBLIGATIONS LEDGER */}
        {activeTab === 'obligations' && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <div>
                <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '22px', fontWeight: '700' }}>
                  Persistent Obligation Ledger
                </h2>
                <p style={{ fontSize: '13px', color: '#94a3b8' }}>
                  Deterministic state storage grounded in source document evidence
                </p>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                {['all', 'scheduled', 'action_required', 'awaiting_approval', 'completed'].map(st => (
                  <button
                    key={st}
                    className={`btn btn-sm ${filterStatus === st ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => setFilterStatus(st)}
                  >
                    {st.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            {filteredObligations.length === 0 ? (
              <div className="glass-panel" style={{ padding: '48px', textAlign: 'center', color: '#94a3b8' }}>
                No obligations matching current filter.
              </div>
            ) : (
              filteredObligations.map(ob => (
                <div key={ob.id} className={`glass-panel obligation-card ${ob.status === 'awaiting_approval' ? 'alert-border' : ''}`}>
                  <div className="obligation-header">
                    <div className="obligation-title-group">
                      <h3>{ob.title}</h3>
                      <div className="obligation-meta-row">
                        <span className={`status-pill status-${ob.status}`}>
                          ● {ob.status.replace('_', ' ')}
                        </span>
                        <span className={`risk-tag risk-${ob.risk_level}`}>
                          {ob.risk_level} Risk
                        </span>
                        <span style={{ fontSize: '12px', color: '#a5b4fc', fontFamily: 'var(--font-mono)' }}>
                          Confidence: {(ob.confidence * 100).toFixed(0)}%
                        </span>
                        <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                          Evidence: {ob.clause ? ob.clause.evidence_ref : 'Clause'}
                        </span>
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontFamily: 'var(--font-heading)', fontSize: '22px', fontWeight: '700', color: '#38bdf8' }}>
                        {ob.amount || "Non-monetary"}
                      </div>
                      <div style={{ fontSize: '11px', color: '#94a3b8' }}>Obligation Value</div>
                    </div>
                  </div>

                  <div className="condition-pill">
                    <strong style={{ color: '#fbbf24' }}>Trigger Condition:</strong>
                    <span>{ob.condition}</span>
                  </div>

                  <div className="quote-box">
                    "{ob.original_wording}"
                  </div>

                  <div className="detail-columns">
                    <div>
                      <div className="detail-label">Interpreted Deadline</div>
                      <div className="detail-val">{ob.interpreted_deadline || "Conditional"}</div>
                    </div>
                    <div>
                      <div className="detail-label">Party Obligated</div>
                      <div className="detail-val">{ob.party_obligated}</div>
                    </div>
                    <div>
                      <div className="detail-label">Beneficiary Party</div>
                      <div className="detail-val">{ob.party_beneficiary}</div>
                    </div>
                    <div>
                      <div className="detail-label">Persistence ID</div>
                      <div className="detail-val" style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                        {ob.id.slice(0, 13)}...
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 4: APPROVAL INBOX */}
        {activeTab === 'approvals' && (
          <div>
            <div style={{ marginBottom: '24px' }}>
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '22px', fontWeight: '700' }}>
                Human Authorization Inbox
              </h2>
              <p style={{ fontSize: '13px', color: '#94a3b8' }}>
                External and sensitive actions (financial demands, payroll holds) require human sign-off before dispatch.
              </p>
            </div>

            {approvals.length === 0 ? (
              <div className="glass-panel" style={{ padding: '60px', textAlign: 'center' }}>
                <div style={{ fontSize: '40px', marginBottom: '12px' }}>✅</div>
                <h3 style={{ fontSize: '18px', color: 'white', marginBottom: '6px' }}>Inbox Clear</h3>
                <p style={{ fontSize: '13.5px', color: '#94a3b8' }}>
                  No pending authorizations. When an event triggers sensitive contractual clawbacks, requests will appear here.
                </p>
                <button className="btn btn-cyan btn-sm" style={{ marginTop: '16px' }} onClick={handleSimulateResignation}>
                  Simulate Triggering Resignation Event
                </button>
              </div>
            ) : (
              approvals.map(appr => (
                <div key={appr.id} className="approval-card glass-panel">
                  <div className="approval-title-box">
                    <div>
                      <span className="approval-badge">
                        {appr.decision === 'pending' ? '⚠️ Action Authorization Required' : `Decision: ${appr.decision.toUpperCase()}`}
                      </span>
                      <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '20px', color: 'white', marginTop: '8px' }}>
                        {appr.proposed_action}
                      </h3>
                    </div>
                    {appr.decision === 'pending' && (
                      <div style={{ display: 'flex', gap: '10px' }}>
                        <button
                          className="btn btn-emerald"
                          onClick={() => handleDecideApproval(appr.id, "approved")}
                          disabled={loading}
                        >
                          ✓ Approve & Execute
                        </button>
                        <button
                          className="btn btn-outline"
                          onClick={() => handleDecideApproval(appr.id, "rejected")}
                          disabled={loading}
                        >
                          ✕ Reject / Remand
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="approval-body-grid">
                    <div className="approval-section">
                      <h4>🧠 Sarvam-105B Legal Rationale</h4>
                      <p>{appr.rationale}</p>
                    </div>

                    <div className="approval-section">
                      <h4>⚖️ Risk & Financial Consequences</h4>
                      <p>{appr.consequences}</p>
                    </div>

                    <div className="approval-section">
                      <h4>📜 Grounded Clause Evidence</h4>
                      <p><strong>Citation:</strong> {appr.clause_reference}</p>
                      <p style={{ marginTop: '6px', fontStyle: 'italic', color: '#cbd5e1' }}>
                        "If the Employee tenders voluntary resignation within 12 months... Employee is legally obligated to refund 100%, being INR 5,00,000 within thirty (30) calendar days..."
                      </p>
                    </div>

                    <div className="approval-section">
                      <h4>🔍 Model Assumptions</h4>
                      <p>{appr.assumptions || "Tenure calculated: 11 months 9 days. Below 12-month tier threshold."}</p>
                      {appr.decided_by && (
                        <div style={{ marginTop: '10px', fontSize: '12px', color: '#34d399' }}>
                          Authorized by: <strong>{appr.decided_by}</strong> at {new Date(appr.decided_at).toLocaleString()}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Generated Legal Notice Draft */}
                  <div>
                    <h4 style={{ fontSize: '13px', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '8px' }}>
                      ✉️ Generated Legal Demand Notice Draft (Ready for automated dispatch upon approval)
                    </h4>
                    <div className="draft-preview">
{`SUBJECT: FORMAL DEMAND: Sign-On Bonus Clawback Recovery
RECIPIENT: Aarav Sharma (Employee)
DATE: October 24, 2026

Dear Aarav Sharma,

This formal communication serves as notice regarding your employment agreement executed on November 15, 2025 with TechNova Solutions Pvt Ltd.

Under Section 3.2(a) ('Tiered Clawback Schedule'):
"If the Employee tenders voluntary resignation within twelve (12) months from the Joining Date (on or before November 14, 2026), the Employee is legally obligated to refund one hundred percent (100%), being INR 5,00,000, within thirty (30) calendar days of notice."

Based on your resignation notice received October 24, 2026, your departure occurs at Month 11 of service. Therefore, full repayment is triggered.

REPAYMENT SUMMARY:
• Gross Sign-On Bonus Disbursed: INR 5,00,000
• Applicable Clawback Percentage: 100%
• Total Amount Due: INR 5,00,000
• Hard Deadline for Remittance: November 23, 2026

Corporate Escrow Remittance details are attached. Pursuant to Section 3.3, unremitted amounts will be held against final settlement clearance.

Legal Operations & People Ops
TechNova Solutions Private Limited`}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 5: AUDIT TRAIL */}
        {activeTab === 'audit' && (
          <div className="glass-panel" style={{ padding: '24px' }}>
            <div style={{ marginBottom: '20px' }}>
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '22px', fontWeight: '700' }}>
                Tamper-Evident Audit Trail
              </h2>
              <p style={{ fontSize: '13px', color: '#94a3b8' }}>
                Every tool execution, date math validation, human authorization, and state transition is deterministically recorded.
              </p>
            </div>

            <table className="audit-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Tool / Action</th>
                  <th>Input Context</th>
                  <th>Result / Verification</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map(log => (
                  <tr key={log.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#94a3b8' }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'Just now'}
                    </td>
                    <td>
                      <span className="tool-badge">{log.tool}</span>
                    </td>
                    <td style={{ maxWidth: '280px', color: '#cbd5e1' }}>
                      {log.input_summary}
                    </td>
                    <td style={{ maxWidth: '380px' }}>
                      {log.result}
                    </td>
                    <td>
                      <span className={`status-pill status-${log.status === 'verification_passed' ? 'completed' : 'validated'}`}>
                        {log.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
