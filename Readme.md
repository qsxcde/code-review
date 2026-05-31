# AI Code Review

> 基于 LLM 的 GitHub Pull Request 自动代码审查工具 —— 输入 PR 链接，秒级生成多维度的结构化审查报告。

🎬 **Demo 视频**：https://www.bilibili.com/video/BV1UhVU6pEc6/

---

## 目录

- [功能概览](#功能概览)
- [项目架构](#项目架构)
- [原创功能](#原创功能)
- [后端依赖说明](#后端依赖说明)
- [前端依赖说明](#前端依赖说明)
- [快速开始](#快速开始)
- [Docker 部署（推荐）](#docker-部署推荐)
- [线上部署（HTTPS + 域名）](#线上部署https--域名)
- [配置指南](#配置指南)
- [项目结构](#项目结构)

---

## 功能概览

| 模块 | 功能 | 说明 |
|------|------|------|
| 🔍 **PR 智能分析** | 一键审查 GitHub PR | 输入 PR URL → 自动拉取代码 → LLM 分析 → 结构化报告 |
| 🧠 **多 Agent 协同** | 安全 + 性能 + 风格三专家并行 | 小 PR 单 Agent 快速分析，大 PR 自动升级深度分析 |
| 📈 **增量审查** | 对比历史结果追踪风险趋势 | 标记新增 / 已修复 / 仍存在的风险 |
| 💬 **讨论上下文** | 自动提取 PR 讨论注入分析 | 评论数 > 30 时自动 LLM 摘要 |
| 📋 **审查历史** | 分页浏览 + 状态/仓库筛选 | 支持单条删除 |
| 👍 **用户反馈** | 风险级"有帮助 / 无用 / 误报"评价 | 反馈数据驱动 Few-Shot 持续优化 |
| 📊 **质量统计** | 覆盖率 / 误报率 / 各 Agent 表现 | 进度条可视化 + 最近误报追踪 |
| 📐 **自定义规则** | CRUD + 文件过滤 + 优先级 | 分析时自动注入对应专家 Agent |
| 📤 **报告导出** | Markdown 导出 + PDF 打印 | 一键生成完整审查报告 |

---

## 项目架构

```
┌──────────────┐     HTTP / REST      ┌──────────────────────────────┐
│   Vue 3 前端  │ ◄──────────────────► │   FastAPI 后端                │
│   (Vite)      │    JSON + JWT        │                              │
│   Port 5173   │                      │   ┌────────────────────────┐ │
└──────────────┘                      │   │  LangGraph 审查图引擎    │ │
                                       │   │  ┌───────┐ ┌─────────┐ │ │
                                       │   │  │安全专家│ │性能专家  │ │ │
                                       │   │  └───────┘ └─────────┘ │ │
                                       │   │  ┌───────────────────┐  │ │
                                       │   │  │风格专家             │  │ │
                                       │   │  └───────────────────┘  │ │
                                       │   └────────────────────────┘ │
                                       │               │               │
                                       │  ┌────────────┴────────────┐ │
                                       │  │  GitHub API  │ DeepSeek  │ │
                                       │  │  (PR 数据)    │ (LLM)    │ │
                                       │  └────────────┴────────────┘ │
                                       │               │               │
                                       │  ┌────────────┴────────────┐ │
                                       │  │  MySQL  │  Redis        │ │
                                       │  │ (持久化) │ (缓存+限流)    │ │
                                       │  └─────────┴───────────────┘ │
                                       └──────────────────────────────┘
```

**分析流程**（多 Agent 模式）：

```
PR URL 输入 → GitHub API 拉取数据 → 阶段1：全局特征分析（识别高风险区域）
  → 阶段2：安全/性能/风格三 Agent 并行审查
  → 阶段3：结果合并 + 冲突消解 + LLM 综合摘要 → 结构化报告输出
```

---

## 原创功能

以下功能为独立设计与实现，非第三方框架提供：

### 1. 智能路由 + 多 Agent 协同审查引擎

`backend/app/agents/review/orchestrator.py`

- **自动路由决策**：根据 PR 文件数 + 行数自动选择单 Agent 快速分析（≤2 文件 & ≤300 行）或三 Agent 深度分析（≥4 文件 或 ≥1000 行）
- **阶段化流水线**：Phase1 全局特征分析 → Phase2 三专家并行审查 → Phase3 合并消解 + LLM 综合摘要
- **专家分工**：安全专家（DeepSeek-V4-Pro，扫描 auth/login/token 等关键路径）、性能专家（DeepSeek-V4-Pro）、风格专家（DeepSeek-V4-Flash）
- **Agent 自适应跳过**：PR 未涉及某领域代码变更时，自动跳过该专家，避免无意义 token 消耗

### 2. PR 讨论上下文理解

`backend/app/agents/review/orchestrator.py` — `_format_discussion` / `_summarize_discussion`

- 自动提取 PR 的 Issue Comments + Review Comments + PR Body
- 按作者优先级排序（PR 作者 > 维护者 > 其他）
- 评论数超过 30 条时自动触发 LLM 摘要，提取设计意图、已知限制和安全讨论等关键信息
- 摘要注入到阶段 1 的全局特征分析 Prompt 中

### 3. 增量审查与风险趋势追踪

- 首次审查后，再次分析同一 PR 时自动对比历史结果
- 标记三类趋势：新增风险 / 已修复 / 仍存在
- 前端以彩色标签可视化展示

### 4. 反馈驱动的 Few-Shot 优化

- 用户对每条风险标记"有帮助"后，该条审查结果自动进入 Few-Shot 示例池
- 后续分析时，相关专家的 System Prompt 中注入历史高质量示例
- 形成"分析 → 反馈 → 学习 → 更准分析"的闭环

### 5. 自定义审查规则引擎

- 支持 CRUD 管理团队专属审查规则
- 每条规则可指定：类别（安全/性能/风格/自定义）、文件过滤（glob pattern）、优先级
- 分析时自动按类别 + 优先级排序后注入到对应 Agent 的 Prompt
- 启用/禁用开关，无需删除即可临时停用

### 6. 审查质量统计面板

- 基于用户反馈计算覆盖率、误报率
- 按 Agent 维度拆解"有帮助/无用/误报"比例
- 最近误报列表方便团队回溯改进规则

### 7. 速率限制中间件

`backend/app/core/rate_limit.py`

- 双层限流：优先 Redis 滑动窗口（生产环境），自动回退到内存滑动窗口（Redis 不可用时）
- 支持 `Retry-After`、`X-RateLimit-*` 标准响应头

---

## 后端依赖说明

| 依赖 | 版本 | 用途 |
|------|------|------|
| **FastAPI** | 0.115.6 | 现代 Python Web 框架，提供路由、依赖注入、请求验证、自动 OpenAPI 文档 |
| **Uvicorn** | 0.34.0 | ASGI 服务器，用于运行 FastAPI 应用，支持热重载和并发 |
| **Pydantic-Settings** | 2.7.1 | 从 `.env` 文件和环境变量加载配置，支持类型验证 |
| **HTTPX** | 0.28.1 | 异步 HTTP 客户端，用于调用 GitHub API 和 LLM API |
| **LangChain-Core** | 1.3.2 | LLM 应用开发框架核心库，提供 ChatModel、Prompt Template 等抽象 |
| **LangChain-OpenAI** | 1.2.1 | LangChain 的 OpenAI 兼容适配器，用于对接 DeepSeek API |
| **LangGraph** | 1.1.10 | 有状态多步骤 LLM 工作流引擎，用于构建单 Agent 审查图 |
| **SQLAlchemy** | 2.0.36 | Python ORM，异步数据库操作（MySQL），管理审查记录、用户、规则等数据 |
| **aiomysql** | 0.2.0 | MySQL 异步驱动，为 SQLAlchemy 异步模式提供底层连接 |
| **Redis** | 5.2.1 | 热缓存（审查结果 L1 缓存）+ 速率限制滑动窗口 + JWT 黑名单 |
| **bcrypt** | 4.2.1 | 密码哈希，用于用户注册和登录验证 |
| **PyJWT** | 2.10.1 | JWT 令牌的生成、签名和验证（Access Token + Refresh Token） |
| **email-validator** | 2.2.0 | 邮箱格式验证，配合 Pydantic `EmailStr` 类型 |
| **cryptography** | — | 加密工具库，为 PyJWT 提供密码学算法支持 |

---

## 前端依赖说明

### 运行时依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| **Vue 3** | 3.5.13 | 渐进式 JavaScript 框架，Composition API + `<script setup>` 语法 |
| **Element Plus** | 2.11.8 | Vue 3 UI 组件库，提供表格、表单、弹窗、消息提示、标签等组件 |
| **@element-plus/icons-vue** | 2.3.1 | Element Plus 配套图标库（搜索、删除、刷新等） |

### 开发依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| **Vite** | 6.0.7 | 前端构建工具，极速 HMR 热更新 + 生产打包 |
| **TypeScript** | 5.7.2 | 类型系统，提升代码健壮性和可维护性 |
| **Vue-TSC** | 2.2.0 | Vue 3 TypeScript 类型检查工具 |
| **@vitejs/plugin-vue** | 5.2.1 | Vite 的 Vue 3 单文件组件编译插件 |
| **Sass** | 1.94.2 | CSS 预处理器，用于 `<style scoped lang="scss">` 样式编写 |
| **@types/node** | 25.9.1 | Node.js 类型声明，支持 `import.meta.env` 等 Vite 环境变量类型 |

---

## 快速开始

### 环境要求

- Python ≥ 3.11
- Node.js ≥ 18
- MySQL ≥ 8.0
- Redis ≥ 6.0

### 1. 克隆项目

```bash
git clone <repo-url>
cd code-review
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt

# 初始化数据库（手动执行 scripts 目录下的 SQL 文件）
# mysql -u root -p < scripts/001_create_users.sql
# mysql -u root -p < scripts/002_create_review_tables.sql
# mysql -u root -p < scripts/003_create_review_rules.sql

# 复制环境变量配置
cp .env.example .env
# 编辑 .env 填入 GitHub Token、DeepSeek API Key、数据库密码等

# 启动
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://127.0.0.1:5173`

---

## Docker 部署（推荐）

无需手动安装 Python、Node.js、MySQL、Redis，一行命令即可启动全部服务。

```bash
# 1. 克隆项目
git clone <repo-url>
cd code-review

# 2. 配置密钥（仅需编辑两个变量）
cp backend/.env.example backend/.env
# 编辑 backend/.env：填入 GITHUB_TOKEN 和 OPENAI_API_KEY

# 3. 一键启动
docker compose up -d

# 4. 访问
open http://localhost
```

首次启动 MySQL 会自动执行 `backend/scripts/` 下的 SQL 脚本建表，约 30 秒即可就绪。二次启动秒级恢复。

**架构说明**：

```
                  docker compose up -d
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
  ┌──────────┐       ┌──────────┐        ┌──────────┐
  │  nginx    │ ────► │ backend  │ ──────► │  mysql   │
  │  (前端)   │       │  :8000   │        │  :3306   │
  │  :80      │       └──────────┘        └──────────┘
  └──────────┘              │                    │
                        ┌───┴────┐          ┌────┴─────┐
                        │ redis  │          │ 持久化卷  │
                        │ :6379  │          │ mysql_data│
                        └────────┘          └──────────┘
```

| 服务 | 对外端口 | 说明 |
|------|---------|------|
| `frontend` (nginx) | **80** | 静态文件 + `/api/` 反向代理到后端 |
| `backend` | — | 仅容器内暴露，不直接对外 |
| `mysql` | 3306 | 数据持久化到 `mysql_data` 卷 |
| `redis` | 6379 | 数据持久化到 `redis_data` 卷 |

---

## 线上部署（HTTPS + 域名）

本地 Docker 部署只需 `docker compose up -d`。线上部署在此基础上增加 Caddy 反向代理，实现自动 HTTPS。

### 架构变化

本地部署对外端口 `80`，线上部署改为：

| 服务 | 本地 | 线上 |
|------|------|------|
| `frontend` (nginx) | 端口 80 对外 | 端口关闭，仅容器内 |
| `caddy` | 无 | 端口 80 + 443 对外，自动 HTTPS |

### 部署步骤

```bash
# 1. SSH 登录服务器，安装 Docker
curl -fsSL https://get.docker.com | sh

# 2. 上传项目
git clone <repo-url> /opt/code-review
cd /opt/code-review

# 3. 配置密钥（务必使用强密码）
cp backend/.env.example backend/.env
# 编辑 backend/.env：
#   GITHUB_TOKEN=ghp_xxx
#   OPENAI_API_KEY=sk-xxx
#   JWT_SECRET=<随机 64 字符>       ← 务必随机生成
#   MYSQL_ROOT_PASSWORD=<强密码>
#   LOG_FORMAT=json
#   APP_DEBUG=false

# 4. 编辑 Caddyfile，把域名换成你的
# code-review.your-domain.com → 你的真实域名

# 5. DNS 解析：添加 A 记录指向服务器 IP

# 6. 启动（使用 prod 覆盖文件）
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 7. 访问
open https://code-review.your-domain.com
```

Caddy 会在首次访问时自动从 Let's Encrypt 申请证书，之后每 90 天自动续签，无需手动操作。

**安全加固**（prod 覆盖文件自动处理）：
- MySQL / Redis 端口不对外暴露
- 前端不直接对外，统一由 Caddy 提供 HTTPS
- 生产日志使用 JSON 格式，便于接入日志收集系统

---

## 配置指南

后端所有配置通过 `backend/.env` 文件管理（参考 `backend/.env.example`）：

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | 必填 |
| `GITHUB_API_PROXY` | GitHub API 代理地址 | 可选 |
| `OPENAI_API_KEY` | DeepSeek API Key | 必填 |
| `OPENAI_BASE_URL` | LLM API 地址 | `https://api.deepseek.com` |
| `OPENAI_MODEL` | 默认模型 | `deepseek-v4-flash` |
| `DEEP_MODEL` | 深度分析模型（Phase1 + 安全/性能专家） | `deepseek-reasoner` |
| `FAST_MODEL` | 快速模型（单 Agent + 风格专家） | `deepseek-chat` |
| `DATABASE_URL` | MySQL 连接串 | `mysql+aiomysql://root:@localhost:3306/code_review` |
| `REDIS_URL` | Redis 连接串 | `redis://localhost:6379/0` |
| `JWT_SECRET` | JWT 签名密钥 | 必填（≥32 字符） |
| `LOG_FORMAT` | 日志格式 `dev` / `json` | `json` |
| `RATE_LIMIT_REQUESTS` | 每分钟请求上限 | `30` |
| `RATE_LIMIT_WINDOW_SECONDS` | 限流窗口（秒） | `60` |

前端配置在 `frontend/.env`：

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 地址 | `http://127.0.0.1:8000/api/v1` |

---

## 项目结构

```
├── docker-compose.yml              ← 一键部署编排
├── docker-compose.prod.yml          ← 线上部署覆盖（HTTPS）
├── Caddyfile                        ← Caddy 反向代理配置
├── backend/
│   ├── Dockerfile                   ← 后端容器镜像
│   ├── app/
│   │   ├── agents/review/          ← 审查引擎核心
│   │   │   ├── orchestrator.py     ← 智能路由 + 多Agent编排
│   │   │   ├── specialist.py       ← 三专家Agent定义
│   │   │   ├── aggregator.py       ← 结果合并 + 冲突消解
│   │   │   ├── context.py          ← Agent上下文构建
│   │   │   ├── graph.py            ← 单Agent LangGraph审查图
│   │   │   ├── normalizer.py       ← 结果规范化
│   │   │   ├── truncator.py        ← 代码截断（适配 LLM context window）
│   │   │   └── prompts/            ← 各Agent System Prompt
│   │   ├── api/v1/endpoints/       ← REST API 路由
│   │   │   ├── auth.py             ← 注册/登录/刷新/登出
│   │   │   ├── review.py           ← PR 分析入口
│   │   │   ├── review_history.py   ← 审查历史 CRUD + 反馈
│   │   │   ├── review_rules.py     ← 自定义规则 CRUD
│   │   │   ├── review_stats.py     ← 质量统计
│   │   │   └── review_progress.py  ← 实时进度推送
│   │   ├── core/                   ← 基础设施
│   │   │   ├── config.py           ← 配置加载
│   │   │   ├── db.py               ← 数据库连接
│   │   │   ├── jwt.py              ← JWT 令牌工具
│   │   │   ├── security.py         ← 认证依赖
│   │   │   ├── rate_limit.py       ← 速率限制中间件
│   │   │   ├── redis.py            ← Redis 连接管理
│   │   │   └── logging.py          ← 日志系统
│   │   ├── services/               ← 业务逻辑层
│   │   │   ├── review/             ← 审查服务（分析/记录/反馈/规则/进度）
│   │   │   ├── llm/                ← LLM 调用封装
│   │   │   ├── github/             ← GitHub API 封装
│   │   │   └── auth/               ← 认证服务
│   │   ├── models/                 ← SQLAlchemy ORM 模型
│   │   └── schemas/                ← Pydantic 请求/响应模型
│   ├── tests/                      ← 单元测试（107 个）
│   └── scripts/                    ← 数据库初始化 SQL
├── frontend/
│   ├── Dockerfile                   ← 前端容器镜像（多阶段构建）
│   ├── nginx.conf                   ← nginx 反向代理配置
│   ├── src/
│   │   ├── views/                  ← 页面组件
│   │   │   ├── AnalysisView.vue    ← 主分析页
│   │   │   ├── SettingsView.vue    ← 规则管理页
│   │   │   └── StatsView.vue       ← 统计面板页
│   │   ├── components/             ← 可复用组件
│   │   │   ├── SearchPanel.vue     ← PR URL 输入 + 分析触发
│   │   │   ├── SummaryCard.vue     ← 分类摘要卡片
│   │   │   ├── RiskCard.vue        ← 风险文件列表
│   │   │   ├── DiffViewer.vue      ← 代码 Diff 查看器
│   │   │   ├── AISummaryPanel.vue  ← AI 建议面板
│   │   │   └── AnalysisProgress.vue← 分析进度条
│   │   ├── composables/            ← 组合式逻辑
│   │   ├── api/                    ← HTTP 请求封装
│   │   ├── types/                  ← TypeScript 类型定义
│   │   └── utils/                  ← 工具函数
│   └── package.json
└── docs/
    ├── demo-script.md              ← Demo 视频录制文稿
    └── pr/                         ← PR 描述归档
```

---

## License

MIT
