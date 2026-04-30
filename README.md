# K8s-AI-Ops-Agent

Kubernetes AI Operations Agent — 全栈项目

## 目录结构

```
K8s-AI-Ops-Agent/
├── backend/
│   ├── main.py              # FastAPI 入口
│   └── requirements.txt     # Python 依赖
├── frontend/
│   ├── app/
│   │   ├── globals.css      # 全局样式 (Tailwind)
│   │   ├── layout.tsx       # 根布局
│   │   └── page.tsx         # 首页（健康检查展示）
│   ├── public/
│   ├── next.config.mjs      # Next.js 配置（含 API 代理）
│   ├── package.json
│   ├── postcss.config.mjs
│   └── tsconfig.json
├── .gitignore
└── README.md
```

## 快速启动

### 1. 后端（FastAPI）

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端运行在 http://localhost:8000，健康检查接口: `GET /health`

### 2. 前端（Next.js）

```bash
cd frontend
npm install
npm run dev
```

前端运行在 http://localhost:3000

前端通过 Next.js rewrites 将 `/api/*` 代理到后端 `http://localhost:8000/*`，无需额外 CORS 配置。

## 技术栈

- **后端**: Python 3.10+ / FastAPI / Uvicorn
- **前端**: Next.js 15 (App Router) / React 19 / TypeScript / Tailwind CSS 4
