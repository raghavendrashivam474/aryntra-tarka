# Deployment Guide

---

## Frontend — Vercel

### Prerequisites

- Vercel account
- Successful production build

```bash
npm run build
```

### Deployment

Install the Vercel CLI:

```bash
npm install -g vercel
```

Deploy the frontend:

```bash
cd frontend
vercel --prod
```

Configure the following environment variable in the Vercel dashboard:

```text
VITE_API_URL=https://your-backend.onrender.com
```

The provided `frontend/vercel.json` includes:

- SPA rewrites
- Security headers
- Production build configuration

---

## Backend — Render

### Prerequisites

- Render account
- GitHub repository connected

### Deployment

1. Create a new **Web Service**.
2. Connect your GitHub repository.
3. Render automatically detects the `render.yaml` configuration.
4. Configure the required environment variables.

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.2
APP_ENV=production
DEBUG=false
```

### Health Check

Configure Render to use:

```text
GET /api/version
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OLLAMA_BASE_URL` | Yes | URL of the Ollama server |
| `OLLAMA_DEFAULT_MODEL` | Yes | Default language model |
| `APP_ENV` | No | Application environment (`development` or `production`) |
| `DEBUG` | No | Enables debug logging |

See `.env.example` for the complete reference.

---

## Local Production Test

### Frontend

```bash
cd frontend

npm run build
npm run preview
```

### Backend

```bash
cd ..

uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

## Deployment Checklist

Before publishing a release, verify:

- Frontend production build succeeds
- Backend starts without errors
- Environment variables are configured
- `/api/version` responds successfully
- Frontend communicates with the deployed backend
- Streaming responses function correctly
- Conversation persistence works as expected

Once all checks pass, Tarka is ready for production deployment.

