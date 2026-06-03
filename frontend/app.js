// ============================================================
// Academic Assistant — Frontend App
// ============================================================

const API_BASE = window.API_BASE || "/api/v1";

// ── i18n strings ──────────────────────────────────────────────
const STRINGS = {
    ar: {
        brandTitle:      "مجيب",
        brandSub:        "مرشدك الجامعي الذكي",
        usernamePH:      "اسم المستخدم",
        passwordPH:      "كلمة المرور",
        loginBtn:        "تسجيل الدخول",
        headerTitle:     "مجيب",
        onlineStatus:    "متصل",
        chatPH:          "اسأل عن اللوائح، المعدل، التدريب...",
        langLabel:       "EN",
        welcome:         "أهلاً بك! أنا مساعدك الأكاديمي الذكي.\nيمكنك الكتابة أو الضغط على الميكروفون للتحدث باللغة العربية أو الإنجليزية. 🎓",
        reasoning:       "الأسباب",
        sources:         "المصادر",
        confidence:      "الثقة",
        credits:         "ساعات",
        cleared:         "تم مسح المحادثة",
        noSpeech:        "لم أسمع شيئاً، حاول مرة أخرى",
        listening:       "أستمع...",
        errorLogin:      "فشل تسجيل الدخول",
        errorServer:     "خطأ في الاتصال بالخادم",
        decisionLabels: {
            APPROVED:    "✅ موافق",
            DENIED:      "❌ مرفوض",
            CONDITIONAL: "⚠️ مشروط",
            PENDING:     "🕐 قيد المراجعة",
            INFO:        "ℹ️ معلومات",
        },
    },
    en: {
        brandTitle:      "Mujeeb",
        brandSub:        "Your smart university guide",
        usernamePH:      "Username",
        passwordPH:      "Password",
        loginBtn:        "Sign In",
        headerTitle:     "Mujeeb",
        onlineStatus:    "Online",
        chatPH:          "Ask about GPA, graduation, registration policy...",
        langLabel:       "عربي",
        welcome:         "Welcome! I'm your Academic Assistant.\nType or tap the microphone to speak in Arabic or English. 🎓",
        reasoning:       "Reasoning",
        sources:         "Sources",
        confidence:      "Confidence",
        credits:         "Credits",
        cleared:         "Chat cleared",
        noSpeech:        "Didn't catch that, please try again",
        listening:       "Listening...",
        errorLogin:      "Login failed",
        errorServer:     "Error communicating with the server",
        decisionLabels: {
            APPROVED:    "✅ Approved",
            DENIED:      "❌ Denied",
            CONDITIONAL: "⚠️ Conditional",
            PENDING:     "🕐 Pending",
            INFO:        "ℹ️ Info",
        },
    },
};

// ── State ─────────────────────────────────────────────────────
let jwtToken      = localStorage.getItem('academic_token');
let currentLang   = localStorage.getItem('academic_lang') || 'ar';
let currentUser   = JSON.parse(localStorage.getItem('academic_user') || 'null');
let isVoiceEnabled = true;
let voiceSpeed    = parseFloat(localStorage.getItem('academic_voice_speed') || '1.3');
let sessionId     = null;
let currentAudio  = null;
let isRecording   = false;

// ── DOM refs ──────────────────────────────────────────────────
const loginScreen    = document.getElementById('login-screen');
const chatScreen     = document.getElementById('chat-screen');
const loginForm      = document.getElementById('login-form');
const loginError     = document.getElementById('login-error');
const logoutBtn      = document.getElementById('logout-btn');
const chatForm       = document.getElementById('chat-form');
const questionInput  = document.getElementById('question-input');
const chatMessages   = document.getElementById('chat-messages');
const micBtn         = document.getElementById('mic-btn');
const voiceToggleBtn = document.getElementById('voice-toggle-btn');
const voiceSpeedSelect = document.getElementById('voice-speed-select');
const clearBtn       = document.getElementById('clear-btn');
const langToggleBtn  = document.getElementById('lang-toggle-btn');
const userDisplay    = document.getElementById('user-display');
const suggestionsEl  = document.getElementById('suggestions');
const toastEl        = document.getElementById('toast');

// ── Shorthand translator ──────────────────────────────────────
function t(key) {
    return STRINGS[currentLang]?.[key] ?? STRINGS.ar[key] ?? key;
}

// ── Language system ───────────────────────────────────────────
function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('academic_lang', lang);

    const html = document.documentElement;
    html.lang = lang === 'ar' ? 'ar' : 'en';
    html.dir  = lang === 'ar' ? 'rtl' : 'ltr';

    if (recognition) {
        recognition.lang = lang === 'ar' ? 'ar-SA' : 'en-US';
    }

    // Update lang pills on login screen
    document.getElementById('lang-ar-btn')?.classList.toggle('active', lang === 'ar');
    document.getElementById('lang-en-btn')?.classList.toggle('active', lang === 'en');

    updateUIText();
    updateSuggestionChips();
}

