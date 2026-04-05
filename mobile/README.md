# TMS Logistics Mobile App

This is a React Native (Expo) mobile app for the logistics workflow.

## Features

- Plan shipment trip from mobile against existing backend endpoint: `POST /dashboard/plan-trip`
- Logistics KPIs: dispatch priority, SLA slack/status, load utilization
- Shipment workflow stages: Assigned -> At Pickup -> Picked Up -> In Transit -> Delivered
- Operational alert feed in-app

## Run

From project root:

```powershell
cd mobile
npm install
npm run start
```

Then open on:
- Android emulator (`a` in Expo terminal)
- iOS simulator (`i` in Expo terminal, macOS only)
- Physical device via Expo Go by scanning QR

## Important API URL Note

Inside the app, set **API Base URL** correctly:

- Emulator (Android): `http://10.0.2.2:8000`
- Same machine web/native bridge: `http://127.0.0.1:8000`
- Physical device: use your PC LAN IP, e.g. `http://192.168.1.20:8000`

Backend must be running:

```powershell
cd ..
python start_server.py
```

## Backend compatibility

The app is already wired to your current FastAPI response shapes:
- `delay_probability` or `predicted_delay.probability`
- `primary_route`, `alternate_routes`
- `driver_notification` or `driver_alert`
