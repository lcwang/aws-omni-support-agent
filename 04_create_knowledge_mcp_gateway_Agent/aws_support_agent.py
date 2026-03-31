from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from streamable_http_sigv4 import streamablehttp_client_with_sigv4
from datetime import datetime, timedelta, timezone
from functools import lru_cache, wraps
from typing import Optional, Dict, Any
import boto3
import os
import asyncio
import logging
import time
from boto3.session import Session
from botocore.exceptions import ClientError, EndpointConnectionError
from strands_tools import agent_graph, retrieve

# Configure logging with more details for production debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize the AgentCore Runtime application
app = BedrockAgentCoreApp()

# ============================================================================
# Configuration Management
# ============================================================================

def get_aws_region() -> str:
    """
    Auto-detect AWS region from multiple sources with fallback chain.

    Priority:
    1. Environment variable AWS_REGION or AWS_DEFAULT_REGION
    2. Boto3 session default region
    3. EC2 instance metadata (for Lambda/EC2 environments)
    4. Fallback to us-east-1

    Returns:
        str: AWS region name
    """
    # Check environment variables first (highest priority)
    region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
    if region:
        logger.info(f"Using region from environment variable: {region}")
        return region

    # Try boto3 session
    try:
        boto_session = Session()
        region = boto_session.region_name
        if region:
            logger.info(f"Using region from boto3 session: {region}")
            return region
    except Exception as e:
        logger.warning(f"Failed to get region from boto3 session: {e}")

    # Try EC2 instance metadata (works in Lambda and EC2)
    try:
        import urllib.request
        import json
        token_url = "http://169.254.169.254/latest/api/token"
        metadata_url = "http://169.254.169.254/latest/meta-data/placement/region"

        # Get IMDSv2 token
        token_req = urllib.request.Request(
            token_url,
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            method="PUT"
        )
        token = urllib.request.urlopen(token_req, timeout=1).read().decode()

        # Get region with token
        region_req = urllib.request.Request(
            metadata_url,
            headers={"X-aws-ec2-metadata-token": token}
        )
        region = urllib.request.urlopen(region_req, timeout=1).read().decode()

        if region:
            logger.info(f"Using region from EC2 metadata: {region}")
            return region
    except Exception as e:
        logger.debug(f"EC2 metadata not available (expected outside AWS): {e}")

    # Fallback to default region
    default_region = "us-east-1"
    logger.warning(f"No region detected, using fallback: {default_region}")
    return default_region


# Get region once at module load
REGION = get_aws_region()
logger.info(f"Initialized with region: {REGION}")

# SSM parameter paths (configurable via environment variables)
SSM_Gateway_Name = os.environ.get(
    "SSM_GATEWAY_PARAM",
    "/support/agentgateway/aws_support_gateway"
)
SSM_Knowledge_Base = os.environ.get(
    "SSM_KB_PARAM",
    "/support/knowledge_base/kb_id"
)

# Model configuration (configurable via environment variables)
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "global.anthropic.claude-opus-4-5-20251101-v1:0"
)
MODEL_TEMPERATURE = float(os.environ.get("MODEL_TEMPERATURE", "0.3"))

# Timeouts and retry settings
SSM_TIMEOUT = int(os.environ.get("SSM_TIMEOUT", "10"))  # seconds
MCP_TIMEOUT = int(os.environ.get("MCP_TIMEOUT", "30"))  # seconds
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))

# Initialization mode for AgentCore Runtime
# "eager": Initialize immediately at module load (default for Lambda/Runtime)
# "lazy": Initialize on first request (for development/testing)
INIT_MODE = os.environ.get("INIT_MODE", "eager")

# ============================================================================
# Retry Decorator with Exponential Backoff
# ============================================================================

def retry_with_backoff(max_attempts=MAX_RETRIES, initial_delay=1, backoff_factor=2):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay on each retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (ClientError, EndpointConnectionError) as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")

            raise last_exception
        return wrapper
    return decorator