function updateUIText() {
    const s = STRINGS[currentLang];
    setText('brand-title',    s.brandTitle);
    setText('brand-sub',      s.brandSub);
    setText('login-btn-text', s.loginBtn);
    setText('header-title',   s.headerTitle);
    setText('online-status',  s.onlineStatus);
    setText('lang-label',     s.langLabel);
    setPlaceholder('username',        s.usernamePH);
    setPlaceholder('password',        s.passwordPH);
    setPlaceholder('question-input',  s.chatPH);
    setText('quick-label', currentLang === 'ar' ? 'دخول سريع:' : 'Quick login:');
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}
function setPlaceholder(id, val) {
    const el = document.getElementById(id);
    if (el) el.placeholder = val;
}

function updateSuggestionChips() {
    document.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.textContent = chip.dataset[currentLang] || chip.dataset.ar;
    });
}

// ── Session ───────────────────────────────────────────────────
function getSessionId() {
    if (!sessionId) {
        sessionId = `sess_${currentUser?.user_id ?? 'guest'}_${Date.now()}`;
    }
    return sessionId;
}

// ── Screen management ─────────────────────────────────────────
function showScreen(screen) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    screen.classList.add('active');
}

function updateUserDisplay() {
    if (!currentUser) { userDisplay.style.display = 'none'; return; }
    const icon = currentUser.role === 'student' ? '🎓'
               : currentUser.role === 'admin'   ? '⚙️'
               : currentUser.role === 'advisor' ? '👨‍🏫' : '👤';
    userDisplay.textContent = `${icon} ${currentUser.username}`;
    userDisplay.style.display = 'flex';
}

// ── Toast ─────────────────────────────────────────────────────
let toastTimer;
function showToast(msg, ms = 2500) {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove('show'), ms);
}

// ── Speech Recognition ────────────────────────────────────────
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = currentLang === 'ar' ? 'ar-SA' : 'en-US';

    recognition.onstart = () => {
        isRecording = true;
        micBtn.classList.add('recording');
        micBtn.querySelector('i').className = 'ph-fill ph-microphone-slash';
        questionInput.placeholder = t('listening');
    };

    recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        questionInput.value = transcript;
        stopRecording();
        chatForm.dispatchEvent(new Event('submit'));
    };

    recognition.onerror = (e) => {
        stopRecording();
        if (e.error === 'no-speech') showToast(t('noSpeech'));
    };

    recognition.onend = () => stopRecording();
} else {
    micBtn.style.display = 'none';
}

function stopRecording() {
    isRecording = false;
    micBtn.classList.remove('recording');
    micBtn.querySelector('i').className = 'ph-fill ph-microphone';
    questionInput.placeholder = t('chatPH');
}

micBtn.addEventListener('click', () => {
    if (!recognition) return;
    if (isRecording) recognition.stop();
    else recognition.start();
});

// ── Text-to-Speech ────────────────────────────────────────────
voiceToggleBtn.addEventListener('click', () => {
    isVoiceEnabled = !isVoiceEnabled;
    voiceToggleBtn.classList.toggle('voice-off', !isVoiceEnabled);
    voiceToggleBtn.querySelector('i').className = isVoiceEnabled
        ? 'ph-fill ph-speaker-high'
        : 'ph-fill ph-speaker-slash';
    if (!isVoiceEnabled) stopSpeech();
});

function stopSpeech() {
    window.speechSynthesis?.cancel();
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
}

