// Automatically adapt API calls to work under subpaths (e.g. /correos/ or root /)
const _origFetch = window.fetch;
window.fetch = function(url, options) {
    if (typeof url === 'string' && url.startsWith('/api')) {
        const pathPrefix = window.location.pathname.replace(/\/$/, '');
        if (pathPrefix && pathPrefix !== '') {
            url = pathPrefix + url;
        }
    }
    return _origFetch.call(this, url, options);
};

let allEmails = [];
let currentSelectedEmailId = null;
let currentSelectedCaseId = null;
let currentUser = null;
let currentToken = null;
let currentResolveCaseId = null;
let currentRejectCaseId = null;

document.addEventListener("DOMContentLoaded", () => {
    if (initAuth()) {
        loadAllData();
    }

    // Auto refresh every 10 seconds
    setInterval(() => {
        if (currentUser) {
            loadStats();
            loadMyCases();
            loadCases();
            loadStoppedCases();
            loadBottlenecks();
        }
    }, 10000);
});

function initAuth() {
    const userStr = localStorage.getItem("ips_user");
    const token = localStorage.getItem("ips_token");
    if (!userStr || !token) {
        showLoginModal();
        return false;
    }
    try {
        currentUser = JSON.parse(userStr);
        currentToken = token;
        renderUserBadge();
        applyRolePermissions();
        return true;
    } catch (e) {
        showLoginModal();
        return false;
    }
}

function showLoginModal() {
    const modal = document.getElementById("login-modal");
    if (modal) modal.classList.remove("hidden");
}

function hideLoginModal() {
    const modal = document.getElementById("login-modal");
    if (modal) modal.classList.add("hidden");
}

function renderUserBadge() {
    if (!currentUser) return;
    const nameEl = document.getElementById("user-display-name");
    const roleEl = document.getElementById("user-display-role");
    const stageEl = document.getElementById("user-display-stage");
    const initialsEl = document.getElementById("user-avatar-initials");

    if (nameEl) nameEl.innerText = currentUser.full_name || currentUser.username;
    if (roleEl) {
        roleEl.innerText = currentUser.role;
        roleEl.className = currentUser.role === "ADMIN" 
            ? "text-[9px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 font-bold"
            : "text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 font-bold";
    }
    if (stageEl) stageEl.innerText = currentUser.assigned_stage || "Área General";
    if (initialsEl) {
        const parts = (currentUser.full_name || currentUser.username).split(" ");
        initialsEl.innerText = parts.length > 1 ? (parts[0][0] + parts[1][0]).toUpperCase() : parts[0].slice(0, 2).toUpperCase();
    }
}

function applyRolePermissions() {
    if (!currentUser) return;
    const adminElements = document.querySelectorAll(".admin-only");
    if (currentUser.role === "ADMIN") {
        adminElements.forEach(el => el.classList.remove("hidden"));
    } else {
        adminElements.forEach(el => el.classList.add("hidden"));
        switchTab("mycases");
    }
}

async function handleLoginSubmit(e) {
    e.preventDefault();
    const uname = document.getElementById("login-username").value.trim();
    const pwd = document.getElementById("login-password").value;
    const alertEl = document.getElementById("login-error-alert");
    const textEl = document.getElementById("login-error-text");

    if (alertEl) alertEl.classList.add("hidden");

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: uname, password: pwd })
        });
        const data = await res.json();
        if (res.ok) {
            currentUser = data.user;
            currentToken = data.token;
            localStorage.setItem("ips_user", JSON.stringify(currentUser));
            localStorage.setItem("ips_token", currentToken);
            hideLoginModal();
            renderUserBadge();
            applyRolePermissions();
            loadAllData();
        } else {
            if (alertEl) {
                alertEl.classList.remove("hidden");
                textEl.innerText = data.detail || "Credenciales inválidas.";
            }
        }
    } catch (err) {
        if (alertEl) {
            alertEl.classList.remove("hidden");
            textEl.innerText = "Error al conectar con el servidor.";
        }
    }
}

function quickLogin(username, password) {
    document.getElementById("login-username").value = username;
    document.getElementById("login-password").value = password;
    const form = document.querySelector("#login-modal form");
    if (form) form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
}

async function doLogout() {
    try {
        await fetch("/api/auth/logout", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: currentToken })
        });
    } catch (e) {}
    localStorage.removeItem("ips_user");
    localStorage.removeItem("ips_token");
    currentUser = null;
    currentToken = null;
    showLoginModal();
}

function loadAllData() {
    loadStats();
    loadMyCases();
    loadCases();
    loadStoppedCases();
    loadBottlenecks();
    if (currentUser && currentUser.role === "ADMIN") {
        loadUsers();
        loadEmails();
        loadSenders();
        loadRules();
        loadLogs();
    }
}

async function loadStats() {
    try {
        const res = await fetch("/api/stats");
        const data = await res.json();

        document.getElementById("stat-total").innerText = data.total_received || 0;
        document.getElementById("stat-replied").innerText = data.auto_replied || 0;
        document.getElementById("stat-info").innerText = data.info_relevant || 0;
        document.getElementById("stat-review").innerText = data.pending_review || 0;
        document.getElementById("stat-urgent").innerText = data.urgent || 0;
        document.getElementById("stat-attach").innerText = data.with_attachments || 0;

        document.getElementById("badge-review-count").innerText = data.pending_review || 0;

        // Toggle mode buttons
        const btnAuto = document.getElementById("btn-mode-auto");
        const btnSup = document.getElementById("btn-mode-supervised");

        if (data.mode === "automatic") {
            btnAuto.className = "px-3 py-1 text-xs rounded-md font-semibold transition-all bg-indigo-600 text-white shadow-sm";
            btnSup.className = "px-3 py-1 text-xs rounded-md font-semibold transition-all text-slate-400 hover:text-slate-200";
        } else {
            btnSup.className = "px-3 py-1 text-xs rounded-md font-semibold transition-all bg-amber-600 text-white shadow-sm";
            btnAuto.className = "px-3 py-1 text-xs rounded-md font-semibold transition-all text-slate-400 hover:text-slate-200";
        }
    } catch (e) {
        console.error("Error loading stats:", e);
    }
}

