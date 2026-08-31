document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const btnStart = document.getElementById("btnStart");
    const btnStop = document.getElementById("btnStop");
    const btnPause = document.getElementById("btnPause");
    const btnResume = document.getElementById("btnResume");
    const btnVerifyCookie = document.getElementById("btnVerifyCookie");
    const btnApplyLiveSpeed = document.getElementById("btnApplyLiveSpeed");
    const btnClearLogs = document.getElementById("btnClearLogs");

    const form = document.getElementById("botConfigForm");
    const cookieInput = document.getElementById("cookieInput");
    const cookieFileInput = document.getElementById("cookieFileInput");
    const cookieValidationResult = document.getElementById("cookieValidationResult");

    const messagesInput = document.getElementById("messagesInput");
    const messagesFileInput = document.getElementById("messagesFileInput");
    const msgFileName = document.getElementById("msgFileName");

    const typingDelaySlider = document.getElementById("typingDelaySlider");
    const messageDelaySlider = document.getElementById("messageDelaySlider");
    const typingVal = document.getElementById("typingVal");
    const intervalVal = document.getElementById("intervalVal");
    const presetButtons = document.querySelectorAll(".preset-btn");

    const globalStatusPill = document.getElementById("globalStatusPill");
    const globalStatusText = document.getElementById("globalStatusText");
    const uptimeDisplay = document.getElementById("uptimeDisplay");

    const statSent = document.getElementById("statSent");
    const statLoop = document.getElementById("statLoop");
    const statProgress = document.getElementById("statProgress");
    const statAccount = document.getElementById("statAccount");

    const terminalLogs = document.getElementById("terminalLogs");
    const terminalContainer = document.getElementById("terminalContainer");
    const autoScrollCheck = document.getElementById("autoScrollCheck");
    const toast = document.getElementById("toast");

    let isRunning = false;
    let eventSource = null;

    const targetLabel = document.getElementById("targetLabel");
    const targetHelper = document.getElementById("targetHelper");
    const targetTypeSelector = document.getElementById("targetTypeSelector");
    const targetIdInput = document.getElementById("targetId");

    // --- Mode Switching (Chat vs Comment) ---
    document.querySelectorAll("input[name='task_mode']").forEach(radio => {
        radio.addEventListener("change", (e) => {
            const mode = e.target.value;
            if (mode === "comment") {
                targetLabel.innerHTML = `<i class="fa-solid fa-comments"></i> Target Facebook Post ID (Photo / Video / Reel)`;
                targetHelper.textContent = "Facebook Post ID (e.g. 1000123456789_987654321 ya numeric ID) daalein.";
                targetIdInput.placeholder = "e.g. 1000123456789_987654321 ya 82736192847291";
                if (targetTypeSelector) targetTypeSelector.style.display = "none";
                showToast("Post Auto-Commenter Mode Selected", "info");
            } else {
                targetLabel.innerHTML = `<i class="fa-solid fa-bullseye"></i> Target Chat ID (Personal UID ya Group ID)`;
                targetHelper.textContent = "Target User UID ya Group Convo Thread ID daalein.";
                targetIdInput.placeholder = "e.g. 10001234567890 ya 82736192847291";
                if (targetTypeSelector) targetTypeSelector.style.display = "grid";
                showToast("Messenger Chat Mode Selected", "info");
            }
        });
    });

    // --- Tab Switching ---
    document.querySelectorAll(".tabs-nav").forEach(nav => {
        nav.querySelectorAll(".tab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const targetTab = btn.getAttribute("data-tab");
                const parentGroup = nav.closest(".form-group");

                nav.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
                parentGroup.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

                btn.classList.add("active");
                const activeContent = document.getElementById(`tab-${targetTab}`);
                if (activeContent) activeContent.classList.add("active");
            });
        });
    });

    // --- File Input Name Display ---
    if (cookieFileInput) {
        cookieFileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                const fileName = e.target.files[0].name;
                showToast(`Cookie file selected: ${fileName}`, "info");
            }
        });
    }

    if (messagesFileInput) {
        messagesFileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                const fileName = e.target.files[0].name;
                msgFileName.innerHTML = `<strong>Selected:</strong> ${fileName}`;
                showToast(`Messages file selected: ${fileName}`, "info");
            }
        });
    }

    // --- Speed Sliders & Presets ---
    typingDelaySlider.addEventListener("input", (e) => {
        typingVal.textContent = `${e.target.value}s`;
        clearActivePreset();
    });

    messageDelaySlider.addEventListener("input", (e) => {
        intervalVal.textContent = `${e.target.value}s`;
        clearActivePreset();
    });

    function clearActivePreset() {
        presetButtons.forEach(b => b.classList.remove("active"));
    }

    presetButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            presetButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const type = btn.getAttribute("data-type");

            if (type === "ultra") {
                setSpeed(1, 2);
            } else if (type === "fast") {
                setSpeed(2, 5);
            } else if (type === "normal") {
                setSpeed(3, 10);
            } else if (type === "safe") {
                setSpeed(5, 20);
            }
        });
    });

    function setSpeed(typing, msgDelay) {
        typingDelaySlider.value = typing;
        typingVal.textContent = `${typing}s`;
        messageDelaySlider.value = msgDelay;
        intervalVal.textContent = `${msgDelay}s`;
    }

    // --- Live Speed Apply ---
    btnApplyLiveSpeed.addEventListener("click", async () => {
        const typing = parseInt(typingDelaySlider.value);
        const interval = parseInt(messageDelaySlider.value);

        try {
            const res = await fetch("/api/update_speed", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ typing_delay: typing, message_delay: interval })
            });
            const data = await res.json();
            showToast(data.message || "Speed updated!", "success");
        } catch (err) {
            showToast("Failed to update live speed.", "error");
        }
    });

    // --- Toast Notifications ---
    function showToast(message, type = "info") {
        toast.className = `toast show ${type}`;
        toast.textContent = message;
        setTimeout(() => {
            toast.className = "toast";
        }, 4000);
    }

    // --- Cookie Validation ---
    btnVerifyCookie.addEventListener("click", async () => {
        let cookieText = cookieInput.value.trim();

        // If file tab active and text empty, read from file
        if (!cookieText && cookieFileInput.files.length > 0) {
            const file = cookieFileInput.files[0];
            cookieText = await file.text();
        }

        if (!cookieText) {
            showToast("Pehle cookies text daalein ya cookie file upload karein.", "error");
            return;
        }

        btnVerifyCookie.disabled = true;
        btnVerifyCookie.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Checking...`;
        cookieValidationResult.style.display = "block";
        cookieValidationResult.className = "cookie-status-msg";
        cookieValidationResult.textContent = "Connecting to Facebook & validating cookies...";

        try {
            const res = await fetch("/api/validate_cookie", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ cookies: cookieText })
            });
            const data = await res.json();

            if (data.success) {
                cookieValidationResult.className = "cookie-status-msg valid";
                cookieValidationResult.innerHTML = `<i class="fa-solid fa-circle-check"></i> <strong>Valid!</strong> Logged in as: <b>${data.user_name}</b> (UID: ${data.user_id})`;
                statAccount.textContent = data.user_name;
                showToast(`Cookie Verified: ${data.user_name}`, "success");
            } else {
                cookieValidationResult.className = "cookie-status-msg invalid";
                cookieValidationResult.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> ${data.message}`;
                showToast("Cookie Invalid ya Expired!", "error");
            }
        } catch (err) {
            cookieValidationResult.className = "cookie-status-msg invalid";
            cookieValidationResult.textContent = `Error: ${err.message}`;
        } finally {
            btnVerifyCookie.disabled = false;
            btnVerifyCookie.innerHTML = `<i class="fa-solid fa-shield-check"></i> Check Cookie`;
        }
    });

    // --- Start Bot ---
    btnStart.addEventListener("click", async (e) => {
        e.preventDefault();

        const formData = new FormData(form);

        // Validation checks
        const targetId = formData.get("target_id");
        if (!targetId || !targetId.trim()) {
            showToast("Target ID / Group ID daalna zaroori hai!", "error");
            document.getElementById("targetId").focus();
            return;
        }

        const cookieText = formData.get("cookies");
        const cookieFile = cookieFileInput.files[0];
        if (!cookieText.trim() && !cookieFile) {
            showToast("Facebook Cookies provide karein!", "error");
            return;
        }

        const msgText = formData.get("messages");
        const msgFile = messagesFileInput.files[0];
        if (!msgText.trim() && !msgFile) {
            showToast("Messages text daalein ya .txt file upload karein!", "error");
            return;
        }

        btnStart.disabled = true;
        btnStart.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> STARTING...`;

        try {
            const res = await fetch("/api/start", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (data.success) {
                showToast(data.message, "success");
                updateUIState(true);
            } else {
                showToast(data.message || "Failed to start bot.", "error");
                btnStart.disabled = false;
                btnStart.innerHTML = `<i class="fa-solid fa-play"></i> START BOT`;
            }
        } catch (err) {
            showToast(`Connection error: ${err.message}`, "error");
            btnStart.disabled = false;
            btnStart.innerHTML = `<i class="fa-solid fa-play"></i> START BOT`;
        }
    });

    // --- Stop Bot (PythonAnywhere One-Click Stop) ---
    btnStop.addEventListener("click", async () => {
        btnStop.disabled = true;
        btnStop.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> STOPPING...`;

        try {
            const res = await fetch("/api/stop", { method: "POST" });
            const data = await res.json();
            showToast(data.message, "info");
            updateUIState(false);
        } catch (err) {
            showToast(`Error stopping bot: ${err.message}`, "error");
        } finally {
            btnStop.innerHTML = `<i class="fa-solid fa-stop"></i> STOP BOT`;
        }
    });

    // --- Pause & Resume ---
    btnPause.addEventListener("click", async () => {
        try {
            const res = await fetch("/api/pause", { method: "POST" });
            const data = await res.json();
            showToast(data.message, "info");
            btnPause.style.display = "none";
            btnResume.style.display = "inline-flex";
        } catch (err) {
            showToast("Pause request failed.", "error");
        }
    });

    btnResume.addEventListener("click", async () => {
        try {
            const res = await fetch("/api/resume", { method: "POST" });
            const data = await res.json();
            showToast(data.message, "success");
            btnResume.style.display = "none";
            btnPause.style.display = "inline-flex";
        } catch (err) {
            showToast("Resume request failed.", "error");
        }
    });

    // --- Clear Logs ---
    btnClearLogs.addEventListener("click", async () => {
        await fetch("/api/clear_logs", { method: "POST" });
        terminalLogs.innerHTML = "";
        showToast("Terminal logs cleared.", "info");
    });

    // --- UI State Management ---
    function updateUIState(running, status = "RUNNING") {
        isRunning = running;

        if (running) {
            btnStart.disabled = true;
            btnStop.disabled = false;
            btnPause.disabled = false;
            btnStart.innerHTML = `<i class="fa-solid fa-play"></i> BOT RUNNING`;

            globalStatusPill.className = `status-pill ${status.toLowerCase()}`;
            globalStatusText.textContent = status.toUpperCase();
        } else {
            btnStart.disabled = false;
            btnStop.disabled = true;
            btnPause.disabled = true;
            btnResume.style.display = "none";
            btnPause.style.display = "inline-flex";
            btnStart.innerHTML = `<i class="fa-solid fa-play"></i> START BOT`;

            globalStatusPill.className = "status-pill";
            globalStatusText.textContent = "STOPPED";
        }
    }

    // --- Status Polling Loop ---
    async function fetchStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();

            uptimeDisplay.textContent = data.uptime || "00:00:00";
            statSent.textContent = data.total_sent || 0;
            statLoop.textContent = `Round #${data.loop_count || 0}`;
            statProgress.textContent = `${data.current_line || 0} / ${data.total_lines || 0}`;

            if (data.user_name) {
                statAccount.textContent = data.user_name;
            }

            if (data.is_running) {
                updateUIState(true, data.status);
            } else if (isRunning) {
                updateUIState(false);
            }
        } catch (err) {
            // Ignore temporary poll error
        }
    }

    setInterval(fetchStatus, 1500);

    // --- Server-Sent Events (SSE) Live Log Streaming ---
    function initLogStream() {
        if (eventSource) eventSource.close();

        eventSource = new EventSource("/api/logs");

        eventSource.onmessage = (event) => {
            if (!event.data) return;
            try {
                const log = JSON.parse(event.data);
                appendLogRow(log);
            } catch (e) {
                // Ignore parse errors
            }
        };

        eventSource.onerror = () => {
            // Auto-reconnect after 3s
            eventSource.close();
            setTimeout(initLogStream, 3000);
        };
    }

    function appendLogRow(log) {
        const row = document.createElement("div");
        row.className = `log-row ${log.level.toLowerCase()}`;

        let tagClass = "tag-info";
        if (log.level === "SUCCESS") tagClass = "tag-success";
        else if (log.level === "TYPING") tagClass = "tag-typing";
        else if (log.level === "SEEN") tagClass = "tag-seen";
        else if (log.level === "COMMENT") tagClass = "tag-comment";
        else if (log.level === "WARN") tagClass = "tag-warn";
        else if (log.level === "ERROR") tagClass = "tag-error";

        row.innerHTML = `
            <span class="log-time">[${log.timestamp}]</span>
            <span class="log-tag ${tagClass}">${log.level}</span>
            <span class="log-text">${escapeHtml(log.message)}</span>
        `;

        terminalLogs.appendChild(row);

        // Keep maximum 400 DOM nodes in terminal to keep browser fast
        while (terminalLogs.children.length > 400) {
            terminalLogs.removeChild(terminalLogs.firstChild);
        }

        if (autoScrollCheck.checked) {
            terminalContainer.scrollTop = terminalContainer.scrollHeight;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    // Start SSE stream
    initLogStream();
});
