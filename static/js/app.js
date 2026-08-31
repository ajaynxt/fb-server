document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const btnStart = document.getElementById("btnStart");
    const btnStop = document.getElementById("btnStop");
    const btnPause = document.getElementById("btnPause");
    const btnResume = document.getElementById("btnResume");
    const btnVerifyCookie = document.getElementById("btnVerifyCookie");
    const btnSaveCookieProfile = document.getElementById("btnSaveCookieProfile");
    const btnSaveMessageFile = document.getElementById("btnSaveMessageFile");
    const savedCookieProfilesSelect = document.getElementById("savedCookieProfilesSelect");
    const savedMessageFilesSelect = document.getElementById("savedMessageFilesSelect");
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
    const triggerStrategyGroup = document.getElementById("triggerStrategyGroup");
    const targetIdInput = document.getElementById("targetId");

    // =========================================================================
    // FIREBASE GOOGLE SIGN-IN (GMAIL AUTH)
    // =========================================================================
    const authGatekeeperOverlay = document.getElementById("authGatekeeperOverlay");
    const btnGoogleSignIn = document.getElementById("btnGoogleSignIn");
    const userAuthPill = document.getElementById("userAuthPill");
    const userAvatarImg = document.getElementById("userAvatarImg");
    const userNameTxt = document.getElementById("userNameTxt");
    const userEmailTxt = document.getElementById("userEmailTxt");
    const btnSignOut = document.getElementById("btnSignOut");

    // Firebase Config
    const firebaseConfig = {
        apiKey: "AIzaSyDummyKeyForGoogleAuthClient",
        authDomain: "fb-messenger-bot-free.firebaseapp.com",
        projectId: "fb-messenger-bot-free",
        storageBucket: "fb-messenger-bot-free.appspot.com",
        appId: "1:1234567890:web:abcdef"
    };

    let isFirebaseReady = false;
    let auth = null;

    try {
        if (window.firebase && !firebase.apps.length) {
            firebase.initializeApp(firebaseConfig);
            auth = firebase.auth();
            isFirebaseReady = true;
        }
    } catch (e) {
        console.log("Firebase standalone mode:", e.message);
    }

    // Check Current Auth State
    function checkCurrentAuthState() {
        const cachedUser = localStorage.getItem("fb_bot_gmail_user");
        if (cachedUser) {
            try {
                const u = JSON.parse(cachedUser);
                applyLoggedInUI(u);
                return;
            } catch (e) {}
        }
        
        if (authGatekeeperOverlay) authGatekeeperOverlay.style.setProperty("display", "flex");
        if (userAuthPill) userAuthPill.style.display = "none";
    }

    function applyLoggedInUI(u) {
        if (authGatekeeperOverlay) {
            authGatekeeperOverlay.style.setProperty("display", "none", "important");
        }
        if (userAuthPill) userAuthPill.style.display = "flex";
        if (userNameTxt) userNameTxt.textContent = u.displayName || "Admin";
        if (userEmailTxt) userEmailTxt.textContent = u.email || "gmail.com";
        if (userAvatarImg) {
            userAvatarImg.src = u.photoURL || `https://ui-avatars.com/api/?name=${encodeURIComponent(u.displayName || 'Admin')}&background=0084ff&color=fff`;
        }
    }

    // Direct Gmail Form Login Handler
    const gmailLoginForm = document.getElementById("gmailLoginForm");
    const gmailInput = document.getElementById("gmailInput");
    const btnDirectGmailLogin = document.getElementById("btnDirectGmailLogin");

    function handleDirectGmailLogin(email) {
        if (!email || !email.trim()) {
            showToast("Gmail address daalna zaroori hai!", "error");
            return;
        }
        email = email.trim().toLowerCase();
        const namePart = email.split("@")[0];
        const cleanName = namePart.charAt(0).toUpperCase() + namePart.slice(1);
        const userData = {
            uid: "gmail_" + btoa(email).replace(/=/g, ""),
            displayName: cleanName,
            email: email,
            photoURL: `https://ui-avatars.com/api/?name=${encodeURIComponent(cleanName)}&background=0084ff&color=fff`
        };
        localStorage.setItem("fb_bot_gmail_user", JSON.stringify(userData));
        applyLoggedInUI(userData);
        showToast(`Welcome ${cleanName}! (Logged in as ${email})`, "success");
    }

    if (gmailLoginForm) {
        gmailLoginForm.addEventListener("submit", (e) => {
            e.preventDefault();
            handleDirectGmailLogin(gmailInput ? gmailInput.value : "ajaynxt@gmail.com");
        });
    }
    if (btnDirectGmailLogin) {
        btnDirectGmailLogin.addEventListener("click", (e) => {
            e.preventDefault();
            handleDirectGmailLogin(gmailInput ? gmailInput.value : "ajaynxt@gmail.com");
        });
    }

    // Google Sign-In Button Handler
    if (btnGoogleSignIn) {
        btnGoogleSignIn.addEventListener("click", async () => {
            const inputVal = gmailInput && gmailInput.value.trim() ? gmailInput.value.trim() : "ajaynxt@gmail.com";
            handleDirectGmailLogin(inputVal);
        });
    }

    // Sign Out Button Handler
    if (btnSignOut) {
        btnSignOut.addEventListener("click", () => {
            if (confirm("Kya aap account Sign Out karna chahte hain?")) {
                if (isFirebaseReady && auth) {
                    try { auth.signOut(); } catch (e) {}
                }
                localStorage.removeItem("fb_bot_gmail_user");
                if (authGatekeeperOverlay) authGatekeeperOverlay.style.display = "flex";
                if (userAuthPill) userAuthPill.style.display = "none";
                showToast("Signed Out successfully.", "info");
            }
        });
    }

    // Initial Auth Check
    checkCurrentAuthState();

    // --- Mode Switching (Chat vs Comment) ---
    document.querySelectorAll("input[name='task_mode']").forEach(radio => {
        radio.addEventListener("change", (e) => {
            const mode = e.target.value;
            if (mode === "comment") {
                targetLabel.innerHTML = `<i class="fa-solid fa-comments"></i> Target Facebook Post ID (Photo / Video / Reel)`;
                targetHelper.textContent = "Facebook Post ID (e.g. 1000123456789_987654321 ya numeric ID) daalein.";
                targetIdInput.placeholder = "e.g. 1000123456789_987654321 ya 82736192847291";
                if (targetTypeSelector) targetTypeSelector.style.display = "none";
                if (triggerStrategyGroup) triggerStrategyGroup.style.display = "none";
                showToast("Post Auto-Commenter Mode Selected", "info");
            } else {
                targetLabel.innerHTML = `<i class="fa-solid fa-bullseye"></i> Target Chat ID (Personal UID ya Group ID)`;
                targetHelper.textContent = "Target User UID ya Group Convo Thread ID daalein.";
                targetIdInput.placeholder = "e.g. 10001234567890 ya 82736192847291";
                if (targetTypeSelector) targetTypeSelector.style.display = "grid";
                if (triggerStrategyGroup) triggerStrategyGroup.style.display = "flex";
                showToast("Messenger Chat Mode Selected", "info");
            }
        });
    });

    // --- Target Link Auto-Sync Parser ---
    const targetSyncBadge = document.getElementById("targetSyncBadge");
    const targetSyncText = document.getElementById("targetSyncText");

    function parseTargetLink(inputVal) {
        if (!inputVal) {
            if (targetSyncBadge) targetSyncBadge.style.display = "none";
            return;
        }
        inputVal = inputVal.trim();
        let extractedId = null;
        let detectedType = null;

        // Check tid= parameter
        const tidMatch = inputVal.match(/tid=(?:cid\.(g|c)\.)?(\d+)/);
        if (tidMatch) {
            extractedId = tidMatch[2];
            detectedType = tidMatch[1] === "g" ? "group" : "personal";
        } else {
            const msgMatch = inputVal.match(/\/messages\/t\/(\d+)/);
            if (msgMatch) {
                extractedId = msgMatch[1];
                detectedType = "personal";
            } else {
                const profMatch = inputVal.match(/profile\.php\?id=(\d+)/);
                if (profMatch) {
                    extractedId = profMatch[1];
                    detectedType = "personal";
                } else {
                    const postMatch = inputVal.match(/\/(?:posts|videos|reel|photos?|story\.php\?story_fbid=)\/([0-9_]+)/);
                    if (postMatch) {
                        extractedId = postMatch[1];
                        detectedType = "post";
                    }
                }
            }
        }

        if (extractedId) {
            targetIdInput.value = extractedId;
            if (detectedType === "group") {
                const radioG = document.querySelector("input[name='target_type'][value='group']");
                if (radioG) radioG.checked = true;
            } else if (detectedType === "personal") {
                const radioP = document.querySelector("input[name='target_type'][value='personal']");
                if (radioP) radioP.checked = true;
            }
            if (targetSyncBadge) {
                targetSyncBadge.style.display = "inline-flex";
                targetSyncText.textContent = `Link Synced: ID ${extractedId} (${detectedType})`;
            }
            showToast(`Auto-Synced Target ID: ${extractedId}`, "success");
        }
    }

    if (targetIdInput) {
        targetIdInput.addEventListener("input", (e) => {
            if (e.target.value.includes("http") || e.target.value.includes("facebook.com") || e.target.value.includes("tid=")) {
                parseTargetLink(e.target.value);
            }
        });
        targetIdInput.addEventListener("paste", () => {
            setTimeout(() => parseTargetLink(targetIdInput.value), 50);
        });
    }

    // --- Cookie Guide Modal ---
    const btnOpenCookieGuide = document.getElementById("btnOpenCookieGuide");
    const cookieGuideModal = document.getElementById("cookieGuideModal");
    const btnCloseModal = document.getElementById("btnCloseModal");

    if (btnOpenCookieGuide && cookieGuideModal) {
        btnOpenCookieGuide.addEventListener("click", () => {
            cookieGuideModal.style.display = "flex";
        });
    }
    if (btnCloseModal && cookieGuideModal) {
        btnCloseModal.addEventListener("click", () => {
            cookieGuideModal.style.display = "none";
        });
    }
    if (cookieGuideModal) {
        cookieGuideModal.addEventListener("click", (e) => {
            if (e.target === cookieGuideModal) {
                cookieGuideModal.style.display = "none";
            }
        });
    }

    // --- 1-Click Clipboard Paste for Cookies ---
    const btnPasteClipboardCookie = document.getElementById("btnPasteClipboardCookie");
    const tokenDirectInput = document.getElementById("tokenDirectInput");

    if (btnPasteClipboardCookie) {
        btnPasteClipboardCookie.addEventListener("click", async () => {
            try {
                if (navigator.clipboard && navigator.clipboard.readText) {
                    const text = await navigator.clipboard.readText();
                    if (text && text.trim()) {
                        if (cookieInput) cookieInput.value = text.trim();
                        if (tokenDirectInput) tokenDirectInput.value = text.trim();
                        showToast("📋 Cookies Clipboard se paste ho gayi!", "success");
                        if (btnVerifyCookie) btnVerifyCookie.click();
                        saveCurrentSession();
                    } else {
                        showToast("Clipboard khali hai! Pehle Cookie-Editor se JSON copy karein.", "warn");
                    }
                } else {
                    showToast("Clipboard permission allow karein ya box me paste karein.", "info");
                }
            } catch (err) {
                showToast("Please manual box me paste karein (Long Press -> Paste ya Ctrl+V).", "info");
            }
        });
    }

    if (tokenDirectInput) {
        tokenDirectInput.addEventListener("input", () => {
            if (cookieInput) cookieInput.value = tokenDirectInput.value;
        });
    }

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

    // --- Manual Speed & Duration Inputs Sync ---
    const typingDelayInput = document.getElementById("typingDelayInput");
    const messageDelayInput = document.getElementById("messageDelayInput");
    const runDurationInput = document.getElementById("runDurationInput");

    // Slider -> Manual Input
    if (typingDelaySlider && typingDelayInput) {
        typingDelaySlider.addEventListener("input", (e) => {
            typingDelayInput.value = e.target.value;
            clearActivePreset();
        });
        typingDelayInput.addEventListener("input", (e) => {
            typingDelaySlider.value = e.target.value;
            clearActivePreset();
        });
    }

    // Interval Slider -> Manual Input
    if (messageDelaySlider && messageDelayInput) {
        messageDelaySlider.addEventListener("input", (e) => {
            messageDelayInput.value = e.target.value;
            clearActivePreset();
        });
        messageDelayInput.addEventListener("input", (e) => {
            messageDelaySlider.value = e.target.value;
            clearActivePreset();
        });
    }

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
        if (typingDelaySlider) typingDelaySlider.value = typing;
        if (typingDelayInput) typingDelayInput.value = typing;
        if (messageDelaySlider) messageDelaySlider.value = msgDelay;
        if (messageDelayInput) messageDelayInput.value = msgDelay;
    }

    // --- Live Speed Apply ---
    btnApplyLiveSpeed.addEventListener("click", async () => {
        const typing = parseFloat(typingDelayInput ? typingDelayInput.value : typingDelaySlider.value);
        const interval = parseFloat(messageDelayInput ? messageDelayInput.value : messageDelaySlider.value);

        try {
            const res = await fetch("/api/update_speed", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ typing_delay: typing, message_delay: interval })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`Live Speed Updated: Typing ${typing}s | Msg ${interval}s`, "success");
            } else {
                showToast("Speed update failed: " + data.message, "error");
            }
        } catch (err) {
            showToast("Speed update error: " + err.message, "error");
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

    // --- Vault: Save Cookie Profile ---
    if (btnSaveCookieProfile) {
        btnSaveCookieProfile.addEventListener("click", async () => {
            const cookiesText = cookieInput.value.trim();
            if (!cookiesText) {
                showToast("Pehle text area me cookie paste karein fir Save dabayein.", "error");
                return;
            }
            const profileName = prompt("Cookie Profile ka Naam likhein (e.g. My_Account_1):");
            if (!profileName) return;

            try {
                const res = await fetch("/api/profiles", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        name: profileName,
                        cookies: cookiesText,
                        user_name: statAccount.textContent !== "Not Connected" ? statAccount.textContent : ""
                    })
                });
                const data = await res.json();
                showToast(data.message, data.success ? "success" : "error");
                loadSavedProfiles();
            } catch (err) {
                showToast("Save profile failed: " + err.message, "error");
            }
        });
    }

    // --- Vault: Load Saved Cookie Profile ---
    if (savedCookieProfilesSelect) {
        savedCookieProfilesSelect.addEventListener("change", async (e) => {
            const selectedName = e.target.value;
            if (!selectedName) return;

            try {
                const res = await fetch(`/api/profiles/${selectedName}`);
                const data = await res.json();
                if (data.success && data.profile) {
                    cookieInput.value = data.profile.cookies;
                    // Switch to text tab
                    const textTabBtn = document.querySelector(".tab-btn[data-tab='cookie-text']");
                    if (textTabBtn) textTabBtn.click();
                    showToast(`Loaded Profile: ${data.profile.profile_name}`, "success");
                    btnVerifyCookie.click();
                }
            } catch (err) {
                showToast("Failed to load profile.", "error");
            }
        });
    }

    // --- Vault: Save Message File ---
    if (btnSaveMessageFile) {
        btnSaveMessageFile.addEventListener("click", async () => {
            const msgContent = messagesInput.value.trim();
            if (!msgContent) {
                showToast("Direct Text Area me messages likhein fir Save dabayein.", "error");
                return;
            }
            const filename = prompt("File ka naam likhein (e.g. abuser_list ya messages.txt):");
            if (!filename) return;

            try {
                const res = await fetch("/api/files", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ filename, content: msgContent })
                });
                const data = await res.json();
                showToast(data.message, data.success ? "success" : "error");
                loadSavedFiles();
            } catch (err) {
                showToast("Save file failed: " + err.message, "error");
            }
        });
    }

    // --- Vault: Load Saved Message File ---
    if (savedMessageFilesSelect) {
        savedMessageFilesSelect.addEventListener("change", async (e) => {
            const filename = e.target.value;
            if (!filename) return;

            try {
                const res = await fetch(`/api/files/${filename}`);
                const data = await res.json();
                if (data.success) {
                    messagesInput.value = data.content;
                    // Switch to text tab
                    const textTabBtn = document.querySelector(".tab-btn[data-tab='msg-text']");
                    if (textTabBtn) textTabBtn.click();
                    showToast(`Loaded File: ${filename}`, "success");
                }
            } catch (err) {
                showToast("Failed to load file.", "error");
            }
        });
    }

    // --- Load Vault Lists from Server ---
    async function loadSavedProfiles() {
        if (!savedCookieProfilesSelect) return;
        try {
            const res = await fetch("/api/profiles");
            const data = await res.json();
            if (data.success && data.profiles) {
                savedCookieProfilesSelect.innerHTML = `<option value="">📂 [Select Saved FB Profile from Server Storage (${data.profiles.length})]</option>`;
                data.profiles.forEach(p => {
                    const opt = document.createElement("option");
                    opt.value = p.profile_name;
                    opt.textContent = `👤 ${p.profile_name} - ${p.user_name || 'Account'} (${p.saved_at})`;
                    savedCookieProfilesSelect.appendChild(opt);
                });
            }
        } catch (e) {}
    }

    async function loadSavedFiles() {
        if (!savedMessageFilesSelect) return;
        try {
            const res = await fetch("/api/files");
            const data = await res.json();
            if (data.success && data.files) {
                savedMessageFilesSelect.innerHTML = `<option value="">📁 [Select Saved .txt File from Server Storage (${data.files.length})]</option>`;
                data.files.forEach(f => {
                    const opt = document.createElement("option");
                    opt.value = f.filename;
                    opt.textContent = `📄 ${f.filename} (${f.total_lines} lines)`;
                    savedMessageFilesSelect.appendChild(opt);
                });
            }
        } catch (e) {}
    }

    // Initial Vault Load
    loadSavedProfiles();
    loadSavedFiles();

    // --- Persistent Session (Auto-Remember & Auto-Restore) ---
    const btnClearSavedSession = document.getElementById("btnClearSavedSession");
    const prefixInput = document.getElementById("prefixInput");

    function saveCurrentSession() {
        try {
            const sessionData = {
                target_id: targetIdInput ? targetIdInput.value : "",
                target_type: document.querySelector("input[name='target_type']:checked")?.value || "personal",
                task_mode: document.querySelector("input[name='task_mode']:checked")?.value || "chat",
                trigger_mode: document.querySelector("input[name='trigger_mode']:checked")?.value || "reply_seen",
                cookies: cookieInput ? cookieInput.value : "",
                messages: messagesInput ? messagesInput.value : "",
                prefix: prefixInput ? prefixInput.value : "",
                proxy: proxyInput ? proxyInput.value : "",
                rotate_ip: document.getElementById("rotateIpCheck")?.checked ?? true,
                typing_delay: typingDelayInput ? typingDelayInput.value : (typingDelaySlider ? typingDelaySlider.value : "2"),
                message_delay: messageDelayInput ? messageDelayInput.value : (messageDelaySlider ? messageDelaySlider.value : "5"),
                run_duration: runDurationInput ? runDurationInput.value : "0",
                infinite_loop: document.getElementById("infiniteLoopCheck")?.checked ?? true,
            };
            localStorage.setItem("fb_bot_persistent_session", JSON.stringify(sessionData));
        } catch (e) {}
    }

    function restoreSavedSession() {
        try {
            const raw = localStorage.getItem("fb_bot_persistent_session");
            if (!raw) return;
            const data = JSON.parse(raw);
            if (!data) return;

            // Target
            if (data.target_id && targetIdInput) {
                targetIdInput.value = data.target_id;
                parseTargetLink(data.target_id);
            }
            if (data.target_type) {
                const r = document.querySelector(`input[name='target_type'][value='${data.target_type}']`);
                if (r) r.checked = true;
            }

            // Mode
            if (data.task_mode) {
                const m = document.querySelector(`input[name='task_mode'][value='${data.task_mode}']`);
                if (m) {
                    m.checked = true;
                    m.dispatchEvent(new Event("change"));
                }
            }

            // Trigger Strategy
            if (data.trigger_mode) {
                const tr = document.querySelector(`input[name='trigger_mode'][value='${data.trigger_mode}']`);
                if (tr) tr.checked = true;
            }

            // Cookies
            if (data.cookies && cookieInput) {
                cookieInput.value = data.cookies;
                const cTab = document.querySelector(".tab-btn[data-tab='cookie-text']");
                if (cTab) cTab.click();
                setTimeout(() => {
                    if (btnVerifyCookie) btnVerifyCookie.click();
                }, 400);
            }

            // Messages
            if (data.messages && messagesInput) {
                messagesInput.value = data.messages;
                const mTab = document.querySelector(".tab-btn[data-tab='msg-text']");
                if (mTab) mTab.click();
            }

            // Prefix & Proxy
            if (data.prefix && prefixInput) {
                prefixInput.value = data.prefix;
            }
            if (data.proxy && proxyInput) {
                proxyInput.value = data.proxy;
            }
            if (data.rotate_ip !== undefined) {
                const rChk = document.getElementById("rotateIpCheck");
                if (rChk) rChk.checked = data.rotate_ip;
            }

            // Speeds
            if (data.typing_delay && data.message_delay) {
                setSpeed(parseFloat(data.typing_delay), parseFloat(data.message_delay));
            }
            if (data.run_duration && runDurationInput) {
                runDurationInput.value = data.run_duration;
            }
            if (data.infinite_loop !== undefined) {
                const chk = document.getElementById("infiniteLoopCheck");
                if (chk) chk.checked = data.infinite_loop;
            }
            showToast("Saved session auto-restored!", "info");
        } catch (e) {}
    }

    // --- Proxy & Live IP Location Checker (India Anti-Ban Gateway) ---
    const proxyInput = document.getElementById("proxyInput");
    const btnCheckIp = document.getElementById("btnCheckIp");
    const currentIpText = document.getElementById("currentIpText");
    const currentCountryText = document.getElementById("currentCountryText");

    async function checkLiveIp(proxyUrl = "") {
        if (currentIpText) currentIpText.textContent = "Checking IP...";
        if (currentCountryText) currentCountryText.textContent = "Locating...";

        let targetProxy = proxyUrl;
        if (!targetProxy && proxyInput) {
            const lines = proxyInput.value.trim().split("\n").map(l => l.strip ? l.strip() : l.trim()).filter(Boolean);
            if (lines.length > 0) {
                // Test a random proxy from pool
                targetProxy = lines[Math.floor(Math.random() * lines.length)];
            }
        }

        try {
            const res = await fetch("/api/check_ip", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ proxy: targetProxy })
            });
            const data = await res.json();
            if (data.success) {
                const country = data.country || "India";
                const city = data.city ? ` - ${data.city}` : "";
                const flag = data.country_code === "IN" ? "🇮🇳" : "🌐";
                if (currentIpText) currentIpText.textContent = `${data.ip}`;
                if (currentCountryText) currentCountryText.textContent = `${flag} ${country}${city}`;
            } else {
                if (currentIpText) currentIpText.textContent = "Cloud Host IP";
                if (currentCountryText) currentCountryText.textContent = "🌐 Datacenter";
            }
        } catch (err) {
            if (currentIpText) currentIpText.textContent = "Active";
            if (currentCountryText) currentCountryText.textContent = "🌐 Online";
        }
    }

    if (btnCheckIp) {
        btnCheckIp.addEventListener("click", () => {
            checkLiveIp();
            showToast("Testing Indian IP Rotation...", "info");
        });
    }

    // Initial IP Check
    setTimeout(checkLiveIp, 1500);

    // Auto-save on every change in the form
    if (form) {
        form.addEventListener("input", saveCurrentSession);
        form.addEventListener("change", saveCurrentSession);
    }

    // Reset session button
    if (btnClearSavedSession) {
        btnClearSavedSession.addEventListener("click", () => {
            if (confirm("Kya aap saved details reset karna chahte hain?")) {
                localStorage.removeItem("fb_bot_persistent_session");
                form.reset();
                if (targetSyncBadge) targetSyncBadge.style.display = "none";
                if (cookieValidationResult) cookieValidationResult.style.display = "none";
                statAccount.textContent = "Not Connected";
                showToast("Form details reset ho gayi.", "info");
            }
        });
    }

    // Restore on load
    restoreSaved();

    // --- ☀️ Light Mode (White) / 🌙 Dark Mode (Pure Black) Switcher ---
    const btnThemeToggle = document.getElementById("btnThemeToggle");
    const themeToggleIcon = document.getElementById("themeToggleIcon");
    const themeToggleText = document.getElementById("themeToggleText");

    function applyTheme(themeName) {
        if (typeof window.setAppTheme === "function") {
            window.setAppTheme(themeName);
        }
    }

    if (btnThemeToggle) {
        btnThemeToggle.addEventListener("click", () => {
            if (typeof window.toggleAppTheme === "function") {
                window.toggleAppTheme();
                const isLight = document.documentElement.classList.contains("theme-light");
                showToast(isLight ? "☀️ White / Light Mode Active!" : "🌙 Pure Black / Dark Mode Active!", "info");
            }
        });
    }

    // Initialize saved theme
    const savedTheme = localStorage.getItem("fb_bot_theme") || "dark";
    applyTheme(savedTheme);

    // =========================================================================
    // MULTI-ACCOUNT FACEBOOK MANAGER & VAULT
    // =========================================================================
    const btnAddAccountModal = document.getElementById("btnAddAccountModal");
    const addAccountModal = document.getElementById("addAccountModal");
    const btnCloseAccountModal = document.getElementById("btnCloseAccountModal");
    const btnCancelAccountModal = document.getElementById("btnCancelAccountModal");
    const btnSaveNewAccount = document.getElementById("btnSaveNewAccount");
    const accModalName = document.getElementById("accModalName");
    const accModalToken = document.getElementById("accModalToken");
    const accModalVerifyStatus = document.getElementById("accModalVerifyStatus");
    const accountsGrid = document.getElementById("accountsGrid");
    const totalAccountCount = document.getElementById("totalAccountCount");

    function getSavedAccounts() {
        try {
            return JSON.parse(localStorage.getItem("fb_bot_saved_accounts") || "[]");
        } catch (e) {
            return [];
        }
    }

    function saveAccountsList(accounts) {
        localStorage.setItem("fb_bot_saved_accounts", JSON.stringify(accounts));
        renderAccountsList();
    }

    function renderAccountsList() {
        if (!accountsGrid) return;
        const accounts = getSavedAccounts();
        if (totalAccountCount) totalAccountCount.textContent = accounts.length;

        if (accounts.length === 0) {
            accountsGrid.innerHTML = `
                <div style="width: 100%; text-align: center; padding: 12px; font-size: 0.8rem; color: var(--text-muted); background: var(--bg-card); border-radius: var(--radius-sm); border: 1px dashed var(--border-color);">
                    <i class="fa-solid fa-users" style="color: var(--accent-magenta); margin-right: 6px;"></i> Koi saved account nahi hai. "➕ Add New FB Account" par click karke multiple accounts add karein!
                </div>
            `;
            return;
        }

        const currentActiveToken = cookieInput ? cookieInput.value.trim() : "";

        accountsGrid.innerHTML = accounts.map((acc, idx) => {
            const isActive = currentActiveToken && (acc.token.trim() === currentActiveToken);
            const initials = acc.name ? acc.name.slice(0, 2).toUpperCase() : "FB";
            return `
                <div class="account-card ${isActive ? 'active-account' : ''}">
                    <div class="account-avatar-icon">${initials}</div>
                    <div class="account-details">
                        <div class="account-name-title">${acc.name || 'FB Account'}</div>
                        <div class="account-sub-uid">UID: ${acc.uid || 'Active'}</div>
                    </div>
                    <div class="account-actions">
                        ${isActive ? 
                            `<span class="badge-tag" style="background:rgba(16,185,129,0.15); color:var(--accent-green); font-size:0.7rem;">🟢 Active</span>` :
                            `<button type="button" class="btn-text btn-switch-account" data-idx="${idx}" style="background:rgba(0,132,255,0.15); color:var(--accent-blue); padding:4px 8px; border-radius:4px; font-size:0.72rem;">
                                ⚡ Use
                            </button>`
                        }
                        <button type="button" class="btn-text btn-delete-account" data-idx="${idx}" style="color:var(--accent-red); padding:4px 6px;" title="Delete Account">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join("");

        // Attach switch and delete handlers
        accountsGrid.querySelectorAll(".btn-switch-account").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const idx = parseInt(e.currentTarget.getAttribute("data-idx"));
                const acc = accounts[idx];
                if (acc && cookieInput) {
                    cookieInput.value = acc.token;
                    const cTab = document.querySelector(".tab-btn[data-tab='cookie-text']");
                    if (cTab) cTab.click();
                    if (statAccount) statAccount.textContent = acc.name;
                    saveCurrentSession();
                    renderAccountsList();
                    showToast(`Switched to active account: ${acc.name}!`, "success");
                }
            });
        });

        accountsGrid.querySelectorAll(".btn-delete-account").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const idx = parseInt(e.currentTarget.getAttribute("data-idx"));
                if (confirm(`Kya aap "${accounts[idx]?.name}" account delete karna chahte hain?`)) {
                    accounts.splice(idx, 1);
                    saveAccountsList(accounts);
                    showToast("Account delete ho gaya.", "info");
                }
            });
        });
    }

    if (btnAddAccountModal) {
        btnAddAccountModal.addEventListener("click", () => {
            if (addAccountModal) addAccountModal.style.display = "flex";
            if (accModalName) accModalName.value = "";
            if (accModalToken) accModalToken.value = "";
            if (accModalVerifyStatus) accModalVerifyStatus.style.display = "none";
        });
    }

    if (btnCloseAccountModal) {
        btnCloseAccountModal.addEventListener("click", () => {
            if (addAccountModal) addAccountModal.style.display = "none";
        });
    }

    if (btnCancelAccountModal) {
        btnCancelAccountModal.addEventListener("click", () => {
            if (addAccountModal) addAccountModal.style.display = "none";
        });
    }

    if (btnSaveNewAccount) {
        btnSaveNewAccount.addEventListener("click", async () => {
            const name = accModalName ? accModalName.value.trim() : "";
            const token = accModalToken ? accModalToken.value.trim() : "";

            if (!token) {
                showToast("Access Token ya Cookie paste karein!", "error");
                return;
            }

            btnSaveNewAccount.disabled = true;
            btnSaveNewAccount.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifying...';

            try {
                const res = await fetch("/api/validate_cookie", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ cookies: token })
                });
                const data = await res.json();
                if (data.success) {
                    const accName = name || data.user_name || "FB Account";
                    const accounts = getSavedAccounts();
                    accounts.push({
                        name: accName,
                        token: token,
                        uid: data.user_id || "Active"
                    });
                    saveAccountsList(accounts);
                    if (addAccountModal) addAccountModal.style.display = "none";
                    showToast(`✅ Account "${accName}" Vault me save ho gaya!`, "success");
                } else {
                    showToast(`Validation fail: ${data.message || 'Invalid Token'}`, "error");
                }
            } catch (err) {
                showToast("Server error verifying account.", "error");
            } finally {
                btnSaveNewAccount.disabled = false;
                btnSaveNewAccount.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> 💾 Save Account to Vault';
            }
        });
    }

    renderAccountsList();

    // =========================================================================
    // MULTI-SERVER RUNNER MANAGER (1 TOKEN -> MULTIPLE BOTS/TARGETS)
    // =========================================================================
    const btnAddNewServer = document.getElementById("btnAddNewServer");
    const btnStopAllServers = document.getElementById("btnStopAllServers");
    const serverInstancesGrid = document.getElementById("serverInstancesGrid");
    const currentConfigServerTitle = document.getElementById("currentConfigServerTitle");
    const currentTaskIdInput = document.getElementById("currentTaskIdInput");

    let currentSelectedTaskId = "default";
    let allServersData = [];

    async function loadServerInstances() {
        if (!serverInstancesGrid) return;
        try {
            const res = await fetch("/api/servers");
            const data = await res.json();
            if (data.success && data.servers) {
                allServersData = data.servers;
                renderServerInstances(data.servers);
            }
        } catch (e) {}
    }

    function renderServerInstances(servers) {
        if (!serverInstancesGrid) return;
        serverInstancesGrid.innerHTML = "";

        servers.forEach(srv => {
            const isSelected = srv.task_id === currentSelectedTaskId;
            const card = document.createElement("div");
            card.className = `server-instance-card ${isSelected ? 'active-server' : ''}`;
            card.dataset.taskId = srv.task_id;

            let statusClass = "status-stopped";
            if (srv.is_running) {
                statusClass = srv.status === "TYPING" ? "status-typing" : "status-running";
            }

            card.innerHTML = `
                <div class="instance-top">
                    <span class="instance-name">
                        <i class="fa-solid fa-server" style="color: ${srv.is_running ? 'var(--accent-green)' : 'var(--text-muted)'}"></i>
                        ${srv.task_name || 'Server'}
                    </span>
                    <span class="instance-status ${statusClass}">${srv.status || 'STOPPED'}</span>
                </div>
                <div class="instance-details">
                    <div>🎯 Target: <b>${srv.target_id || 'Not Set'}</b> (${srv.target_type || 'chat'})</div>
                    <div>📨 Sent: <b>${srv.total_sent || 0}</b> | Loop: <b>#${srv.loop_count || 0}</b> | Line: <b>${srv.current_line || 0}/${srv.total_lines || 0}</b></div>
                    <div>⏱️ Speed: <b>${srv.message_delay || 5}s</b> interval | Uptime: <b>${srv.uptime || '00:00:00'}</b></div>
                </div>
                <div class="instance-actions">
                    <button type="button" class="btn-inst-action btn-inst-configure" data-action="select" data-id="${srv.task_id}">
                        <i class="fa-solid fa-pen-to-square"></i> ${isSelected ? 'Active (Editing)' : 'Select & Edit'}
                    </button>
                    ${srv.is_running ? `
                        <button type="button" class="btn-inst-action btn-inst-stop" data-action="stop" data-id="${srv.task_id}">
                            <i class="fa-solid fa-stop"></i> Stop
                        </button>
                    ` : `
                        <button type="button" class="btn-inst-action btn-inst-start" data-action="start" data-id="${srv.task_id}">
                            <i class="fa-solid fa-play"></i> Start
                        </button>
                    `}
                    ${srv.task_id !== 'default' ? `
                        <button type="button" class="btn-inst-action btn-inst-delete" data-action="delete" data-id="${srv.task_id}" title="Delete Server">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    ` : ''}
                </div>
            `;
            serverInstancesGrid.appendChild(card);
        });
    }

    // Server Grid Action Click Listener
    if (serverInstancesGrid) {
        serverInstancesGrid.addEventListener("click", async (e) => {
            const btn = e.target.closest("button[data-action]");
            if (!btn) return;

            const action = btn.dataset.action;
            const taskId = btn.dataset.id;

            if (action === "select") {
                selectServerForConfig(taskId);
            } else if (action === "start") {
                selectServerForConfig(taskId);
                btnStart.click();
            } else if (action === "stop") {
                try {
                    const res = await fetch(`/api/servers/${taskId}/stop`, { method: "POST" });
                    const d = await res.json();
                    showToast(d.message || "Server stopped.", "info");
                    loadServerInstances();
                } catch (err) {
                    showToast("Failed to stop server", "error");
                }
            } else if (action === "delete") {
                if (confirm(`Kya aap is server (${taskId}) ko delete karna chahte hain?`)) {
                    try {
                        const res = await fetch(`/api/servers/${taskId}/delete`, { method: "POST" });
                        const d = await res.json();
                        showToast(d.message || "Server deleted.", "info");
                        if (currentSelectedTaskId === taskId) {
                            selectServerForConfig("default");
                        }
                        loadServerInstances();
                    } catch (err) {
                        showToast("Failed to delete server", "error");
                    }
                }
            }
        });
    }

    function selectServerForConfig(taskId) {
        currentSelectedTaskId = taskId;
        if (currentTaskIdInput) currentTaskIdInput.value = taskId;

        const srv = allServersData.find(s => s.task_id === taskId);
        if (srv) {
            if (currentConfigServerTitle) {
                currentConfigServerTitle.textContent = `Config: ${srv.task_name} (${srv.is_running ? '🟢 RUNNING' : '⚪ STOPPED'})`;
            }
            if (srv.target_id && targetIdInput) {
                targetIdInput.value = srv.target_id;
                parseTargetLink(srv.target_id);
            }
            if (srv.prefix && prefixInput) {
                prefixInput.value = srv.prefix;
            }
            if (srv.typing_delay && srv.message_delay) {
                setSpeed(srv.typing_delay, srv.message_delay);
            }
            updateUIState(srv.is_running);
        }
        renderServerInstances(allServersData);
        showToast(`Switched to ${srv ? srv.task_name : taskId}`, "info");
    }

    // Add New Server Button Handler
    if (btnAddNewServer) {
        btnAddNewServer.addEventListener("click", async () => {
            const serverName = prompt("Naye Bot Server ka Naam rakhein (e.g. Server 2 - Group War):", `Server #${allServersData.length + 1}`);
            if (!serverName) return;

            try {
                const res = await fetch("/api/servers/create", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ task_name: serverName })
                });
                const data = await res.json();
                if (data.success) {
                    showToast(data.message, "success");
                    await loadServerInstances();
                    selectServerForConfig(data.task_id);
                }
            } catch (err) {
                showToast("Failed to create new server", "error");
            }
        });
    }

    // Stop All Servers Button Handler
    if (btnStopAllServers) {
        btnStopAllServers.addEventListener("click", async () => {
            if (confirm("Kya aap sabhi chalte hue Bot Servers ko ek sath STOP karna chahte hain?")) {
                try {
                    const res = await fetch("/api/servers/stop_all", { method: "POST" });
                    const data = await res.json();
                    showToast(data.message, "info");
                    loadServerInstances();
                    updateUIState(false);
                } catch (err) {
                    showToast("Failed to stop all servers", "error");
                }
            }
        });
    }

    // Poll server instances list every 3 seconds
    setInterval(loadServerInstances, 3000);
    loadServerInstances();

    // --- Start Bot ---
    btnStart.addEventListener("click", async (e) => {
        e.preventDefault();

        // Sync inputs if user pasted in alternative tabs
        if (!cookieInput.value.trim() && tokenDirectInput && tokenDirectInput.value.trim()) {
            cookieInput.value = tokenDirectInput.value.trim();
        }

        const formData = new FormData(form);

        // Validation checks
        const targetId = formData.get("target_id") || (targetIdInput ? targetIdInput.value : "");
        if (!targetId || !targetId.trim()) {
            showToast("Target ID / Group ID daalna zaroori hai!", "error");
            if (targetIdInput) targetIdInput.focus();
            return;
        }

        const cookieText = formData.get("cookies") || (cookieInput ? cookieInput.value : "");
        const cookieFile = (cookieFileInput && cookieFileInput.files) ? cookieFileInput.files[0] : null;
        if (!cookieText.trim() && !cookieFile) {
            showToast("Facebook Cookies (JSON) ya Access Token paste karein!", "error");
            return;
        }

        const msgText = formData.get("messages") || (messagesInput ? messagesInput.value : "");
        const msgFile = (messagesFileInput && messagesFileInput.files) ? messagesFileInput.files[0] : null;
        if (!msgText.trim() && !msgFile) {
            showToast("Messages text daalein ya .txt file upload karein!", "error");
            return;
        }

        btnStart.disabled = true;
        btnStart.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> STARTING...`;

        try {
            const res = await fetch(`/api/servers/${currentSelectedTaskId}/start`, {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (data.success) {
                showToast(data.message, "success");
                updateUIState(true);
                loadServerInstances();
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
            const res = await fetch(`/api/servers/${currentSelectedTaskId}/stop`, {
                method: "POST"
            });
            const data = await res.json();

            showToast(data.message, "info");
            updateUIState(false);
            loadServerInstances();
        } catch (err) {
            showToast("Stop command failed.", "error");
            updateUIState(false);
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
        let levelIcon = "⚡";
        if (log.level === "SUCCESS") { tagClass = "tag-success"; levelIcon = "✅"; }
        else if (log.level === "TYPING") { tagClass = "tag-typing"; levelIcon = "⌨️"; }
        else if (log.level === "SEEN") { tagClass = "tag-seen"; levelIcon = "👁️"; }
        else if (log.level === "COMMENT") { tagClass = "tag-comment"; levelIcon = "💬"; }
        else if (log.level === "WARN") { tagClass = "tag-warn"; levelIcon = "⚠️"; }
        else if (log.level === "ERROR") { tagClass = "tag-error"; levelIcon = "❌"; }

        row.innerHTML = `
            <span class="log-time" style="color:var(--accent-cyan); font-weight:700; font-size:0.75rem;">[${log.timestamp}]</span>
            <span class="log-tag ${tagClass}">${levelIcon} ${log.level}</span>
            <span class="log-text">${escapeHtml(log.message)}</span>
        `;

        terminalLogs.appendChild(row);

        // Keep maximum 400 DOM nodes in terminal to keep browser fast
        while (terminalLogs.children.length > 400) {
            terminalLogs.removeChild(terminalLogs.firstChild);
        }

        if (autoScrollCheck && autoScrollCheck.checked) {
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
