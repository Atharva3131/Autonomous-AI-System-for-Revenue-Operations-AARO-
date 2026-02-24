# 🚀 AARO Full Interactive Demo Deployment

## Deploy Complete System (Backend + Frontend UI)

Your AARO system has two components that work together:
- **Backend API** (FastAPI) - Port 8000
- **Frontend UI** (Interactive Dashboard) - Port 3000

## Option 1: Railway.app (Recommended)

### Step 1: Deploy Backend API
```bash
# 1. Create railway.toml for API
echo '[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "python -m uvicorn aboa.main:app --host 0.0.0.0 --port $PORT"' > railway.toml

# 2. Push to GitHub
git add .
git commit -m "Ready for Railway deployment"
git push origin main

# 3. Deploy on Railway
# - Go to railway.app
# - "Deploy from GitHub repo"
# - Select your repo
# - Set environment variables:
#   ENVIRONMENT=production
#   SECRET_KEY=your-secret-key
#   DATABASE_URL=sqlite:///./demo.db
```

### Step 2: Deploy Frontend UI
```bash
# 1. Create separate UI service on Railway
# - Add new service to same project
# - Use Dockerfile.ui
# - Set environment variable:
#   API_BASE_URL=https://your-api-service.railway.app
```

## Option 2: Single Docker Deployment

### Local Test First:
```bash
# Test the full system locally
docker-compose -f docker-compose.demo.yml up -d

# Access at:
# - Full UI: http://localhost (nginx proxy)
# - Direct UI: http://localhost:3000
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Deploy to VPS:
```bash
# On your server (DigitalOcean, Linode, etc.)
git clone your-repo-url
cd aaro
docker-compose -f docker-compose.demo.yml up -d
```

## Option 3: Render.com (Two Services)

### Backend Service:
- **Type**: Web Service
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python -m uvicorn aboa.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  ```
  ENVIRONMENT=production
  SECRET_KEY=your-secret-key
  DATABASE_URL=sqlite:///./demo.db
  ```

### Frontend Service:
- **Type**: Static Site or Web Service
- **Build Command**: `echo "No build needed"`
- **Start Command**: `cd ui && python server.py`
- **Environment Variables**:
  ```
  API_BASE_URL=https://your-backend.onrender.com
  ```

## 📋 What Recruiters Will See

**Live Demo Experience:**
- ✅ Full interactive dashboard (exactly like localhost:3000)
- ✅ Real-time data updates
- ✅ Pipeline risk monitoring
- ✅ AI decision approvals
- ✅ Action execution with feedback
- ✅ Data input forms
- ✅ Configuration management
- ✅ Observability metrics

**URLs to Share:**
- **Main UI**: `https://your-app.railway.app` or `https://your-ui.onrender.com`
- **API Docs**: `https://your-api.railway.app/docs`
- **Health Check**: `https://your-api.railway.app/health`

## 🔧 Quick Deploy Commands

### Railway (Easiest):
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Docker Compose (VPS):
```bash
# One command deployment
docker-compose -f docker-compose.demo.yml up -d
```

## 🎯 Demo Script for Recruiters

**"This is a full-stack AI system I built for revenue operations:**

1. **Show Overview Dashboard** - Real-time metrics and KPIs
2. **Pipeline Risk Monitor** - AI detecting stalled deals
3. **AI Decisions** - Intelligent recommendations with approval workflow
4. **Action Execution** - Automated CRM actions with human oversight
5. **Data Management** - Full CRUD operations for deals, playbooks, team
6. **Observability** - System health and performance metrics

**Technical highlights:**
- Python FastAPI backend with async processing
- Interactive JavaScript frontend with real-time updates
- Docker containerization for easy deployment
- RESTful APIs with OpenAPI documentation
- Event-driven architecture with proper error handling
- Production-ready with health checks and monitoring"

## 🚀 Next Steps

1. **Choose deployment method** (Railway recommended for simplicity)
2. **Deploy both services** (API + UI)
3. **Test the full workflow** 
4. **Share live URLs** with recruiters
5. **Prepare demo talking points**

The deployed system will work exactly like your localhost experience!