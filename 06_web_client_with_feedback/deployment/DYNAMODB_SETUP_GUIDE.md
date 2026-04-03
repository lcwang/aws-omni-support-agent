# DynamoDB 表创建指南

> 详细说明如何创建反馈系统所需的 DynamoDB 表

**更新时间**: 2026-04-03

---

## 📋 概述

### 为什么需要 DynamoDB？

反馈系统使用 DynamoDB 存储所有**点踩（thumbs down）**反馈数据，用于：
- 记录低质量 QA 对
- 自动问题分类（knowledge_gap, bad_document, weak_retrieval, synthesis_issue）
- 优先级判断（high, medium, low）
- 后续数据分析和知识库优化

### 表基本信息

- **表名**: `support-agent-feedback-negative`
- **区域**: us-east-1（可修改）
- **计费模式**: Provisioned（可改为 On-Demand）
- **预估成本**: 按需计费 < $1/月（低流量场景）

---

## 🏗️ 表结构

### 主键设计

```
Partition Key: feedback_id (String, UUID)
Sort Key: timestamp (String, ISO 8601 格式)
```

**设计理由**：
- `feedback_id` 保证唯一性
- `timestamp` 支持按时间排序查询

---

### 属性说明

| 属性名 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `feedback_id` | String | ✅ | 主键，UUID 格式 |
| `timestamp` | String | ✅ | Sort Key，ISO 8601 时间戳 |
| `question` | String | ✅ | 用户提问 |
| `answer` | String | ✅ | Agent 回答 |
| `negative_reason` | String | ✅ | 点踩原因（hallucination/incorrect/incomplete/irrelevant） |
| `user_comment` | String | ⏸️ | 用户补充说明（可选） |
| `retrieval_details` | Map | ✅ | 检索详情（source, rag_documents, scores） |
| `issue_category` | String | ✅ | 自动分类结果 |
| `priority` | String | ✅ | 优先级（high/medium/low） |
| `status` | String | ✅ | 处理状态（pending/reviewed/resolved） |
| `frequency` | Number | ✅ | 相同问题出现次数 |
| `ttl` | Number | ⏸️ | TTL 时间戳（90 天后自动删除） |

---

### 全局二级索引（GSI）

```
索引名: issue_category-status-index
Partition Key: issue_category (String)
Sort Key: status (String)
```

**用途**: 按问题分类和状态查询
```sql
-- 查询所有待处理的知识缺口问题
SELECT * FROM support-agent-feedback-negative
WHERE issue_category = 'knowledge_gap' AND status = 'pending'
```

---

## 🚀 创建方法

### 方法 1: 使用脚本自动创建（推荐）⭐

**适用场景**: 快速部署、多环境部署

**步骤**:

```bash
# 1. 进入部署目录
cd /Users/havpan/CC_Demo/aws-omni-support-agent-v2/06_feedback/deployment

# 2. 确保 AWS 凭证已配置
aws sts get-caller-identity

# 3. 运行创建脚本
python3 setup_dynamodb.py
```

**预期输出**:
```
============================================================
DynamoDB Table Setup - Feedback System
============================================================
Creating DynamoDB table: support-agent-feedback-negative...
✓ Table creation initiated: support-agent-feedback-negative
  Status: CREATING
  ARN: arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/support-agent-feedback-negative

Waiting for table to become ACTIVE...
✓ Table is now ACTIVE

Enabling TTL...
✓ TTL enabled (attribute: ttl)

✅ Table support-agent-feedback-negative created successfully!

Next steps:
1. Update backend/config.py with table name: support-agent-feedback-negative
2. Ensure Lambda IAM role has DynamoDB permissions
3. Deploy backend API
```

**脚本功能**:
- ✅ 创建表（如果已存在则跳过）
- ✅ 配置 GSI
- ✅ 启用 TTL（90 天自动清理）
- ✅ 添加项目标签
- ✅ 等待表变为 ACTIVE
- ✅ 验证配置正确性

---

### 方法 2: AWS Console 手动创建

**适用场景**: 不熟悉脚本、需要可视化操作

**步骤**:

#### 第 1 步: 进入 DynamoDB 控制台

访问: https://console.aws.amazon.com/dynamodbv2/home?region=us-east-1

#### 第 2 步: 创建表

点击 **Create table**，填写：

**基本设置**:
- **Table name**: `support-agent-feedback-negative`
- **Partition key**: `feedback_id` (String)
- **Sort key**: `timestamp` (String)

#### 第 3 步: 配置设置

**Table settings**:
- 选择 **Customize settings**

**Read/write capacity**:
- **Capacity mode**: Provisioned（或 On-demand）
- **Read capacity**: 5 units（按需调整）
- **Write capacity**: 5 units（按需调整）

> 💡 提示: 低流量场景建议使用 **On-demand**，成本更低

#### 第 4 步: 创建 GSI

