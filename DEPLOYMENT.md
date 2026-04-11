# Deployment Guide

This guide covers deploying the Gov Intelligence NLP platform to Railway.

## Architecture

- **Backend**: FastAPI (Python) + PostgreSQL with pgvector
- **Frontend**: Next.js 16
- **Platform**: Railway (PaaS)

## Branch Strategy

- **`main`**: Development branch - push changes here for testing
- **`production`**: Production branch - only deploys when you merge/ push here

## Prerequisites

1. [Railway CLI](https://docs.railway.app/develop/cli) installed: `npm install -g @railway-cli`
2. Railway account connected to GitHub
3. GitHub repository with `RAILWAY_TOKEN` secret configured

## Setup Steps

### 1. Create Railway Project

```bash
# Login to Railway
railway login

# Create new project
railway init
```

### 2. Provision PostgreSQL with pgvector

In Railway Dashboard:
1. Click "New" → "Database"
2. Select "Add PostgreSQL"
3. After creation, click on the database service
4. Go to "Settings" → "Configure"
5. Add the pgvector extension by connecting and running:
   ```sql
   CREATE EXTENSION IF NOT EXISTS "vector";
   ```

### 3. Deploy Backend Service

```bash
# Link to your Railway project
railway link

# Deploy backend service
railway up --service backend

# Set environment variables
railway variables --service backend DATABASE_URL="postgresql+asyncpg://..."
railway variables --service backend DATABASE_SYNC_URL="postgresql://..."
railway variables --service backend OPENAI_API_KEY="sk-..."
railway variables --service backend APP_ENV="production"
```

### 4. Deploy Frontend Service

```bash
# Deploy frontend service
railway up --service frontend

# Set environment variables
railway variables --service frontend NEXT_PUBLIC_API_BASE_URL="https://your-backend-url.up.railway.app"
```

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL async connection string | Yes |
| `DATABASE_SYNC_URL` | PostgreSQL sync connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `OPENAI_CHAT_MODEL` | OpenAI model for chat | No (default: gpt-4o-mini) |
| `OPENAI_EMBEDDING_MODEL` | OpenAI model for embeddings | No (default: text-embedding-3-small) |
| `APP_ENV` | Environment (production) | Yes |

### Frontend (`frontend/.env.local`)

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend API URL | Yes |

## Deployment Workflow

### Automatic Deployment (via GitHub Actions)

1. Push changes to `main` branch for testing
2. When ready to deploy, merge `main` into `production`:
   ```bash
   git checkout production
   git merge main
   git push origin production
   ```
3. GitHub Actions will automatically deploy to Railway

### Manual Deployment

```bash
# Deploy backend
railway up --service backend

# Deploy frontend  
railway up --service frontend
```

## Health Checks

- Backend health: `GET /health`
- Database health: `GET /health/db`

## Troubleshooting

### pgvector Extension Not Found

If you get errors about the vector extension:
1. Connect to your Railway PostgreSQL database
2. Run: `CREATE EXTENSION IF NOT EXISTS "vector";`

### CORS Errors

Update `CORS_ORIGINS` in backend environment variables:
```
https://your-frontend-url.up.railway.app,http://localhost:3000
```

### Database Connection Issues

Ensure your `DATABASE_URL` uses the correct format:
- Async: `postgresql+asyncpg://...`
- Sync: `postgresql://...`

## Custom Domain (Optional)

1. In Railway Dashboard, go to your service
2. Click "Settings" → "Domains"
3. Add your custom domain
4. Update DNS records as instructed

## Monitoring

- Railway Dashboard: View logs, metrics, and resource usage
- Health endpoints: Check `/health` and `/health/db`
- Railway CLI: `railway logs --service backend`
