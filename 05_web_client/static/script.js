// State
let isStreaming = false;
let attachments = [];

// DOM elements (declared in global scope but will be initialized in DOMContentLoaded)
let messagesContainer;
let chatForm;
let messageInput;
let sendButton;
let statusDot;
let statusText;
let attachmentButton;
let fileInput;
let attachmentsContainer;
let attachmentsList;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Initialize DOM elements
    messagesContainer = document.getElementById('messages');
    chatForm = document.getElementById('chat-form');
    messageInput = document.getElementById('message-input');
    sendButton = document.getElementById('send-button');
    statusDot = document.querySelector('.status-dot');
    statusText = document.querySelector('.status-text');
    attachmentButton = document.getElementById('attachment-button');
    fileInput = document.getElementById('file-input');
    attachmentsContainer = document.getElementById('attachments-container');
    attachmentsList = document.getElementById('attachments-list');

    console.log('DOM elements initialized:', {
        attachmentButton: !!attachmentButton,
        fileInput: !!fileInput,
        attachmentsContainer: !!attachmentsContainer
    });

    checkHealth();
    setupEventListeners();
    adjustTextareaHeight();
});

// Check backend health
async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();

        if (data.status === 'healthy') {
            statusDot.classList.remove('error');
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.add('error');
            statusText.textContent = 'Error: ' + data.error;
        }
    } catch (error) {
        statusDot.classList.add('error');
        statusText.textContent = 'Connection failed';
        console.error('Health check failed:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Form submission
    chatForm.addEventListener('submit', handleSubmit);

    // Textarea auto-resize
    messageInput.addEventListener('input', adjustTextareaHeight);

    // Enter to submit (Shift+Enter for new line)
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.requestSubmit();
        }
    });

    // Attachment button
    if (attachmentButton && fileInput) {
        attachmentButton.addEventListener('click', () => {
            console.log('Attachment button clicked');
            fileInput.click();
        });
        console.log('Attachment button listener added');
    } else {
        console.error('Attachment button or file input not found!', {
            attachmentButton: !!attachmentButton,
            fileInput: !!fileInput
        });
    }

    // File input change
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
        console.log('File input listener added');
    }
}

// Handle file selection
async function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    const maxSingleFileSize = 5 * 1024 * 1024; // 5MB - AWS Support single file limit
    const maxTotalSize = 25 * 1024 * 1024; // 25MB - AWS Support total limit

    for (const file of files) {
        if (file.size > maxSingleFileSize) {
            alert(`文件 "${file.name}" 超过 5MB 限制\n\nAWS Support 单个附件最大 5MB`);
            continue;
        }

        // Check total size
        const currentTotalSize = attachments.reduce((sum, att) => sum + att.size, 0);
        if (currentTotalSize + file.size > maxTotalSize) {
            alert(`添加此文件将超过总大小限制 (25MB)\n\n当前已有: ${formatFileSize(currentTotalSize)}\n新文件: ${formatFileSize(file.size)}`);
            continue;
        }

        // Read file as base64
        const base64 = await readFileAsBase64(file);

        attachments.push({
            name: file.name,
            size: file.size,
            type: file.type,
            data: base64
        });
    }

    // Clear file input
    fileInput.value = '';

    // Update UI
    updateAttachmentsDisplay();
}

// Read file as base64
function readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            // Remove data:*/*;base64, prefix
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// Update attachments display
function updateAttachmentsDisplay() {
    if (attachments.length === 0) {
        attachmentsContainer.style.display = 'none';
        return;
    }

    attachmentsContainer.style.display = 'block';
    attachmentsList.innerHTML = '';

    attachments.forEach((attachment, index) => {
        const item = document.createElement('div');
        item.className = 'attachment-item';

        const sizeStr = formatFileSize(attachment.size);

        item.innerHTML = `
            <span class="attachment-name" title="${escapeHtml(attachment.name)}">${escapeHtml(attachment.name)}</span>
            <span class="attachment-size">(${sizeStr})</span>
            <button class="attachment-remove" onclick="removeAttachment(${index})" title="移除">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
            </button>
        `;

        attachmentsList.appendChild(item);
    });
}

// Remove attachment (exposed to global scope for onclick)
window.removeAttachment = function(index) {
    attachments.splice(index, 1);
    updateAttachmentsDisplay();
}