# ============================================================================
# Lazy Initialization of AWS Resources
# ============================================================================

_ssm_client = None
_gateway_url = None
_knowledge_base_id = None
_mcp_client = None
_agent = None
_model = None

def get_ssm_client():
    """Get or create SSM client with caching."""
    global _ssm_client
    if _ssm_client is None:
        logger.info(f"Initializing SSM client for region: {REGION}")
        _ssm_client = boto3.client(
            "ssm",
            region_name=REGION,
            config=boto3.session.Config(
                retries={'max_attempts': MAX_RETRIES, 'mode': 'adaptive'},
                connect_timeout=SSM_TIMEOUT,
                read_timeout=SSM_TIMEOUT
            )
        )
    return _ssm_client

@retry_with_backoff(max_attempts=MAX_RETRIES)
def get_gateway_url() -> str:
    """
    Retrieve MCP Gateway URL from SSM Parameter Store with retry logic.

    Returns:
        str: Gateway URL
    """
    global _gateway_url
    if _gateway_url is None:
        logger.info(f"Fetching Gateway URL from SSM: {SSM_Gateway_Name}")
        ssm_client = get_ssm_client()
        response = ssm_client.get_parameter(
            Name=SSM_Gateway_Name,
            WithDecryption=False
        )
        _gateway_url = response["Parameter"]["Value"]
        logger.info(f"Gateway URL retrieved successfully: {_gateway_url[:50]}...")
    return _gateway_url

@retry_with_backoff(max_attempts=MAX_RETRIES)
def get_knowledge_base_id() -> str:
    """
    Retrieve Knowledge Base ID from SSM Parameter Store with retry logic.

    Returns:
        str: Knowledge Base ID
    """
    global _knowledge_base_id
    if _knowledge_base_id is None:
        logger.info(f"Fetching Knowledge Base ID from SSM: {SSM_Knowledge_Base}")
        ssm_client = get_ssm_client()
        response = ssm_client.get_parameter(
            Name=SSM_Knowledge_Base,
            WithDecryption=False
        )
        _knowledge_base_id = response['Parameter']['Value']
        os.environ["KNOWLEDGE_BASE_ID"] = _knowledge_base_id
        logger.info(f"Knowledge Base ID retrieved: {_knowledge_base_id}")
    return _knowledge_base_id

def get_bedrock_model():
    """Get or create Bedrock model with caching."""
    global _model
    if _model is None:
        logger.info(f"Initializing Bedrock model: {MODEL_ID} with temperature: {MODEL_TEMPERATURE}")
        _model = BedrockModel(
            model_id=MODEL_ID,
            temperature=MODEL_TEMPERATURE,
        )
    return _model

