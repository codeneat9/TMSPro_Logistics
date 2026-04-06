# TMSPro Logistics - Complete Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                           FRONTEND LAYER                        │
├──────────────────────────┬──────────────────────┬───────────────┤
│  Customer Mobile App     │   Logistics Mobile   │  Web Dashboard│
│  (React Native/Expo)     │   (React Native)     │  (React.js)   │
│  - Tracking              │   - Fleet Mgmt       │  - Analytics  │
│  - Notifications         │   - Rerouting       │  - KPI        │
│  - Delivery Status       │   - Performance     │  - Reports    │
└──────────────────────────┴──────────────────────┴───────────────┘
                                    ↓ (HTTP + WebSocket)
┌─────────────────────────────────────────────────────────────────┐
│                      SHARED LAYER (Mobile)                      │
├──────────────────┬─────────────┬──────────────┬─────────────────┤
│   Auth Service   │  API Client │    Utils     │  State/Context  │
│  (Firebase Auth) │  (Axios)    │   (Helpers)  │  (Redux/Context)│
└──────────────────┴─────────────┴──────────────┴─────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                          BACKEND LAYER                          │
│                       (FastAPI + WebSocket)                     │
├──────────────────┬──────────────┬──────────────┬────────────────┤
│  HTTP Endpoints  │  WebSocket   │  Task Queue  │  Background    │
│  (REST API)      │  (Socket.io) │  (Celery)    │  Jobs          │
└──────────────────┴──────────────┴──────────────┴────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                       SERVICE LAYER                             │
├────────────┬──────────┬────────────┬──────────┬─────────────────┤
│   Auth     │ Routing  │  Traffic   │ Tracking │ Analytics       │
│ (Firebase) │ (OSRM)   │ (OpenMap)  │ (Geo)    │ (Processing)    │
└────────────┴──────────┴────────────┴──────────┴─────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                      DATA ACCESS LAYER                          │
├──────────────────┬──────────────┬──────────────┬────────────────┤
│  PostgreSQL      │    Redis     │  File Store  │  Cache Layer   │
│  (Primary DB)    │  (Cache)     │  (Logs)      │  (Upstash)     │
└──────────────────┴──────────────┴──────────────┴────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL INTEGRATIONS                        │
├──────────┬────────────────┬──────────┬──────────┬───────────────┤
│ Firebase │ OpenStreetMap  │  OSRM    │ Mapbox   │ SMS/Email     │
│ (Auth)   │ (Map tiles)    │ (Routing)│ (Backup) │ (Notifications)
└──────────┴────────────────┴──────────┴──────────┴───────────────┘
```

---

## Technology Stack (FREE TIER)

### Frontend
- **Mobile**: React Native (Expo) - iOS/Android from single codebase
- **Web**: React.js - Analytics dashboard
- **State**: Redux Toolkit - Predictable state management
- **Maps**: Leaflet + OpenStreetMap - Free, privacy-focused
- **Maps Routing**: OSRM (Open Source Routing Machine) - Free routing
- **Charts**: Recharts - Lightweight, React-native compatible
- **Forms**: React Hook Form + Yup - Validation
- **UI Components**: React Native Paper / Tailwind CSS

### Backend
- **Framework**: FastAPI (existing)
- **Database**: PostgreSQL + Supabase (free tier: 2GB, 1M rows)
- **Cache**: Redis + Upstash (free tier: 10K commands/day)
- **Real-time**: Socket.io + python-socketio
- **Task Queue**: Celery + Redis (background processing)
- **ORM**: SQLAlchemy - Database abstraction
- **Auth**: Firebase Auth + JWT tokens
- **Routing**: OSRM API (self-hosted or public)

### Deployment
- **Hosting**: Render (free tier: 1 free service, 0.5GB RAM)
- **Database**: Supabase (PostgreSQL, free tier)
- **Cache**: Upstash (Redis, free tier)
- **Storage**: Render built-in (read-only filesystem)

---

## Database Schema

### Core Tables

#### `users`
```sql
id (PK) | email | password_hash | role (customer|driver|admin) | 
phone | created_at | updated_at | is_active
```

#### `trips`
```sql
id (PK) | user_id (FK) | driver_id (FK) | status (pending|assigned|in_transit|completed|cancelled) |
pickup_lat | pickup_lon | destination_lat | destination_lon |
promised_delivery_time | actual_delivery_time | created_at | updated_at
```

#### `locations` (high-frequency updates)
```sql
id (PK) | trip_id (FK) | vehicle_id (FK) | 
lat | lon | accuracy | speed | heading | timestamp (INDEX)
```

#### `routes`
```sql
id (PK) | trip_id (FK) | route_type (primary|alt1|alt2) |
distance_m | duration_s | polyline (geometry) | risk_score | 
created_at
```

#### `drivers`
```sql
id (PK) | user_id (FK) | vehicle_id (FK) | 
status (active|on_break|offline) | rating | trips_completed |
avg_delay_mins | created_at | updated_at
```

#### `vehicles`
```sql
id (PK) | registration | license_plate | capacity_kg | 
current_load_kg | status (active|maintenance|offline) | 
created_at | updated_at
```

#### `notifications`
```sql
id (PK) | user_id (FK) | trip_id (FK) | 
title | message | type (alert|update|info) | 
read (boolean) | read_at | created_at
```

#### `analytics`
```sql
id (PK) | trip_id (FK) | driver_id (FK) |
predicted_delay_mins | actual_delay_mins | 
route_taken | cost | efficiency_score | created_at
```

#### `feedback`
```sql
id (PK) | trip_id (FK) | user_id (FK) | driver_id (FK) |
rating (1-5) | comment | created_at
```

#### `geofences`
```sql
id (PK) | company_id (FK) | name | center_lat | center_lon | 
radius_m | type (alert|zone|restricted) | created_at
```

#### `compliance_logs`
```sql
id (PK) | trip_id (FK) | driver_id (FK) | 
event_type | details (JSON) | timestamp
```

#### `api_keys`
```sql
id (PK) | user_id (FK) | key_hash | scope (read|write|admin) | 
active (boolean) | created_at | expires_at
```

---

## API Endpoint Structure

### Auth (Firebase)
```
POST   /api/auth/register         → Create user
POST   /api/auth/login            → Create session
POST   /api/auth/refresh-token    → Refresh JWT
POST   /api/auth/logout           → Destroy session
POST   /api/auth/verify-email     → Email verification
```

### Trips
```
GET    /api/trips                 → List user's trips
POST   /api/trips                 → Create new trip
GET    /api/trips/{id}            → Get trip details
PATCH  /api/trips/{id}            → Update trip
GET    /api/trips/{id}/tracking   → Real-time location
POST   /api/trips/{id}/complete   → Mark completed
```

### Routes
```
POST   /api/trips/{id}/routes     → Plan routes (calls OSRM)
GET    /api/trips/{id}/routes     → Get all routes
POST   /api/trips/{id}/reroute    → Accept/reject reroute
GET    /api/routes/{route_id}     → Get route details
```

### Drivers
```
GET    /api/drivers               → List drivers (admin)
GET    /api/drivers/me            → Current driver info
PATCH  /api/drivers/me            → Update driver status
GET    /api/drivers/{id}/metrics  → Performance data
POST   /api/drivers/{id}/location → Send GPS location
```

### Locations (Real-time)
```
POST   /api/locations             → Create location record
GET    /api/locations/{trip_id}   → Trip location history
WebSocket: /ws/locations/{trip_id} → Live location stream
```

### Notifications
```
GET    /api/notifications         → User's notifications
POST   /api/notifications/{id}/read → Mark as read
DELETE /api/notifications/{id}    → Delete notification
WebSocket: /ws/notifications      → Real-time notification stream
```

### Analytics
```
GET    /api/analytics/kpis        → Overall KPIs
GET    /api/analytics/routes      → Route performance
GET    /api/analytics/drivers     → Driver metrics
GET    /api/analytics/delays/heatmap → Delay zones
GET    /api/analytics/reports     → Generated reports
```

### Geofences
```
POST   /api/geofences             → Create geofence
GET    /api/geofences             → List geofences
DELETE /api/geofences/{id}        → Delete geofence
WebSocket: /ws/geofences/{trip_id} → Geofence events
```

---

## WebSocket Events

### Location Updates
```
Location.Create      → Driver sends GPS
Location.Update      → Periodic updates
Location.Geofence    → Enters/exits geofence
```

### Trip Events
```
Trip.Created         → New trip assigned
Trip.StatusChanged   → Status update (in_transit → completed)
Trip.Delayed         → Delay predicted
Trip.Rerouting       → AI recommends reroute
```

### Notifications
```
Alert.Urgent         → Critical situation
Alert.FuelingNeeded   → Fuel warning
Alert.MaintenanceDue  → Service needed
```

### Driver Events
```
Driver.Available      → Driver goes online
Driver.Busy           → Driver accepts trip
Driver.Break          → Driver on break
Driver.Offline        → Driver goes offline
```

---

## Deployment Targets

### Development
- Backend: `localhost:8000` (FastAPI)
- Frontend: `localhost:3000` (React)
- Mobile: Expo Go app on device

### Staging (Render Free Tier)
- Backend: `https://tmspro-api-staging.onrender.com`
- Database: Supabase (PostgreSQL)
- Cache: Upstash (Redis)
- WebSocket: Same backend (Socket.io)