async function loadEmails() {
    try {
        const res = await fetch("/api/emails");
        allEmails = await res.json();
        renderEmailTable(allEmails);
        renderReviewTable(allEmails.filter(e => e.requires_human_review && e.status === "PENDIENTE"));
    } catch (e) {
        console.error("Error loading emails:", e);
    }
}

function renderEmailTable(emails) {
    const tbody = document.getElementById("emails-table-body");
    tbody.innerHTML = "";

    if (emails.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-500">No hay correos registrados.</td></tr>`;
        return;
    }

    emails.forEach(msg => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-700/40 transition-colors border-b border-slate-700/40";

        // Priority Badge
        let prioBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-700 text-slate-300">MEDIA</span>`;
        if (msg.priority === "CRITICA") prioBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">🔴 CRITICA</span>`;
        else if (msg.priority === "ALTA") prioBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-500/20 text-orange-400 border border-orange-500/30">🟠 ALTA</span>`;
        else if (msg.priority === "BAJA") prioBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">🟢 BAJA</span>`;

        // Tags
        const tagsHtml = (msg.tags || []).map(t => `<span class="px-1.5 py-0.5 rounded bg-slate-900 text-slate-300 text-[10px] mr-1 border border-slate-700">${t}</span>`).join("");

        // Status Badge
        let statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-300">Pendiente</span>`;
        if (msg.status === "RESPONDIDO_IA") statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-300">🤖 Respondido IA</span>`;
        else if (msg.status === "REVISADO_HUMANO") statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/20 text-blue-300">👤 Revisado Humano</span>`;

        tr.innerHTML = `
            <td class="p-3">
                <div class="font-bold text-white">${msg.sender_name || msg.sender_email}</div>
                <div class="text-[11px] text-slate-400">${msg.company ? msg.company + " | " : ""}${msg.sender_email}</div>
            </td>
            <td class="p-3">
                <div class="font-semibold text-slate-200">${msg.subject}</div>
                <div class="text-[11px] text-slate-400 truncate max-w-xs">${msg.snippet}</div>
            </td>
            <td class="p-3">
                <div class="font-bold text-indigo-400 mb-1">${msg.category}</div>
                <div>${tagsHtml}</div>
            </td>
            <td class="p-3">${prioBadge}</td>
            <td class="p-3 text-center font-bold ${msg.confidence >= 90 ? 'text-emerald-400' : 'text-amber-400'}">${msg.confidence}%</td>
            <td class="p-3">${statusBadge}</td>
            <td class="p-3 text-right">
                <button onclick="openEmailModal('${msg.id}')" class="bg-indigo-600/80 hover:bg-indigo-600 text-white px-3 py-1 rounded text-xs font-medium transition-all">
                    Ver / Detalles
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderReviewTable(reviewEmails) {
    const tbody = document.getElementById("review-table-body");
    tbody.innerHTML = "";

    if (reviewEmails.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-500">No hay correos pendientes de revisión humana.</td></tr>`;
        return;
    }

    reviewEmails.forEach(msg => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-700/40 border-b border-slate-700/40";
        tr.innerHTML = `
            <td class="p-3">
                <div class="font-bold text-white">${msg.sender_name}</div>
                <div class="text-slate-400">${msg.sender_email}</div>
            </td>
            <td class="p-3">
                <div class="font-semibold text-slate-200">${msg.subject}</div>
                <div class="text-slate-400 italic">${msg.intent_summary}</div>
            </td>
            <td class="p-3 text-rose-400 font-medium">
                ${(msg.risk_reasons || []).join(", ") || "Alto riesgo/Supervisión requerida"}
            </td>
            <td class="p-3 font-bold">${msg.priority}</td>
            <td class="p-3 text-amber-400 font-bold">${msg.confidence}%</td>
            <td class="p-3 text-right">
                <button onclick="openEmailModal('${msg.id}')" class="bg-amber-600 hover:bg-amber-500 text-white px-3 py-1.5 rounded text-xs font-bold transition-all shadow-sm">
                    Review & Reply
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function openEmailModal(msgId) {
    currentSelectedEmailId = msgId;
    try {
        const res = await fetch(`/api/emails/${msgId}`);
        const msg = await res.json();

        document.getElementById("modal-subject").innerText = msg.subject;
        document.getElementById("modal-sender").innerText = `De: ${msg.sender_name} <${msg.sender_email}> ${msg.company ? '('+msg.company+')' : ''}`;
        document.getElementById("modal-category").innerText = msg.category;
        document.getElementById("modal-priority").innerText = msg.priority;
        document.getElementById("modal-confidence").innerText = `${msg.confidence}%`;
        document.getElementById("modal-risk").innerText = msg.risk_level;
        document.getElementById("modal-intent").innerText = msg.intent_summary || "Sin resumen";
        document.getElementById("modal-body").innerText = msg.body;
        document.getElementById("modal-draft-reply").value = msg.draft_reply || "";

        document.getElementById("email-modal").classList.remove("hidden");
    } catch (e) {
        console.error("Error opening detail modal:", e);
    }
}

function closeEmailModal() {
    document.getElementById("email-modal").classList.add("hidden");
    currentSelectedEmailId = null;
}

async function submitApproveReply() {
    if (!currentSelectedEmailId) return;
    const replyText = document.getElementById("modal-draft-reply").value;

    try {
        const res = await fetch(`/api/emails/${currentSelectedEmailId}/approve-reply`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ reply_text: replyText })
        });
        const data = await res.json();
        if (res.ok) {
            alert("Respuesta enviada exitosamente.");
            closeEmailModal();
            loadStats();
            loadEmails();
        } else {
            alert("Error: " + data.detail);
        }
    } catch (e) {
        alert("Error de conexión al enviar.");
    }
}

async function setMode(mode) {
    try {
        await fetch("/api/config/mode", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode: mode })
        });
        loadStats();
    } catch (e) {
        console.error("Error setting mode:", e);
    }
}

async function triggerSync() {
    try {
        await fetch("/api/trigger-sync", { method: "POST" });
        alert("Sincronización iniciada en segundo plano.");
        setTimeout(() => {
            loadStats();
            loadEmails();
        }, 1500);
    } catch (e) {
        console.error("Error syncing:", e);
    }
}

async function loadSenders() {
    try {
        const res = await fetch("/api/senders");
        const senders = await res.json();
        const tbody = document.getElementById("senders-table-body");
        tbody.innerHTML = "";

        senders.forEach(s => {
            const tr = document.createElement("tr");
            tr.className = "hover:bg-slate-700/40 border-b border-slate-700/40";
            tr.innerHTML = `
                <td class="p-3 font-bold text-white">${s.name || s.email} <div class="text-slate-400 font-normal">${s.email}</div></td>
                <td class="p-3 text-slate-300">${s.company || "-"}</td>
                <td class="p-3 text-slate-300">${(s.frequent_topics || []).join(", ") || "-"}</td>
                <td class="p-3 font-bold text-indigo-400">${s.total_emails}</td>
                <td class="p-3 text-slate-400">${s.last_interaction ? new Date(s.last_interaction).toLocaleString() : "-"}</td>
                <td class="p-3 font-semibold">${s.priority}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error loading senders:", e);
    }
}

