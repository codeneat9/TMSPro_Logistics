# API Integration & Deployment Guide

## Stack Configuration

### Backend (FastAPI)
```yaml
Framework: FastAPI (existing upgrade)
Database: PostgreSQL (Supabase free tier)
Cache: Redis (Upstash free tier)
Real-time: Socket.io (python-socketio)
Authentication: Firebase Auth + JWT
Hosting: Render (free tier)
```

### Mobile (React Native + Expo)
```yaml
Framework: React Native (Expo)
State: Redux Toolkit / Context API
Maps: Leaflet + OpenStreetMap
Auth: Firebase Auth
API Client: Axios
Notifications: Firebase Cloud Messaging
Distribution: Expo only
```

### Web (React.js)
```yaml
Framework: React.js
State: Redux Toolkit
UI: Material-UI / Tailwind CSS
Charts: Recharts
Maps: Leaflet + Mapbox
API Client: Axios
Hosting: Vercel / Netlify (free tier)
```

---

## Step-by-Step Setup

### 1. Backend Infrastructure Setup

#### 1.1 Supabase Database Setup (2GB FREE)
```bash
# Go to https://supabase.com
# Sign up with GitHub
# Create new project
# Wait for database to initialize (5-10 mins)

# Copy connection details:
# - DATABASE_URL: postgres://...
# - ANON_KEY: eyJ...
# - SERVICE_KEY: eyJ...

# In project, copy to .env.backend:
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
DATABASE_URL=postgres://user:password@db.supabase.co:5432/postgres
```

#### 1.2 Upstash Redis Setup (10K commands/day FREE)
```bash
# Go to https://upstash.com
# Sign up with GitHub
# Create new database
# Select free tier
# Copy connection details

# In .env.backend:
REDIS_URL=redis://default:password@host.upstash.io:port
```

#### 1.3 Firebase Setup (Authentication)
```bash
# Go to https://firebase.google.com
# Create new project
# Enable Authentication (Email/Password)
# Get Firebase config from Project Settings
# Download service account key as JSON

# In .env.backend:
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY=your-private-key
FIREBASE_CLIENT_EMAIL=your-client-email
```

### 2. Backend Code Enhancements

#### 2.1 Install Dependencies
```bash
cd c:\Users\Bruger\embedded-tms-ai

# Create backend requirements file
cat > requirements-backend.txt << 'EOF'
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
alembic==1.13.0
psycopg2-binary==2.9.9
redis==5.0.1
python-socketio==5.10.0
python-engineio==4.8.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
firebase-admin==6.2.0
pyjwt==2.8.1
bcrypt==4.1.1
aioredis==2.0.1
httpx==0.25.1
requests==2.31.0
# Routing
shapely==2.0.2
geopy==2.4.0
# Task Queue
celery==5.3.4
# CORS
fastapi-cors==0.0.6
# Validation
email-validator==2.1.0
# Utilities
python-multipart==0.0.6
click==8.1.7
EOF

pip install -r requirements-backend.txt
```

#### 2.2 Create Backend Structure
```bash
# Create backend directories
mkdir -p backend/{models,schemas,routes,services,websocket,tasks,migrations/versions}

# Create __init__.py files
touch backend/__init__.py backend/models/__init__.py backend/schemas/__init__.py backend/routes/__init__.py
```

#### 2.3 Create main.py
```python
# backend/main.py
from fastapi import FastAPI
from fastapi.cors import CORSMiddleware
import socketio
from contextlib import asynccontextmanager

# Initialize Socket.io
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=['*'],
)

app = FastAPI(title="TMSPro Logistics API", version="1.0.0")
app_asgi = socketio.ASGIApp(sio, app)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}

# Include Routes (will create these next)
# from backend.routes import auth, trips, drivers, routes, locations, notifications

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 2.4 Create config.py
```python
# backend/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # Firebase
    firebase_project_id: str
    firebase_private_key: str
    firebase_client_email: str
    
    # App
    app_name: str = "TMSPro Logistics API"
    debug: bool = False
    
    class Config:
        env_file = ".env.backend"

settings = Settings()
```

#### 2.5 Create database.py
```python
# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import settings

engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 3. Database Migration Setup

#### 3.1 Initialize Alembic
```bash
cd backend
alembic init migrations
```

#### 3.2 Configure alembic.ini
```python
# Edit backend/migrations/env.py
# Add:
from backend.database import Base
from backend import models  # Import all models

target_metadata = Base.metadata
```

