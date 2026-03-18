# Lambda Architecture - Deployment Guide

## 架构优化说明

本项目已从 **MCP Server on AgentCore Runtime** 迁移到 **Lambda + AgentCore Gateway** 架构：

### 旧架构（已废弃）
```
AgentCore Runtime (Agent)
    ↓ HTTP + Cognito Token
AgentCore Runtime (MCP Server)
    ↓ IAM Role
AWS Support API
```

### 新架构（当前）
```
AgentCore Runtime (Agent)
    ↓ AgentCore Gateway
Lambda Function (AWS Support Tools)
    ↓ IAM Role
AWS Support API
```

## 优势对比

| 特性 | 旧架构 | 新架构 |
|------|--------|--------|
| **部署复杂度** | 需要部署2个Runtime | 只需1个Runtime + 1个Lambda |
| **认证方式** | Cognito + Token刷新 | IAM Role（原生） |
| **成本** | 两个Runtime持续运行 | Lambda按调用付费 |
| **运维** | 复杂 | 简单 |
| **扩展性** | 一般 | 优秀（Lambda自动扩展） |

---

## 部署步骤

### 前置要求

1. **AWS账号权限**
   - IAM 创建角色权限
   - Lambda 创建/更新权限
   - AWS Support API 访问权限（商业或企业支持计划）

2. **本地环境**
   - Python 3.11+
   - AWS CLI 已配置
   - boto3

### Step 1: 部署 Lambda 函数

```bash
cd Lambda/

# 执行部署脚本
python deploy_lambda.py
```

部署脚本会自动完成：
- ✅ 创建部署包
- ✅ 创建 IAM 执行角色
- ✅ 创建/更新 Lambda 函数
- ✅ 测试函数
- ✅ 添加 AgentCore Gateway 调用权限

**输出示例：**
```
🚀 AWS Support Lambda Deployment Script

[1/6] Creating Lambda deployment package...
✓ Deployment package created: /tmp/lambda_deployment.zip

[2/6] Creating IAM role...
✓ Created IAM role: arn:aws:iam::123456789012:role/aws-support-lambda-execution-role
✓ Attached policy to role

[3/6] Creating/Updating Lambda function...
✓ Created Lambda function: arn:aws:lambda:us-east-1:123456789012:function:aws-support-tools-lambda

[4/6] Testing Lambda function...
✓ Lambda test successful

[5/6] Adding AgentCore Gateway permission...
✓ Added permission for AgentCore Gateway

============================================================
[6/6] Deployment Summary
============================================================
Lambda Function ARN: arn:aws:lambda:us-east-1:123456789012:function:aws-support-tools-lambda
Function Name: aws-support-tools-lambda
Region: us-east-1

Available Tools:
  - create_support_case
  - describe_support_cases
  - add_communication_to_case
  - resolve_support_case
  - describe_services
  - describe_severity_levels
  - add_attachments_to_set

============================================================
Next Steps:
1. Copy the Lambda ARN above
2. Add this Lambda as a target in your AgentCore Gateway
3. Update your Agent code to use Lambda tools (see support_case_agent_lambda.py)
============================================================

✅ Deployment completed successfully!
```

### Step 2: 配置 AgentCore Gateway

1. **登录 AWS Console**
   - 进入 Amazon Bedrock 服务
   - 选择 AgentCore → Gateways

2. **在你已创建的 Gateway 中添加 Lambda target**
   - Target Type: Lambda Function
   - Function ARN: `从 Step 1 输出中复制`
   - Tool Name Mapping:
     ```
     create_support_case → create_support_case
     describe_support_cases → describe_support_cases
     add_communication_to_case → add_communication_to_case
     resolve_support_case → resolve_support_case
     describe_services → describe_services
     describe_severity_levels → describe_severity_levels
     add_attachments_to_set → add_attachments_to_set
     ```

### Step 3: 更新 Agent 代码

1. **修改 Agent 配置文件**
   ```bash
   cd ../Agent/
   ```

2. **更新 Lambda ARN**
   编辑 `support_case_agent_lambda.py`，替换：
   ```python
   LAMBDA_FUNCTION_ARN = "arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:aws-support-tools-lambda"
   ```
   为你的实际 Lambda ARN（从 Step 1 获取）