async function loadRules() {
    try {
        const res = await fetch("/api/rules");
        const rules = await res.json();
        const container = document.getElementById("rules-list-container");
        container.innerHTML = "";

        if (rules.length === 0) {
            container.innerHTML = `<p class="text-slate-500 text-xs">No hay reglas personalizadas activas.</p>`;
            return;
        }

        rules.forEach(r => {
            const div = document.createElement("div");
            div.className = "bg-slate-900/80 p-3 rounded-lg border border-slate-700 flex justify-between items-center text-xs";
            div.innerHTML = `
                <div>
                    <span class="font-bold text-indigo-400">${r.name}</span>
                    <span class="text-slate-400 ml-2">SI (${r.condition_type}) contiene '${r.condition_value}'</span>
                </div>
                <div class="flex items-center space-x-2">
                    ${r.action_priority ? `<span class="bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-bold">${r.action_priority}</span>` : ''}
                    ${r.action_label ? `<span class="bg-indigo-900/60 text-indigo-300 px-2 py-0.5 rounded font-bold">${r.action_label}</span>` : ''}
                    <button onclick="deleteRule(${r.id})" class="text-rose-400 hover:text-rose-300 ml-2"><i class="fa-solid fa-trash"></i></button>
                </div>
            `;
            container.appendChild(div);
        });
    } catch (e) {
        console.error("Error loading rules:", e);
    }
}

function openRuleModal() { document.getElementById("rule-modal").classList.remove("hidden"); }
function closeRuleModal() { document.getElementById("rule-modal").classList.add("hidden"); }

async function saveRule() {
    const name = document.getElementById("rule-name").value;
    const cond_type = document.getElementById("rule-type").value;
    const cond_val = document.getElementById("rule-value").value;
    const priority = document.getElementById("rule-action-priority").value;
    const label = document.getElementById("rule-action-label").value;

    if (!name || !cond_val) {
        alert("Por favor completa los campos obligatorios.");
        return;
    }

    try {
        await fetch("/api/rules", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name, condition_type: cond_type, condition_value: cond_val,
                action_priority: priority, action_label: label
            })
        });
        closeRuleModal();
        loadRules();
    } catch (e) {
        alert("Error al guardar la regla.");
    }
}

async function deleteRule(id) {
    if (!confirm("¿Eliminar esta regla?")) return;
    try {
        await fetch(`/api/rules/${id}`, { method: "DELETE" });
        loadRules();
    } catch (e) {
        console.error("Error deleting rule:", e);
    }
}

async function loadLogs() {
    try {
        const res = await fetch("/api/logs");
        const logs = await res.json();
        const container = document.getElementById("logs-container");
        container.innerHTML = "";

        logs.forEach(l => {
            const div = document.createElement("div");
            div.className = "border-b border-slate-700/40 pb-1 text-slate-300";
            div.innerHTML = `
                <span class="text-slate-500">[${new Date(l.timestamp).toLocaleTimeString()}]</span>
                <span class="font-bold text-indigo-400">${l.action_taken}</span> -
                <span>${l.subject} (${l.sender_email})</span> |
                <span class="text-slate-400">${l.details}</span>
            `;
            container.appendChild(div);
        });
    } catch (e) {
        console.error("Error loading logs:", e);
    }
}

function switchTab(tabName) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));
    const target = document.getElementById(`tab-${tabName}`);
    if (target) target.classList.remove("hidden");

    document.querySelectorAll("[id^='tab-btn-']").forEach(btn => {
        btn.className = "tab-inactive py-3 text-sm font-semibold border-b-2 transition-all flex items-center space-x-2";
    });
    const activeBtn = document.getElementById(`tab-btn-${tabName}`);
    if (activeBtn) {
        activeBtn.className = "tab-active py-3 text-sm font-semibold border-b-2 transition-all flex items-center space-x-2";
    }

    if (tabName === 'mycases') {
        loadMyCases();
    } else if (tabName === 'stopped') {
        loadStoppedCases();
    } else if (tabName === 'users') {
        loadUsers();
    } else if (tabName === 'cases') {
        loadCases();
    } else if (tabName === 'bottlenecks') {
        loadBottlenecks();
    } else if (tabName === 'config') {
        loadFullConfig();
    }
}

function filterEmails() {
    const q = document.getElementById("search-input").value.toLowerCase();
    const filtered = allEmails.filter(e => 
        e.subject.toLowerCase().includes(q) || 
        e.sender_email.toLowerCase().includes(q) || 
        e.sender_name.toLowerCase().includes(q) ||
        e.snippet.toLowerCase().includes(q)
    );
    renderEmailTable(filtered);
}

