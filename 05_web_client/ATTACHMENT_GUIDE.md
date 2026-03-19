# 附件上传功能说明

## AWS Support 附件限制

根据 AWS Support API 的限制：
- **单个文件最大**: 5MB
- **所有附件总计最大**: 25MB
- **支持的文件类型**: PDF, DOC, DOCX, TXT, PNG, JPG, JPEG, GIF, ZIP, LOG 等

## 附件上传流程

```
用户选择附件
    ↓
前端验证 (5MB单文件, 25MB总计)
    ↓
Base64 编码
    ↓
发送到后端
    ↓
后端再次验证大小
    ↓
调用 AWS Support API: add_attachments_to_set()
    ↓
获得 attachmentSetId
    ↓
将 attachmentSetId 包含在 prompt 中发送给 Agent
    ↓
Agent 调用 create_support_case(attachment_set_id=xxx)
    ↓
附件成功关联到 Case
```

## 使用方法

### 1. 在 Web UI 中上传附件

1. 点击输入框左侧的 📎 按钮
2. 选择要上传的文件（可多选）
3. 检查文件列表，可移除不需要的文件
4. 输入消息描述问题
5. 发送

### 2. 附件会自动处理

系统会：
- 上传附件到 AWS Support
- 获取 attachmentSetId
- 在 prompt 中告知 Agent 这个 ID
- Agent 创建 case 时自动关联附件

### 3. Agent 侧的处理

Agent 收到的 prompt 示例：
```
帮我创建一个关于 EC2 实例无法启动的 case

📎 已上传 2 个附件:
- error.log
- screenshot.png

attachmentSetId: as-123456789

请在创建 Support Case 时使用这个 attachmentSetId。
```

Agent 会调用：
```python
create_support_case(
    subject="EC2 instance failed to start",
    service_code="amazon-ec2",
    category_code="instance-issue",
    severity_code="urgent",
    communication_body="...",
    attachment_set_id="as-123456789"  # 使用这个 ID
)
```

## 错误处理

### 文件太大
```
❌ 文件 "large-file.zip" 超过 5MB 限制
```
**解决方案**: 压缩文件或分成多个较小的文件

### 总大小超限
```
❌ 添加此文件将超过总大小限制 (25MB)
当前已有: 20MB
新文件: 8MB
```
**解决方案**: 移除一些已添加的文件

### 上传失败
```
❌ 附件上传失败: An error occurred (AttachmentSetSizeLimitExceeded)
```
**解决方案**: 检查文件大小，确保符合限制

## 注意事项

1. **attachmentSetId 有过期时间**（通常 4 小时）
   - 上传后应尽快创建 case
   - 如果过期需要重新上传

2. **不要在 prompt 中包含敏感信息**
   - 附件会直接上传到 AWS Support
   - prompt 会被 Agent 记录

3. **附件类型建议**
   - 日志文件：`.log`, `.txt`
   - 截图：`.png`, `.jpg`
   - 配置文件：`.json`, `.yaml`, `.conf`
   - 压缩包：`.zip` (如果包含多个文件)

## 配置

### 环境变量

```bash
export AGENT_ARN="arn:aws:bedrock:REGION:ACCOUNT_ID:agent/YOUR_AGENT_ID"
```

### 启动服务

```bash
source venv/bin/activate
python3 app.py
```

访问 http://localhost:8080 测试。
