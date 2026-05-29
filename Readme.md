# AI Code Review Tool

一个用于分析 GitHub Pull Request 的 AI 代码审查工具。后端基于 FastAPI、LangChain 和 LangGraph，前端基于 Vue 3 与 Vite。

## Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

访问：

```text
http://127.0.0.1:5173
```

前端默认调用：

```text
http://127.0.0.1:8001/api/v1
```

如需修改后端地址，可在 `frontend/.env` 中配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8001/api/v1
```