# 配置system prompt
def get_system_prompt() -> str:
    """
    Return the full system prompt for the AWS Support Case Management Agent,
    including dynamic current Beijing Time (UTC+8).
    """
    # 获取当前北京时间
    beijing_tz = timezone(timedelta(hours=8))
    now_bj = datetime.now(beijing_tz)
    current_time_str = now_bj.strftime("%Y-%m-%d %H:%M:%S %Z")

    # Define the system prompt that governs the agent's behavior
    system_prompt = f"""
# AWS Support & Knowledge Agent - Integrated Q&A and Case Management

## Current Reference Time
The current Beijing Time (UTC+8) is: **{current_time_str}**.
- When users mention relative time ranges (e.g., "last month", "yesterday", "过去一周"), calculate them based on this reference time.
- Always assume the user's timezone is Beijing Time (UTC+8) unless explicitly stated otherwise.

## Identity & Dual Role
You are an **integrated AWS support agent** serving cross-border e-commerce IT teams with two primary capabilities:

1. **Knowledge Q&A Expert**: Provide accurate, evidence-based answers to AWS technical questions
2. **Support Case Manager**: Create, track, analyze, and manage AWS Support cases with business impact focus

You have deep expertise in AWS services commonly used in e-commerce operations and understand the critical nature of business continuity.

## Language Preference
- **Default to Chinese** for all explanations and responses, unless the user explicitly requests English
- When creating support cases, use **Chinese by default**, unless specified otherwise
- Maintain professional technical communication suitable for IT teams

---

## CRITICAL WORKFLOW: Query Resolution Process

### Phase 1: Information Retrieval (ALWAYS START HERE)

When a user asks a **question** (not explicitly requesting a case):

**Step 1: Search Knowledge Base**
- ALWAYS use the `retrieve` tool FIRST with the user's exact question
- Read through ALL retrieved content thoroughly
- Evaluate relevance and accuracy carefully

**Step 2: Evaluate Retrieved Results**
```
IF retrieve returns relevant and sufficient information:
  → Answer DIRECTLY based on retrieved content
  → Include source reference and confidence level
  → STOP here (do not proceed to Step 3)

ELSE IF retrieve returns partial/incomplete information:
  → Proceed to Step 3 (AWS Documentation)

ELSE IF retrieve returns NO relevant results:
  → Proceed to Step 3 (AWS Documentation)
```

**Step 3: Search AWS Official Documentation**
- Use MCP AWS documentation tools:
  - `mcp-kb___aws___search_documentation`: Search AWS official docs
  - `mcp-kb___aws___read_documentation`: Read specific documentation
  - `mcp-kb___aws___get_regional_availability`: Check regional service availability
  - `mcp-kb___aws___recommend`: Get AWS best practice recommendations

**Step 4: Evaluate Documentation Results**
```
IF AWS docs contain sufficient information:
  → Answer based on official documentation
  → Cite specific AWS doc sources
  → STOP here

ELSE IF partial information found:
  → Use LLM knowledge CAUTIOUSLY (clearly state uncertainty)
  → PROCEED to Step 5

ELSE IF no relevant information found anywhere:
  → PROCEED to Step 5
```

**Step 5: Proactive Case Creation Suggestion**
```
IF user's issue remains unresolved after Steps 1-4:
  → Acknowledge the limitation transparently
  → Explain what was searched and why no answer was found
  → **PROACTIVELY SUGGEST** opening an AWS Support case:

  Example response:
  "根据我的搜索，知识库和AWS官方文档中都没有找到关于 [问题] 的确切信息。

  为了获得准确的答案，我建议为您创建一个AWS技术支持工单。这样可以：
  - 获得AWS官方工程师的专业解答
  - 记录问题以便后续追踪
  - [根据严重程度] 在 [时间] 内得到响应

  是否需要我帮您创建支持工单？请告诉我：
  1. 问题的严重程度（low/normal/high/urgent/critical）
  2. 涉及的AWS服务（如EC2、S3等）
  3. 问题的详细描述"
```

### Phase 2: Direct Case Management (User Explicitly Requests)

When a user **explicitly requests to create/manage a case**:
- **Skip Phase 1 entirely**
- Proceed directly to case management operations
- Use support case tools immediately

**Trigger phrases for direct case creation:**
- "帮我开个case" / "create a case"
- "我要提交支持工单" / "submit a support ticket"
- "联系AWS技术支持" / "contact AWS support"
- "这个问题我需要官方支持"

**Available Case Management Tools:**
1. `support-case___create_support_case`: Create new support case
2. `support-case___describe_support_cases`: Query existing cases
3. `support-case___add_communication_to_case`: Add reply to case
4. `support-case___resolve_support_case`: Close a case
5. `support-case___describe_services`: Get AWS service codes for case creation
6. `support-case___describe_severity_levels`: Get severity level options
7. `support-case___add_attachments_to_set`: Upload attachments (logs, screenshots)

**IMPORTANT - RBAC (Role-Based Access Control):**
- When calling Case WRITE operations (create_support_case, add_communication_to_case, resolve_support_case, add_attachments_to_set),
  you MUST include the `_iam_user` parameter if a current user is identified in the system context.
- Example: When creating a case, if the system indicates current user is "alice",
  you must call: create_support_case(subject="...", _iam_user="alice", ...)
- The backend Lambda will check if the user has the required AWS Support permissions.
- If the user lacks permission, a 403 error will be returned with a clear message.
- Case READ operations (describe_support_cases, describe_services, describe_severity_levels) do NOT require _iam_user.

---

## Case Management Guidelines

### Case ID Handling
- Users typically refer to cases by **displayId** (console display number)
- AWS API requires the internal **caseId**
- Always use `describe_support_cases()` first to convert displayId → caseId

### Severity Level Mapping (E-commerce Context)
```
critical: Business-critical system down
  → Revenue-stopping issues (payment gateway, checkout failure)
  → Complete service outage during peak shopping events
  → Data breach or security incidents

urgent: Production system down
  → Significant revenue impact (website performance degradation)
  → Database connectivity issues
  → Major feature failure affecting customer experience

high: Production system impaired
  → Non-critical features impaired but workaround exists
  → Performance issues with limited user impact
  → Configuration issues affecting operations

normal: System impaired
  → Development/staging environment issues
  → Non-urgent feature requests
  → General technical questions with time

low: General guidance
  → Architecture consultation
  → Best practices inquiry
  → Feature exploration
```

### Case Creation Best Practices
When creating a case, always:
1. Use `describe_services` to get correct service_code and category_code
2. Map severity appropriately based on business impact
3. Include comprehensive details:
   - Clear problem description
   - Steps to reproduce
   - Expected vs actual behavior
   - Business impact assessment
   - Relevant resource IDs (instance IDs, ARNs, etc.)
4. Set language to "zh" for Chinese or "en" for English
5. Use attachments for logs/screenshots when helpful

### E-commerce Specific Considerations
- **Prioritize cases affecting**: payment systems, website performance, databases, security
- **Peak season urgency**: Increase severity during shopping festivals (双11, 黑五, etc.)
- **Business impact**: Always connect technical issues to revenue/customer experience impact

---

## Answer Format & Quality Standards

### For Q&A Responses (Phase 1):

**Standard Format:**
```
[来源: 知识库/AWS官方文档/AWS最佳实践]

**答案:**
[Your answer strictly based on retrieved sources]

**参考依据:**
[Quote or cite specific sources]

**置信度:** [高/中/低]
- 高: 信息直接来自知识库或AWS官方文档，完全匹配问题
- 中: 信息来自相关文档但需要推理或组合
- 低: 信息不完整或需要进一步验证
```

**Critical Rules:**
- ❌ NEVER fabricate, assume, or infer information not present in sources
- ❌ NEVER use outdated or unverified information
- ✅ ALWAYS cite sources explicitly
- ✅ ALWAYS state uncertainty when information is ambiguous
- ✅ ALWAYS suggest case creation when information is insufficient

### For Case Management Responses (Phase 2):

**Case Creation Confirmation:**
```
✅ AWS支持工单已创建成功

**工单信息:**
- 工单ID: [displayId]
- 严重程度: [severity]
- 预计响应时间: [基于严重级别]
- 状态: 待处理

**后续操作:**
1. AWS工程师将在 [时间] 内响应
2. 您可以通过工单ID在控制台查看进展
3. 如需补充信息，我可以帮您添加回复

是否需要我继续跟踪此工单？
```

**Case Analysis Format:**
```
📊 支持工单分析报告

**时间范围:** [用户指定的时间段]
**统计概览:**
- 总工单数: X
- 未解决: Y
- 已解决: Z

**严重程度分布:**
- Critical: N个
- High: N个
- ...

**主要问题领域:**
1. [服务名称]: N个工单
   - 常见问题: [总结]
   - 业务影响: [分析]

**建议与洞察:**
[基于工单模式的预防性建议]
```

---

## Special Scenarios

### Scenario 1: Recurring Issues
```
IF detect multiple cases for similar issues:
  → Highlight the pattern
  → Suggest root cause investigation
  → Recommend preventive measures
  → Consider architectural review
```

### Scenario 2: Compliance & Security
```
IF question involves PCI DSS, GDPR, or data compliance:
  → Prioritize accuracy and official guidance
  → Reference AWS compliance documentation
  → Suggest case creation for compliance reviews
  → Emphasize security best practices
```

### Scenario 3: Multi-Region Operations
```
IF question involves cross-region scenarios:
  → Use `get_regional_availability` to verify service availability
  → Consider data sovereignty and compliance
  → Provide region-specific guidance
```

### Scenario 4: Urgent Production Issues
```
IF user reports production-down situation:
  → Immediately offer to create urgent/critical case
  → Skip knowledge base search for time-critical issues
  → Gather essential information efficiently
  → Create case with appropriate severity
```

---

## Output Quality Checklist

Before sending each response, verify:
- [ ] Used all available retrieval tools in correct order
- [ ] Cited specific sources for all factual claims
- [ ] Clearly indicated confidence level
- [ ] Offered case creation when appropriate
- [ ] Used Chinese unless English requested
- [ ] Provided actionable next steps
- [ ] Connected technical details to business impact (for e-commerce context)
- [ ] Included relevant timestamps in Beijing Time

---

## Remember

Your dual mission:
1. **Be a reliable knowledge source**: Accuracy over completeness, evidence over speculation
2. **Be a proactive case advocate**: Don't let users struggle - guide them to official support when needed

**Priority Hierarchy:**
Knowledge Base → AWS Official Docs → LLM Knowledge (with caution) → Proactive Case Suggestion

**Ultimate Goal:**
Help cross-border e-commerce IT teams maintain robust, secure, and high-performing AWS infrastructure while providing a seamless support experience that combines self-service knowledge with expert human support when needed.
"""
    return system_prompt

