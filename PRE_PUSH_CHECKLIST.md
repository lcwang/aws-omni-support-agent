# 📋 推送到 GitHub 前的检查清单

> 在执行 `git push` 前，请确保完成以下所有检查

---

## ✅ 必需检查项

### 1. 清理临时文件和输出 🧹

```bash
# 运行自动清理脚本
chmod +x scripts/cleanup_before_push.sh
./scripts/cleanup_before_push.sh
```

**检查内容**:
- [ ] Jupyter Notebook 输出已清除
- [ ] `.ipynb_checkpoints/` 目录已删除
- [ ] `__pycache__/` 目录已删除
- [ ] `.pyc` 文件已删除
- [ ] `.DS_Store` 文件已删除（macOS）
- [ ] `*.pkl` 文件已删除
- [ ] 空目录已删除

---

### 2. 敏感信息检查 🔒

**手动检查**:
- [ ] `.bedrock_agentcore.yaml` 在 `.gitignore` 中
- [ ] 没有 AWS Access Key (`AKIA...`)
- [ ] 没有硬编码的账户 ID（除了文档）
- [ ] 没有私钥文件 (`*.pem`, `*.key`)
- [ ] 没有密码或 Token

**运行检查**:
```bash
# 检查 AWS Access Key
grep -r "AKIA[0-9A-Z]{16}" . --exclude-dir=.git --exclude="*.md"

# 检查账户 ID
grep -r "887221633712" . --exclude-dir=.git --exclude="*.md" --exclude=".gitignore"

# 检查私钥
find . -name "*.pem" -o -name "*.key" | grep -v ".git"
```

---

### 3. 文档完整性检查 📚

必需文档:
- [ ] `README.md` - 项目主文档
- [ ] `LICENSE` - 许可证
- [ ] `.gitignore` - Git 忽略规则
- [ ] `DEPLOYMENT_GUIDE.md` - 部署指南
- [ ] `SAGEMAKER_NOTEBOOK_CHECKLIST.md` - Notebook 清单

模块文档:
- [ ] `02_AWS_Support_Case_Lambda/README.md` - Lambda 说明
- [ ] `.github/CICD_SETUP.md` - CI/CD 配置
- [ ] `.github/QUICK_REFERENCE.md` - 快速参考

---

### 4. 代码质量检查 🔍

```bash
# 运行本地 CI 测试
./.github/scripts/local-ci-test.sh

# 或手动检查
cd /Users/havpan/CC_Demo/aws-omni-support-agent

# Python 代码格式
pip install black ruff mypy
black --check 02_AWS_Support_Case_Lambda/ 04_create_knowledge_mcp_gateway_Agent/
ruff check 02_AWS_Support_Case_Lambda/ 04_create_knowledge_mcp_gateway_Agent/

# 验证 Lambda 导入
cd 02_AWS_Support_Case_Lambda
python -c "import lambda_handler; print('✅ OK')"

# 验证 Agent 导入
cd ../04_create_knowledge_mcp_gateway_Agent
export INIT_MODE=lazy
python -c "import aws_support_agent; print('✅ OK')"
```

**检查结果**:
- [ ] 代码格式正确（Black）
- [ ] 无 Linting 错误（Ruff）
- [ ] Lambda 模块可导入
- [ ] Agent 模块可导入

---

### 5. 依赖文件检查 📦

确保所有 requirements.txt 存在且完整:
- [ ] `01_create_support_knowledegbase_rag/requirements.txt`
- [ ] `02_AWS_Support_Case_Lambda/requirements.txt`
- [ ] `04_create_knowledge_mcp_gateway_Agent/requirements.txt`

**验证**:
```bash
# 检查是否有版本锁定
cat 01_create_support_knowledegbase_rag/requirements.txt | head
# 应该看到: package==version

cat 04_create_knowledge_mcp_gateway_Agent/requirements.txt | head
# 应该看到: package==version
```

---

### 6. Git 状态检查 🔄