async function loadFullConfig() {
    try {
        const res = await fetch("/api/config/full");
        const cfg = await res.json();

        document.getElementById("cfg-imap-user").value = cfg.imap_user || "";
        document.getElementById("cfg-imap-password").value = cfg.imap_password || "";
        document.getElementById("cfg-imap-server").value = cfg.imap_server || "imap.gmail.com";
        document.getElementById("cfg-imap-port").value = cfg.imap_port || 993;
        document.getElementById("cfg-smtp-server").value = cfg.smtp_server || "smtp.gmail.com";
        document.getElementById("cfg-smtp-port").value = cfg.smtp_port || 587;
        document.getElementById("cfg-ai-provider").value = cfg.ai_provider || "gemini";
        document.getElementById("cfg-gemini-key").value = cfg.gemini_api_key || "";
        document.getElementById("cfg-op-mode").value = cfg.operational_mode || "automatic";
        document.getElementById("cfg-company-name").value = cfg.company_name || "";
        document.getElementById("cfg-agent-name").value = cfg.agent_name || "Asistente Virtual IA";
        const supInput = document.getElementById("cfg-supervisor-email");
        if (supInput) supInput.value = cfg.supervisor_email || "coordinacion@clinica.com";
        document.getElementById("cfg-signature").value = cfg.reply_signature || "";
    } catch (e) {
        console.error("Error loading config:", e);
    }
}

function applyEmailPreset() {
    const preset = document.getElementById("cfg-preset").value;
    if (preset === "gmail") {
        document.getElementById("cfg-imap-server").value = "imap.gmail.com";
        document.getElementById("cfg-imap-port").value = 993;
        document.getElementById("cfg-smtp-server").value = "smtp.gmail.com";
        document.getElementById("cfg-smtp-port").value = 587;
    } else if (preset === "office365") {
        document.getElementById("cfg-imap-server").value = "outlook.office365.com";
        document.getElementById("cfg-imap-port").value = 993;
        document.getElementById("cfg-smtp-server").value = "smtp.office365.com";
        document.getElementById("cfg-smtp-port").value = 587;
    } else if (preset === "yahoo") {
        document.getElementById("cfg-imap-server").value = "imap.mail.yahoo.com";
        document.getElementById("cfg-imap-port").value = 993;
        document.getElementById("cfg-smtp-server").value = "smtp.mail.yahoo.com";
        document.getElementById("cfg-smtp-port").value = 587;
    }
}

async function saveFullConfig() {
    const payload = {
        email_provider: "imap",
        imap_user: document.getElementById("cfg-imap-user").value.trim(),
        imap_password: document.getElementById("cfg-imap-password").value.trim(),
        imap_server: document.getElementById("cfg-imap-server").value.trim(),
        imap_port: parseInt(document.getElementById("cfg-imap-port").value) || 993,
        smtp_server: document.getElementById("cfg-smtp-server").value.trim(),
        smtp_port: parseInt(document.getElementById("cfg-smtp-port").value) || 587,
        ai_provider: document.getElementById("cfg-ai-provider").value,
        gemini_api_key: document.getElementById("cfg-gemini-key").value.trim(),
        operational_mode: document.getElementById("cfg-op-mode").value,
        company_name: document.getElementById("cfg-company-name").value.trim(),
        agent_name: document.getElementById("cfg-agent-name").value.trim(),
        supervisor_email: document.getElementById("cfg-supervisor-email") ? document.getElementById("cfg-supervisor-email").value.trim() : "coordinacion@clinica.com",
        reply_signature: document.getElementById("cfg-signature").value.trim()
    };

    if (!payload.imap_user || !payload.imap_password) {
        alert("Por favor ingresa el correo electrónico y la contraseña.");
        return;
    }

    try {
        const res = await fetch("/api/config/full", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            alert("✅ Configuración guardada e implementada correctamente en tiempo real.");
            triggerSync();
        } else {
            alert("Error: " + data.detail);
        }
    } catch (e) {
        alert("Error al guardar la configuración.");
    }
}

// --- WORKFLOW & CASE TRACEABILITY FUNCTIONS ---

