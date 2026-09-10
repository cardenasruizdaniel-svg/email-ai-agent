let allEmails = [];
let currentSelectedEmailId = null;

document.addEventListener("DOMContentLoaded", () => {
    loadStats();
    loadEmails();
    loadSenders();
    loadRules();
    loadLogs();

    // Auto refresh every 10 seconds
    setInterval(() => {
        loadStats();
        loadEmails();
    }, 10000);
});

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
    document.getElementById(`tab-${tabName}`).classList.remove("hidden");

    document.querySelectorAll("[id^='tab-btn-']").forEach(btn => {
        btn.className = "tab-inactive py-3 text-sm font-semibold border-b-2 transition-all flex items-center space-x-2";
    });
    document.getElementById(`tab-btn-${tabName}`).className = "tab-active py-3 text-sm font-semibold border-b-2 transition-all flex items-center space-x-2";

    if (tabName === 'config') {
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
