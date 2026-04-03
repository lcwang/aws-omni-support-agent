// 调试脚本 - 检查反馈按钮问题
console.log('=== 反馈按钮调试 ===');

// 1. 检查 feedback-ui.js 是否加载
console.log('1. handleFeedback 函数存在:', typeof handleFeedback !== 'undefined');

// 2. 检查 CSS 是否加载
const feedbackCss = Array.from(document.styleSheets).find(s =>
    s.href && s.href.includes('feedback-ui.css')
);
console.log('2. feedback-ui.css 已加载:', !!feedbackCss);

// 3. 检查所有 assistant 消息
const assistantMessages = document.querySelectorAll('.message.assistant');
console.log('3. Assistant 消息数量:', assistantMessages.length);

// 4. 检查每个消息是否有反馈容器
assistantMessages.forEach((msg, index) => {
    const messageId = msg.getAttribute('data-message-id');
    const feedbackContainer = msg.querySelector('.feedback-container');
    const feedbackButtons = msg.querySelector('.feedback-buttons');

    console.log(`   消息 ${index + 1}:`, {
        messageId: messageId,
        有反馈容器: !!feedbackContainer,
        有反馈按钮: !!feedbackButtons
    });
});

// 5. 尝试手动添加按钮到最后一条消息
setTimeout(() => {
    const lastMessage = document.querySelector('.message.assistant:last-child');
    if (lastMessage && !lastMessage.querySelector('.feedback-container')) {
        console.log('⚠️ 发现消息没有反馈按钮，尝试手动添加...');

        const messageId = lastMessage.getAttribute('data-message-id');
        const contentDiv = lastMessage.querySelector('.message-content');

        if (messageId && contentDiv) {
            const feedbackDiv = document.createElement('div');
            feedbackDiv.className = 'feedback-container';
            feedbackDiv.setAttribute('data-message-id', messageId);
            feedbackDiv.innerHTML = `
                <div class="feedback-buttons">
                    <button class="feedback-btn feedback-btn-up"
                            onclick="handleFeedback('${messageId}', 'thumbs_up')"
                            title="这个回答有帮助">
                        <span class="icon">👍</span>
                        <span class="text">有帮助</span>
                    </button>
                    <button class="feedback-btn feedback-btn-down"
                            onclick="handleFeedback('${messageId}', 'thumbs_down')"
                            title="这个回答没帮助">
                        <span class="icon">👎</span>
                        <span class="text">没帮助</span>
                    </button>
                </div>
                <div class="feedback-success" style="display: none;">
                    <span class="icon">✓</span>
                    <span class="text">感谢你的反馈！</span>
                </div>
            `;
            contentDiv.appendChild(feedbackDiv);
            console.log('✅ 手动添加成功！');
        }
    }
}, 1000);