async function loadCases() {
    try {
        const folder = document.getElementById("case-folder-filter")?.value || "";
        const status = document.getElementById("case-status-filter")?.value || "";
        let url = "/api/cases?";
        if (folder) url += `folder=${encodeURIComponent(folder)}&`;
        if (status) url += `status=${encodeURIComponent(status)}&`;

        const res = await fetch(url);
        const cases = await res.json();
        
        const badge = document.getElementById("badge-cases-count");
        if (badge) badge.innerText = cases.length;

        const tbody = document.getElementById("cases-table-body");
        if (!tbody) return;
        tbody.innerHTML = "";

        if (cases.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="p-6 text-center text-slate-500">No hay casos en trámite con los filtros seleccionados.</td></tr>`;
            return;
        }

        cases.forEach(c => {
            const tr = document.createElement("tr");
            tr.className = "hover:bg-slate-700/40 transition-colors border-b border-slate-700/40";

            let statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">⏳ EN PROCESO</span>`;
            if (c.status === "DETENIDO_PROBLEMA") {
                statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">🚨 DETENIDO / PROBLEMA</span>`;
            } else if (c.status === "COMPLETADO") {
                statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">✅ COMPLETADO</span>`;
            }

            const returnsClass = c.total_returns > 0 ? "text-rose-400 font-bold bg-rose-500/10 px-2 py-0.5 rounded" : "text-slate-400";

            tr.innerHTML = `
                <td class="p-3">
                    <span class="font-mono font-bold text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/60">${c.case_code}</span>
                </td>
                <td class="p-3">
                    <div class="font-bold text-white">${c.patient_name || 'Paciente'}</div>
                    <div class="text-[11px] text-slate-400">${c.patient_id_doc || 'Doc en adjunto'}</div>
                </td>
                <td class="p-3">
                    <span class="text-xs font-semibold text-slate-300">📁 ${c.target_folder}</span>
                </td>
                <td class="p-3">
                    <div class="font-bold text-indigo-300">${c.current_step_name || 'Admisiones'}</div>
                    <div class="text-[11px] text-slate-400 truncate max-w-xs">${c.current_assigned_email}</div>
                </td>
                <td class="p-3 text-center font-bold text-indigo-400">${c.total_transitions}</td>
                <td class="p-3 text-center"><span class="${returnsClass}">${c.total_returns}</span></td>
                <td class="p-3">${statusBadge}</td>
                <td class="p-3 text-right">
                    <button onclick="openCaseModal(${c.id})" class="bg-indigo-600/80 hover:bg-indigo-600 text-white font-semibold px-3 py-1.5 rounded-lg text-xs transition-all shadow-sm">
                        <i class="fa-solid fa-list-check mr-1"></i> Ver Historial
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error loading cases:", e);
    }
}

async function loadBottlenecks() {
    try {
        const res = await fetch("/api/reports/bottlenecks");
        const report = await res.json();

        const statStopped = document.getElementById("bn-stat-stopped");
        const statReturns = document.getElementById("bn-stat-returns");
        const statCompleted = document.getElementById("bn-stat-completed");
        const statTransitions = document.getElementById("bn-stat-transitions");
        const badge = document.getElementById("badge-bottlenecks-count");

        if (statStopped) statStopped.innerText = report.stopped_cases || 0;
        if (statReturns) statReturns.innerText = report.total_returns || 0;
        if (statCompleted) statCompleted.innerText = report.completed_cases || 0;
        if (statTransitions) statTransitions.innerText = report.total_transitions || 0;
        if (badge) badge.innerText = report.stopped_cases || 0;

        // Causes cards
        const container = document.getElementById("bn-causes-container");
        if (container) {
            container.innerHTML = "";
            const causes = report.bottlenecks_by_reason || [];
            if (causes.length === 0) {
                container.innerHTML = `<p class="text-xs text-slate-400 col-span-full">No se han registrado cuellos de botella ni detenciones actualmente.</p>`;
            } else {
                const maxCount = Math.max(...causes.map(c => c.count), 1);
                causes.forEach(cause => {
                    const pct = Math.round((cause.count / maxCount) * 100);
                    const div = document.createElement("div");
                    div.className = "bg-slate-900/80 p-3.5 rounded-xl border border-slate-700 space-y-1.5";
                    div.innerHTML = `
                        <div class="flex justify-between items-center text-xs">
                            <span class="font-bold text-rose-300">${cause.reason}</span>
                            <span class="font-mono font-bold text-rose-400 text-sm">${cause.count}</span>
                        </div>
                        <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                            <div class="bg-gradient-to-r from-rose-500 to-amber-500 h-2 rounded-full" style="width: ${pct}%"></div>
                        </div>
                        <span class="text-[10px] text-slate-400 block text-right">${pct}% de incidencia relativa</span>
                    `;
                    container.appendChild(div);
                });
            }
        }

        // Delayed cases table
        const tbody = document.getElementById("bn-delayed-table-body");
        if (tbody) {
            tbody.innerHTML = "";
            const delayed = report.delayed_cases || [];
            if (delayed.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-500">No hay casos con detenciones o retrasos en este momento.</td></tr>`;
            } else {
                delayed.forEach(d => {
                    const tr = document.createElement("tr");
                    tr.className = "hover:bg-slate-700/40 transition-colors border-b border-slate-700/40";
                    tr.innerHTML = `
                        <td class="p-3 font-mono font-bold text-cyan-400">${d.case_code}</td>
                        <td class="p-3 font-semibold text-white">${d.patient_name}</td>
                        <td class="p-3">
                            <div class="font-bold text-rose-300">${d.current_step_name}</div>
                            <div class="text-[11px] text-slate-400">${d.current_assigned_email}</div>
                        </td>
                        <td class="p-3 font-bold text-amber-400">${d.bottleneck_reason || 'Revisión'}</td>
                        <td class="p-3 text-slate-300 max-w-xs truncate">${d.last_problem_reported || '-'}</td>
                        <td class="p-3 text-center font-bold text-rose-400">${d.total_returns}</td>
                        <td class="p-3 text-right">
                            <button onclick="switchTab('cases')" class="bg-rose-600 hover:bg-rose-500 text-white font-semibold px-3 py-1 rounded text-xs">
                                Gestionar
                            </button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        }

    } catch (e) {
        console.error("Error loading bottlenecks:", e);
    }
}

async function openCaseModal(caseId) {
    currentSelectedCaseId = caseId;
    try {
        const res = await fetch(`/api/cases/${caseId}`);
        const c = await res.json();

        document.getElementById("case-modal-code").innerText = c.case_code;
        document.getElementById("case-modal-patient").innerText = c.patient_name || 'Paciente';
        document.getElementById("case-modal-doc").innerText = c.patient_id_doc || 'Documento en expediente';
        document.getElementById("case-modal-folder").innerText = `📁 ${c.target_folder}`;
        document.getElementById("case-modal-step").innerText = c.current_step_name;
        document.getElementById("case-modal-actor").innerText = c.current_assigned_email;
        document.getElementById("case-modal-counts").innerHTML = `${c.total_transitions} pases / <span class="text-rose-400">${c.total_returns} retrasos</span>`;

        // Status badge
        const badge = document.getElementById("case-modal-status-badge");
        if (c.status === "DETENIDO_PROBLEMA") {
            badge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30";
            badge.innerText = "🚨 DETENIDO / PROBLEMA";
        } else if (c.status === "COMPLETADO") {
            badge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
            badge.innerText = "✅ COMPLETADO";
        } else {
            badge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30";
            badge.innerText = "⏳ EN PROCESO";
        }

        // Problem alert box
        const alertBox = document.getElementById("case-modal-alert-box");
        const alertText = document.getElementById("case-modal-alert-text");
        if (c.last_problem_reported) {
            alertBox.classList.remove("hidden");
            alertText.innerText = `Causa: ${c.bottleneck_reason || 'Inconsistencia'} | Detalle: ${c.last_problem_reported}`;
        } else {
            alertBox.classList.add("hidden");
        }

        // Timeline
        const timeline = document.getElementById("case-modal-timeline");
        timeline.innerHTML = "";
        (c.logs || []).forEach(log => {
            const item = document.createElement("div");
            item.className = "relative group";
            
            let iconClass = "fa-circle-check text-emerald-400";
            if (log.action === "PROBLEMA_REPORTADO") iconClass = "fa-circle-exclamation text-rose-400";
            else if (log.action === "ALERTA_SUPERVISOR_ENVIADA") iconClass = "fa-bullhorn text-amber-400";
            else if (log.action === "INICIADO") iconClass = "fa-play text-cyan-400";
            else if (log.action === "COMPLETADO_FINAL") iconClass = "fa-flag-checkered text-emerald-300";

            item.innerHTML = `
                <div class="absolute -left-[23px] top-0.5 bg-slate-900 rounded-full p-1 border border-slate-700">
                    <i class="fa-solid ${iconClass} text-xs"></i>
                </div>
                <div class="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800 text-xs">
                    <div class="flex justify-between items-center mb-1">
                        <span class="font-bold text-white">${log.step_name || 'Etapa'} - <span class="text-cyan-400">${log.action}</span></span>
                        <span class="text-[10px] text-slate-400">${log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}</span>
                    </div>
                    <div class="text-slate-300">${log.comments || ''}</div>
                    ${log.problem_details ? `<div class="mt-1 text-rose-300 bg-rose-950/40 p-1.5 rounded border border-rose-900/60 font-semibold text-[11px]"><i class="fa-solid fa-triangle-exclamation mr-1"></i>${log.problem_details}</div>` : ''}
                    <div class="text-[10px] text-slate-500 mt-1">Responsable: ${log.actor_email || 'Sistema'}</div>
                </div>
            `;
            timeline.appendChild(item);
        });

        // Hide problem form if open
        document.getElementById("case-problem-form").classList.add("hidden");
        document.getElementById("case-action-comments").value = "";

        // Show/hide actions if already completed
        const actionsArea = document.getElementById("case-modal-actions-area");
        if (c.status === "COMPLETADO") {
            actionsArea.classList.add("hidden");
        } else {
            actionsArea.classList.remove("hidden");
        }

        document.getElementById("case-modal").classList.remove("hidden");
    } catch (e) {
        console.error("Error opening case modal:", e);
    }
}

function closeCaseModal() {
    document.getElementById("case-modal").classList.add("hidden");
    currentSelectedCaseId = null;
}

function toggleProblemForm() {
    const form = document.getElementById("case-problem-form");
    form.classList.toggle("hidden");
}

async function advanceCaseAction() {
    if (!currentSelectedCaseId) return;
    const comments = document.getElementById("case-action-comments").value.trim();

    try {
        const res = await fetch(`/api/cases/${currentSelectedCaseId}/advance`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ comments: comments })
        });
        const data = await res.json();
        if (res.ok) {
            alert(`✅ Paso avanzado exitosamente. Estado actual: ${data.new_status} (${data.current_step_name || 'Completado'})`);
            openCaseModal(currentSelectedCaseId);
            loadCases();
            loadBottlenecks();
        } else {
            alert("Error: " + data.detail);
        }
    } catch (e) {
        alert("Error al avanzar el paso.");
    }
}

async function submitProblemAction() {
    if (!currentSelectedCaseId) return;
    const reason = document.getElementById("case-problem-reason").value.trim();
    const category = document.getElementById("case-problem-category").value;

    if (!reason) {
        alert("Por favor ingrese el motivo del problema o rechazo.");
        return;
    }

    try {
        const res = await fetch(`/api/cases/${currentSelectedCaseId}/problem`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                reason: reason,
                bottleneck_category: category
            })
        });
        const data = await res.json();
        if (res.ok) {
            alert(`🚨 Novedad registrada y ALERTA ENVIADA INMEDIATAMENTE a la Coordinación (${data.alert_sent_to}).`);
            openCaseModal(currentSelectedCaseId);
            loadCases();
            loadBottlenecks();
            loadMyCases();
            loadStoppedCases();
        } else {
            alert("Error: " + data.detail);
        }
    } catch (e) {
        alert("Error al reportar el problema.");
    }
}

// --- OPERATOR & CASE ADVANCE / NOVELTY FUNCTIONS ---

async function loadMyCases() {
    if (!currentUser) return;
    try {
        let url = "/api/cases";
        if (currentUser.role !== "ADMIN" && currentUser.assigned_stage !== "TODAS") {
            url += `?stage=${encodeURIComponent(currentUser.assigned_stage)}`;
        }
        const res = await fetch(url);
        const cases = await res.json();

        const myPending = cases.filter(c => c.status !== "COMPLETADO");
        const badge = document.getElementById("badge-mycases-count");
        if (badge) badge.innerText = myPending.length;

        const tbody = document.getElementById("mycases-table-body");
        if (!tbody) return;
        tbody.innerHTML = "";

        if (cases.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-500">No hay pacientes asignados actualmente para su área.</td></tr>`;
            return;
        }

        cases.forEach(c => {
            const tr = document.createElement("tr");
            tr.className = "hover:bg-slate-700/40 transition-colors border-b border-slate-700/40";

            let statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">⏳ EN PROCESO</span>`;
            if (c.status === "DETENIDO_PROBLEMA") {
                statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">🚨 NOVEDAD DETENIDA</span>`;
            } else if (c.status === "COMPLETADO") {
                statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">✅ COMPLETADO</span>`;
            }

            const canAct = (c.status === "EN_PROCESO");

            tr.innerHTML = `
                <td class="p-3">
                    <span class="font-mono font-bold text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/60">${c.case_code}</span>
                </td>
                <td class="p-3">
                    <div class="font-bold text-white">${c.patient_name || 'Paciente'}</div>
                    <div class="text-[11px] text-slate-400">${c.patient_id_doc || 'Doc en orden'}</div>
                </td>
                <td class="p-3">
                    <div class="text-slate-200 font-semibold">${c.patient_address || 'Dirección en historia'}</div>
                    <div class="text-[11px] text-cyan-400">${c.city_zone || 'Zona Domiciliaria'}</div>
                </td>
                <td class="p-3">
                    <div class="text-indigo-300 font-bold">${c.eps_name || 'EPS Subsidiado/Contributivo'}</div>
                    <div class="text-[11px] text-slate-400">${c.service_requested || 'Atención Domiciliaria Integral'}</div>
                </td>
                <td class="p-3">
                    <div class="font-bold text-emerald-300">${c.current_step_name || 'Admisiones'}</div>
                    <div class="text-[11px] text-slate-400">${c.current_assigned_email}</div>
                </td>
                <td class="p-3">${statusBadge}</td>
                <td class="p-3 text-right space-x-1.5 whitespace-nowrap">
                    ${canAct ? `
                    <button onclick="quickApproveCase(${c.id}, '${c.case_code}')" title="Aprobar y pasar a siguiente usuario" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-2.5 py-1.5 rounded-lg text-xs shadow-sm transition-all">
                        <i class="fa-solid fa-check mr-1"></i> Aprobar
                    </button>
                    <button onclick="openQuickRejectModal(${c.id}, '${c.case_code}', '${(c.patient_name || '').replace(/'/g, "\\'")}')" title="Reportar novedad / desaprobar" class="bg-rose-600 hover:bg-rose-500 text-white font-bold px-2.5 py-1.5 rounded-lg text-xs shadow-sm transition-all">
                        <i class="fa-solid fa-triangle-exclamation mr-1"></i> Desaprobar
                    </button>
                    ` : ''}
                    <button onclick="openCaseModal(${c.id})" class="bg-indigo-600/60 hover:bg-indigo-600 text-slate-200 font-semibold px-2.5 py-1.5 rounded-lg text-xs transition-all">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error loading my cases:", e);
    }
}

async function quickApproveCase(caseId, caseCode) {
    const comments = prompt(`Aprobar y avanzar caso ${caseCode}:\nIngrese observaciones o confirmación de la diligencia realizada:`, "Diligencia realizada conforme. Avanza a siguiente etapa.");
    if (comments === null) return;

    try {
        const res = await fetch(`/api/cases/${caseId}/advance`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                actor_email: currentUser ? currentUser.email : "",
                comments: comments || "Aprobado conforme"
            })
        });
        const data = await res.json();
        if (res.ok) {
            alert(`✅ Caso ${caseCode} aprobado y enviado a: ${data.current_step_name || 'Completado'}`);
            loadMyCases();
            loadCases();
            loadStats();
        } else {
            alert("Error: " + data.detail);
        }
    } catch (e) {
        alert("Error al avanzar el caso.");
    }
}

function openQuickRejectModal(caseId, caseCode, patientName) {
    currentRejectCaseId = caseId;
    document.getElementById("quick-reject-code").innerText = caseCode;
    document.getElementById("quick-reject-patient").innerText = patientName;
    document.getElementById("quick-reject-reason").value = "";
    document.getElementById("quick-reject-modal").classList.remove("hidden");
}

function closeQuickRejectModal() {
    document.getElementById("quick-reject-modal").classList.add("hidden");
    currentRejectCaseId = null;
}

async function submitQuickRejectModal() {
    if (!currentRejectCaseId) return;
    const reason = document.getElementById("quick-reject-reason").value.trim();
    const category = document.getElementById("quick-reject-category").value;

    if (!reason) {
        alert("Debe detallar el motivo por el cual no se acepta o se detiene el caso.");
        return;
    }

    try {
        const res = await fetch(`/api/cases/${currentRejectCaseId}/problem`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                actor_email: currentUser ? currentUser.email : "",
                reason: reason,
                bottleneck_category: category
            })
        });
        const data = await res.json();
        if (res.ok) {
            alert(`🚨 Novedad registrada. Se notificó inmediatamente a la Coordinación (${data.alert_sent_to}) para subsanación.`);
            closeQuickRejectModal();
            loadMyCases();
            loadCases();
            loadStoppedCases();
            loadBottlenecks();
            loadStats();
        } else {
            alert("Error: " + data.detail);
        }
    } catch (e) {
        alert("Error al reportar la novedad.");
    }
}

// --- STOPPED CASES & RESOLUTION FUNCTIONS (ADMIN) ---

async function loadStoppedCases() {
    try {
        const res = await fetch("/api/cases?status=DETENIDO_PROBLEMA");
        const stopped = await res.json();

        const badge = document.getElementById("badge-stopped-count");
        if (badge) badge.innerText = stopped.length;

        const tbody = document.getElementById("stopped-cases-table-body");
        if (!tbody) return;
        tbody.innerHTML = "";

        if (stopped.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-500">🎉 No hay casos detenidos en este momento. Todos los pacientes avanzan sin novedad.</td></tr>`;
            return;
        }

        stopped.forEach(c => {
            const tr = document.createElement("tr");
            tr.className = "hover:bg-slate-700/40 transition-colors border-b border-slate-700/40 bg-rose-950/15";
            tr.innerHTML = `
                <td class="p-3 font-mono font-bold text-cyan-400">${c.case_code}</td>
                <td class="p-3">
                    <div class="font-bold text-white">${c.patient_name}</div>
                    <div class="text-[11px] text-slate-400">${c.patient_id_doc || ''}</div>
                </td>
                <td class="p-3">
                    <div class="font-bold text-rose-300">${c.current_step_name}</div>
                    <div class="text-[11px] text-slate-400">${c.current_assigned_email}</div>
                </td>
                <td class="p-3 font-bold text-amber-300">${c.bottleneck_reason || 'Inconsistencia'}</td>
                <td class="p-3 text-rose-200 text-xs font-semibold max-w-xs">${c.last_problem_reported || '-'}</td>
                <td class="p-3 text-center font-bold text-rose-400">${c.total_returns}</td>
                <td class="p-3 text-right">
                    <button onclick="openResolveModal(${c.id}, '${c.case_code}', '${(c.patient_name || '').replace(/'/g, "\\'")}', '${(c.last_problem_reported || '').replace(/'/g, "\\'")}')" class="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold px-3 py-1.5 rounded-lg text-xs shadow-md transition-all">
                        <i class="fa-solid fa-wrench mr-1"></i> Subsanar & Reanudar
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error loading stopped cases:", e);
    }
}

function openResolveModal(caseId, caseCode, patientName, problemReason) {
    currentResolveCaseId = caseId;
    document.getElementById("resolve-modal-code").innerText = caseCode;
    document.getElementById("resolve-modal-patient").innerText = patientName;
    document.getElementById("resolve-modal-problem").innerText = problemReason;
    document.getElementById("resolve-modal-notes").value = "";
    document.getElementById("resolve-modal").classList.remove("hidden");
}

function closeResolveModal() {
    document.getElementById("resolve-modal").classList.add("hidden");
    currentResolveCaseId = null;
}

async function submitResolveModal() {
    if (!currentResolveCaseId) return;
    const notes = document.getElementById("resolve-modal-notes").value.trim();
    if (!notes) {
        alert("Por favor detalle la acción correctiva realizada para subsanar la novedad.");
        return;
    }

    try {
        const res = await fetch(`/api/cases/${currentResolveCaseId}/resolve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                resolved_by: currentUser ? currentUser.email : "coordinacion@ipsdomiciliaria.com",
                resolution_notes: notes
            })
        });
        const data = await res.json();
        if (res.ok) {
            alert(`✅ ${data.message} El caso regresa a ${data.current_step_name} para continuar el proceso.`);
            closeResolveModal();
            loadStoppedCases();
            loadMyCases();
            loadCases();
            loadBottlenecks();
            loadStats();
        } else {
            alert("Error: " + data.detail);
        }
    } catch (e) {
        alert("Error al resolver la novedad.");
    }
}