async function speak(text) {
    if (!isVoiceEnabled || !text) return;
    stopSpeech();
    // Trim to 500 chars and strip markdown symbols for cleaner speech
    const clean = text.replace(/[#*`_\[\]>]/g, '').slice(0, 500);

    if (currentLang === 'ar') {
        // Try Munsit (Arabic TTS API) first, fall back to browser
        const ok = await speakViaMunsit(clean);
        if (!ok) speakViaBrowser(clean, 'ar-SA');
    } else {
        speakViaBrowser(clean, 'en-US');
    }
}

async function speakViaMunsit(text) {
    try {
        const res = await fetch(`${API_BASE}/tts`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${jwtToken}`,
            },
            body: JSON.stringify({ text, voice_id: 'ar-najdi-male-2', speed: voiceSpeed }),
        });
        if (!res.ok) {
            const errBody = await res.text();
            console.error(`Munsit TTS failed: ${res.status}`, errBody);
            return false;
        }
        const blob = await res.blob();
        if (!blob || blob.size < 100) {
            console.warn('Munsit returned empty or too-small audio blob:', blob?.size);
            return false;
        }
        const url  = URL.createObjectURL(blob);
        currentAudio = new Audio(url);
        currentAudio.onended = () => { URL.revokeObjectURL(url); currentAudio = null; };
        currentAudio.play().catch(err => {
            console.error('Munsit playback play() promise rejected:', err);
        });
        return true;
    } catch (e) {
        console.error('Munsit TTS error:', e);
        return false;
    }
}

function speakViaBrowser(text, lang) {
    if (!window.speechSynthesis) return;
    const utt = new SpeechSynthesisUtterance(text);
    utt.lang = lang;
    utt.rate = voiceSpeed;
    window.speechSynthesis.speak(utt);
}

// ── Language toggle button ────────────────────────────────────
langToggleBtn.addEventListener('click', () => {
    setLanguage(currentLang === 'ar' ? 'en' : 'ar');
});

// ── Suggestion chips ──────────────────────────────────────────
document.querySelectorAll('.suggestion-chip').forEach(chip => {
    chip.addEventListener('click', () => {
        questionInput.value = chip.dataset[currentLang] || chip.dataset.ar;
        hideSuggestions();
        chatForm.dispatchEvent(new Event('submit'));
    });
});

function showSuggestions() { suggestionsEl.style.display = 'flex'; }
function hideSuggestions()  { suggestionsEl.style.display = 'none'; }

// ── Clear chat ────────────────────────────────────────────────
clearBtn.addEventListener('click', () => {
    chatMessages.innerHTML = '';
    sessionId = null;
    appendWelcomeMessage();
    showSuggestions();
    showToast(t('cleared'));
});

// ── Welcome message ───────────────────────────────────────────
function appendWelcomeMessage() {
    const html = t('welcome')
        .split('\n')
        .map(l => `<p>${l}</p>`)
        .join('');
    appendMessage('assistant welcome', html);
}

// ── Message helpers ───────────────────────────────────────────
function appendMessage(type, htmlContent) {
    const div = document.createElement('div');
    div.className = `message ${type}`;
    if (type.includes('assistant') && !type.includes('welcome')) {
        div.innerHTML = `
            <div class="message-wrapper">
                <div class="bot-avatar-small">
                    <img src="robot.png" alt="Mascot">
                </div>
                <div class="bubble">${htmlContent}</div>
            </div>`;
    } else {
        div.innerHTML = `<div class="bubble">${htmlContent}</div>`;
    }
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
}

function appendTypingIndicator() {
    return appendMessage('assistant', `
        <div class="typing-indicator">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>`);
}

function appendStreamingMessage() {
    const div    = document.createElement('div');
    div.className = 'message assistant';
    
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper';
    
    const avatar = document.createElement('div');
    avatar.className = 'bot-avatar-small';
    avatar.innerHTML = `<img src="robot.png" alt="Mascot">`;
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    const text   = document.createElement('p');
    text.className = 'streaming-text';
    
    bubble.appendChild(text);
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    div.appendChild(wrapper);
    
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return { div, bubble, text };
}

// ── Response metadata renderer ────────────────────────────────
function formatMetadataHtml(data) {
    let html = '';

    // Student data card
    if (data.student_data) {
        const sd = data.student_data;
        html += `<div class="student-data-card">`;
        if (sd.full_name)      html += `<span>👤 ${escHtml(sd.full_name)}</span>`;
        if (sd.gpa != null)    html += `<span>📊 GPA <strong>${sd.gpa.toFixed(2)}</strong></span>`;
        if (sd.total_credits != null) html += `<span>📚 ${t('credits')} <strong>${sd.total_credits}</strong></span>`;
        html += `</div>`;
    }

    // Decision badge
    if (data.decision && data.decision !== 'INFO') {
        const label = t('decisionLabels')[data.decision] || data.decision;
        html += `<div class="decision-badge decision-${data.decision}">${label}</div>`;
    }

    // Confidence bar
    if (data.confidence != null) {
        const pct = Math.round(data.confidence * 100);
        html += `<div class="confidence-row">
            <span class="confidence-label">${t('confidence')}: ${pct}%</span>
            <div class="confidence-track">
                <div class="confidence-fill" style="width:${pct}%"></div>
            </div>
        </div>`;
    }

    return html;
}

// ── SSE stream parser ─────────────────────────────────────────
function parseSSE(text) {
    const events = [];
    let cur = {};
    for (const line of text.split('\n')) {
        if (line.startsWith('event: '))      cur.event = line.slice(7).trim();
        else if (line.startsWith('data: '))  cur.data  = line.slice(6);
        else if (line === '' && cur.event)   { events.push({ ...cur }); cur = {}; }
    }
    return events;
}

// ── Login ─────────────────────────────────────────────────────
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const btn      = document.getElementById('login-btn');

    btn.disabled = true;
    btn.innerHTML = `<i class="ph ph-circle-notch spin"></i>`;
    loginError.textContent = '';

    try {
        const res  = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || t('errorLogin'));

        jwtToken = data.access_token;
        localStorage.setItem('academic_token', jwtToken);

        currentUser = {
            username:   data.username,
            role:       data.role,
            student_id: data.student_id,
            user_id:    data.user_id,
        };
        localStorage.setItem('academic_user', JSON.stringify(currentUser));

        sessionId = null;
        chatMessages.innerHTML = '';
        appendWelcomeMessage();
        showSuggestions();
        updateUserDisplay();
        showScreen(chatScreen);

    } catch (err) {
        loginError.textContent = err.message;
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span id="login-btn-text">${t('loginBtn')}</span><i class="ph-bold ph-sign-in"></i>`;
    }
});

// ── Logout ────────────────────────────────────────────────────
logoutBtn.addEventListener('click', () => {
    stopSpeech();
    localStorage.removeItem('academic_token');
    localStorage.removeItem('academic_user');
    jwtToken = null; currentUser = null; sessionId = null;
    userDisplay.style.display = 'none';
    document.getElementById('password').value = '';
    showScreen(loginScreen);
});

// ── Chat submit — streaming with non-streaming fallback ───────
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = questionInput.value.trim();
    if (!question) return;

    hideSuggestions();
    appendMessage('user', `<p>${escHtml(question)}</p>`);
    questionInput.value = '';

    const typingMsg = appendTypingIndicator();

    try {
        await sendStreaming(question, typingMsg);
    } catch {
        // Streaming failed — try regular endpoint
        try {
            await sendRegular(question, typingMsg);
        } catch (err) {
            if (typingMsg.parentNode) typingMsg.remove();
            appendMessage('assistant',
                `<p class="error-msg"><i class="ph-fill ph-warning-circle"></i> ${err.message}</p>`);
        }
    }
});

