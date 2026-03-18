# 使用指南 - 优化后的 agentic_rag_mcp.py

## 快速开始

### 1. 本地开发测试

```bash
# 克隆代码
cd /path/to/04_create_knowledge_mcp_gateway_Agent

# 安装依赖
uv pip install -r requirements.txt

# 设置环境变量（可选，如果你想覆盖默认值）
export AWS_REGION=us-west-2
export SSM_TIMEOUT=15

# 运行 Agent
python agentic_rag_mcp.py
```

### 2. 不同 Region 部署

#### 场景 A: SageMaker Notebook 在 us-west-2
```bash
# 不需要任何特殊配置，自动检测 region
# 所有资源（Gateway, KB, Runtime）会使用 us-west-2

cd /home/sagemaker-user/your-project
python agentic_rag_mcp.py
```

#### 场景 B: 手动指定 Region
```bash
# 方法 1: 环境变量
export AWS_REGION=us-east-1
python agentic_rag_mcp.py

# 方法 2: 内联设置
AWS_REGION=eu-west-1 python agentic_rag_mcp.py
```

#### 场景 C: Lambda 部署
在 Lambda 函数配置中设置环境变量：
```json
{
  "Environment": {
    "Variables": {
      "AWS_REGION": "us-west-2",
      "MAX_RETRIES": "5",
      "MCP_TIMEOUT": "60"
    }
  }
}
```

### 3. AgentCore Runtime 部署

#### 方式 1: 通过 .bedrock_agentcore.yaml
```yaml
# 注意：不要提交包含账号信息的 yaml 到版本控制
agents:
  my_agent:
    name: my_agent
    aws:
      region: us-west-2  # 自动使用此 region
      environment:
        MAX_RETRIES: "5"
        MCP_TIMEOUT: "60"
```

#### 方式 2: 通过 deploy_QA_agent.ipynb
```python
# 在 notebook 中部署时
import os
os.environ['AWS_REGION'] = 'us-west-2'

# 然后运行部署命令
!bedrock-agentcore deploy
```

---

## 配置参考

### 环境变量完整列表

| 变量名 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `AWS_REGION` | string | auto-detect | AWS 区域（us-east-1, us-west-2 等） |
| `AWS_DEFAULT_REGION` | string | auto-detect | AWS 区域（备用） |
| `SSM_GATEWAY_PARAM` | string | /support/agentgateway/aws_support_gateway | Gateway URL 的 SSM 参数路径 |
| `SSM_KB_PARAM` | string | /support/knowledge_base/kb_id | Knowledge Base ID 的 SSM 参数路径 |
| `BEDROCK_MODEL_ID` | string | global.anthropic.claude-opus-4-5-20251101-v1:0 | Bedrock 模型 ID |
| `MODEL_TEMPERATURE` | float | 0.3 | 模型温度（0-1） |
| `SSM_TIMEOUT` | int | 10 | SSM 操作超时（秒） |
| `MCP_TIMEOUT` | int | 30 | MCP 操作超时（秒） |
| `MAX_RETRIES` | int | 3 | 最大重试次数 |
| `INIT_MODE` | string | eager | 初始化模式（eager/lazy） |
| `LOG_LEVEL` | string | INFO | 日志级别 |

### ⚠️ INIT_MODE 重要说明

**`eager` 模式（默认 - 推荐用于生产）：**
- 在模块加载时立即初始化所有资源
- Lambda 容器启动后立即可用（"热"容器）
- 首次请求无延迟
- **适用于 AgentCore Runtime / Lambda 部署**

**`lazy` 模式（用于开发测试）：**
- 首次请求时才初始化资源
- 减少模块导入时间
- 首次请求会慢（5-8秒）
- **仅用于本地开发和测试**

### Region 自动检测逻辑
```
1. 检查 AWS_REGION 环境变量
   ↓ 未设置
2. 检查 AWS_DEFAULT_REGION 环境变量
   ↓ 未设置
3. 从 boto3 Session 获取默认 region
   ↓ 未设置
4. 从 EC2 实例元数据获取（适用于 Lambda/EC2）
   ↓ 不可用
5. 使用默认值 us-east-1
```

---

## 性能优化建议

### 1. 冷启动优化

#### 问题：首次请求慢
**原因：** 延迟初始化导致第一个请求需要初始化所有资源

**解决方案 A：预热请求**
```python
# 在 Lambda 初始化阶段发送一个预热请求
if __name__ == "__main__":
    import asyncio

    # 预加载 agent
    _ = get_agent()

    # 然后启动应用
    app.run()
```

