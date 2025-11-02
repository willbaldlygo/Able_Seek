// Able2 Frontend Application

const API_BASE = 'http://localhost:8000';
let sessionId = null;

// DOM Elements
const messagesContainer = document.getElementById('messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const autonomySelect = document.getElementById('autonomy');
const sourcesSelect = document.getElementById('sources');
const statusText = document.getElementById('status-text');
const sessionInfo = document.getElementById('session-info');
const uploadBtn = document.getElementById('upload-btn');
const uploadModal = document.getElementById('upload-modal');
const fileInput = document.getElementById('file-input');
const uploadSubmit = document.getElementById('upload-submit');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    setupEventListeners();
    addWelcomeMessage();
});

// Setup Event Listeners
function setupEventListeners() {
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    uploadBtn.addEventListener('click', () => {
        uploadModal.classList.remove('hidden');
    });

    document.querySelector('.close').addEventListener('click', () => {
        uploadModal.classList.add('hidden');
    });

    uploadSubmit.addEventListener('click', uploadDocument);
}

// Add Welcome Message
function addWelcomeMessage() {
    addMessage('system', `
        <h3>Welcome to Able2!</h3>
        <p>I'm your multi-agent AI assistant with advanced knowledge retrieval.</p>
        <p><strong>Features:</strong></p>
        <ul>
            <li>📚 Hybrid document search (Vector + BM25 + GraphRAG)</li>
            <li>🤖 Multi-agent orchestration</li>
            <li>🎯 Adjustable autonomy levels</li>
            <li>📧 Email & Calendar integration (Phase 2)</li>
        </ul>
        <p><strong>Try:</strong> "Search for information about..." or upload a document to get started!</p>
    `);
}

// Check API Health
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();

        if (data.status === 'ok') {
            updateStatus('Connected', 'success');
        } else {
            updateStatus('API Degraded', 'warning');
        }
    } catch (error) {
        updateStatus('API Offline', 'error');
    }
}

// Send Message
async function sendMessage() {
    const message = userInput.value.trim();

    if (!message) return;

    // Add user message
    addMessage('user', message);
    userInput.value = '';

    // Show loading
    updateStatus('Processing...', 'loading');
    sendBtn.disabled = true;

    try {
        // Get selected sources
        const selectedOptions = Array.from(sourcesSelect.selectedOptions);
        const sources = selectedOptions.map(opt => opt.value);

        // Call API
        const response = await fetch(`${API_BASE}/chat/v2`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                autonomy_level: autonomySelect.value,
                sources: sources
            })
        });

        const data = await response.json();

        if (data.success) {
            // Update session ID
            sessionId = data.session_id;
            updateSessionInfo(sessionId);

            // Add assistant response
            let responseHtml = `<p>${data.message}</p>`;

            // Add sources if present
            if (data.sources && data.sources.length > 0) {
                responseHtml += '<div class="sources">';
                responseHtml += '<h4>Sources:</h4>';

                data.sources.slice(0, 5).forEach((source, i) => {
                    const filename = source.metadata?.filename || 'Unknown';
                    const score = (source.score * 100).toFixed(1);

                    responseHtml += `
                        <div class="source">
                            <strong>${i + 1}. ${filename}</strong>
                            <span class="score">${score}% relevant</span>
                            <p class="source-text">${source.text.substring(0, 200)}...</p>
                        </div>
                    `;
                });

                responseHtml += '</div>';
            }

            // Add reasoning if present
            if (data.reasoning) {
                responseHtml += `<div class="reasoning"><strong>Reasoning:</strong> ${data.reasoning}</div>`;
            }

            addMessage('assistant', responseHtml);

            // Check if confirmation required
            if (data.requires_confirmation) {
                addMessage('system', '<strong>⚠️ This action requires your confirmation.</strong>');
            }

            updateStatus('Ready', 'success');
        } else {
            addMessage('error', `Error: ${data.message || 'Unknown error'}`);
            updateStatus('Error', 'error');
        }

    } catch (error) {
        addMessage('error', `Failed to connect to API: ${error.message}`);
        updateStatus('Error', 'error');
    } finally {
        sendBtn.disabled = false;
    }
}

// Upload Document
async function uploadDocument() {
    const file = fileInput.files[0];

    if (!file) {
        alert('Please select a file');
        return;
    }

    updateStatus('Uploading...', 'loading');
    uploadSubmit.disabled = true;

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            addMessage('system', `
                <strong>✓ Document uploaded successfully!</strong><br>
                File: ${data.filename}<br>
                Chunks: ${data.num_chunks}<br>
                Document ID: ${data.document_id}
            `);

            uploadModal.classList.add('hidden');
            fileInput.value = '';
            updateStatus('Ready', 'success');
        } else {
            addMessage('error', `Upload failed: ${data.message}`);
            updateStatus('Error', 'error');
        }

    } catch (error) {
        addMessage('error', `Upload failed: ${error.message}`);
        updateStatus('Error', 'error');
    } finally {
        uploadSubmit.disabled = false;
    }
}

// Add Message to Chat
function addMessage(type, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;

    if (type === 'user') {
        messageDiv.innerHTML = `<strong>You:</strong> ${content}`;
    } else if (type === 'assistant') {
        messageDiv.innerHTML = `<strong>Able2:</strong> ${content}`;
    } else if (type === 'system') {
        messageDiv.innerHTML = content;
    } else if (type === 'error') {
        messageDiv.innerHTML = `<strong>Error:</strong> ${content}`;
    }

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Update Status
function updateStatus(text, type) {
    statusText.textContent = text;
    statusText.className = `status-${type}`;
}

// Update Session Info
function updateSessionInfo(id) {
    if (id) {
        sessionInfo.textContent = `Session: ${id.substring(0, 8)}...`;
    }
}
