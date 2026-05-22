const API_BASE = "http://localhost:8000/api/v1";

// DOM Elements
const loginScreen = document.getElementById('login-screen');
const chatScreen = document.getElementById('chat-screen');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const logoutBtn = document.getElementById('logout-btn');
const chatForm = document.getElementById('chat-form');
const questionInput = document.getElementById('question-input');
const chatMessages = document.getElementById('chat-messages');
const micBtn = document.getElementById('mic-btn');
const voiceToggleBtn = document.getElementById('voice-toggle-btn');

// State
let jwtToken = localStorage.getItem('academic_token');
let isVoiceEnabled = true;

// ----------------------------------------------------
// Web Speech API Setup
// ----------------------------------------------------
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isRecording = false;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    // Set to 'ar-SA' if you want arabic, or 'en-US' for english. 
    // Usually it defaults to the browser language or we can leave it empty to detect.
    recognition.lang = 'ar-SA'; 
    recognition.interimResults = false;

    recognition.onstart = () => {
        isRecording = true;
        micBtn.classList.add('recording');
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        questionInput.value = transcript;
        // Auto submit
        chatForm.dispatchEvent(new Event('submit'));
    };

    recognition.onerror = (event) => {
        console.error("Speech recognition error", event.error);
        isRecording = false;
        micBtn.classList.remove('recording');
    };

    recognition.onend = () => {
        isRecording = false;
        micBtn.classList.remove('recording');
    };
} else {
    micBtn.style.display = 'none'; // Hide if not supported
}

// Mic Button Handler
micBtn.addEventListener('click', () => {
    if (!recognition) return;
    if (isRecording) {
        recognition.stop();
    } else {
        recognition.start();
    }
});

// Voice Toggle Handler
voiceToggleBtn.addEventListener('click', () => {
    isVoiceEnabled = !isVoiceEnabled;
    if (isVoiceEnabled) {
        voiceToggleBtn.classList.remove('voice-off');
        voiceToggleBtn.classList.add('voice-on');
    } else {
        voiceToggleBtn.classList.remove('voice-on');
        voiceToggleBtn.classList.add('voice-off');
        window.speechSynthesis.cancel(); // Stop current speech
    }
});

// Audio State
let currentAudio = null;