在 **Secondary indexes** 部分，点击 **Create global index**:

- **Partition key**: `issue_category` (String)
- **Sort key**: `status` (String)
- **Index name**: `issue_category-status-index`
- **Attribute projections**: All

#### 第 5 步: 配置 TTL（可选）

在 **Additional settings** 部分:
- **Time to live (TTL)**: Enabled
- **TTL attribute**: `ttl`

#### 第 6 步: 添加标签（可选）

- **Project**: AWS-Omni-Support-Agent
- **Module**: Feedback-System
- **Environment**: Production

#### 第 7 步: 创建

点击 **Create table**，等待 3-5 分钟

---

### 方法 3: AWS CLI 手动创建

**适用场景**: 自动化脚本、CI/CD 集成

```bash
# 创建表
aws dynamodb create-table \
  --table-name support-agent-feedback-negative \
  --attribute-definitions \
      AttributeName=feedback_id,AttributeType=S \
      AttributeName=timestamp,AttributeType=S \
      AttributeName=issue_category,AttributeType=S \
      AttributeName=status,AttributeType=S \
  --key-schema \
      AttributeName=feedback_id,KeyType=HASH \
      AttributeName=timestamp,KeyType=RANGE \
  --global-secondary-indexes \
      "[
        {
          \"IndexName\": \"issue_category-status-index\",
          \"KeySchema\": [
            {\"AttributeName\":\"issue_category\",\"KeyType\":\"HASH\"},
            {\"AttributeName\":\"status\",\"KeyType\":\"RANGE\"}
          ],
          \"Projection\": {\"ProjectionType\":\"ALL\"},
          \"ProvisionedThroughput\": {
            \"ReadCapacityUnits\": 5,
            \"WriteCapacityUnits\": 5
          }
        }
      ]" \
  --billing-mode PROVISIONED \
  --provisioned-throughput \
      ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --tags \
      Key=Project,Value=AWS-Omni-Support-Agent \
      Key=Module,Value=Feedback-System \
  --region us-east-1

# 等待表创建完成
aws dynamodb wait table-exists \
  --table-name support-agent-feedback-negative \
  --region us-east-1

# 启用 TTL
aws dynamodb update-time-to-live \
  --table-name support-agent-feedback-negative \
  --time-to-live-specification \
      "Enabled=true,AttributeName=ttl" \
  --region us-east-1
```

---

## 🔐 IAM 权限要求

### 创建表所需权限

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DescribeTable",
        "dynamodb:UpdateTimeToLive",
        "dynamodb:TagResource"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/support-agent-feedback-negative"
    }
  ]
}
```

### 应用运行时权限

Lambda 或 EC2 需要以下权限访问表：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:*:table/support-agent-feedback-negative",
        "arn:aws:dynamodb:us-east-1:*:table/support-agent-feedback-negative/index/*"
      ]
    }
  ]
}
```

---

## ✅ 验证创建成功

### 方法 1: AWS CLI

```bash
# 查看表状态
aws dynamodb describe-table \
  --table-name support-agent-feedback-negative \
  --region us-east-1 \
  --query 'Table.[TableName,TableStatus,GlobalSecondaryIndexes[0].IndexName]'

# 预期输出:
# [
#   "support-agent-feedback-negative",
#   "ACTIVE",
#   "issue_category-status-index"
# ]
```

### 方法 2: Python 脚本

```python
import boto3

dynamodb = boto3.client('dynamodb', region_name='us-east-1')

response = dynamodb.describe_table(
    TableName='support-agent-feedback-negative'
)

print(f"Table Status: {response['Table']['TableStatus']}")
print(f"Item Count: {response['Table'].get('ItemCount', 0)}")

# 检查 GSI
gsi_names = [gsi['IndexName'] for gsi in response['Table'].get('GlobalSecondaryIndexes', [])]
print(f"GSI: {gsi_names}")
```

### 方法 3: AWS Console

访问: https://console.aws.amazon.com/dynamodbv2/home?region=us-east-1#table?name=support-agent-feedback-negative

检查：
- ✅ 表状态为 **Active**
- ✅ GSI `issue_category-status-index` 存在
- ✅ TTL 已启用

---

## 🧪 测试写入数据

```bash
# 写入测试记录
aws dynamodb put-item \
  --table-name support-agent-feedback-negative \
  --item '{
    "feedback_id": {"S": "test-001"},
    "timestamp": {"S": "2026-04-03T10:00:00Z"},
    "question": {"S": "测试问题"},
    "answer": {"S": "测试答案"},
    "negative_reason": {"S": "incorrect"},
    "issue_category": {"S": "knowledge_gap"},
    "priority": {"S": "high"},
    "status": {"S": "pending"},
    "frequency": {"N": "1"}
  }' \
  --region us-east-1

# 查询数据
aws dynamodb get-item \
  --table-name support-agent-feedback-negative \
  --key '{
    "feedback_id": {"S": "test-001"},
    "timestamp": {"S": "2026-04-03T10:00:00Z"}
  }' \
  --region us-east-1

# 删除测试数据
aws dynamodb delete-item \
  --table-name support-agent-feedback-negative \
  --key '{
    "feedback_id": {"S": "test-001"},
    "timestamp": {"S": "2026-04-03T10:00:00Z"}
  }' \
  --region us-east-1
```

