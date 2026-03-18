# 🔄 强制推送指南 - 完全覆盖 GitHub 内容

> 因为项目变化较大，需要用新内容完全替换 GitHub 上的旧版本

---

## ⚠️ 重要警告

**强制推送会完全覆盖远程仓库的历史！**

- ✅ 适用：项目重构，旧内容完全作废
- ❌ 不适用：团队协作，其他人可能基于旧版本开发

**确认以下事项后再继续**:
- [ ] 旧 GitHub 内容可以完全丢弃
- [ ] 没有其他人基于旧版本开发
- [ ] 已备份重要内容（如果需要）
- [ ] 理解强制推送的风险

---

## 🚀 强制推送步骤

### 方案 1: 强制推送（推荐）⭐

完全覆盖远程历史，保留新的 Git 历史。

```bash
cd /Users/havpan/CC_Demo/aws-omni-support-agent

# 1. 运行清理脚本
chmod +x scripts/cleanup_before_push.sh
./scripts/cleanup_before_push.sh

# 2. 检查当前状态
git status

# 3. 添加所有文件
git add .

# 4. 提交新版本
git commit -m "refactor: complete project restructure

Major changes:
- Migrate from MCP Server to Lambda architecture (40-60% cost reduction)
- Add comprehensive documentation (10+ files, 5000+ lines)
- Implement mixed CI/CD architecture (GitHub Actions + SageMaker)
- Add 320-line optimized System Prompt for e-commerce scenarios
- Complete security hardening and cleanup

BREAKING CHANGE: This version is incompatible with previous versions.
All infrastructure needs to be redeployed following the new guides.
"

# 5. 检查远程仓库
git remote -v
# 应该看到: origin  https://github.com/percy-han/aws-omni-support-agent.git

# 6. 强制推送到 main 分支
git push origin main --force

# 或者使用更安全的 --force-with-lease（推荐）
# 只有在远程没有新提交时才强制推送
git push origin main --force-with-lease
```

### 方案 2: 删除并重新初始化

完全清除 Git 历史，从零开始。

```bash
cd /Users/havpan/CC_Demo/aws-omni-support-agent

# 1. 运行清理脚本
./scripts/cleanup_before_push.sh

# 2. 删除本地 Git 历史
rm -rf .git

# 3. 重新初始化
git init
git add .
git commit -m "Initial commit: Complete project restructure

This is a complete rewrite of the AWS Omni Support Agent project.

Major features:
- Lambda + AgentCore Gateway architecture
- RAG knowledge base with OpenSearch
- 7 AWS Support API tools
- Mixed CI/CD (GitHub Actions + SageMaker Notebook)
- Comprehensive documentation
- Enterprise-grade security

Previous version history has been archived.
"

# 4. 添加远程仓库
git remote add origin https://github.com/percy-han/aws-omni-support-agent.git

# 5. 强制推送
git branch -M main
git push -u origin main --force
```

### 方案 3: 在 GitHub 上先删除仓库（最彻底）

如果你想要完全清空远程仓库：

**在 GitHub 网站上**:
1. 进入仓库 Settings
2. 滚动到最底部 "Danger Zone"
3. 点击 "Delete this repository"
4. 输入仓库名确认
5. 删除完成

**然后重新创建**:
1. 在 GitHub 创建同名新仓库（空仓库）
2. 本地推送:
```bash
cd /Users/havpan/CC_Demo/aws-omni-support-agent
git remote set-url origin https://github.com/percy-han/aws-omni-support-agent.git
git push -u origin main
```

---

## 📋 推荐流程（结合清理）

### Step 1: 清理项目 🧹

```bash
cd /Users/havpan/CC_Demo/aws-omni-support-agent

# 运行清理脚本
chmod +x scripts/cleanup_before_push.sh
./scripts/cleanup_before_push.sh

# 检查清理结果
git status
```

### Step 2: 个性化信息 ✏️

```bash
# 替换 README.md 中的用户名（如果需要）
# vim README.md
# 将 percy-han 替换为你的 GitHub 用户名
# 将 your-email@example.com 替换为你的邮箱
```

### Step 3: 最终检查 🔍

```bash
# 敏感信息检查
grep -r "AKIA[0-9A-Z]{16}" . --exclude-dir=.git --exclude="*.md" 2>/dev/null
# 应该无输出

# 确认 .bedrock_agentcore.yaml 被忽略
git check-ignore 04_create_knowledge_mcp_gateway_Agent/.bedrock_agentcore.yaml
# 应该输出文件路径

# 查看即将推送的文件
git ls-files | head -50
```

### Step 4: 提交新版本 📝