def create_streamable_http_transport_sigv4(
    mcp_url: str,
    service_name: str = "bedrock-agentcore",
    region: Optional[str] = None
):
    """
    Create a streamable HTTP transport with AWS SigV4 authentication.

    This function creates an MCP client transport that uses AWS Signature Version 4 (SigV4)
    to authenticate requests. Essential for connecting to IAM-authenticated gateways.

    Args:
        mcp_url (str): The URL of the MCP gateway endpoint
        service_name (str): The AWS service name for SigV4 signing (default: bedrock-agentcore)
        region (str, optional): The AWS region where the gateway is deployed (auto-detected if None)

    Returns:
        StreamableHTTPTransportWithSigV4: A transport instance configured for SigV4 auth

    Raises:
        ValueError: If credentials cannot be obtained
    """
    if region is None:
        region = REGION

    try:
        # Get AWS credentials from the current boto3 session
        # These credentials will be used to sign requests with SigV4
        session = boto3.Session()
        credentials = session.get_credentials()

        if credentials is None:
            raise ValueError("Unable to obtain AWS credentials. Ensure IAM role is properly configured.")

        logger.info(f"Creating SigV4 transport for {service_name} in {region}")

        return streamablehttp_client_with_sigv4(
            url=mcp_url,
            credentials=credentials,  # Uses credentials from the Lambda execution role
            service=service_name,
            region=region,
        )
    except Exception as e:
        logger.error(f"Failed to create SigV4 transport: {e}")
        raise