---

## 🔧 高级配置

### 切换到按需计费模式

```bash
aws dynamodb update-table \
  --table-name support-agent-feedback-negative \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

**优势**:
- 自动扩展
- 只为实际使用付费
- 适合流量不确定的场景

**成本估算**（按需模式）:
- 写入: $1.25 per million requests
- 读取: $0.25 per million requests
- 存储: $0.25 per GB-month

**预估**: 每月 1000 次反馈 < $0.01

---

### 启用 Point-in-Time Recovery（备份）

```bash
aws dynamodb update-continuous-backups \
  --table-name support-agent-feedback-negative \
  --point-in-time-recovery-specification \
      PointInTimeRecoveryEnabled=true \
  --region us-east-1
```

**用途**: 支持过去 35 天内任意时间点恢复

---

### 启用 DynamoDB Streams（可选）

```bash
aws dynamodb update-table \
  --table-name support-agent-feedback-negative \
  --stream-specification \
      StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
  --region us-east-1
```

**用途**: 实时捕获数据变更，触发 Lambda 进行后续处理

---

## ❓ 常见问题

### Q1: 表已存在，如何修改配置？

**A**: 无法直接修改主键，但可以修改其他配置：

```bash
# 修改容量
aws dynamodb update-table \
  --table-name support-agent-feedback-negative \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10 \
  --region us-east-1

# 添加新的 GSI（如需要）
aws dynamodb update-table \
  --table-name support-agent-feedback-negative \
  --attribute-definitions AttributeName=new_attr,AttributeType=S \
  --global-secondary-index-updates \
      "[{\"Create\":{\"IndexName\":\"new-index\",\"KeySchema\":[{\"AttributeName\":\"new_attr\",\"KeyType\":\"HASH\"}],\"Projection\":{\"ProjectionType\":\"ALL\"},\"ProvisionedThroughput\":{\"ReadCapacityUnits\":5,\"WriteCapacityUnits\":5}}}]" \
  --region us-east-1
```

---

### Q2: 如何删除表？

**A**: 谨慎操作！删除前请备份数据

```bash
# 导出数据（可选）
aws dynamodb scan \
  --table-name support-agent-feedback-negative \
  --region us-east-1 \
  > backup_$(date +%Y%m%d).json

# 删除表
aws dynamodb delete-table \
  --table-name support-agent-feedback-negative \
  --region us-east-1
```

---

### Q3: 如何在不同区域创建？

**A**: 修改脚本或 CLI 命令中的 `--region` 参数

```python
# 在 setup_dynamodb.py 中修改
AWS_REGION = 'ap-southeast-1'  # 改为你的区域
```

或

```bash
# CLI 命令中指定
aws dynamodb create-table ... --region ap-southeast-1
```

---

### Q4: 成本如何估算？

**A**: 低流量场景（< 1000 次反馈/月）

**Provisioned 模式**:
- 5 RCU + 5 WCU ≈ $0.65/月
- 存储 (< 1GB) ≈ $0.25/月
- **总计**: < $1/月

**On-Demand 模式**:
- 1000 次写入 ≈ $0.00125
- 存储 (< 1GB) ≈ $0.25/月
- **总计**: < $0.30/月（更便宜！）

---

### Q5: 如何监控表使用情况？

**A**: 使用 CloudWatch Metrics

```bash
# 查看读写容量使用
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=support-agent-feedback-negative \
  --start-time 2026-04-02T00:00:00Z \
  --end-time 2026-04-03T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --region us-east-1
```

或在 CloudWatch Console 查看:
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#metricsV2:graph=~();query=~'*7bAWS*2fDynamoDB*2cTableName*7d

---

## 📚 相关文档

- [DynamoDB 操作代码](../backend/operations/dynamodb_operations.py)
- [反馈数据模型](../backend/models.py)
- [IAM 权限模板](./iam_policy.json)
- [快速开始指南](../QUICKSTART.md)

---

## 📞 获取帮助

如果遇到问题：

1. 检查 AWS 凭证: `aws sts get-caller-identity`
2. 检查 IAM 权限: 是否有 `dynamodb:CreateTable` 权限
3. 查看 CloudTrail 日志: 查找失败原因
4. 参考 AWS 文档: https://docs.aws.amazon.com/dynamodb/

---

**文档版本**: 1.0
**最后更新**: 2026-04-03
**维护者**: AWS Omni Support Agent Team