**解决方案 B：Lambda 预配置并发**
```bash
aws lambda put-provisioned-concurrency-config \
  --function-name my-agent-function \
  --provisioned-concurrent-executions 2
```

### 2. 成本优化

#### 场景：大量简单查询
**问题：** Opus 4.5 成本高

**解决方案：根据查询复杂度动态选择模型**
```bash
# 简单查询使用 Haiku
export BEDROCK_MODEL_ID=global.anthropic.claude-3-5-haiku-20241022-v1:0

# 复杂案例分析使用 Opus
export BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-5-20251101-v1:0
```

或者在代码中实现智能路由：
```python
# 未来优化：根据查询长度/复杂度选择模型
def select_model(prompt):
    if len(prompt) < 50 and not any(kw in prompt for kw in ['分析', '详细']):
        return "haiku"
    else:
        return "opus"
```

### 3. 网络优化

#### 场景：跨 Region 调用慢
**确保资源在同一 Region：**
```bash
# 检查各资源所在 region
aws bedrock-agentcore describe-runtime --runtime-id xxx --query 'runtime.region'
aws bedrock list-knowledge-bases --query 'knowledgeBaseSummaries[0].region'

# 如果不一致，重新部署到同一 region
export AWS_REGION=us-west-2
```

---

## 故障排查

### 问题 1: "Unable to locate credentials"
**错误信息：**
```
ValueError: Unable to obtain AWS credentials. Ensure IAM role is properly configured.
```

**解决方法：**
```bash
# 检查 AWS 凭证
aws sts get-caller-identity

# 如果使用 IAM role（Lambda/EC2）
# 确保 IAM role 有以下权限：
# - ssm:GetParameter
# - bedrock:InvokeModel
# - bedrock-agentcore:*

# 本地开发配置凭证
aws configure
```

### 问题 2: "Parameter not found"
**错误信息：**
```
ClientError: An error occurred (ParameterNotFound) when calling the GetParameter operation
```

**解决方法：**
```bash
# 1. 检查 SSM 参数是否存在
aws ssm get-parameter --name /support/agentgateway/aws_support_gateway --region us-west-2

# 2. 如果路径不同，设置环境变量
export SSM_GATEWAY_PARAM=/your/custom/path

# 3. 或者创建缺失的参数
aws ssm put-parameter \
  --name /support/agentgateway/aws_support_gateway \
  --value "https://your-gateway-url" \
  --type String \
  --region us-west-2
```

### 问题 3: 请求超时
**错误信息：**
```
TimeoutError: Tool retrieval exceeded 30s timeout
```

**解决方法：**
```bash
# 增加超时时间
export MCP_TIMEOUT=60
export SSM_TIMEOUT=20

# 或者检查网络连接
curl -v https://your-gateway-url
```

### 问题 4: Region 不匹配
**症状：** 请求失败或延迟高

**诊断：**
```python
# 在代码中添加调试日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看实际使用的 region
# 日志会输出：Initialized with region: us-west-2
```

**解决：**
```bash
# 显式设置正确的 region
export AWS_REGION=us-west-2
```

---

## 监控和日志

### CloudWatch Logs 查询示例

#### 1. 查找慢请求（>10秒）
```
filter @message like /Completed successfully/
| parse @message /(?<elapsed>[\d.]+)s$/
| filter elapsed > 10
| stats count() by bin(5m)
```

#### 2. 错误率统计
```
filter @message like /error/
| stats count() by type
```

#### 3. 冷启动分析
```
filter @message like /Initializing/
| stats count() by bin(1h)
```

### 自定义 CloudWatch Metrics
```python
import boto3

cloudwatch = boto3.client('cloudwatch', region_name=REGION)

def publish_metrics(request_id, elapsed_time, chunk_count):
    cloudwatch.put_metric_data(
        Namespace='AgentCore/Support',
        MetricData=[
            {
                'MetricName': 'RequestLatency',
                'Value': elapsed_time,
                'Unit': 'Seconds'
            },
            {
                'MetricName': 'ResponseChunks',
                'Value': chunk_count,
                'Unit': 'Count'
            }
        ]
    )
```

---

## 安全最佳实践

### 1. 不要提交敏感信息到 Git
```bash
# .gitignore 已配置，但务必检查
git status  # 确保 .bedrock_agentcore.yaml 未被追踪

# 如果不小心提交了，立即撤销
git rm --cached .bedrock_agentcore.yaml
git commit -m "Remove sensitive config"
```