#### 3.3 Run migrations
```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### 4. Create Core API Endpoints

#### 4.1 Authentication Routes (backend/routes/auth.py)
```python
from fastapi import APIRouter, Depends, HTTPException
from backend.database import get_db
from backend.schemas import UserRegisterRequest, UserLoginRequest
import firebase_admin
from firebase_admin import auth

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/register")
async def register(user: UserRegisterRequest, db = Depends(get_db)):
    """Create user account"""
    try:
        firebase_user = auth.create_user(
            email=user.email,
            password=user.password,
            display_name=user.full_name
        )
        # Create in PostgreSQL
        # Save user to DB
        return {"uid": firebase_user.uid, "email": firebase_user.email}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(user: UserLoginRequest):
    """Authenticate user"""
    # Verify with Firebase
    # Return JWT token
    pass

@router.post("/refresh-token")
async def refresh_token(token: str):
    """Refresh JWT token"""
    pass
```

#### 4.2 Trips Routes (backend/routes/trips.py)
```python
from fastapi import APIRouter, Depends
from backend.database import get_db
from backend.schemas import TripCreate, TripUpdate

router = APIRouter(prefix="/api/trips", tags=["Trips"])

@router.get("")
async def list_trips(db = Depends(get_db)):
    """Get user's trips"""
    pass

@router.post("")
async def create_trip(trip: TripCreate, db = Depends(get_db)):
    """Create new trip"""
    # Call existing /dashboard/plan-trip logic
    # Return trip with routes
    pass

@router.get("/{trip_id}")
async def get_trip(trip_id: str, db = Depends(get_db)):
    """Get trip details"""
    pass

@router.patch("/{trip_id}")
async def update_trip(trip_id: str, trip: TripUpdate, db = Depends(get_db)):
    """Update trip"""
    pass

@router.get("/{trip_id}/locations")
async def get_locations(trip_id: str, db = Depends(get_db)):
    """Get location history"""
    pass
```

### 5. WebSocket Setup

#### 5.1 Socket.io Handlers (backend/websocket/handlers.py)
```python
from backend.main import sio
import json

# Location tracking
@sio.event
async def connect(sid, environ):
    """Client connects"""
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    """Client disconnects"""
    print(f"Client disconnected: {sid}")

@sio.on('location:update')
async def handle_location(data):
    """Receive location from driver"""
    # {trip_id, lat, lon, speed, heading}
    # Save to locations table
    # Broadcast to customers watching this trip
    await sio.emit('location:broadcast', data, room=f"trip_{data['trip_id']}", skip_sid=True)

@sio.on('join:trip')
async def join_trip(sid, data):
    """Join trip room for real-time updates"""
    # Join socket.io room named "trip_{trip_id}"
    sio.enter_room(sid, f"trip_{data['trip_id']}")
    print(f"User {sid} joined trip {data['trip_id']}")
```

#### 5.2 Connect WebSocket to Main App
```python
# In backend/main.py, add:
from backend.websocket import handlers  # This imports and registers handlers
```

---

## Mobile App Setup

### 1. Customer Mobile App Structure

```bash
# Navigate to customer app
cd mobile/customer

# Create package.json
cat > package.json << 'EOF'
{
  "name": "tmspro-customer",
  "version": "1.0.0",
  "main": "App.js",
  "scripts": {
    "start": "expo start",
    "android": "expo start --android",
    "ios": "expo start --ios",
    "eject": "expo eject"
  },
  "dependencies": {
    "react": "18.2.0",
    "react-native": "0.72.0",
    "expo": "~49.0.0",
    "react-native-maps": "1.3.2",
    "@react-navigation/native": "6.1.9",
    "@react-navigation/bottom-tabs": "6.5.11",
    "axios": "1.6.2",
    "firebase": "10.3.1",
    "redux": "4.2.1",
    "@reduxjs/toolkit": "1.9.7",
    "react-redux": "8.1.3",
    "react-native-paper": "5.12.3",
    "react-native-vector-icons": "10.0.0",
    "socket.io-client": "4.7.2"
  }
}
EOF

npm install
```

### 2. Configure Firebase in Mobile Apps

```javascript
// mobile/shared/services/firebase.js
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getMessaging } from 'firebase/messaging';

const firebaseConfig = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.REACT_APP_FIREBASE_APP_ID,
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const messaging = getMessaging(app);
```

### 3. Create API Client

```javascript
// mobile/shared/api/client.js
import axios from 'axios';
import { getAuth } from 'firebase/auth';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