```bash
# 添加所有文件
git add .

# 查看变更
git status

# 提交
git commit -m "refactor: complete project restructure

Major changes:
- Lambda architecture (replaced MCP Server)
- Comprehensive documentation (10+ guides)
- Mixed CI/CD architecture
- Enterprise-grade security
- Complete cleanup and optimization

BREAKING CHANGE: Incompatible with previous versions.
"
```

### Step 5: 强制推送 🚀

```bash
# 推荐：使用 --force-with-lease（更安全）
git push origin main --force-with-lease

# 如果上面失败，使用 --force
git push origin main --force
```

### Step 6: 验证推送 ✅

```bash
# 在浏览器中打开
open https://github.com/percy-han/aws-omni-support-agent

# 检查:
# ✅ README 正确显示
# ✅ 没有敏感信息
# ✅ 文件结构正确
# ✅ GitHub Actions 触发（如果配置了）
```

---

## 🔧 故障排除

### 问题 1: 推送被拒绝

**错误信息**:
```
! [rejected]        main -> main (fetch first)
error: failed to push some refs
```

**原因**: 远程有新提交，Git 拒绝强制推送

**解决**:
```bash
# 选项 1: 使用更强的 --force
git push origin main --force

# 选项 2: 先 pull 再推（不推荐，会混合历史）
git pull origin main --allow-unrelated-histories
git push origin main
```

---

### 问题 2: 权限错误

**错误信息**:
```
remote: Permission to percy-han/aws-omni-support-agent.git denied
```

**原因**: 没有推送权限或认证失败

**解决**:
```bash
# 检查远程 URL
git remote -v

# 如果是 HTTPS，确保输入了正确的 GitHub 用户名和密码/Token
# 如果是 SSH，确保 SSH key 已添加到 GitHub

# 使用 HTTPS (推荐)
git remote set-url origin https://github.com/percy-han/aws-omni-support-agent.git

# 或使用 SSH
git remote set-url origin git@github.com:percy-han/aws-omni-support-agent.git
```

---

### 问题 3: 推送超时

**错误信息**:
```
fatal: the remote end hung up unexpectedly
```

**原因**: 文件太大或网络问题

**解决**:
```bash
# 检查大文件
find . -type f -size +10M -not -path "./.git/*"

# 增加 buffer
git config http.postBuffer 524288000

# 重试推送
git push origin main --force
```

---

### 问题 4: Notebook 文件太大

**错误信息**:
```
remote: error: File XXX.ipynb is 150.00 MB; this exceeds GitHub's file size limit of 100.00 MB
```

**解决**:
```bash
# 清理 Notebook 输出
jupyter nbconvert --clear-output --inplace *.ipynb

# 或手动在 Jupyter 中清理

# 重新提交
git add .
git commit --amend
git push origin main --force
```

---

## 📊 推送前后对比

### 推送前
```
旧 GitHub 仓库
├── 旧的 MCP Server 架构
├── 不完整的文档
├── 可能包含敏感信息
└── 混乱的提交历史
```

### 推送后
```
新 GitHub 仓库
├── Lambda 架构（优化后）
├── 完整文档（10+ 文件）
├── 安全的代码（无敏感信息）
├── 清晰的提交历史
└── 自动化 CI/CD
```

---

## ⚡ 快速命令（复制粘贴）

### 完整流程 - 一键执行

```bash
# 进入项目目录
cd /Users/havpan/CC_Demo/aws-omni-support-agent

# 清理
./scripts/cleanup_before_push.sh

# 提交
git add .
git commit -m "refactor: complete project restructure"

# 强制推送
git push origin main --force-with-lease

# 如果失败，使用更强的 force
# git push origin main --force

# 验证
open https://github.com/percy-han/aws-omni-support-agent
```

---

## ✅ 推送后检查清单

### 在 GitHub 网站上检查

- [ ] README.md 正确显示
- [ ] 没有敏感信息泄露
- [ ] 文件结构正确
- [ ] LICENSE 存在
- [ ] .gitignore 生效（.bedrock_agentcore.yaml 未推送）
- [ ] Actions 标签可见（workflows 已推送）

### 配置 GitHub（推送后立即）

- [ ] Settings → Secrets → 添加 AWS 凭证
- [ ] Settings → Environments → 创建 dev/prod
- [ ] Settings → Actions → 启用 workflows
- [ ] About → 添加描述和标签

---

## 🎉 完成！

强制推送后，GitHub 上的内容将**完全被新版本替换**。

**注意事项**:
1. ⚠️ 旧的提交历史将消失
2. ⚠️ 旧的 Issues/PRs 保留（但引用可能失效）
3. ✅ 旧的 Releases/Tags 保留
4. ✅ Stars/Forks 数量保留

**下一步**:
1. 配置 GitHub Secrets 和 Environments
2. 测试 GitHub Actions workflows
3. 邀请协作者（如果有）
4. 享受新架构带来的便利！

---

**准备好了吗？运行上面的命令开始吧！** 🚀