### Production (Render Free Tier + Upgrades)
- Backend: `https://api.tmspro-logistics.com`
- Web Dashboard: `https://dashboard.tmspro-logistics.com`
- Mobile: Expo CDN + App Store/Play Store
- Database: Supabase PostgreSQL (paid tier for scale)
- Cache: Upstash Redis (paid tier for scale)

---

## File Structure

```
project/
├── cloud/                   (existing FastAPI backend)
│   ├── app.py
│   ├── dashboard_api.py
│   ├── routing_api.py
│   ├── traffic_api.py
│   ├── feature_builder.py
│   └── mobile_sync_api.py
│
├── backend/                 (NEW - Enhanced backend)
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/              (SQLAlchemy ORM models)
│   ├── schemas/             (Pydantic request/response)
│   ├── routes/              (API endpoints)
│   ├── services/            (Business logic)
│   ├── websocket/           (Socket.io handlers)
│   ├── tasks/               (Celery background jobs)
│   └── migrations/          (Alembic DB versions)
│
├── mobile/
│   ├── customer/            (Customer React Native app)
│   ├── logistics/           (Logistics React Native app)
│   ├── shared/              (Shared auth, API, utils)
│   └── package.json
│
├── web-dashboard/           (NEW - React web dashboard)
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── store/           (Redux)
│   │   ├── services/
│   │   └── App.js
│   └── package.json
│
├── analytics/               (NEW - Separate analytics service)
│   ├── models/
│   ├── services/
│   └── main.py
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API_INTEGRATION.md
│   ├── DEPLOYMENT.md
│   ├── FEATURES_CHECKLIST.md
│   └── DATABASE_SCHEMA.md
│
├── docker-compose.yml       (Local development)
├── docker-compose.prod.yml  (Production)
├── requirements-backend.txt
├── requirements-mobile.txt
└── .env.example
```