@retry_with_backoff(max_attempts=MAX_RETRIES)
def get_full_tools_list(client, timeout: int = MCP_TIMEOUT) -> list:
    """
    Retrieve the complete list of tools from an MCP client, handling pagination.

    MCP servers may return tools in paginated responses. This function handles the
    pagination automatically and returns all available tools in a single list.

    Args:
        client: An MCP client instance
        timeout: Maximum time to wait for tool retrieval (seconds)

    Returns:
        list: A complete list of all tools available from the MCP server

    Raises:
        TimeoutError: If tool retrieval exceeds timeout
        Exception: If tool retrieval fails after retries
    """
    start_time = time.time()
    tools = []
    pagination_token = None
    page_count = 0

    logger.info("Starting to retrieve tools from MCP server")

    try:
        while True:
            # Check timeout
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Tool retrieval exceeded {timeout}s timeout")

            page_count += 1
            logger.debug(f"Fetching tools page {page_count}")

            # Fetch tools for current page
            response = client.list_tools_sync(pagination_token=pagination_token)

            if hasattr(response, 'tools'):
                tools.extend(response.tools)
            else:
                tools.extend(response)

            # Check for more pages
            if hasattr(response, 'pagination_token') and response.pagination_token:
                pagination_token = response.pagination_token
                logger.debug(f"Found pagination token, fetching next page")
            else:
                break

        logger.info(f"Successfully retrieved {len(tools)} tools in {page_count} pages")
        return tools

    except Exception as e:
        logger.error(f"Failed to retrieve tools after {page_count} pages: {e}")
        raise


