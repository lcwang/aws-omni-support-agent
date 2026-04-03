/**
 * 反馈系统 - 前端逻辑
 *
 * 功能：
 * 1. 处理点赞/点踩事件
 * 2. 显示点踩原因弹窗
 * 3. 提交反馈到后端 API
 * 4. 本地缓存防止重复反馈
 */

// 全局变量
let currentFeedbackMessageId = null;
let feedbackCache = new Set(); // 防止重复反馈

/**
 * 初始化反馈系统
 */
function initFeedbackSystem() {
    console.log('[Feedback] System initialized');

    // 从 localStorage 加载已反馈的消息
    const cached = localStorage.getItem('feedback_cache');
    if (cached) {
        feedbackCache = new Set(JSON.parse(cached));
    }

    // 监听字符计数
    const commentInput = document.getElementById('user-comment');
    if (commentInput) {
        commentInput.addEventListener('input', updateCharCount);
    }
}

/**
 * 处理反馈点击
 * @param {string} messageId - 消息 ID
 * @param {string} feedbackType - 'thumbs_up' | 'thumbs_down'
 */
function handleFeedback(messageId, feedbackType) {
    console.log(`[Feedback] ${feedbackType} clicked for message: ${messageId}`);

    // 检查是否已经反馈过
    const cacheKey = `${messageId}_${feedbackType}`;
    if (feedbackCache.has(cacheKey)) {
        showToast('你已经对这条回答做过反馈了', 'info');
        return;
    }

    // 禁用反馈按钮
    disableFeedbackButtons(messageId);

    if (feedbackType === 'thumbs_up') {
        // 点赞：直接提交
        submitFeedback(messageId, feedbackType, null, null);
    } else {
        // 点踩：显示原因选择弹窗
        currentFeedbackMessageId = messageId;
        showNegativeFeedbackModal();
    }
}

/**
 * 提交反馈到后端
 * @param {string} messageId - 消息 ID
 * @param {string} feedbackType - 'thumbs_up' | 'thumbs_down'
 * @param {string} negativeReason - 点踩原因（点踩时必填）
 * @param {string} userComment - 用户补充说明（可选）
 */
async function submitFeedback(messageId, feedbackType, negativeReason, userComment) {
    console.log(`[Feedback] Submitting ${feedbackType} for ${messageId}`);

    try {
        // 获取消息的完整上下文
        const messageData = getMessageData(messageId);

        if (!messageData) {
            throw new Error('Message data not found');
        }

        // 构建请求数据
        const payload = {
            message_id: messageId,
            feedback_type: feedbackType,
            timestamp: new Date().toISOString(),

            // 问答内容
            question: messageData.question,
            answer: messageData.answer,
            interaction_type: messageData.interaction_type, // 'qa' | 'case'

            // 检索详情（从消息 metadata 中获取）
            retrieval_source: messageData.retrieval_source, // 'rag' | 'llm_generated' | 'hybrid'
            rag_documents: messageData.rag_documents || [],

            // 用户信息
            user_id: getUserId(),
            session_id: getSessionId(),

            // 点踩特有字段
            negative_reason: negativeReason,
            user_comment: userComment
        };

        // 发送到后端
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('[Feedback] Submission successful:', result);

        // 缓存反馈记录
        const cacheKey = `${messageId}_${feedbackType}`;
        feedbackCache.add(cacheKey);
        localStorage.setItem('feedback_cache', JSON.stringify([...feedbackCache]));

        // 显示成功反馈
        showFeedbackSuccess(messageId);
        showToast('感谢你的反馈！', 'success');

    } catch (error) {
        console.error('[Feedback] Submission failed:', error);
        showToast('反馈提交失败，请稍后重试', 'error');

        // 重新启用按钮
        enableFeedbackButtons(messageId);
    }
}

/**
 * 获取消息的完整数据
 * @param {string} messageId - 消息 ID
 * @returns {object|null} 消息数据
 */
function getMessageData(messageId) {
    // 从 DOM 或全局变量中获取消息数据
    // 这需要在消息生成时存储相关数据

    const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
    if (!messageElement) {
        console.error('[Feedback] Message element not found:', messageId);
        return null;
    }

    // 从 data 属性中获取（需要在生成消息时设置）
    return {
        question: messageElement.dataset.question,
        answer: messageElement.dataset.answer,
        interaction_type: messageElement.dataset.interactionType || 'qa',
        retrieval_source: messageElement.dataset.retrievalSource || 'unknown',
        rag_documents: JSON.parse(messageElement.dataset.ragDocuments || '[]')
    };
}

