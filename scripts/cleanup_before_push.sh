#!/bin/bash
#
# 清理脚本 - 在推送到 GitHub 前执行
# 清理 Notebook 输出、临时文件、缓存等
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================================"
echo "🧹 Cleaning up project before GitHub push"
echo "======================================================"
echo ""

# ============================================================================
# 1. 清理 Jupyter Notebook 输出
# ============================================================================
echo "📓 Cleaning Jupyter Notebook outputs..."

if command -v jupyter &> /dev/null; then
    find . -name "*.ipynb" -not -path "./.git/*" -not -path "./.ipynb_checkpoints/*" | while read notebook; do
        echo "  Cleaning: $notebook"
        jupyter nbconvert --clear-output --inplace "$notebook"
    done
    echo "✅ Notebook outputs cleared"
else
    echo "⚠️  jupyter-nbconvert not installed, skipping notebook cleanup"
    echo "   Install with: pip install nbconvert"
fi
echo ""

# ============================================================================
# 2. 删除 .ipynb_checkpoints 目录
# ============================================================================
echo "🗑️  Removing .ipynb_checkpoints directories..."

find . -type d -name ".ipynb_checkpoints" -not -path "./.git/*" | while read dir; do
    echo "  Removing: $dir"
    rm -rf "$dir"
done
echo "✅ Checkpoint directories removed"
echo ""

# ============================================================================
# 3. 删除 Python 缓存
# ============================================================================
echo "🗑️  Removing Python cache files..."

# __pycache__ 目录
find . -type d -name "__pycache__" -not -path "./.git/*" | while read dir; do
    echo "  Removing: $dir"
    rm -rf "$dir"
done

# .pyc 文件
find . -name "*.pyc" -not -path "./.git/*" -delete
find . -name "*.pyo" -not -path "./.git/*" -delete
find . -name "*.pyd" -not -path "./.git/*" -delete

echo "✅ Python cache removed"
echo ""

# ============================================================================
# 4. 删除临时文件
# ============================================================================
echo "🗑️  Removing temporary files..."

# .DS_Store (macOS)
find . -name ".DS_Store" -not -path "./.git/*" -delete

# Vim swap files
find . -name "*.swp" -not -path "./.git/*" -delete
find . -name "*.swo" -not -path "./.git/*" -delete
find . -name "*~" -not -path "./.git/*" -delete

# pytest cache
find . -type d -name ".pytest_cache" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true

# mypy cache
find . -type d -name ".mypy_cache" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true

# Coverage files
find . -name ".coverage" -not -path "./.git/*" -delete 2>/dev/null || true
find . -type d -name "htmlcov" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true

echo "✅ Temporary files removed"
echo ""

# ============================================================================
# 5. 删除 PKL 和二进制文件
# ============================================================================
echo "🗑️  Removing pickle and binary files..."

find . -name "*.pkl" -not -path "./.git/*" | while read file; do
    echo "  Removing: $file"
    rm -f "$file"
done

find . -name "launch_result.pkl" -not -path "./.git/*" -delete 2>/dev/null || true

echo "✅ Binary files removed"
echo ""

# ============================================================================
# 6. 清理空目录
# ============================================================================
echo "🗑️  Removing empty directories..."

find . -type d -empty -not -path "./.git/*" | while read dir; do
    if [ "$dir" != "." ] && [ "$dir" != "./.git" ]; then
        echo "  Removing empty dir: $dir"
        rmdir "$dir" 2>/dev/null || true
    fi
done

echo "✅ Empty directories removed"
echo ""

# ============================================================================
# 7. 检查敏感信息
# ============================================================================
echo "🔒 Checking for sensitive information..."

FOUND_ISSUES=false

# 检查 AWS Access Key
if grep -r "AKIA[0-9A-Z]{16}" . --exclude-dir=.git --exclude="*.md" --exclude="cleanup_before_push.sh" 2>/dev/null; then
    echo "❌ Found potential AWS Access Key!"
    FOUND_ISSUES=true
fi

# 检查账户 ID（排除文档）
if grep -r "887221633712" . --exclude-dir=.git --exclude="*.md" --exclude=".gitignore" 2>/dev/null; then
    echo "⚠️  Found account ID 887221633712 in code (check if it's in documentation only)"
fi

# 检查 .bedrock_agentcore.yaml
if [ -f "04_create_knowledge_mcp_gateway_Agent/.bedrock_agentcore.yaml" ]; then
    if ! grep -q ".bedrock_agentcore.yaml" .gitignore; then
        echo "❌ .bedrock_agentcore.yaml is not in .gitignore!"
        FOUND_ISSUES=true
    fi
fi

if [ "$FOUND_ISSUES" = false ]; then
    echo "✅ No obvious sensitive information found"
fi
echo ""

# ============================================================================
# 8. 验证必要文件存在
# ============================================================================
echo "📋 Verifying essential files..."

MISSING_FILES=false

# 检查必要的文档
for file in README.md LICENSE .gitignore; do
    if [ ! -f "$file" ]; then
        echo "⚠️  Missing: $file"
        if [ "$file" = "README.md" ]; then
            MISSING_FILES=true
        fi
    fi
done

# 检查必要的配置
for file in requirements.txt; do
    if [ ! -f "02_AWS_Support_Case_Lambda/$file" ]; then
        echo "❌ Missing: 02_AWS_Support_Case_Lambda/$file"
        MISSING_FILES=true
    fi
    if [ ! -f "04_create_knowledge_mcp_gateway_Agent/$file" ]; then
        echo "❌ Missing: 04_create_knowledge_mcp_gateway_Agent/$file"
        MISSING_FILES=true
    fi
done

if [ "$MISSING_FILES" = false ]; then
    echo "✅ All essential files present"
fi
echo ""

# ============================================================================
# 9. 统计信息
# ============================================================================
echo "======================================================"
echo "📊 Cleanup Summary"
echo "======================================================"

echo ""
echo "Project structure:"
echo "  Notebooks:       $(find . -name "*.ipynb" -not -path "./.git/*" -not -path "./.ipynb_checkpoints/*" | wc -l | xargs)"
echo "  Python files:    $(find . -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" | wc -l | xargs)"
echo "  Markdown files:  $(find . -name "*.md" -not -path "./.git/*" | wc -l | xargs)"
echo "  YAML files:      $(find . -name "*.yml" -o -name "*.yaml" -not -path "./.git/*" | wc -l | xargs)"
echo ""

echo "Git status:"
git status --short | head -20
echo ""

# ============================================================================
# 完成
# ============================================================================
echo "======================================================"
echo "✅ Cleanup completed!"
echo "======================================================"
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Review README.md"
echo "  3. Test deployment locally if needed"
echo "  4. Commit: git add . && git commit -m 'chore: clean up before initial push'"
echo "  5. Push: git push origin main"
echo ""