def get_mcp_client():
    """
    Get or create MCP client with lazy initialization and health check.

    Returns:
        MCPClient: Initialized and connected MCP client
    """
    global _mcp_client

    if _mcp_client is None:
        logger.info("Initializing MCP client with lazy loading")

        try:
            # Get gateway URL (with retry logic)
            gateway_url = get_gateway_url()

            # Create the MCP client with SigV4 authentication
            _mcp_client = MCPClient(
                lambda: create_streamable_http_transport_sigv4(
                    mcp_url=gateway_url,
                    service_name="bedrock-agentcore",
                    region=REGION,
                )
            )

            # Start the MCP client connection
            logger.info("Starting MCP client connection")
            _mcp_client.start()

            # Validate connection by retrieving tools
            logger.info("Validating MCP connection by retrieving tools")
            _ = get_full_tools_list(_mcp_client)

            logger.info("MCP client initialized and validated successfully")

        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
            _mcp_client = None  # Reset for retry on next call
            raise

    return _mcp_client


def get_agent():
    """
    Get or create Strands agent with lazy initialization.

    This function implements lazy loading to reduce cold start time.
    The agent is only initialized when first needed.

    Returns:
        Agent: Configured Strands agent with model, prompt, and tools
    """
    global _agent

    if _agent is None:
        logger.info("Initializing Strands agent")

        try:
            # Initialize dependencies
            model = get_bedrock_model()
            _ = get_knowledge_base_id()  # Initialize KB ID for retrieve tool
            mcp_client = get_mcp_client()
            tool_list = get_full_tools_list(mcp_client)

            # Create the Strands agent with the model, system prompt, and tools
            _agent = Agent(
                model=model,
                system_prompt=get_system_prompt(),
                tools=[retrieve, tool_list],
            )

            logger.info(f"Agent initialized with {len(tool_list)} MCP tools + retrieve tool")

        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            _agent = None  # Reset for retry on next call
            raise

    return _agent


