---
inclusion: auto
---

# AWS Omni Support Agent - 部署完成

## 状态：全部部署完成，已验证通过 ✅

## 环境
- AWS Account: 985539765717, IAM User: luchen-udemystudy, Region: us-east-1
- Business Support Plan: 已开通

## 资源清单
- Lambda: `arn:aws:lambda:us-east-1:985539765717:function:aws-support-tools-lambda`
- KB ID: `GZDVPKC7AU`, SSM: `/support/knowledge_base/kb_id`
- S3: `bedrock-aws-support-rag-bucket-985539765717`
- Gateway ID: `gateway-support-xosfk0wt5b`
- Gateway URL SSM: `/support/agentgateway/aws_support_gateway`
- Lambda Target ID: `N1US1ZRO1N`
- Agent ARN: `arn:aws:bedrock-agentcore:us-east-1:985539765717:runtime/AWS_Support_knowledge_QA_Agent-d03Gjw6Uy4`
- Agent Execution Role: `AmazonBedrockAgentCoreSDKRuntime-us-east-1-295f81767d`
- OpenSearch Collection: `bedrock-sample-rag-1170134-f` (id: xggorutm23tchjsravz0)
- Web Client: `05_web_client/app.py`, port 8080

## 待办
- Gateway 上添加 AWS Knowledge MCP Server target（可选，增强 AWS 官方文档搜索）
- 往 S3 添加更多文档并同步知识库