### 2. 使用 IAM 最小权限原则
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter"
      ],
      "Resource": [
        "arn:aws:ssm:*:*:parameter/support/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude*"
      ]
    }
  ]
}
```

### 3. 启用 CloudTrail 审计
```bash
# 记录所有 SSM GetParameter 调用
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetParameter
```

---

## 测试示例

### 单元测试
```python
# test_agentic_rag_mcp.py
import pytest
import os

def test_region_detection_from_env():
    os.environ['AWS_REGION'] = 'ap-southeast-1'
    from agentic_rag_mcp import get_aws_region
    assert get_aws_region() == 'ap-southeast-1'

def test_lazy_initialization():
    from agentic_rag_mcp import _agent, get_agent
    assert _agent is None  # 未初始化
    agent = get_agent()
    assert agent is not None  # 已初始化
```

### 集成测试
```bash
# 测试完整流程
cat > test_payload.json <<EOF
{
  "prompt": "show me my recent support cases",
  "request_id": "test-123"
}
EOF

python -c "
import asyncio
from agentic_rag_mcp import strands_agent_bedrock

async def test():
    payload = {'prompt': 'test query', 'request_id': 'test-123'}
    async for chunk in strands_agent_bedrock(payload):
        print(chunk)

asyncio.run(test())
"
```

---

## 常见使用场景

### 场景 1: 多环境部署
```bash
# 开发环境（us-west-2）
cat > .env.dev <<EOF
AWS_REGION=us-west-2
SSM_GATEWAY_PARAM=/support/dev/gateway
BEDROCK_MODEL_ID=global.anthropic.claude-3-5-haiku-20241022-v1:0
EOF

# 生产环境（us-east-1）
cat > .env.prod <<EOF
AWS_REGION=us-east-1
SSM_GATEWAY_PARAM=/support/prod/gateway
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-5-20251101-v1:0
MAX_RETRIES=5
EOF

# 使用
export $(cat .env.dev | xargs) && python agentic_rag_mcp.py
```

### 场景 2: 批量请求处理
```python
import asyncio
from agentic_rag_mcp import strands_agent_bedrock

async def batch_process(prompts):
    tasks = [
        strands_agent_bedrock({"prompt": p, "request_id": f"batch-{i}"})
        for i, p in enumerate(prompts)
    ]

    results = []
    for task in asyncio.as_completed(tasks):
        result = []
        async for chunk in await task:
            result.append(chunk)
        results.append(result)

    return results

# 使用
prompts = ["query 1", "query 2", "query 3"]
results = asyncio.run(batch_process(prompts))
```

### 场景 3: 健康检查端点
```python
from fastapi import FastAPI
from agentic_rag_mcp import get_agent, get_mcp_client

app = FastAPI()

@app.get("/health")
async def health_check():
    try:
        # 检查 agent 是否可用
        agent = get_agent()
        mcp_client = get_mcp_client()

        return {
            "status": "healthy",
            "agent_initialized": agent is not None,
            "mcp_connected": mcp_client is not None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 503
```

---

## 升级指南

### 从旧版本迁移
如果你使用的是优化前的代码：

1. **无需修改调用代码** - 完全向后兼容
2. **可选配置增强** - 添加环境变量以获得更好的控制
3. **日志更详细** - 查看新的日志输出，调整告警阈值

```bash
# 1. 备份现有代码
cp agentic_rag_mcp.py agentic_rag_mcp.py.backup

# 2. 替换为新版本
# （已完成）

# 3. 测试
python agentic_rag_mcp.py

# 4. 如果有问题，回滚
# cp agentic_rag_mcp.py.backup agentic_rag_mcp.py
```

---

## 获取帮助

### 查看详细日志
```bash
export LOG_LEVEL=DEBUG
python agentic_rag_mcp.py 2>&1 | tee debug.log
```

### 常见问题
- **问题集合**：查看 OPTIMIZATION_SUMMARY.md 的"遗留问题"部分
- **性能分析**：查看 CloudWatch Logs 的性能指标
- **配置验证**：运行健康检查确认所有资源可达

---

## 下一步

- [ ] 阅读 OPTIMIZATION_SUMMARY.md 了解技术细节
- [ ] 根据你的部署环境配置环境变量
- [ ] 运行测试验证功能
- [ ] 设置 CloudWatch 告警
- [ ] 定期检查成本和性能指标