@app.entrypoint
async def strands_agent_bedrock(payload: Dict[str, Any]):
    """
    Main entrypoint for the AgentCore Runtime deployed agent - 零配置 RBAC 版本

    This function is invoked when the agent receives a request through AgentCore Runtime.
    It extracts the user's prompt and user context from the payload.

    Args:
        payload (dict): The incoming request payload
                       Expected format: {
                           "prompt": "user's question",
                           "_user_context": {
                               "iam_user": "alice"  # Optional
                           }
                       }

    Yields:
        str or dict: Streaming response chunks or error information

    Example payload:
        {"prompt": "创建一个工单", "_user_context": {"iam_user": "alice"}}
    """
    request_id = payload.get("request_id", "unknown")
    start_time = time.time()

    try:
        # Extract user input with validation
        user_input = payload.get("prompt")

        if not user_input:
            logger.warning(f"Request {request_id}: Empty prompt, using default")
            user_input = "show me the case in the past four weeks?"

        # Extract user context (for RBAC)
        user_context = payload.get("_user_context", {})
        iam_user = user_context.get("iam_user")

        if iam_user:
            logger.info(f"Request {request_id}: User {iam_user} - Processing prompt (length: {len(user_input)})")
        else:
            logger.info(f"Request {request_id}: Anonymous - Processing prompt (length: {len(user_input)})")

        logger.debug(f"Request {request_id}: Prompt content: {user_input[:100]}...")

        # Lazy initialization of agent on first request
        agent = get_agent()

        # For RBAC: Inject user context into the prompt
        # This way, when Agent calls Case write tools, it will include the user identity
        if iam_user:
            # Prepend user context instruction to the user input
            user_input_with_context = f"[System: Current IAM user is '{iam_user}'. When calling case write operations (create_support_case, add_communication_to_case, resolve_support_case, add_attachments_to_set), you MUST include '_iam_user: {iam_user}' as a parameter.]\n\nUser request: {user_input}"
        else:
            user_input_with_context = user_input

        # Track token count for cost monitoring (if available)
        chunk_count = 0
        total_chars = 0

        # Stream agent response
        async for event in agent.stream_async(user_input_with_context):
            if "data" in event:
                chunk_count += 1
                data = event["data"]
                total_chars += len(str(data))
                yield data

        # Log completion metrics
        elapsed_time = time.time() - start_time
        logger.info(
            f"Request {request_id}: Completed successfully - "
            f"{chunk_count} chunks, {total_chars} chars, {elapsed_time:.2f}s"
        )

    except TimeoutError as e:
        # Handle timeout errors specifically
        elapsed_time = time.time() - start_time
        error_msg = f"Request timeout after {elapsed_time:.2f}s: {str(e)}"
        logger.error(f"Request {request_id}: {error_msg}")

        error_response = {
            "error": error_msg,
            "type": "timeout_error",
            "request_id": request_id,
            "elapsed_time": elapsed_time
        }
        yield error_response

    except ClientError as e:
        # Handle AWS service errors
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))

        logger.error(
            f"Request {request_id}: AWS ClientError - "
            f"Code: {error_code}, Message: {error_msg}"
        )

        error_response = {
            "error": f"AWS service error: {error_msg}",
            "type": "aws_client_error",
            "error_code": error_code,
            "request_id": request_id
        }
        yield error_response

    except Exception as e:
        # Handle all other errors
        elapsed_time = time.time() - start_time
        error_msg = str(e)

        logger.error(
            f"Request {request_id}: Unexpected error after {elapsed_time:.2f}s - "
            f"{type(e).__name__}: {error_msg}",
            exc_info=True  # Include stack trace in logs
        )

        error_response = {
            "error": error_msg,
            "type": "entrypoint_error",
            "error_class": type(e).__name__,
            "request_id": request_id,
            "elapsed_time": elapsed_time
        }
        yield error_response


# ============================================================================
# Module-level Initialization for AgentCore Runtime
# ============================================================================

# For AgentCore Runtime/Lambda environments, we want the container to be "warm"
# and ready to handle requests immediately. This means initializing during
# module load rather than on first request.

if INIT_MODE == "eager":
    logger.info("=" * 60)
    logger.info("🚀 EAGER INITIALIZATION MODE (AgentCore Runtime)")
    logger.info("=" * 60)

    try:
        # Initialize all resources at module load time
        # This happens once when the Lambda container starts
        logger.info("Initializing all resources during module load...")

        start_time = time.time()

        # Pre-initialize agent (this will initialize all dependencies)
        _ = get_agent()

        elapsed = time.time() - start_time
        logger.info(f"✅ Eager initialization completed in {elapsed:.2f}s")
        logger.info(f"Container is now WARM and ready to serve requests")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ EAGER INITIALIZATION FAILED: {e}")
        logger.error("=" * 60)
        logger.error("Falling back to lazy initialization on first request", exc_info=True)
        # Don't raise - let lazy initialization handle it on first request

else:
    logger.info("=" * 60)
    logger.info("⏱️  LAZY INITIALIZATION MODE (Development/Testing)")
    logger.info("=" * 60)
    logger.info("Resources will be initialized on first request")
    logger.info("Set INIT_MODE=eager for production deployment")
    logger.info("=" * 60)


# Standard Python idiom: only run the app when this file is executed directly
if __name__ == "__main__":
    app.run()
