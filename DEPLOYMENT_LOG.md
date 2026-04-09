# AWS Omni Support Agent 完整部署记录

> 记录人：luchen-udemystudy | 日期：2026-04-02 | 环境：macOS + AWS us-east-1

---

## 项目是什么

一个企业级 AI 客服系统。用户在网页上提问 AWS 技术问题，AI Agent（Claude Opus 4.5）会：
1. 先从知识库（RAG）里搜答案
2. 搜不到就去 AWS 官方文档找
3. 还是解决不了就主动建议开 AWS Support 工单
4. 工单操作有权限控制（RBAC），不同用户有不同权限

### 数据流

```
用户浏览器 → Web Client (FastAPI:8080)
    → Bedrock AgentCore Runtime (Claude Opus 4.5)
        → 知识库检索 (OpenSearch + Titan Embeddings)
        → AgentCore Gateway → Lambda (7个工单工具 + RBAC)
            → AWS Support API
            → IAM Policy Simulator (权限检查)
```

---

## Step 0: 环境准备

### 做了什么
- `git clone git@github.com:percy-han/aws-omni-support-agent.git`
- AWS CLI 默认 region 从 `ap-northeast-1` 改为 `us-east-1`（Support API 只在这个 region 可用）
- 手动在 AWS Console 开通 Business Support Plan（$100/月起）

### 为什么
- 项目所有组件都硬编码了 us-east-1
- Support API 必须有 Business 或 Enterprise Plan 才能调用

### 验证
```bash
aws support describe-severity-levels --region us-east-1 --language en
# 返回 5 个 severity level 说明 OK
```

---

## Step 1: 部署 Lambda（模块 02）

### 做了什么
运行 `python3 02_AWS_Support_Case_Lambda/deploy_lambda.py`，自动完成：
1. 创建 IAM Role `aws-support-lambda-execution-role`，附加权限策略（`lambda_rbac_policy.json`）
2. 把 `lambda_handler.py` 打包成 zip 上传为 Lambda 函数
3. 测试 Lambda（调用 `describe_severity_levels`）
4. 给 Lambda 添加 Bedrock AgentCore 的调用权限

### Lambda 的 7 个工具

| 工具名 | 作用 | 需要 RBAC？ |
|--------|------|------------|
| `create_support_case` | 创建新的 Support 工单 | ✅ 需要 `support:CreateCase` |
| `describe_support_cases` | 查询现有工单 | ❌ 不需要 |
| `add_communication_to_case` | 给工单添加回复 | ✅ 需要 `support:AddCommunicationToCase` |
| `resolve_support_case` | 关闭工单 | ✅ 需要 `support:ResolveCase` |
| `describe_services` | 获取 AWS 服务代码列表（创建工单时需要） | ❌ 不需要 |
| `describe_severity_levels` | 获取严重程度选项 | ❌ 不需要 |
| `add_attachments_to_set` | 上传附件 | ✅ 需要 `support:AddAttachmentsToSet` |

### RBAC 工作原理
- 查询类工具（describe_*）：直接执行，不检查权限
- 写入类工具（create/add/resolve）：Lambda 提取 `_iam_user` 参数，调用 `iam:SimulatePrincipalPolicy` API 检查该用户是否有对应的 support 权限
- 权限检查结果缓存 5 分钟
- 所有操作记录审计日志到 CloudWatch

### Lambda 的 IAM 权限（lambda_rbac_policy.json）
- `logs:*` — CloudWatch 日志
- `iam:SimulatePrincipalPolicy` — RBAC 权限检查
- `sts:GetCallerIdentity` — 获取账号 ID
- `support:*` — 调用 AWS Support API

### 产出
- Lambda ARN: `arn:aws:lambda:us-east-1:985539765717:function:aws-support-tools-lambda`

### 遇到的问题
无，一次成功。

---

## Step 2: 创建 Knowledge Base（模块 01）

### 做了什么
原项目用 Jupyter Notebook（`create_knowledge_base.ipynb`），我们提取成了脚本 `deploy_knowledge_base.py`：

1. 创建 S3 bucket `bedrock-aws-support-rag-bucket-985539765717`
2. 上传文档到 S3（目前 1 份 EC2 实例规格 HTML）
3. 使用 `BedrockKnowledgeBase` helper 类自动创建：
   - IAM 执行角色
   - OpenSearch Serverless Collection（向量数据库）
   - OpenSearch 向量索引
   - Bedrock Knowledge Base
4. 触发数据同步（文档 → 切片 → Titan Embeddings 向量化 → 存入 OpenSearch）
5. 把 KB ID 存到 SSM Parameter Store