3. **部署 Agent**
   使用原有的 Agent 部署流程（Notebook或脚本），但使用新的 `support_case_agent_lambda.py`

### Step 4: 测试完整流程

```bash
# 返回 Lambda 目录
cd ../Lambda/

# 运行测试脚本
python test_lambda.py
```

---

## Lambda 函数说明

### 工具列表

#### 1. create_support_case
创建新的 Support Case

**参数：**
```json
{
  "tool_name": "create_support_case",
  "parameters": {
    "subject": "EC2 instance not starting",
    "service_code": "amazon-elastic-compute-cloud-linux",
    "category_code": "using-aws",
    "severity_code": "urgent",
    "communication_body": "My EC2 instance i-1234567890abcdef0 is not starting."
  }
}
```

#### 2. describe_support_cases
查询 Support Cases

**参数：**
```json
{
  "tool_name": "describe_support_cases",
  "parameters": {
    "include_resolved_cases": false,
    "include_communications": true
  }
}
```

#### 3. add_communication_to_case
添加回复

**参数：**
```json
{
  "tool_name": "add_communication_to_case",
  "parameters": {
    "case_id": "case-12345678910-2013-c4c1d2bf33c5cf47",
    "communication_body": "Here is an update..."
  }
}
```

#### 4. resolve_support_case
关闭 Case

**参数：**
```json
{
  "tool_name": "resolve_support_case",
  "parameters": {
    "case_id": "case-12345678910-2013-c4c1d2bf33c5cf47"
  }
}
```

#### 5. describe_services
获取服务列表

**参数：**
```json
{
  "tool_name": "describe_services",
  "parameters": {
    "language": "en"
  }
}
```

#### 6. describe_severity_levels
获取严重级别

**参数：**
```json
{
  "tool_name": "describe_severity_levels",
  "parameters": {
    "language": "en"
  }
}
```

#### 7. add_attachments_to_set
上传附件

**参数：**
```json
{
  "tool_name": "add_attachments_to_set",
  "parameters": {
    "attachments": [
      {
        "fileName": "error_log.txt",
        "data": "base64_encoded_content"
      }
    ]
  }
}
```

---

## 监控和日志

### CloudWatch Logs
```
Log Group: /aws/lambda/aws-support-tools-lambda
```

### CloudWatch Metrics
- Invocations (调用次数)
- Duration (执行时长)
- Errors (错误数)
- Throttles (限流次数)

### 查看日志
```bash
aws logs tail /aws/lambda/aws-support-tools-lambda --follow
```

---

## 故障排除

### 问题 1: Lambda执行超时
**症状：** Task timed out after 60.00 seconds
**解决：** 增加 Lambda timeout（在 `deploy_lambda.py` 中修改 `LAMBDA_TIMEOUT`）

### 问题 2: 权限错误
**症状：** AccessDeniedException
**解决：** 检查 IAM Role 是否有 Support API 权限（查看 `iam_policy.json`）

### 问题 3: Gateway 无法调用 Lambda
**症状：** Lambda was not invoked
**解决：** 确认已执行 Step 2，添加了 Gateway 权限

### 问题 4: 找不到 boto3
**症状：** No module named 'boto3'
**解决：** Lambda Runtime 已内置 boto3，无需额外打包

---

## 成本估算

### Lambda 成本
```
请求费用: $0.20 / 1M 请求
执行费用: $0.0000166667 / GB-秒

示例（每月1000次调用，每次500ms，512MB内存）：
请求费用: $0.00020
执行费用: $0.00417
总计: ~$0.00437/月
```

### 对比旧架构
- 旧架构：2个 AgentCore Runtime = ~$XXX/月
- 新架构：1个 Runtime + Lambda = ~$XX/月
- **节省约 40-60%**

---

## 回滚方案

如需回滚到旧的 MCP 架构：

1. 保留 Lambda（不影响）
2. 重新部署 MCP Runtime
3. Agent 切换回 `support_case_agent.py`
4. 更新 Gateway 配置

---

## 联系支持

如遇问题，请提供：
- Lambda 函数日志
- Agent 执行日志
- 错误截图
- AWS 账号 ID（脱敏）
