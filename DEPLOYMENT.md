# 🚀 ChainSentry Deployment & Production Guide

This guide details how to build, deploy, configure, and maintain the **ChainSentry** Bitcoin transaction monitoring and forensics investigation platform across containerized and cloud environments. It also provides workflows for developing and updating the backend and frontend post-deployment.

---

## 📋 Table of Contents
1. [Architecture & Deployment Model](#-architecture--deployment-model)
2. [Prerequisites & Environment Configuration](#-prerequisites--environment-configuration)
3. [Quick Test Locally (Production Mode)](#-quick-test-locally-production-mode)
4. [Deployment Option 1: Docker / Container (Recommended)](#-deployment-option-1-docker--container-recommended)
5. [Deployment Option 2: Cloud PaaS (Render, Railway, Fly.io)](#-deployment-option-2-cloud-paas-render-railway-flyio)
6. [Deployment Option 3: Split Deployment (Vercel/Netlify + Backend API)](#-deployment-option-3-split-deployment)
7. [Post-Deployment: Making Ongoing Changes](#-post-deployment-making-ongoing-changes)
8. [Database Management & Persistence](#-database-management--persistence)
9. [Environment Variables Reference](#-environment-variables-reference)

---

## 🏛️ Architecture & Deployment Model

ChainSentry is engineered as an **offline-first, zero-daemon** forensics suite:
- **Unified Single-Process Mode**: The FastAPI backend (`uvicorn`) serves both the REST API endpoints (`/api/...`) and the precompiled React single-page application (`/`) with client-side SPA routing.
- **Embedded Persistence**: Defaults to SQLite (`chainsentry.db`) and in-memory NetworkX graph processing, requiring no external databases to run at 100% functionality.
- **Enterprise Pluggability**: Optionally connects to PostgreSQL (`DATABASE_URL=postgresql://...`) and Neo4j (`ENABLE_NEO4J=true`) via environment variables without requiring code modifications.

---

## ⚙️ Prerequisites & Environment Configuration

### Credentials
Default investigator accounts provisioned upon first boot:
- **System Administrator**: `admin` / `chainsentry2026!`
- **Lead Investigator**: `investigator` / `forensics2026!`

### Environment File
Copy [.env.example](file:///.env.example) to `.env` and configure:
```bash
cp .env.example .env
```
Key production variables:
- `SECRET_KEY`: Set to a strong random 32+ character string.
- `ENVIRONMENT`: Set to `production`.
- `PORT`: Automatically respected from platform environment (default: `8000`).
- `CORS_ORIGINS`: Comma-separated list of allowed origins or `*`.

---

## 💻 Quick Test Locally (Production Mode)

To verify the production build on your local machine:

1. **Build the frontend bundle**:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```
2. **Start the unified server**:
   ```bash
   python run.py
   ```
3. Visit **[http://localhost:8000](http://localhost:8000)** in your browser.
   - SPA loads at `/`
   - API docs load at `/docs`
   - Healthcheck responds at `/health`

---

## 🐳 Deployment Option 1: Docker / Container (Recommended)

ChainSentry includes a production-ready, multi-stage [Dockerfile](file:///Dockerfile) that compiles the TypeScript/React frontend in Node 20 and packages it with the Python 3.12 FastAPI backend.

### Single Container Build & Run
```bash
# Build the unified container
docker build -t chainsentry:latest .

# Run the container (binds to port 8000)
docker run -d \
  --name chainsentry \
  -p 8000:8000 \
  -e SECRET_KEY="your-production-secret-key" \
  -e ENVIRONMENT="production" \
  chainsentry:latest
```

### Docker Compose
```bash
# Launch with volume persistence
docker compose up --build -d

# Check logs
docker compose logs -f

# Stop container
docker compose down
```

### Google Cloud Run
```bash
# Deploy directly from repository source
gcloud run deploy chainsentry \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars ENVIRONMENT=production,SECRET_KEY=your-production-secret
```

---

## ☁️ Deployment Option 2: Cloud PaaS (Render, Railway, Fly.io)

### Render (render.com)
1. Create a **New Web Service** connected to your GitHub repository.
2. **Method 1 (Docker - Recommended)**:
   - Environment: **Docker**
   - Health Check Path: `/health`
   - Add environment variables (`SECRET_KEY`, `ENVIRONMENT=production`).
   - Render automatically reads the Dockerfile, exposes `$PORT`, and deploys.
3. **Method 2 (Native Python)**:
   - Environment: **Python 3**
   - Build Command: `bash build.sh`
   - Start Command: `python run.py`

### Railway (railway.app)
1. Click **New Project** -> **Deploy from GitHub repo**.
2. Railway automatically detects the `Dockerfile`.
3. Set environment variable `SECRET_KEY` in Railway dashboard.
4. Railway maps the dynamic `$PORT` automatically.

### Fly.io
```bash
fly launch
fly deploy
```

---

## 🌐 Deployment Option 3: Split Deployment

If you prefer hosting the React frontend on **Vercel** / **Netlify** / **Cloudflare Pages** and the backend on **Render** / **Railway**:

1. **Deploy Backend**:
   - Deploy backend to Render/Railway.
   - Note the backend URL (e.g., `https://chainsentry-api.onrender.com`).
   - Set backend environment variable:
     ```env
     CORS_ORIGINS=https://your-frontend.vercel.app
     ```
2. **Deploy Frontend (Vercel / Netlify)**:
   - Project Root: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Environment Variable:
     ```env
     VITE_API_BASE_URL=https://chainsentry-api.onrender.com
     ```
   The frontend API layer in `frontend/src/lib/api.ts` automatically routes requests to your remote backend.

---

## 🛠️ Post-Deployment: Making Ongoing Changes

You mentioned planning to make frequent additions and updates to both the backend and frontend after deploying. Here is the recommended workflow to ensure smooth development without deployment issues:

### 1. Local Development Workflow
Run frontend and backend concurrently with hot reloading:

- **Terminal 1 (Backend with auto-reload)**:
  ```powershell
  python run.py --reload
  # or: uvicorn backend.api_service.main:app --reload --port 8000
  ```
- **Terminal 2 (Frontend with Vite HMR)**:
  ```powershell
  cd frontend
  npm run dev
  ```
  Vite runs at `http://localhost:5173` and automatically proxies `/api` calls to `http://127.0.0.1:8000`.

### 2. Modifying the Backend
- **Adding new routers**:
  Create the service logic under `backend/<service_dir>/`, add route handlers in `backend/api_service/routers/`, and register the router in `backend/api_service/main.py`.
- **Adding database models**:
  Define models in `backend/case_svc/models.py`. The `init_db()` routine in `backend/chainsentry_common/db.py` will automatically create any new tables on server boot.
- **Run tests before pushing**:
  ```powershell
  pytest backend/tests
  ```

### 3. Modifying the Frontend
- **UI Components & Pages**:
  Edit files in `frontend/src/`. All TypeScript types are located in `frontend/src/types/`.
- **API Endpoints**:
  Add typed fetch calls in `frontend/src/lib/api.ts`.
- **Verify TypeScript and Build**:
  ```powershell
  cd frontend
  npm run build
  cd ..
  ```

### 4. Pushing Updates to Production
If your cloud deployment (Render, Railway, Cloud Run) is connected to your Git repository:
1. Commit your changes:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin main
   ```
2. Your cloud provider will automatically trigger a new Docker multi-stage build, compile the new frontend assets, update the backend, and deploy with zero downtime.

---

## 💾 Database Management & Persistence

- **SQLite (Default)**:
  When using Docker, persist `chainsentry.db` by mounting a volume to the data directory (configured in `docker-compose.yml`).
- **PostgreSQL**:
  To switch to PostgreSQL, set:
  ```env
  DATABASE_URL=postgresql://username:password@hostname:5432/chainsentry
  ```
  The database connector in `backend/chainsentry_common/db.py` automatically initializes tables on startup and configures production connection pooling.

---

## 🔐 Environment Variables Reference

| Variable | Default | Description |
| :--- | :--- | :--- |
| `APP_NAME` | `ChainSentry` | Platform title in logs and OpenAPI |
| `ENVIRONMENT` | `development` | Set to `production` in live environments |
| `HOST` | `0.0.0.0` | IP interface to bind server |
| `PORT` | `8000` | Port number (automatically detected from platform `$PORT`) |
| `SECRET_KEY` | *(dev key)* | Secret key used for signing JWT authentication tokens |
| `CORS_ORIGINS` | `localhost:5173,...` | Allowed CORS origins (comma-separated or `*`) |
| `DATABASE_URL` | `sqlite:///chainsentry.db` | SQLAlchemy database connection URI |
| `ENABLE_NEO4J` | `false` | Enable remote Neo4j graph database driver |
| `NEO4J_URI` | `bolt://localhost:7687` | Bolt connection string for Neo4j |
| `CELERY_ALWAYS_EAGER` | `true` | Synchronous task execution when Redis is not present |
| `ENABLE_LLM_NARRATIVE`| `false` | Enable Claude LLM for automated dossier narratives |
| `ANTHROPIC_API_KEY` | *(empty)* | Optional Anthropic API key |
