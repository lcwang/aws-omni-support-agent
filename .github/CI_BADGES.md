# CI/CD Status Badges

将以下徽章添加到项目 README.md 中，展示 CI/CD 状态：

```markdown
# AWS Omni Support Agent

[![CI](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/ci.yml)
[![Deploy Lambda](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/deploy-lambda.yml/badge.svg)](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/deploy-lambda.yml)
[![Deploy Agent](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/deploy-agent.yml/badge.svg)](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/deploy-agent.yml)
[![Security](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/dependency-update.yml/badge.svg)](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/dependency-update.yml)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
```

## 预览效果

![CI](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/ci.yml/badge.svg)
![Deploy Lambda](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/deploy-lambda.yml/badge.svg)
![Deploy Agent](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/deploy-agent.yml/badge.svg)
![Security](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/dependency-update.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## 自定义徽章

如果你的仓库路径不同，请替换 `percy-han/aws-omni-support-agent` 为你的实际路径。

### 添加更多徽章

**代码覆盖率** (需要配置 Codecov):
```markdown
[![codecov](https://codecov.io/gh/percy-han/aws-omni-support-agent/branch/main/graph/badge.svg)](https://codecov.io/gh/percy-han/aws-omni-support-agent)
```

**代码质量** (需要配置 Codacy):
```markdown
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/xxx)](https://www.codacy.com/gh/percy-han/aws-omni-support-agent)
```

**最后提交时间**:
```markdown
[![GitHub last commit](https://img.shields.io/github/last-commit/percy-han/aws-omni-support-agent)](https://github.com/percy-han/aws-omni-support-agent/commits/main)
```

**Issues 统计**:
```markdown
[![GitHub issues](https://img.shields.io/github/issues/percy-han/aws-omni-support-agent)](https://github.com/percy-han/aws-omni-support-agent/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/percy-han/aws-omni-support-agent)](https://github.com/percy-han/aws-omni-support-agent/pulls)
```

**环境徽章**:
```markdown
[![Environment - DEV](https://img.shields.io/badge/env-dev-blue)](https://console.aws.amazon.com/lambda)
[![Environment - PROD](https://img.shields.io/badge/env-prod-green)](https://console.aws.amazon.com/lambda)
```