---

## Development Workflow

1. **Backend Development**
   - Create models in `backend/models/`
   - Define schemas in `backend/schemas/`
   - Implement routes in `backend/routes/`
   - Add services in `backend/services/`
   - Set up WebSocket handlers in `backend/websocket/`

2. **Mobile Development**
   - Build screens in `mobile/[customer|logistics]/screens/`
   - Create components in `mobile/[customer|logistics]/components/`
   - Use shared API client from `mobile/shared/api/`
   - Manage state with context/Redux

3. **Web Dashboard**
   - Create pages in `web-dashboard/pages/`
   - Build components in `web-dashboard/components/`
   - Connect to backend APIs
   - Use Redux for state

4. **Testing**
   - Unit tests for services
   - Integration tests for APIs
   - E2E tests for critical flows

---

## Security Considerations

- **Firebase Auth**: Secure user authentication
- **JWT Tokens**: API authentication + authorization
- **HTTPS Only**: All external communication encrypted
- **CORS**: Configured for frontend origins only
- **Rate Limiting**: Protect endpoints from abuse
- **Input Validation**: Pydantic schemas validate all inputs
- **SQL Injection**: SQLAlchemy ORM prevents attacks
- **Secrets Management**: Environment variables in `.env`

---

## Scalability Notes

- **PostgreSQL**: Can scale to millions of rows with proper indexing
- **Redis**: In-memory caching for frequent queries
- **WebSocket**: Socket.io handles thousands of concurrent connections
- **Celery**: Background tasks prevent blocking main thread
- **CDN**: Static assets cached globally (for web/mobile assets)

---

## Performance Targets

- API Response Time: < 200ms
- WebSocket Message Latency: < 100ms
- Database Query Time: < 50ms (with indexes)
- Mobile App Load Time: < 2s
- Web Dashboard Load Time: < 1s
