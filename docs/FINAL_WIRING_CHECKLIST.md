# Final Wiring Checklist (Backend + Expo)

## 1) Backend Environment

Update `.env.backend` with:

- `DATABASE_URL` (Supabase/Postgres or local sqlite)
- `JWT_SECRET` (32+ chars)
- Optional SMS:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_FROM_NUMBER`

Optional push and infra:

- `REDIS_URL`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_PRIVATE_KEY`
- `FIREBASE_CLIENT_EMAIL`

## 2) Mobile Environment

Create `mobile-expo-demo/.env` from `mobile-expo-demo/.env.example`.

Set:

- `EXPO_PUBLIC_API_BASE_URL=http://<your-laptop-ip>:8000`
- `EXPO_PUBLIC_TOMTOM_API_KEY=<optional>`

## 3) Start Backend

```powershell
Set-Location c:/Users/Bruger/embedded-tms-ai
C:/Users/Bruger/AppData/Local/Programs/Python/Python314/python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Health check:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/health
```

## 4) Start Expo App

```powershell
Set-Location c:/Users/Bruger/embedded-tms-ai/mobile-expo-demo
npx expo start --offline --port 8083
```

Scan QR in Expo Go.

## 5) Expected End-to-End Behavior

- Sign up creates user in backend DB.
- Sign in fetches `/api/auth/me` and persists tokens locally.
- Trip creation:
  - User enters source/destination addresses (empty by default).
  - OSM geocoding + OSRM alternatives are fetched.
  - Weather auto-fetched (Open-Meteo).
  - Traffic auto-fetched (TomTom if key exists).
- Dashboard shows:
  - Source/destination markers on OSM map.
  - Route alternatives and telemetry.
- Notifications:
  - In-app banners and local fallback alerts.
  - SMS endpoint called for trip updates.

## 6) SMS Verification

If Twilio keys are missing, SMS endpoint responds:

- `sent: false`
- `result: "twilio_not_configured"`

Once Twilio keys are configured, updates are sent to user phone.

## 7) Already Validated in this session

- Backend health endpoint returned `healthy`.
- Auth register + protected SMS endpoint path works.
- SMS path currently returns `twilio_not_configured` until Twilio credentials are set.
- Expo Android bundle compiles after all changes.
