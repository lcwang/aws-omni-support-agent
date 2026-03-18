# 📓 SageMaker Notebook 执行清单

> 本清单用于在 SageMaker Jupyter Notebook 中手动部署和管理基础设施

---

## 🚀 快速导航

- [初次部署完整流程](#初次部署完整流程)
- [日常更新场景](#日常更新场景)
- [故障排除](#故障排除)

---

## ✅ 初次部署完整流程

### 前置准备

**时间**: 10 分钟

- [ ] SageMaker Notebook Instance 已启动
- [ ] 实例类型: `ml.t3.medium` 或更高
- [ ] IAM Role 包含以下权限:
  - Bedrock 完整权限
  - S3 读写权限
  - OpenSearch 管理权限
  - ECR 推送权限

**验证环境**:
```bash
# 在 Notebook Terminal 中
python --version  # 应为 Python 3.11+
aws --version     # AWS CLI 已安装
```

---

### Step 1: 克隆代码

**时间**: 2 分钟

```bash
# 在 SageMaker Notebook Terminal 中
cd ~/SageMaker
git clone https://github.com/percy-han/aws-omni-support-agent.git
cd aws-omni-support-agent
```

**验证**:
```bash
ls -la
# 应该看到:
# 01_create_support_knowledegbase_rag/
# 02_AWS_Support_Case_Lambda/
# 03_create_agentcore_gateway/
# 04_create_knowledge_mcp_gateway_Agent/
```

---

### Step 2: 创建 Knowledge Base

**时间**: 15-20 分钟

**Notebook**: `01_create_support_knowledegbase_rag/create_knowledge_base.ipynb`

#### 执行顺序:

1. **Cell 1-3**: 导入依赖和配置
   - [ ] 执行成功
   - [ ] 无 ModuleNotFoundError

2. **Cell 4-6**: 准备数据源
   - [ ] S3 bucket 存在
   - [ ] 文档已上传
   - [ ] 记录 S3 URI: `s3://_______________`

3. **Cell 7-10**: 创建 Knowledge Base
   - [ ] 执行完成
   - [ ] **记录 KB ID**: `______________________`

4. **Cell 11-13**: 创建数据源并同步
   - [ ] 数据源创建成功
   - [ ] 同步任务启动
   - [ ] 等待同步完成（5-10 分钟）

5. **Cell 14**: 测试检索
   - [ ] 测试查询: "What is AWS Lambda?"
   - [ ] 返回相关结果
   - [ ] 记录示例结果

#### 输出保存:

```bash
# 保存 KB ID 到 SSM Parameter Store
aws ssm put-parameter \
  --name /support/knowledge_base/kb_id_dev \
  --value "YOUR_KB_ID" \
  --type String \
  --overwrite
```

**验证**:
```bash
aws ssm get-parameter --name /support/knowledge_base/kb_id_dev
```

---

### Step 3: 创建 AgentCore Gateway

**时间**: 10-15 分钟

**Notebook**: `03_create_agentcore_gateway/create_agentcore_gateway.ipynb`

#### 执行顺序:

1. **Cell 1-2**: 导入依赖
   - [ ] 执行成功

2. **Cell 3-5**: 配置 Gateway 参数
   - [ ] Gateway name: `aws-support-gateway-dev`
   - [ ] Region: `us-east-1`
   - [ ] 记录配置

3. **Cell 6-8**: 创建 Gateway
   - [ ] 执行完成（约 5 分钟）
   - [ ] **记录 Gateway ARN**: `______________________`
   - [ ] **记录 Gateway URL**: `______________________`

4. **Cell 9**: 添加 Lambda Target
   - [ ] Lambda ARN: `从 02_AWS_Support_Case_Lambda 部署获取`
   - [ ] Target name: `aws-support-tools`

5. **Cell 10-16**: 配置 Tool Mappings
   - [ ] 添加 7 个工具映射:
     - [ ] `create_support_case`
     - [ ] `describe_support_cases`
     - [ ] `add_communication_to_case`
     - [ ] `resolve_support_case`
     - [ ] `describe_services`
     - [ ] `describe_severity_levels`
     - [ ] `add_attachments_to_set`

6. **Cell 17**: 测试 Gateway
   - [ ] 测试工具: `describe_severity_levels`
   - [ ] 返回结果正常

#### 输出保存:

```bash
# 保存 Gateway URL 到 SSM
aws ssm put-parameter \
  --name /support/agentgateway/aws_support_gateway_dev \
  --value "YOUR_GATEWAY_URL" \
  --type String \
  --overwrite
```

**验证**:
```bash
aws ssm get-parameter --name /support/agentgateway/aws_support_gateway_dev
```

---

### Step 4: 部署 Agent Runtime

**时间**: 20-30 分钟

**Notebook**: `04_create_knowledge_mcp_gateway_Agent/deploy_QA_agent.ipynb`

#### 执行顺序:

1. **Cell 1-3**: 环境配置
   - [ ] 执行成功
   - [ ] 依赖安装完成

2. **Cell 4-6**: 配置 Agent 参数
   - [ ] Agent name: `AWS_Support_knowledge_QA_Agent_DEV`
   - [ ] Model: `claude-opus-4-5`
   - [ ] Region: `us-east-1`
   - [ ] 从 SSM 获取 KB ID 和 Gateway URL

3. **Cell 7-10**: 构建 Docker 镜像
   - [ ] Dockerfile 正确
   - [ ] 镜像构建成功（约 5 分钟）
   - [ ] 记录镜像 tag

4. **Cell 11-13**: 推送到 ECR
   - [ ] ECR repository 存在或自动创建
   - [ ] 推送成功（约 3 分钟）
   - [ ] **记录 ECR URI**: `______________________`

5. **Cell 14-17**: 部署 Agent Runtime
   - [ ] Runtime 创建中（约 10 分钟）
   - [ ] 状态变为 ACTIVE
   - [ ] **记录 Agent ARN**: `______________________`
   - [ ] **记录 Session ID**: `______________________`

6. **Cell 18**: 测试 Agent
   - [ ] 测试提示: "帮我查看一下过去一周的 support cases"
   - [ ] Agent 响应正常
   - [ ] 记录测试结果

#### 输出保存:

```bash
# .bedrock_agentcore.yaml 已自动生成
cat 04_create_knowledge_mcp_gateway_Agent/.bedrock_agentcore.yaml

# 确认 agent_arn 已保存
grep agent_arn 04_create_knowledge_mcp_gateway_Agent/.bedrock_agentcore.yaml
```

**验证**:
```bash
# 使用 client 测试
cd 04_create_knowledge_mcp_gateway_Agent
python agent_client.py
```

---

## 🔄 日常更新场景

### Scenario A: 更新 Agent System Prompt

**时间**: 10-15 分钟

**触发条件**:
- Agent 响应需要优化
- 添加新的业务场景
- 修改指令逻辑

**步骤**:

1. **在 GitHub 中修改代码**
   ```bash
   # 本地或 GitHub Web UI
   vim 04_create_knowledge_mcp_gateway_Agent/aws_support_agent.py
   # 修改 get_system_prompt() 函数
   git commit -m "feat: improve system prompt"
   git push
   ```

2. **在 SageMaker Notebook 中拉取**
   ```bash
   cd ~/SageMaker/aws-omni-support-agent
   git pull origin main
   ```

3. **重新部署 Agent**
   - [ ] 打开 `deploy_QA_agent.ipynb`
   - [ ] **只执行 Cell 14-17**（部署 Runtime）
   - [ ] 等待更新完成（约 5 分钟）
   - [ ] 验证新 prompt 生效

**验证**:
```python
# 在 Notebook 新 cell 中
from aws_support_agent import get_system_prompt
print(get_system_prompt()[:200])  # 检查 prompt 内容
```

---

### Scenario B: 更新 Knowledge Base 内容

**时间**: 20-30 分钟

**触发条件**:
- 新增 AWS 文档
- 更新现有文档
- 删除过时内容

**步骤**:

1. **上传新文档到 S3**
   ```bash
   aws s3 cp new_docs/ s3://your-kb-bucket/docs/ --recursive
   ```

2. **触发同步**
   - [ ] 打开 `01_create_support_knowledegbase_rag/create_knowledge_base.ipynb`
   - [ ] **只执行 Cell 11-12**（数据源同步）
   - [ ] 等待同步完成（5-15 分钟）

3. **验证检索**
   - [ ] **执行 Cell 14**（测试检索）
   - [ ] 查询新文档内容
   - [ ] 确认返回结果包含新内容

---

### Scenario C: 添加新的 Gateway 工具

**时间**: 15-20 分钟

**触发条件**:
- Lambda 新增了工具函数
- 需要在 Gateway 中暴露

**步骤**:

1. **确认 Lambda 已更新**
   ```bash
   # GitHub Actions 应该已自动部署 Lambda
   # 验证
   aws lambda get-function --function-name aws-support-tools-lambda-dev
   ```

2. **在 Gateway 中添加工具映射**
   - [ ] 打开 `03_create_agentcore_gateway/create_agentcore_gateway.ipynb`
   - [ ] **执行 Cell 10-12**（添加工具映射）
   - [ ] 工具名称与 Lambda 一致
   - [ ] 配置 input schema

3. **测试新工具**
   - [ ] **执行 Cell 17**（测试工具）
   - [ ] 调用新工具
   - [ ] 验证返回结果

---

### Scenario D: 环境变量更新

**时间**: 5 分钟

**触发条件**:
- Model ID 变更
- Timeout 调整
- Region 变更

**步骤**:

1. **修改代码配置**
   ```bash
   vim 04_create_knowledge_mcp_gateway_Agent/aws_support_agent.py
   # 修改环境变量默认值
   MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "new-model-id")
   ```

2. **重新部署**（同 Scenario A）

**或者通过 SSM Parameter Store**:
```bash
aws ssm put-parameter \
  --name /support/config/model_id \
  --value "new-model-id" \
  --type String \
  --overwrite
```

---

## 🆘 故障排除

### 问题 1: Notebook Kernel 死机

**症状**: Cell 执行卡住，无响应

**解决**:
```bash
# 在 Notebook 菜单: Kernel → Restart Kernel
# 或 Terminal 中强制重启
jupyter notebook list
jupyter notebook stop <port>
```

---

### 问题 2: ModuleNotFoundError

**症状**: `ModuleNotFoundError: No module named 'bedrock_agentcore'`

**解决**:
```bash
cd 04_create_knowledge_mcp_gateway_Agent
pip install -r requirements.txt

# 或重新创建虚拟环境
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### 问题 3: Docker 构建失败

**症状**: `Error building Docker image`

**解决**:
```bash
# 检查 Docker daemon
docker ps

# 清理旧镜像
docker system prune -a

# 手动构建测试
cd 04_create_knowledge_mcp_gateway_Agent
docker build -t test-agent .
```

---

### 问题 4: ECR 推送权限错误

**症状**: `denied: User: ... is not authorized to perform: ecr:PutImage`

**解决**:
```bash
# 检查 IAM Role 权限
aws sts get-caller-identity

# 确保 SageMaker Execution Role 包含:
# - ecr:GetAuthorizationToken
# - ecr:BatchCheckLayerAvailability
# - ecr:PutImage
# - ecr:InitiateLayerUpload
# - ecr:UploadLayerPart
# - ecr:CompleteLayerUpload
```

---

### 问题 5: Agent 部署超时

**症状**: Agent 创建一直处于 CREATING 状态

**解决**:
```bash
# 检查 CloudWatch Logs
aws logs tail /aws/bedrock/agentcore/<agent-id> --follow

# 检查 ECR 镜像
aws ecr describe-images --repository-name aws-support-agent

# 如果卡住超过 20 分钟，取消并重试
aws bedrock-agentcore delete-agent --agent-id <agent-id>
# 重新执行 deploy_QA_agent.ipynb
```

---

## 📊 检查清单总结

### 初次部署完成后应该有:

- [ ] Knowledge Base ID 保存到 SSM
- [ ] Gateway URL 保存到 SSM
- [ ] Agent ARN 记录在 `.bedrock_agentcore.yaml`
- [ ] Lambda 函数已部署（通过 GitHub Actions）
- [ ] 所有 7 个工具在 Gateway 中配置
- [ ] Agent 测试通过

### 日常检查:

- [ ] SageMaker Notebook Instance 正常运行
- [ ] Git 代码已同步最新
- [ ] Python 环境依赖完整
- [ ] AWS 凭证有效
- [ ] CloudWatch Logs 无错误

---

## 🔗 相关文档

- [部署指南](DEPLOYMENT_GUIDE.md) - 完整部署流程
- [快速参考](.github/QUICK_REFERENCE.md) - 常用命令
- [CI/CD 配置](.github/CICD_SETUP.md) - GitHub Actions 配置

---

**祝部署顺利！** 🚀

有问题参考故障排除章节或查看详细文档。
