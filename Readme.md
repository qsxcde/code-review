# AI Code Review

> 基于 LLM 的 GitHub Pull Request 自动代码审查工具 —— 输入 PR 链接，秒级生成多维度的结构化审查报告。

🎬 **Demo 视频**：https://www.bilibili.com/video/BV1UhVU6pEc6/

 启动项目前需要保证科学上网，否则会报错，因为链接不上github。
 务必填入github token和deepseek api key
 
---

## 目录

- [功能概览](#功能概览)
- [项目架构](#项目架构)
- [原创功能](#原创功能)
- [后端依赖说明](#后端依赖说明)
- [前端依赖说明](#前端依赖说明)
- [快速开始](#快速开始)
- [Docker 部署（推荐）](#docker-部署推荐)
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
# 编辑 .env：填入 GITHUB_TOKEN、OPENAI_API_KEY、OPENAI_BASE_URL、OPENAI_MODEL

# 启动
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. 启动前端

```bash
cd frontend
cp .env.example .env
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

# 2. 配置密钥
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# 编辑 backend/.env：填入 GITHUB_TOKEN、OPENAI_API_KEY、OPENAI_BASE_URL、OPENAI_MODEL

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
| `mysql` | — | 数据持久化到 `mysql_data` 卷 |
| `redis` | — | 数据持久化到 `redis_data` 卷 |

> **提示**：如果宿主机已有 MySQL/Redis 占用 3306/6379 端口，可编辑 `docker-compose.yml` 修改对外端口映射（如 `3307:3306`），容器内部通信不受影响。

### 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| `ports are not available: 3306` | 宿主机端口被占用 | 改 `docker-compose.yml` 端口映射为 `3307:3306` |
| 前端请求返回 500 | `DATABASE_URL` 用了 `localhost` | 改为 `mysql`（Docker 服务名） |
| 修改 `.env` 后前端 502 | nginx 缓存了旧后端 IP | `docker compose restart frontend` |
| 构建报 `Access is denied: .pytest_cache` | 构建上下文包含权限异常的缓存目录 | 已通过 `.dockerignore` 排除 |

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
├── backend/
│   ├── Dockerfile                   ← 后端容器镜像
│   ├── .dockerignore                ← 构建排除（.pytest_cache 等）
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
│   ├── .dockerignore                ← 构建排除（node_modules 等）
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

## 设计思路

本节从分析准确度、上下文理解、误报与漏报控制、响应速度、使用体验五个维度，说明各设计决策的出发点。

### 1. 分析准确度

目标是让 LLM 输出的审查结论尽可能接近资深工程师的 Code Review 质量。为此设计了多层保障：

**三阶段流水线，逐步聚焦**
```
Phase 1: 全局特征分析（识别高风险区域 + 讨论上下文注入）
  → Phase 2: 安全 / 性能 / 风格三 Agent 并行审查（各司其职，缩小关注面）
    → Phase 3: 结果合并 + 冲突消解 + LLM 综合摘要
```
Phase 1 让 reasoning 模型先通读 PR 全貌，输出安全焦点、性能焦点、高风险文件列表，Phase 2 各专家带着这些焦点去审查，避免"漫无目的地扫代码"导致遗漏。

**专家分工，Prompt 专业化**

三专家的 System Prompt 各自聚焦一个领域，不互相干扰：
- 安全专家扫描 `auth|login|token|session|permission|middleware|config|crypto` 等关键路径，自带 OWASP Top 10、CWE 知识
- 性能专家关注 N+1 查询、不合理的缓存策略、大对象拷贝、阻塞 I/O
- 风格专家负责命名规范、函数长度、代码重复、错误处理一致性

**大 PR 升级深度分析**

| PR 规模 | 策略 | 原因 |
|---------|------|------|
| ≤2 文件 & ≤300 行 | 单 Agent 快速分析（Flash 模型） | 变更简单，深度分析浪费 token |
| 中等规模 | 自动选择多 Agent | 按复杂度判断 |
| ≥4 文件 或 ≥1000 行 | 三 Agent 深度分析 + Phase 1 | 变更范围大，需要多视角覆盖 |

**Agent 自适应跳过**

安全专家仅在被审查文件路径命中预定义模式时才激活。PR 如果只改了 CSS/文档，跳过安全 Agent，避免无意义 token 消耗，也减少无关噪声干扰分析质量。

**语言感知的代码截断**

`truncator.py` 按语言语法边界（函数/类/方法定义）截断超长文件，而非粗暴按字符数截断。支持 Python、JS/TS、Java、Go、SQL 六种语言，确保送入 LLM 的代码片段语义完整。

### 2. 上下文理解

纯靠 diff 审查代码如同"盲人摸象"，必须理解变更的 WHY 才能判断对错。

**PR 讨论自动注入**

- 自动拉取 PR 的 Issue Comments + Review Comments + PR Body
- 评论数 ≤30 时：按作者优先级排序后直接注入 Phase 1 Prompt
- 评论数 >30 时：触发 LLM 摘要，提取设计意图、已知限制、安全讨论、争议/共识
- 摘要失败时自动回退到格式化方式，保证流程不被阻断

**全文件上下文增强**

不仅看 diff，还对最多 15 个文件拉取完整内容 + import 分析，让 LLM 理解函数调用链和模块依赖关系。`context.py:enhance_files()` 负责这一增强逻辑，获取失败时静默降级。

**讨论上下文上限控制**

讨论上下文注入有严格上限：最多 15 条评论、每条 ≤200 字符、总计 ≤2000 字符。避免超过 LLM context window，也是在"信息量"和"注意力聚焦"之间取平衡。

### 3. 误报与漏报控制

审查工具最大的信任危机来自两个极端：过多的误报让用户不再看报告，漏报让审查失去意义。

**Fake positive（误报）控制**

| 手段 | 机制 |
|------|------|
| 用户反馈"误报" | 前端每个风险项支持"有帮助 / 无用 / 误报"评价 |
| 反馈驱动 Few-Shot | 被标记"有帮助"的审查结果自动进入 Few-Shot 示例池，后续分析时注入对应 Agent 的 System Prompt |
| 审查质量统计 | 实时计算覆盖率、误报率，按 Agent 维度拆解，暴露问题 Agent |
| 冲突消解 | Phase 3 对同一位置来自不同 Agent 的风险进行冲突检测，severity 不一致时标记并消解 |

**Fake negative（漏报）控制**

| 手段 | 机制 |
|------|------|
| 多 Agent 交叉覆盖 | 安全 + 性能 + 风格三视角降低单一视角的盲区概率 |
| 自定义规则注入 | 团队可将历史漏报转化为自定义审查规则，按类别 + 文件过滤注入对应 Agent |
| 增量审查 | 二次分析同一 PR 时对比历史结果，标记"仍存在"的风险，避免修复后回退 |

**反馈闭环**

```
用户提交反馈 → 后端记录反馈标签 → 统计面板展示误报率
     ↓
被标记"有帮助"的审查结果 → 进入 Few-Shot 示例池
     ↓
后续分析时注入对应 Agent 的 System Prompt → 提升相关场景识别率
```

### 4. 响应速度

代码审查工具的快慢直接影响是否会被日常使用。

**模型分层策略**

| 阶段 | 模型 | 原因 |
|------|------|------|
| Phase 1（全局分析） | DeepSeek-V4-Pro（reasoning） | 需要深度推理识别高风险区域，但不分析具体代码 |
| Phase 2 安全专家 | DeepSeek-V4-Pro | 安全审查需要强推理能力 |
| Phase 2 性能专家 | DeepSeek-V4-Pro | 性能瓶颈识别需要上下文推理 |
| Phase 2 风格专家 | DeepSeek-V4-Flash | 风格检查是模式匹配，不需要深度推理 |
| Phase 3 综合摘要 | DeepSeek-V4-Flash | 合并结果不涉及新分析 |
| 讨论摘要 | DeepSeek-V4-Flash | 文本摘要任务 |
| 单 Agent 快速模式 | DeepSeek-V4-Flash | 小 PR 不需要深度分析 |

**并行执行**

Phase 2 三专家完全并行执行，总耗时 = max(安全, 性能, 风格) 而非 sum。Phase 1 期间讨论摘要也在并行启动。

**输出截断与上限控制**

- 单文件 patch ≤6000 字符
- 全文件内容 ≤4000 字符
- 最多 30 个文件入审查上下文
- 最多 15 个全文件内容拉取
- 讨论上下文 ≤2000 字符

每项上限都是在"分析质量"和"响应速度"之间测试后取的平衡点。

**缓存策略**

审查结果写入 Redis L1 缓存，短时间内重复分析同一 PR 直接返回缓存结果，避免重复调用 LLM。

### 5. 使用体验

**一键审查**

用户只需粘贴 PR URL，系统自动完成 URL 解析 → 数据拉取 → 分析 → 报告输出全流程，无需手动选择分析参数。

**实时进度反馈**

分析过程中通过 SSE（Server-Sent Events）向前端推送实时进度，为用户提供明确的状态反馈（拉取 PR 数据 → 全局分析 → 安全审查中 → 性能审查中 → 风格审查中 → 生成摘要），避免长时间等待的焦虑。

**结构化报告**

审查结果分为摘要总览、风险分级（高/中/低）、按文件归类、修复建议四个层次，支持按严重程度和文件筛选。

**彩色 Diff 查看器**

前端内置代码 Diff 查看器，风险项关联到具体代码行，点击即可查看变更内容，无需跳转到 GitHub。

**审查历史管理**

- 分页浏览历史审查记录
- 支持按状态（已完成/进行中/失败）和仓库筛选
- 支持单条删除

**自定义规则 CRUD 面板**

可视化创建/编辑/启用/禁用审查规则，无需修改代码即可定制审查策略。

**报告导出**

支持 Markdown 文件导出和 PDF 打印，方便归档和分享。

**速率限制与容错**

双层限流（Redis + 内存回退）防止 API 滥用。组件级静默降级：Redis 不可用时自动切换到内存限流，讨论摘要失败自动回退到格式化，全文件拉取失败继续只用 diff 审查。

---

## 未来拓展方向

| 方向 | 说明 | 优先级 |
|------|------|--------|
| **自动修复建议生成** | 不仅指出问题，还生成可直接应用的 patch / fix suggestion，配合 GitHub Suggestions API 一键提交 | 高 |
| **CI/CD 原生集成** | 提供 GitHub Actions / GitLab CI 原生 Action，PR 提交时自动触发审查并评论 | 高 |
| **多仓库对比审查** | 跨仓库 PR 联动分析（如前后端同步变更的 PR），检测接口契约不一致 | 中 |
| **代码资产知识图谱** | 构建项目的类/函数/模块依赖图，让 LLM 理解"改了 A 会影响 B/C/D"，提升跨文件风险识别准确率 | 中 |
| **语义级代码搜索** | 对全量代码建向量索引，审查时自动检索相关代码上下文（相似实现、历史 bug），而非仅依赖当前 PR 的 diff | 中 |
| **审查策略自进化** | 基于反馈数据自动调优 Prompt、自定义规则权重和 Agent 激活策略，减少人工调参 | 中 |
| **多模型适配层** | 抽象 LLM 调用接口，支持一键切换 DeepSeek / GPT / Claude / 本地模型，根据任务复杂度自动路由到不同模型 | 低 |
| **IDE 插件** | VS Code / JetBrains 插件，在编辑器内直接触发审查，结果叠加到代码行上 | 低 |
| **组织级审查基准** | 支持按团队/项目设置不同的审查标准基线（如金融项目要求更高的安全审查权重） | 低 |
| **多语言深度支持** | 扩展语言感知截断和 import 解析到更多语言（Rust、Kotlin、Swift 等），并注入语言特定的最佳实践规则 | 低 |

---

## License

MIT
