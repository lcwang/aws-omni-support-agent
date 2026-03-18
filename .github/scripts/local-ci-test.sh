#!/bin/bash
#
# 本地 CI 测试脚本
# 在提交前本地运行 CI 检查，避免在 GitHub Actions 中失败
#
# 使用方法: ./local-ci-test.sh [--fix]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FIX_MODE=false
if [ "$1" == "--fix" ]; then
    FIX_MODE=true
fi

echo "======================================================"
echo "🧪 Running Local CI Tests"
echo "======================================================"
echo ""

# ============================================================================
# 1. Python 环境检查
# ============================================================================
echo "📦 Checking Python environment..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python $(python3 --version)${NC}"
echo ""

# ============================================================================
# 2. 安装测试依赖
# ============================================================================
echo "📥 Installing test dependencies..."
pip install -q ruff black mypy pytest safety > /dev/null 2>&1
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# ============================================================================
# 3. 代码格式检查
# ============================================================================
echo "🎨 Running code formatting checks..."

if [ "$FIX_MODE" = true ]; then
    echo "  Running Black formatter (auto-fix)..."
    black 02_AWS_Support_Case_Lambda/ 04_create_knowledge_mcp_gateway_Agent/ 2>&1 | grep -v "reformatted" || true
    echo -e "${GREEN}✅ Code formatted${NC}"
else
    if black --check 02_AWS_Support_Case_Lambda/ 04_create_knowledge_mcp_gateway_Agent/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Code formatting OK${NC}"
    else
        echo -e "${YELLOW}⚠️  Code formatting issues detected${NC}"
        echo "   Run './local-ci-test.sh --fix' to auto-format"
    fi
fi
echo ""

# ============================================================================
# 4. Linting
# ============================================================================
echo "🔍 Running linter (Ruff)..."

if ruff check 02_AWS_Support_Case_Lambda/ 04_create_knowledge_mcp_gateway_Agent/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ No linting issues${NC}"
else
    echo -e "${YELLOW}⚠️  Linting issues detected:${NC}"
    ruff check 02_AWS_Support_Case_Lambda/ 04_create_knowledge_mcp_gateway_Agent/ || true
fi
echo ""

# ============================================================================
# 5. 类型检查
# ============================================================================
echo "🔬 Running type checks (mypy)..."

if mypy 02_AWS_Support_Case_Lambda/lambda_handler.py --ignore-missing-imports > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Type checking passed${NC}"
else
    echo -e "${YELLOW}⚠️  Type checking issues (non-blocking):${NC}"
    mypy 02_AWS_Support_Case_Lambda/lambda_handler.py --ignore-missing-imports | head -10 || true
fi
echo ""

# ============================================================================
# 6. Lambda 模块验证
# ============================================================================
echo "🔧 Validating Lambda module..."

cd 02_AWS_Support_Case_Lambda
if python3 -c "import lambda_handler; assert len(lambda_handler.TOOL_HANDLERS) == 7" 2>/dev/null; then
    echo -e "${GREEN}✅ Lambda handler valid (7 tools found)${NC}"
else
    echo -e "${RED}❌ Lambda handler validation failed${NC}"
    exit 1
fi
cd "$PROJECT_ROOT"
echo ""

# ============================================================================
# 7. Agent 模块验证
# ============================================================================
echo "🤖 Validating Agent module..."

cd 04_create_knowledge_mcp_gateway_Agent
export INIT_MODE=lazy
export AWS_REGION=us-east-1

if python3 -c "import aws_support_agent; print('Model:', aws_support_agent.MODEL_ID)" 2>/dev/null; then
    echo -e "${GREEN}✅ Agent module valid${NC}"
else
    echo -e "${RED}❌ Agent module validation failed${NC}"
    echo "   Ensure requirements.txt dependencies are installed"
    exit 1
fi
cd "$PROJECT_ROOT"
echo ""

# ============================================================================
# 8. JSON 配置验证
# ============================================================================
echo "📄 Validating JSON configuration files..."

JSON_VALID=true
for file in $(find . -name "*.json" -not -path "./.git/*" -not -path "./.ipynb_checkpoints/*"); do
    if ! python3 -m json.tool "$file" > /dev/null 2>&1; then
        echo -e "${RED}❌ Invalid JSON: $file${NC}"
        JSON_VALID=false
    fi
done

if [ "$JSON_VALID" = true ]; then
    echo -e "${GREEN}✅ All JSON files valid${NC}"
fi
echo ""

# ============================================================================
# 9. 敏感信息检查
# ============================================================================
echo "🔐 Checking for sensitive information..."

SECRETS_FOUND=false

# 检查 AWS Access Key
if grep -r "AKIA[0-9A-Z]{16}" . --exclude-dir=.git --exclude-dir=.venv 2>/dev/null; then
    echo -e "${RED}❌ Potential AWS Access Key found!${NC}"
    SECRETS_FOUND=true
fi

# 检查账户 ID (排除文档和 gitignore)
if grep -r "887221633712" . --exclude-dir=.git --exclude-dir=.venv --exclude="*.md" --exclude=".gitignore" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Account ID found in code${NC}"
fi

# 检查私钥
if find . -name "*.pem" -o -name "*.key" 2>/dev/null | grep -v ".git"; then
    echo -e "${RED}❌ Private key files found!${NC}"
    SECRETS_FOUND=true
fi

if [ "$SECRETS_FOUND" = false ]; then
    echo -e "${GREEN}✅ No obvious secrets detected${NC}"
fi
echo ""

# ============================================================================
# 10. 依赖安全扫描
# ============================================================================
echo "🛡️  Running security scan (quick)..."

if command -v safety &> /dev/null; then
    for dir in 02_AWS_Support_Case_Lambda 04_create_knowledge_mcp_gateway_Agent; do
        if [ -f "$dir/requirements.txt" ]; then
            echo "  Scanning $dir..."
            if safety check -r "$dir/requirements.txt" --json > /dev/null 2>&1; then
                echo -e "  ${GREEN}✅ No vulnerabilities in $dir${NC}"
            else
                echo -e "  ${YELLOW}⚠️  Vulnerabilities detected in $dir${NC}"
                echo "     Run 'safety check -r $dir/requirements.txt' for details"
            fi
        fi
    done
else
    echo -e "${YELLOW}⚠️  'safety' not installed, skipping security scan${NC}"
    echo "   Install with: pip install safety"
fi
echo ""

# ============================================================================
# 总结
# ============================================================================
echo "======================================================"
echo "📊 CI Test Summary"
echo "======================================================"
echo ""
echo -e "${GREEN}✅ Local CI tests completed${NC}"
echo ""
echo "Next steps:"
echo "  1. Review any warnings above"
echo "  2. Fix issues if needed (run with --fix to auto-format)"
echo "  3. Commit your changes"
echo "  4. Push to trigger GitHub Actions CI"
echo ""
echo "To run only specific checks:"
echo "  Format:   black --check <path>"
echo "  Lint:     ruff check <path>"
echo "  Security: safety check -r <path>/requirements.txt"
echo ""