// Add Firebase token to all requests
client.interceptors.request.use(async (config) => {
  const auth = getAuth();
  if (auth.currentUser) {
    const token = await auth.currentUser.getIdToken();
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default client;
```

---

## Web Dashboard Setup

### 1. React Project Setup
```bash
npx create-react-app web-dashboard
cd web-dashboard

npm install \
  react-redux @reduxjs/toolkit \
  react-router-dom \
  recharts \
  leaflet react-leaflet \
  firebase \
  axios \
  react-icons \
  tailwindcss
```

### 2. Create Redux Store

```javascript
// web-dashboard/src/store/slices/authSlice.js
import { createSlice } from '@reduxjs/toolkit';

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user: null,
    loading: false,
    error: null,
  },
  reducers: {
    setUser: (state, action) => {
      state.user = action.payload;
    },
    logout: (state) => {
      state.user = null;
    },
  },
});

export const { setUser, logout } = authSlice.actions;
export default authSlice.reducer;
```

---

## Deployment on Render

### 1. Prepare Backend for Deployment

#### 1.1 Create render.yaml
```yaml
services:
  - type: web
    name: tmspro-backend
    env: python
    plan: free
    buildCommand: |
      pip install -r requirements-backend.txt
      alembic upgrade head
    startCommand: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        scope: run
        value: ${DATABASE_URL} # From Supabase
      - key: REDIS_URL
        scope: run
        value: ${REDIS_URL} # From Upstash
      - key: FIREBASE_PROJECT_ID
        scope: run
        value: ${FIREBASE_PROJECT_ID}
```

#### 1.2 Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

COPY . .

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Deploy Backend
```bash
# Commit and push to GitHub
git add .
git commit -m "feat: Complete backend infrastructure setup"
git push origin master

# On Render:
# 1. Go to https://dashboard.render.com
# 2. Click "New +" → "Web Service"
# 3. Connect GitHub repository
# 4. Select runtime: Python
# 5. Build command: pip install -r requirements-backend.txt && alembic upgrade head
# 6. Start command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
# 7. Add environment variables (DATABASE_URL, REDIS_URL, etc)
# 8. Deploy
```

### 3. Deploy Web Dashboard
```bash
# Build for production
cd web-dashboard
npm run build

# Deploy to Vercel or Netlify (free tier)
# Or deploy to Render as static site
```

---

## Environment Files

### .env.backend
```
# Database
DATABASE_URL=postgres://user:password@db.supabase.co:5432/postgres

# Redis
REDIS_URL=redis://default:password@host.upstash.io:port

# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@project.iam.gserviceaccount.com

# App
DEBUG=False
API_URL=https://your-api.onrender.com
```

### .env.mobile
```
REACT_APP_API_URL=https://your-api.onrender.com/api
REACT_APP_FIREBASE_API_KEY=AIzaSy...
REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=your-project-id
REACT_APP_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=123456789
REACT_APP_FIREBASE_APP_ID=1:123456789:web:...
```

---

## Testing the Full Stack

### 1. Local Development
```bash
# Terminal 1: Run backend
cd backend
uvicorn main:app --reload

# Terminal 2: Run mobile app
cd mobile/customer
expo start

# Terminal 3: Run web dashboard
cd web-dashboard
npm start
```

### 2. Test Flow
1. Register user via mobile/web
2. Create trip (call /api/trips POST)
3. Check trip in database (SELECT * FROM trips)
4. Driver sends location (POST /api/locations)
5. Customer receives update via WebSocket
6. Check analytics dashboard

---

## Monitoring

### Render Monitoring
- Logs: Visit deployment in Render dashboard → Logs
- Metrics: CPU, Memory, Requests visible in dashboard
- Alerts: Set up email alerts

### Supabase Monitoring
- Database health: https://supabase.com dashboard
- Query performance: Via Supabase Studio
- Backups: Automatic daily

### Error Tracking (Optional)
```bash
# Add Sentry for error tracking
pip install sentry-sdk

# In main.py:
import sentry_sdk
sentry_sdk.init("your-sentry-dsn")
```

---

## Documentation Checklist

- [ ] API Endpoint documentation (Swagger)
- [ ] Database schema diagram
- [ ] Architecture diagrams
- [ ] Deployment guide
- [ ] Troubleshooting guide
- [ ] Contributing guide
- [ ] Security best practices