// TTS Function (Using Munsit API)
async function speak(text) {
    if (!isVoiceEnabled) return;
    
    // Stop currently playing audio
    if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
    }
    
    // Remove markdown or special characters to make speech cleaner
    const cleanText = text.replace(/[#*`_\[\]]/g, '');
    
    try {
        const response = await fetch(`${API_BASE}/tts`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${jwtToken}`
            },
            body: JSON.stringify({
                text: cleanText,
                voice_id: "ar-najdi-male-2",
                speed: 1.0
            })
        });

        if (!response.ok) {
            console.error("TTS Failed:", await response.text());
            return;
        }

        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        
        currentAudio = new Audio(audioUrl);
        currentAudio.play();
        
        currentAudio.onended = () => {
            URL.revokeObjectURL(audioUrl);
            currentAudio = null;
        };

    } catch (err) {
        console.error("TTS Error:", err);
    }
}
// ----------------------------------------------------

// Initialize
if (jwtToken) {
    showScreen(chatScreen);
} else {
    showScreen(loginScreen);
}

// Utility: Switch Screens
function showScreen(screenElement) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    screenElement.classList.add('active');
}

// Utility: Append Message to Chat
function appendMessage(type, htmlContent) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;
    msgDiv.innerHTML = `<div class="bubble">${htmlContent}</div>`;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
}

function appendTypingIndicator() {
    return appendMessage('assistant', `
        <div class="typing-indicator">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
    `);
}

// Create a streaming message bubble that we can append text to
function appendStreamingMessage() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant';
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    const textContainer = document.createElement('p');
    textContainer.className = 'streaming-text';
    
    bubble.appendChild(textContainer);
    msgDiv.appendChild(bubble);
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return { msgDiv, bubble, textContainer };
}

// Format API Response (for metadata after streaming)
function formatMetadataHtml(data) {
    let html = '';

    if (data.decision && data.decision !== 'INFO') {
        html += `<div class="decision-badge decision-${data.decision}">${data.decision}</div>`;
    }

    if (data.reasoning && data.reasoning.length > 0) {
        html += `<h3>Reasoning</h3><ul>`;
        data.reasoning.forEach(r => {
            html += `<li>${r}</li>`;
        });
        html += `</ul>`;
    }

    if (data.citations && data.citations.length > 0) {
        html += `<div class="citations"><strong>Sources:</strong>`;
        data.citations.forEach(c => {
            html += `<div class="citation-box">
                <em>${c.source} (${c.section || ''})</em><br>
                ${c.text}
            </div>`;
        });
        html += `</div>`;
    }

    return html;
}

// Format full response (non-streaming fallback)
function formatAssistantResponse(data) {
    let html = `<p>${data.answer}</p>`;

    if (data.decision) {
        html += `<div class="decision-badge decision-${data.decision}">${data.decision}</div>`;
    }

    if (data.reasoning && data.reasoning.length > 0) {
        html += `<h3>Reasoning</h3><ul>`;
        data.reasoning.forEach(r => {
            html += `<li>${r}</li>`;
        });
        html += `</ul>`;
    }

    if (data.citations && data.citations.length > 0) {
        html += `<div class="citations"><strong>Sources:</strong>`;
        data.citations.forEach(c => {
            html += `<div class="citation-box">
                <em>${c.source} (${c.section})</em><br>
                ${c.text}
            </div>`;
        });
        html += `</div>`;
    }

    return html;
}

// Handle Login
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const btn = document.getElementById('login-btn');
    
    btn.disabled = true;
    btn.innerHTML = '<span>Signing In...</span> <i class="ph ph-spinner ph-spin"></i>';
    loginError.innerText = '';

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || "Login failed");
        }

        jwtToken = data.access_token;
        localStorage.setItem('academic_token', jwtToken);
        showScreen(chatScreen);
        
        // Clear old chat except welcome
        Array.from(chatMessages.children).forEach((child, index) => {
            if(index > 0) chatMessages.removeChild(child);
        });
        
    } catch (err) {
        loginError.innerText = err.message;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>Sign In</span> <i class="ph-bold ph-arrow-right"></i>';
    }
});

// Handle Logout
logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('academic_token');
    jwtToken = null;
    showScreen(loginScreen);
    document.getElementById('password').value = '';
});

// ============================================================
// SSE Streaming Chat Handler
// ============================================================

// Parse SSE text into events
function parseSSE(text) {
    const events = [];
    const lines = text.split('\n');
    let currentEvent = {};
    
    for (const line of lines) {
        if (line.startsWith('event: ')) {
            currentEvent.event = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
            currentEvent.data = line.slice(6);
        } else if (line === '' && currentEvent.event) {
            events.push({ ...currentEvent });
            currentEvent = {};
        }
    }
    
    return events;
}

// Handle Chat Submit — Streaming
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = questionInput.value.trim();
    if (!question) return;

    // Show User Message
    appendMessage('user', `<p>${question}</p>`);
    questionInput.value = '';
    
    // Show Typing Indicator
    const typingMsg = appendTypingIndicator();

    try {
        const res = await fetch(`${API_BASE}/ask/stream`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${jwtToken}`
            },
            body: JSON.stringify({ question })
        });

        if (res.status === 401) {
            logoutBtn.click();
            return;
        }

        if (!res.ok) {
            const errorData = await res.json().catch(() => ({ detail: 'Server error' }));
            throw new Error(errorData.detail || "Error communicating with the assistant");
        }

        // Remove typing indicator and create streaming bubble
        chatMessages.removeChild(typingMsg);
        const { msgDiv, bubble, textContainer } = appendStreamingMessage();

        // Read the SSE stream
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let fullAnswer = '';
        let metadata = null;
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            
            // Process complete SSE events from buffer
            const events = parseSSE(buffer);
            
            // Keep any incomplete event data in the buffer
            const lastDoubleNewline = buffer.lastIndexOf('\n\n');
            if (lastDoubleNewline !== -1) {
                buffer = buffer.slice(lastDoubleNewline + 2);
            }

            for (const sseEvent of events) {
                if (sseEvent.event === 'token' && sseEvent.data) {
                    try {
                        const tokenData = JSON.parse(sseEvent.data);
                        fullAnswer += tokenData.token;
                        textContainer.textContent = fullAnswer;
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    } catch (e) {
                        // Skip malformed token data
                    }
                } else if (sseEvent.event === 'metadata' && sseEvent.data) {
                    try {
                        metadata = JSON.parse(sseEvent.data);
                    } catch (e) {
                        console.error("Failed to parse metadata:", e);
                    }
                } else if (sseEvent.event === 'done') {
                    // Stream complete
                }
            }
        }

        // Remove the streaming cursor effect
        textContainer.classList.remove('streaming-text');

        // Append metadata (decision, reasoning, citations) below the answer
        if (metadata) {
            const metaHtml = formatMetadataHtml(metadata);
            if (metaHtml) {
                const metaDiv = document.createElement('div');
                metaDiv.className = 'response-metadata';
                metaDiv.innerHTML = metaHtml;
                bubble.appendChild(metaDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        }
        
        // Speak the answer after streaming is complete
        const answerToSpeak = metadata?.answer || fullAnswer;
        speak(answerToSpeak);

    } catch (err) {
        // Remove typing indicator if still present
        if (typingMsg.parentNode) {
            chatMessages.removeChild(typingMsg);
        }
        appendMessage('assistant', `<p style="color:var(--danger)"><i class="ph-fill ph-warning-circle"></i> ${err.message}</p>`);
    }
});