### 关键概念
- **S3 Bucket**：存放原始文档的地方
- **Titan Embeddings**：AWS 的模型，把文字转成数字向量，语义相近的文字向量也相近
- **OpenSearch Serverless**：向量数据库，存放文档切片的向量，支持语义搜索
- **Bedrock Knowledge Base**：把上面三个串起来的托管服务，一个 KB ID 代表整个检索链路
- **SSM Parameter Store**：云上的 key-value 配置存储，Agent 启动时从这里读 KB ID

### 产出
- KB ID: `GZDVPKC7AU`
- SSM: `/support/knowledge_base/kb_id` = `GZDVPKC7AU`
- S3: `bedrock-aws-support-rag-bucket-985539765717`
- OpenSearch Collection: `bedrock-sample-rag-1170134-f`

### 遇到的问题
- S3 bucket 名字 `bedrock-aws-support-rag-bucket` 被别人占了（全局唯一），加了账号 ID 后缀解决

---

## Step 3: 创建 AgentCore Gateway（模块 03）

### 做了什么
Gateway 是 Agent 和 Lambda 之间的桥梁。Agent 通过 MCP 协议调用工具，Gateway 把调用转发给 Lambda。

1. 在 AWS Console 创建 Gateway `gateway-support`
   - Auth: AWS IAM (SigV4 签名认证)
   - Protocol: MCP
2. 用 API 脚本（`create_target.py`）添加 Lambda Target
   - 包含 7 个工具的 schema 定义
   - 使用 GATEWAY_IAM_ROLE 认证
3. 把 Gateway URL 存到 SSM（`store_gateway_url.py`）

### 为什么需要 Gateway
Agent 代码用的是 MCP（Model Context Protocol）协议调用工具。Lambda 本身不懂 MCP。Gateway 做了协议转换：
- Agent 发 MCP 请求 → Gateway 接收 → 转成 Lambda invoke → Lambda 返回结果 → Gateway 转成 MCP 响应 → Agent 收到

### API 参数结构（踩坑记录）
boto3 的 `create_gateway_target` 参数结构：
```python
targetConfiguration={
    "mcp": {
        "lambda": {
            "lambdaArn": "...",
            "toolSchema": {
                "inlinePayload": [...]  # 7 个工具的 schema
            }
        }
    }
},
credentialProviderConfigurations=[
    {"credentialProviderType": "GATEWAY_IAM_ROLE"}
]
```
注意：不是 `lambdaTarget`，是 `mcp.lambda`。`credentialProviderConfigurations` 是必填的。

### 产出
- Gateway ID: `gateway-support-xosfk0wt5b`
- Gateway URL: `https://gateway-support-xosfk0wt5b.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp`
- Lambda Target ID: `N1US1ZRO1N`
- SSM: `/support/agentgateway/aws_support_gateway`

### 遇到的问题
- Console 创建 Gateway 时 target 报错，改用 API 成功
- boto3 参数格式跟文档不一致，通过 `help()` 查到正确结构
- AWS Knowledge MCP Server target 未添加（boto3 不支持 `mcpRemoteServer` 参数），后续可在 Console 手动加

---

## Step 4: 部署 Agent Runtime（模块 04）

### 做了什么
把 Agent 代码部署到 AWS 的托管容器环境（AgentCore Runtime）。

1. 使用 `bedrock_agentcore_starter_toolkit` 的 **direct code deploy** 方式（不需要 Docker）
2. 工具自动完成：
   - 创建 IAM 执行角色
   - 用 `uv` 交叉编译所有 Python 依赖到 Linux ARM64
   - 打包成 134MB 的 zip
   - 上传到 S3
   - 创建 AgentCore Runtime
3. 等待状态变成 READY
4. 给执行角色补权限（`grant_permissions.py`）：
   - `ssm:GetParameter` — 读取 KB ID 和 Gateway URL
   - `bedrock:Retrieve` / `bedrock:InvokeModel` — 调用知识库和 LLM
   - `bedrock-agentcore:InvokeGateway` — 调用 Gateway
   - `aoss:APIAccessAll` — 访问 OpenSearch

### Agent 核心逻辑（aws_support_agent.py）
- 框架：Strands Agents（AWS 开源）
- 模型：Claude Opus 4.5（`global.anthropic.claude-opus-4-5-20251101-v1:0`）
- System Prompt：320 行，定义了双阶段工作流
  - Phase 1（Q&A）：知识库 → AWS 文档 → LLM 知识 → 建议开工单
  - Phase 2（工单管理）：用户明确要求时直接操作工单
- RBAC 实现：把 `_iam_user` 注入到 prompt 里，Agent 调用写入工具时自动带上
- 初始化模式：eager（启动时就初始化所有资源，减少首次请求延迟）