```bash
# 查看未跟踪的文件
git status

# 查看变更内容
git diff

# 查看即将提交的文件
git add -n .
```

**确认**:
- [ ] 所有必要文件已添加
- [ ] 没有意外包含的大文件
- [ ] 没有敏感信息
- [ ] Commit message 清晰

---

## ⚠️ 可选检查项

### 7. README 个性化 📝

替换 README.md 中的占位符:
- [ ] GitHub 用户名: `percy-han` → 你的用户名
- [ ] 仓库地址: `https://github.com/percy-han/aws-omni-support-agent.git`
- [ ] Email: `your-email@example.com` → 你的邮箱
- [ ] Badge 地址（如果仓库地址变更）

---

### 8. GitHub 仓库设置 🏗️

在推送后需要在 GitHub 上配置:
- [ ] 仓库描述和标签
- [ ] GitHub Actions 权限
- [ ] GitHub Secrets（AWS 凭证）
- [ ] GitHub Environments（dev/staging/prod）
- [ ] Branch protection rules（可选）

---

### 9. 文档链接检查 🔗

验证所有内部链接是否有效:
```bash
# 检查 README 中的链接
grep -o '\[.*\](.*\.md)' README.md

# 确认文件存在
ls -la DEPLOYMENT_GUIDE.md
ls -la SAGEMAKER_NOTEBOOK_CHECKLIST.md
ls -la .github/CICD_SETUP.md
```

---

### 10. 许可证检查 📜

- [ ] LICENSE 文件存在
- [ ] LICENSE 类型正确（MIT）
- [ ] 版权年份正确（2025）
- [ ] 版权所有者正确

---

## 🚀 最终推送步骤

### Step 1: 运行清理脚本

```bash
./scripts/cleanup_before_push.sh
```

### Step 2: 审查变更

```bash
git status
git diff --staged
```

### Step 3: 提交

```bash
git add .
git commit -m "chore: clean up and prepare for initial push"
```

### Step 4: 推送

```bash
# 如果是首次推送
git remote add origin https://github.com/percy-han/aws-omni-support-agent.git
git branch -M main
git push -u origin main

# 如果已有 remote
git push origin main
```

### Step 5: 验证

```bash
# 在 GitHub 上检查
# 1. 文件是否都推送成功
# 2. README 是否正确渲染
# 3. 没有敏感信息
# 4. Actions 是否自动运行
```

---

## 📊 清单总结

### 核心检查（必须）
- [x] 运行清理脚本
- [x] 敏感信息检查
- [x] 文档完整性
- [x] 代码质量
- [x] Git 状态

### 可选优化
- [ ] README 个性化
- [ ] 文档链接验证
- [ ] GitHub 配置准备

---

## 🔄 如果发现问题

### 问题：清理脚本失败

```bash
# 检查权限
chmod +x scripts/cleanup_before_push.sh

# 手动清理
find . -name ".ipynb_checkpoints" -type d -exec rm -rf {} +
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### 问题：发现敏感信息

```bash
# 从 Git 历史中移除
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/sensitive/file" \
  --prune-empty --tag-name-filter cat -- --all

# 或使用 BFG Repo-Cleaner
bfg --delete-files sensitive_file.txt
```

### 问题：代码检查失败

```bash
# 自动修复格式
black 02_AWS_Support_Case_Lambda/ 04_create_knowledge_mcp_gateway_Agent/

# 查看具体错误
ruff check 02_AWS_Support_Case_Lambda/ --show-source
```

---

## ✅ 完成标志

当你看到以下所有输出都是 ✅，就可以放心推送了：

```
✅ Notebook outputs cleared
✅ Checkpoint directories removed
✅ Python cache removed
✅ Temporary files removed
✅ Binary files removed
✅ No obvious sensitive information found
✅ All essential files present
✅ Cleanup completed!
```

---

## 📞 需要帮助？

- 查看清理脚本输出的错误信息
- 参考 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- 创建 Issue 寻求帮助

---

**祝推送顺利！** 🎉