/**
 * 显示点踩原因弹窗
 */
function showNegativeFeedbackModal() {
    const modal = document.getElementById('negative-feedback-modal');
    modal.style.display = 'flex';

    // 重置表单
    document.querySelector('input[name="negative_reason"]:checked').checked = true;
    document.getElementById('user-comment').value = '';
    updateCharCount();
}

/**
 * 关闭点踩原因弹窗
 */
function closeNegativeFeedbackModal() {
    const modal = document.getElementById('negative-feedback-modal');
    modal.style.display = 'none';

    // 重新启用按钮（如果用户取消）
    if (currentFeedbackMessageId) {
        enableFeedbackButtons(currentFeedbackMessageId);
        currentFeedbackMessageId = null;
    }
}

/**
 * 提交点踩反馈（从弹窗）
 */
function submitNegativeFeedback() {
    if (!currentFeedbackMessageId) {
        console.error('[Feedback] No current message ID');
        return;
    }

    // 获取选中的原因
    const reasonInput = document.querySelector('input[name="negative_reason"]:checked');
    const negativeReason = reasonInput ? reasonInput.value : 'other';

    // 获取用户补充说明
    const userComment = document.getElementById('user-comment').value.trim();

    // 提交反馈
    submitFeedback(currentFeedbackMessageId, 'thumbs_down', negativeReason, userComment);

    // 关闭弹窗
    closeNegativeFeedbackModal();
    currentFeedbackMessageId = null;
}

/**
 * 禁用反馈按钮
 * @param {string} messageId - 消息 ID
 */
function disableFeedbackButtons(messageId) {
    const container = document.querySelector(`[data-message-id="${messageId}"] .feedback-buttons`);
    if (container) {
        container.style.pointerEvents = 'none';
        container.style.opacity = '0.5';
    }
}

/**
 * 启用反馈按钮
 * @param {string} messageId - 消息 ID
 */
function enableFeedbackButtons(messageId) {
    const container = document.querySelector(`[data-message-id="${messageId}"] .feedback-buttons`);
    if (container) {
        container.style.pointerEvents = 'auto';
        container.style.opacity = '1';
    }
}

/**
 * 显示反馈成功状态
 * @param {string} messageId - 消息 ID
 */
function showFeedbackSuccess(messageId) {
    const container = document.querySelector(`[data-message-id="${messageId}"]`);
    if (container) {
        const buttonsDiv = container.querySelector('.feedback-buttons');
        const successDiv = container.querySelector('.feedback-success');

        if (buttonsDiv && successDiv) {
            buttonsDiv.style.display = 'none';
            successDiv.style.display = 'flex';
        }
    }
}

/**
 * 更新字符计数
 */
function updateCharCount() {
    const commentInput = document.getElementById('user-comment');
    const charCount = document.getElementById('comment-char-count');

    if (commentInput && charCount) {
        const length = commentInput.value.length;
        charCount.textContent = length;

        // 接近上限时变红
        if (length > 450) {
            charCount.style.color = '#e74c3c';
        } else {
            charCount.style.color = '#95a5a6';
        }
    }
}

/**
 * 显示提示消息
 * @param {string} message - 消息内容
 * @param {string} type - 'success' | 'error' | 'info'
 */
function showToast(message, type = 'info') {
    // 创建 toast 元素
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    // 添加到页面
    document.body.appendChild(toast);

    // 动画显示
    setTimeout(() => {
        toast.classList.add('toast-show');
    }, 10);

    // 3秒后移除
    setTimeout(() => {
        toast.classList.remove('toast-show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

/**
 * 获取当前用户 ID
 * @returns {string} 用户 ID
 */
function getUserId() {
    // 从现有的用户输入框获取
    const userIdInput = document.getElementById('user-id-input');
    return userIdInput ? userIdInput.value : 'anonymous';
}

/**
 * 获取当前 Session ID
 * @returns {string} Session ID
 */
function getSessionId() {
    // 从现有的 session 管理获取
    const userId = getUserId();
    const storageKey = `session_${userId}`;
    return localStorage.getItem(storageKey) || 'unknown';
}

// 页面加载时初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFeedbackSystem);
} else {
    initFeedbackSystem();
}

// 模态框外部点击关闭
document.addEventListener('click', function(event) {
    const modal = document.getElementById('negative-feedback-modal');
    if (event.target === modal) {
        closeNegativeFeedbackModal();
    }
});

// ESC 键关闭模态框
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeNegativeFeedbackModal();
    }
});