async function sendStreaming(question, typingMsg) {
    const res = await fetch(`${API_BASE}/ask/stream`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${jwtToken}`,
        },
        body: JSON.stringify({ question, session_id: getSessionId() }),
    });

    if (res.status === 401) { logoutBtn.click(); return; }
    if (!res.ok) throw new Error(t('errorServer'));

    typingMsg.remove();
    const { bubble, text } = appendStreamingMessage();

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '', fullAnswer = '', metadata = null;

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = parseSSE(buffer);
        const cut = buffer.lastIndexOf('\n\n');
        if (cut !== -1) buffer = buffer.slice(cut + 2);

        for (const ev of events) {
            if (ev.event === 'token' && ev.data) {
                try {
                    fullAnswer += JSON.parse(ev.data).token;
                    text.textContent = fullAnswer;
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                } catch { /* skip */ }
            } else if (ev.event === 'metadata' && ev.data) {
                try { metadata = JSON.parse(ev.data); } catch { /* skip */ }
            }
        }
    }

    text.classList.remove('streaming-text');

    if (metadata) {
        if (metadata.answer) {
            text.textContent = metadata.answer;
        }
        appendMetadata(bubble, metadata);
    }
    speak(metadata?.answer || fullAnswer);
}

async function sendRegular(question, typingMsg) {
    const res = await fetch(`${API_BASE}/ask`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${jwtToken}`,
        },
        body: JSON.stringify({ question, session_id: getSessionId() }),
    });

    if (res.status === 401) { logoutBtn.click(); return; }
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || t('errorServer'));

    typingMsg.remove();
    const msgDiv = appendMessage('assistant', `<p>${escHtml(data.answer)}</p>`);
    appendMetadata(msgDiv.querySelector('.bubble'), data);
    speak(data.answer);
}

function appendMetadata(bubble, data) {
    const html = formatMetadataHtml(data);
    if (!html) return;
    const div = document.createElement('div');
    div.className = 'response-metadata';
    div.innerHTML = html;
    bubble.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ── XSS helper ────────────────────────────────────────────────
function escHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ── Quick-login buttons ──────────────────────────────────────
document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.getElementById('username').value = btn.dataset.u;
        document.getElementById('password').value = btn.dataset.p;
        loginForm.dispatchEvent(new Event('submit'));
    });
});

// ── Initialise ────────────────────────────────────────────────
setLanguage(currentLang);

if (voiceSpeedSelect) {
    voiceSpeedSelect.value = voiceSpeed.toString();
    voiceSpeedSelect.addEventListener('change', (e) => {
        voiceSpeed = parseFloat(e.target.value);
        localStorage.setItem('academic_voice_speed', voiceSpeed);
    });
}

if (jwtToken && currentUser) {
    appendWelcomeMessage();
    showSuggestions();
    updateUserDisplay();
    showScreen(chatScreen);
} else {
    showScreen(loginScreen);
}