### direct code deploy vs Docker
| 对比 | direct code deploy | Docker |
|------|-------------------|--------|
| 需要 Docker？ | ❌ 不需要 | ✅ 需要 |
| 包大小限制 | 250MB | 2GB |
| 部署速度 | 首次 ~30s，后续 ~10s | 首次 ~5min |
| 适用场景 | Python 项目，快速迭代 | 复杂依赖，多语言 |

### 产出
- Agent ARN: `arn:aws:bedrock-agentcore:us-east-1:985539765717:runtime/AWS_Support_knowledge_QA_Agent-d03Gjw6Uy4`
- Execution Role: `AmazonBedrockAgentCoreSDKRuntime-us-east-1-295f81767d`
- `launch_result.pkl` 保存在项目根目录（Web Client 用来读取 Agent ARN）

### 遇到的问题
- 没装 Docker → 改用 direct code deploy 方式
- `deployment_type` 参数值是 `direct_code_deploy` 不是 `code_zip`
- 需要指定 `runtime_type="PYTHON_3_13"`
- 首次打包时 `BadZipFile` 错误 → 清理缓存重试解决

---

## Step 5: 启动 Web Client（模块 05）

### 做了什么
启动 FastAPI 后端服务：
```bash
cd 05_web_client && python3 app.py
# 运行在 http://localhost:8080
```

### Web Client 架构
- 后端：FastAPI，处理 `/chat` POST 请求，调用 Bedrock AgentCore Runtime
- 前端：原生 HTML/CSS/JS，用 SSE（Server-Sent Events）实现流式输出
- Session 管理：前端用 localStorage 按用户名存储 session ID
- 附件支持：Base64 编码上传，单文件 ≤5MB，总计 ≤25MB

### 产出
- 访问地址：http://localhost:8080

---

## Step 6: 修复知识库 401 错误

### 问题
Agent 调用知识库检索时返回 `401 Unauthorized`。

### 排查过程
1. 检查 IAM 权限 → 已正确配置 `bedrock:Retrieve` + `aoss:APIAccessAll`
2. 检查 OpenSearch data access policy → Agent 角色已在 Principal 列表中
3. 检查 OpenSearch **network policy** → 发现根因！

### 根因
OpenSearch Serverless 的网络策略设置为：
```json
{"AllowFromPublic": false, "SourceVPCEs": ["vpce-dummy12345678901"]}
```
`AllowFromPublic: false` + 一个不存在的假 VPC Endpoint = Bedrock 根本连不上 OpenSearch。
这是 `BedrockKnowledgeBase` helper 类的 bug。

### 修复
运行 `fix_network_policy.py`，把网络策略改为 `AllowFromPublic: true`。

### 验证
```python
bedrock_runtime.retrieve(knowledgeBaseId="GZDVPKC7AU", ...)
# ✅ Success: 1 results
```

---

## 创建的辅助脚本清单

| 脚本 | 位置 | 作用 |
|------|------|------|
| `deploy_knowledge_base.py` | 01_.../ | 知识库一键部署（替代 Jupyter Notebook） |
| `create_target.py` | 03_.../ | API 方式创建 Gateway Lambda Target |
| `store_gateway_url.py` | 03_.../ | Gateway URL 存到 SSM |
| `deploy_agent.py` | 04_.../ | Agent Runtime 一键部署（direct code deploy） |
| `grant_permissions.py` | 04_.../ | 给 Agent 执行角色添加权限 |
| `fix_kb_permissions.py` | 04_.../ | 补充 KB 检索权限 |
| `fix_opensearch_access.py` | 04_.../ | 更新 OpenSearch data access policy |
| `fix_network_policy.py` | 04_.../ | 修复 OpenSearch 网络策略（根因修复） |
| `fix_aoss_final.py` | 04_.../ | 排查 OpenSearch 访问问题 |
| `debug_kb.py` | 04_.../ | 诊断知识库连接问题 |
| `check_network.py` | 04_.../ | 检查 OpenSearch 网络策略和连通性 |

---

## 查看日志

| 日志 | 位置 | 看什么 |
|------|------|--------|
| Web Client | 本地终端（app.py 输出） | HTTP 请求 |
| Lambda | CloudWatch `/aws/lambda/aws-support-tools-lambda` | 工具执行、RBAC 检查 |
| Agent Runtime | CloudWatch `/aws/bedrock-agentcore/runtimes/AWS_Support_knowledge_QA_Agent-d03Gjw6Uy4-DEFAULT` | Agent 推理过程 |

---

## 待办事项

- [ ] 在 Console 给 Gateway 添加 AWS Knowledge MCP Server target（增强 AWS 官方文档搜索）
- [ ] 往 S3 bucket 添加更多技术文档并同步知识库
- [ ] 清理多余的 OpenSearch Collection（有 4 个，只用了 1 个）