// --- USER MANAGEMENT FUNCTIONS (ADMIN) ---

async function loadUsers() {
    const tbody = document.getElementById("users-table-body");
    if (!tbody) return;
    try {
        const res = await fetch("/api/users");
        if (!res.ok) {
            console.error("HTTP error loading users:", res.status);
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="p-4 text-center text-amber-300 font-semibold bg-amber-500/10">
                        <i class="fa-solid fa-triangle-exclamation mr-1.5"></i>
                        El backend aún no tiene activos los endpoints de usuarios. Reinicie el servicio en su terminal:
                        <code class="block mt-1 font-mono text-xs text-white bg-slate-900 px-2 py-1 rounded inline-block">sudo systemctl restart email-ai-agent</code>
                    </td>
                </tr>
            `;
            return;
        }
        const users = await res.json();
        tbody.innerHTML = "";

        if (!Array.isArray(users) || users.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="p-6 text-center text-slate-400">
                        <i class="fa-solid fa-users text-2xl block mb-2 text-slate-500"></i>
                        No hay usuarios adicionales registrados. Use el botón <b class="text-purple-400">+ Nuevo Usuario IPS</b> para dar de alta colaboradores.
                    </td>
                </tr>
            `;
            return;
        }

        users.forEach(u => {
            const tr = document.createElement("tr");
            tr.className = "hover:bg-slate-700/40 transition-colors border-b border-slate-700/40";
            const roleBadge = u.role === "ADMIN" 
                ? `<span class="bg-indigo-500/20 text-indigo-300 font-bold px-2 py-0.5 rounded text-[10px] border border-indigo-500/30">ADMINISTRADOR</span>`
                : `<span class="bg-emerald-500/20 text-emerald-300 font-bold px-2 py-0.5 rounded text-[10px] border border-emerald-500/30">OPERADOR</span>`;

            tr.innerHTML = `
                <td class="p-3 font-mono font-bold text-white">${u.username}</td>
                <td class="p-3 font-semibold text-slate-200">${u.full_name}</td>
                <td class="p-3">${roleBadge}</td>
                <td class="p-3 font-bold text-cyan-300">${u.assigned_stage}</td>
                <td class="p-3 text-slate-300">${u.email}</td>
                <td class="p-3 text-slate-400">${u.phone || '-'}</td>
                <td class="p-3"><span class="text-emerald-400 font-bold"><i class="fa-solid fa-circle-check text-[10px] mr-1"></i>Activo</span></td>
                <td class="p-3 text-right">
                    <button onclick="deleteUser(${u.id}, '${u.username}')" class="text-rose-400 hover:text-rose-300 p-1" title="Eliminar usuario">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error loading users:", e);
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="8" class="p-4 text-center text-rose-400"><i class="fa-solid fa-circle-exclamation mr-1"></i> Error de conexión al cargar usuarios.</td></tr>`;
        }
    }
}

function openCreateUserModal() {
    const modal = document.getElementById("user-modal");
    if (!modal) {
        alert("Error: No se encontró el modal de usuarios en la página. Recargue la página (Ctrl+F5).");
        return;
    }
    document.getElementById("user-modal-id").value = "";
    document.getElementById("user-modal-username").value = "";
    document.getElementById("user-modal-password").value = "";
    document.getElementById("user-modal-fullname").value = "";
    document.getElementById("user-modal-email").value = "";
    document.getElementById("user-modal-phone").value = "";
    modal.classList.remove("hidden");
}

function closeUserModal() {
    const modal = document.getElementById("user-modal");
    if (modal) modal.classList.add("hidden");
}

async function submitUserModal() {
    const uname = document.getElementById("user-modal-username").value.trim();
    const pwd = document.getElementById("user-modal-password").value;
    const fname = document.getElementById("user-modal-fullname").value.trim();
    const email = document.getElementById("user-modal-email").value.trim();
    const role = document.getElementById("user-modal-role").value;
    const stage = document.getElementById("user-modal-stage").value;
    const phone = document.getElementById("user-modal-phone").value.trim();

    if (!uname || !pwd || !fname || !email) {
        alert("Por favor diligencie todos los campos obligatorios: Nombre Completo, Usuario, Contraseña y Correo Electrónico.");
        return;
    }

    const payload = {
        username: uname,
        password: pwd,
        full_name: fname,
        email: email,
        role: role,
        assigned_stage: stage,
        phone: phone
    };

    try {
        const res = await fetch("/api/users", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            alert(`✅ Usuario '${uname}' (${fname}) registrado exitosamente.`);
            closeUserModal();
            loadUsers();
        } else {
            alert("Error del servidor: " + (data.detail || JSON.stringify(data)));
        }
    } catch (e) {
        alert("Error de conexión al registrar usuario. Asegúrese de haber reiniciado el servicio en el iMac con: sudo systemctl restart email-ai-agent");
    }
}

async function deleteUser(userId, username) {
    if (!confirm(`¿Está seguro de eliminar al usuario '${username}'?`)) return;
    try {
        const res = await fetch(`/api/users/${userId}`, { method: "DELETE" });
        if (res.ok) {
            loadUsers();
        } else {
            alert("No se pudo eliminar el usuario.");
        }
    } catch (e) {
        alert("Error de conexión al eliminar.");
    }
}

// Ensure global scope accessibility
window.openCreateUserModal = openCreateUserModal;
window.closeUserModal = closeUserModal;
window.submitUserModal = submitUserModal;
window.loadUsers = loadUsers;
window.deleteUser = deleteUser;