// Format file size
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();

    const message = messageInput.value.trim();
    if ((!message && attachments.length === 0) || isStreaming) return;

    // Add user message (with attachments info if any)
    let displayMessage = message;
    if (attachments.length > 0) {
        displayMessage += `\n\n📎 附件 (${attachments.length}): ${attachments.map(a => a.name).join(', ')}`;
    }
    addMessage(displayMessage, 'user');

    // Clear input
    messageInput.value = '';
    adjustTextareaHeight();

    // Disable input during streaming
    setInputState(false);
    isStreaming = true;

    // Send message and stream response
    await streamResponse(message, attachments);

    // Clear attachments
    attachments = [];
    updateAttachmentsDisplay();

    // Re-enable input
    setInputState(true);
    isStreaming = false;
    messageInput.focus();
}

// Add message to chat
function addMessage(content, role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';

    if (role === 'user') {
        avatarDiv.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
            </svg>
        `;
    } else {
        avatarDiv.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
            </svg>
        `;
    }

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';

    if (role === 'user') {
        textDiv.textContent = content;
    } else {
        // For assistant, use innerHTML for markdown
        textDiv.innerHTML = marked.parse(content);
        // Highlight code blocks
        textDiv.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }

    contentDiv.appendChild(textDiv);
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    scrollToBottom();
    return textDiv;
}

// Add thinking indicator
function addThinkingIndicator() {
    console.log('Adding thinking indicator...');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.id = 'thinking-message';

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
        </svg>
    `;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'thinking-indicator';
    thinkingDiv.innerHTML = `
        <span>思考中</span>
        <div class="thinking-dots">
            <div class="thinking-dot"></div>
            <div class="thinking-dot"></div>
            <div class="thinking-dot"></div>
        </div>
    `;

    contentDiv.appendChild(thinkingDiv);
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    console.log('Thinking indicator added');
    scrollToBottom();
    return messageDiv;
}

// Remove thinking indicator
function removeThinkingIndicator() {
    const thinkingMsg = document.getElementById('thinking-message');
    if (thinkingMsg) {
        thinkingMsg.remove();
    }
}

// Stream response from backend
async function streamResponse(message, attachmentData = []) {
    // Show thinking indicator
    const thinkingMsg = addThinkingIndicator();
    let hasReceivedContent = false;

    // Create assistant message container (hidden initially)
    const assistantTextDiv = addMessage('', 'assistant');
    assistantTextDiv.parentElement.parentElement.style.display = 'none';
    let fullContent = '';

    try {
        const requestBody = { message };
        if (attachmentData.length > 0) {
            requestBody.attachments = attachmentData;
        }

        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();

            if (done) break;

            // Decode chunk
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));

                        if (data.error) {
                            // Remove thinking indicator and show error
                            removeThinkingIndicator();
                            assistantTextDiv.parentElement.parentElement.style.display = 'flex';
                            assistantTextDiv.innerHTML = `
                                <div class="error-message">
                                    错误: ${escapeHtml(data.error)}
                                </div>
                            `;
                        } else if (data.done) {
                            // Streaming complete
                            removeThinkingIndicator();
                            break;
                        } else if (data.content) {
                            // First content - remove thinking indicator
                            if (!hasReceivedContent) {
                                removeThinkingIndicator();
                                assistantTextDiv.parentElement.parentElement.style.display = 'flex';
                                hasReceivedContent = true;
                            }

                            // Append content
                            fullContent += data.content;
                            // Render markdown incrementally
                            assistantTextDiv.innerHTML = marked.parse(fullContent);
                            // Highlight code blocks
                            assistantTextDiv.querySelectorAll('pre code').forEach((block) => {
                                hljs.highlightElement(block);
                            });
                            scrollToBottom();
                        }
                    } catch (e) {
                        console.error('Error parsing SSE data:', e);
                    }
                }
            }
        }

        // Ensure thinking indicator is removed
        removeThinkingIndicator();
        if (!hasReceivedContent) {
            assistantTextDiv.parentElement.parentElement.style.display = 'flex';
        }

    } catch (error) {
        console.error('Streaming error:', error);
        removeThinkingIndicator();
        assistantTextDiv.parentElement.parentElement.style.display = 'flex';
        assistantTextDiv.innerHTML = `
            <div class="error-message">
                连接错误: ${escapeHtml(error.message)}
            </div>
        `;
    }
}

// Set input state (enabled/disabled)
function setInputState(enabled) {
    messageInput.disabled = !enabled;
    sendButton.disabled = !enabled;
    attachmentButton.disabled = !enabled;
}

// Adjust textarea height based on content
function adjustTextareaHeight() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
}

// Scroll to bottom of messages
function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Configure marked.js
marked.setOptions({
    breaks: true,
    gfm: true,
    headerIds: false,
    mangle: false
});
