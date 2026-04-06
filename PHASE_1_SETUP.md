# Phase 1: Backend Infrastructure Setup Guide

## 🎯 Phase 1 Objectives (Week 1-2)
- ✅ **Days 1-2**: Setup cloud services (Supabase + Upstash + Firebase)
- ✅ **Days 3-4**: Database setup & ORM models
- ✅ **Days 5-6**: Authentication endpoints (register, login, refresh, logout)
- ✅ **Days 7-8**: Core CRUD endpoints (trips, routes, drivers, locations)
- ✅ **Days 9-10**: WebSocket setup for real-time location streaming
- ✅ **Days 11-14**: Testing, fixes, deployment to Render

---

## 📋 Prerequisites

### System Requirements
- Python 3.10+ (Windows, Mac, Linux)
- PostgreSQL client tools (for Supabase)
- Git (already installed)
- Node.js (for Firebase CLI, later phases)

### Accounts Needed
- GitHub (✅ you have this)
- Supabase (free tier signup at https://supabase.com)
- Upstash (free tier signup at https://console.upstash.com)
- Firebase (free tier signup at https://console.firebase.google.com)
- Render (free tier signup at https://render.com)

---

## 🔧 Step 1: Install Python Dependencies (30 mins)

### 1.1 Create Virtual Environment
```powershell
cd c:\Users\Bruger\embedded-tms-ai

# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 1.2 Install Required Packages
```powershell
pip install --upgrade pip

# Core FastAPI
pip install fastapi uvicorn python-multipart

# Database
pip install sqlalchemy psycopg2-binary alembic

# Data validation
pip install pydantic pydantic-settings email-validator

# Authentication
pip install pyJWT python-jose passlib

# Firebase
pip install firebase-admin

# Redis client
pip install redis aioredis

# WebSocket
pip install python-socketio python-engineio aiohttp

# Environment variables
pip install python-dotenv

# Utilities
pip install python-dateutil requests httpx

# Development tools (optional but recommended)
pip install black flake8 pytest pytest-asyncio
```

### 1.3 Verify Installation
```powershell
python -c "import fastapi; print(fastapi.__version__)"
python -c "import sqlalchemy; print(sqlalchemy.__version__)"
python -c "import redis; print(redis.__version__)"
```

Expected output: Version numbers should print without errors.

---

## ☁️ Step 2: Setup Supabase (PostgreSQL Database) - 10 mins

### 2.1 Create Supabase Project
1. Go to https://supabase.com/dashboard
2. Click "New Project"
3. **Project name**: `tmspro`
4. **Database password**: Create a strong password (save it!)
5. **Region**: Choose closest to your location
6. Click "Create new project"
7. Wait 3-5 minutes for database initialization

### 2.2 Get Connection Details
After project is ready:
1. Go to **Settings** → **Database**
2. Find **Connection String** section
3. Select **Postgres** tab
4. Copy the full connection string
5. Replace `[YOUR-PASSWORD]` with your database password
6. Save this string - you'll need it for `.env.backend`

Example:
```
postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
```

### 2.3 Setup Tables
1. In Supabase dashboard, go to **SQL Editor**
2. Click **New Query**
3. Copy ALL of the SQL from [docs/DATABASE_SCHEMA.md](../docs/DATABASE_SCHEMA.md)
4. Paste into SQL editor
5. Click **Run**
6. Wait for all tables to be created

**Verify tables created:**
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
```

Should show: users, drivers, vehicles, trips, routes, locations, notifications, feedback, analytics, geofences, compliance_logs, api_keys

---

## 🔴 Step 3: Setup Upstash (Redis Cache) - 5 mins

### 3.1 Create Upstash Database
1. Go to https://console.upstash.com/redis
2. Click **Create Database**
3. **Database name**: `tmspro-cache`
4. **Region**: Choose closest to your location
5. Click **Create**

### 3.2 Get Connection Details
After database is created:
1. Copy the **UPSTASH_REDIS_REST_URL**
2. Copy the **UPSTASH_REDIS_REST_TOKEN**
3. Construct the Redis URL:
```
redis://default:[TOKEN]@[HOST]:[PORT]
```

Or use the REST endpoint provided.

---

## 🔐 Step 4: Setup Firebase (Authentication & FCM) - 10 mins

### 4.1 Create Firebase Project
1. Go to https://console.firebase.google.com
2. Click **Create a project**
3. **Project name**: `tmspro`
4. Choose **Analytics location**: Your country
5. Click **Create project**
6. Wait 1-2 minutes

### 4.2 Setup Authentication
1. In left sidebar, go to **Build** → **Authentication**
2. Click **Get Started**
3. Enable **Email/Password** provider
4. Click **Save**

### 4.3 Generate Service Account Key
1. Go to **Project Settings** (⚙️ icon, top right)
2. Click **Service Accounts** tab
3. Click **Generate New Private Key**
4. Save the JSON file securely
5. Copy the contents - you'll need them for `.env.backend`

### 4.4 Get Project ID
In **Project Settings** → **General**:
- Copy **Project ID** (e.g., `tmspro-xxxxx`)
- Copy other Firebase config values

---

## 🔑 Step 5: Create Environment Variables File

### 5.1 Create `.env.backend` File
In `c:\Users\Bruger\embedded-tms-ai\`, create file `.env.backend`:

```bash
# Application
APP_NAME=TMSPro Backend
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Database - From Supabase
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres

# Redis - From Upstash
REDIS_URL=redis://default:[TOKEN]@[HOST]:[PORT]

# Firebase - From service account JSON
FIREBASE_PROJECT_ID=tmspro-xxxxx
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@tmspro-xxxxx.iam.gserviceaccount.com

# JWT
JWT_SECRET=your-super-secret-key-change-in-production-12345
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
JWT_REFRESH_EXPIRATION_DAYS=30

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001","http://localhost:8000","http://localhost:19000"]

# Feature flags
ENABLE_LOCATION_STREAMING=true
ENABLE_REROUTE_RECOMMENDATIONS=true
ENABLE_DELAY_PREDICTIONS=true
ENABLE_GEOFENCING=true
```

⚠️ **IMPORTANT**: Add `.env.backend` to `.gitignore` to prevent exposing secrets!

### 5.2 Create `.env.mobile` File (for later)
Save for Phase 2 when building mobile app.

---

## 🚀 Step 6: Fix Import Issues

The SQLAlchemy models have circular imports. We need to fix the import in `backend/models/user.py` (and all models):

In each model file, change:
```python
from database import Base
```

To:
```python
from backend.database import Base
```

Execute this PowerShell script:
```powershell
# Fix all model imports
$files = Get-ChildItem -Path .\backend\models -Filter "*.py" -Exclude "__init__.py", "database.py"
foreach($file in $files) {
    (Get-Content $file.FullName) -replace "from database import Base", "from backend.database import Base" | Set-Content $file.FullName
}
```

Or manually edit each file in `backend/models/`:
- user.py
- driver.py
- vehicle.py
- trip.py
- route.py
- location.py
- notification.py
- feedback.py
- analytics.py
- geofence.py
- compliance_log.py
- api_key.py

---

## 🧪 Step 7: Test Local Setup

### 7.1 Verify Database Connection
```powershell
# Still in venv
python -c "
from backend.database import SessionLocal
db = SessionLocal()
print('✅ Database connection successful!')
"
```

### 7.2 Initialize Database Tables
```powershell
python -c "
from backend.database import init_db
init_db()
print('✅ Database tables created!')
"
```

### 7.3 Start Development Server
```powershell
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 7.4 Test API Health
Open browser or use curl:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "app": "TMSPro Backend",
  "version": "1.0.0",
  "environment": "development"
}
```

---

## 📝 What's Done vs What's Next

### ✅ Done (Days 1-2)
- [x] Backend structure created
- [x] SQLAlchemy ORM models (12 tables)
- [x] Pydantic schemas for validation
- [x] FastAPI app initialized
- [x] Configuration system
- [x] Database setup

### ⏭️ Next (Days 3-4)
Build authentication system:
1. Create auth routes (`backend/routes/auth.py`):
   - `POST /api/auth/register` - User registration
   - `POST /api/auth/login` - User login (returns JWT)
   - `POST /api/auth/refresh-token` - Refresh JWT token
   - `POST /api/auth/logout` - Logout

2. Create auth service (`backend/services/auth.py`):
   - Password hashing with bcrypt
   - JWT token generation
   - Token verification

3. Create auth middleware:
   - `@require_auth` decorator
   - Firebase token verification

### ⏭️ Then (Days 5-6)
Build core API endpoints:
- `backend/routes/trips.py` - Trip CRUD
- `backend/routes/routes.py` - Route management
- `backend/routes/drivers.py` - Driver management
- `backend/routes/locations.py` - Location tracking

### ⏭️ Then (Days 7-8)
WebSocket real-time features:
- Location streaming (`/ws/locations/{trip_id}`)
- Notifications (`/ws/notifications`)
- Live fleet tracking

---

## 🐛 Troubleshooting

### Import Error: "No module named 'backend'"
**Solution**: Make sure you're running commands from project root and uvicorn sees the module.
```powershell
# Run from project root
cd c:\Users\Bruger\embedded-tms-ai
python -m uvicorn backend.main:app --reload
```

### Database Connection Failed
**Solution**: Check your `.env.backend` DATABASE_URL is correct.
```powershell
python -c "
from backend.config import settings
print(f'URL: {settings.DATABASE_URL}')
"
```

### Pydantic Validation Errors
**Solution**: Install the correct pydantic version.
```powershell
pip install pydantic==2.0.0 pydantic-settings
```

### Port 8000 Already in Use
**Solution**: Use a different port.
```powershell
uvicorn backend.main:app --reload --port 8001
```

---

## ✨ Next: Automated Deployment (Optional for Phase 1)

Want to deploy to Render now (for testing)?

See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) section **"Docker + Render Deployment"** for steps.

Estimated time: 15-20 mins to deploy a working backend!

---

## 📞 Questions?

Refer to:
- [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System design
- [docs/DATABASE_SCHEMA.md](../docs/DATABASE_SCHEMA.md) - Full SQL schema
- [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) - Production deployment

New API routes will be added over the next 13 days. Come back to this guide as reference!

