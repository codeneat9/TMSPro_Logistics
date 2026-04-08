# TMS Logistics Mobile App

This is the mobile app for the logistics workflow.

Current state: Step 8 bare workflow kickoff is active and native projects are now present (`android/` and `ios/`).

## Features

- Plan shipment trip from mobile against existing backend endpoint: `POST /dashboard/plan-trip`
- Logistics KPIs: dispatch priority, SLA slack/status, load utilization
- Shipment workflow stages: Assigned -> At Pickup -> Picked Up -> In Transit -> Delivered
- Operational alert feed in-app

## Run (Bare Workflow)

From project root:

```powershell
cd mobile
npm install
npm run start
```

In separate terminals, run:

```powershell
npm run start
npm run android
```

For iOS (macOS only):

```bash
npm run ios
```

Migration notes are in:

- `STEP8_BARE_WORKFLOW_KICKOFF.md`

## Platform Support

- Android native build: supported from this Windows machine.
- iPhone native build: supported after opening this same `mobile/` project on macOS with Xcode.

### Android on Windows

Prerequisites:

- JDK 17
- Android Studio + Android SDK
- `platform-tools` available in `PATH` (`adb`)
- One emulator/device connected

Verify setup:

```powershell
adb devices
```

Run app:

```powershell
cd mobile
npm run start
npm run android
```

### iPhone on macOS

Prerequisites:

- Xcode (latest stable)
- CocoaPods
- iOS Simulator or a physical iPhone with developer signing configured

Run app:

```bash
cd mobile
npm install
cd ios && pod install && cd ..
npm run start
npm run ios
```

## Important API URL Note

Inside the app, set **API Base URL** correctly:

- Emulator (Android): `http://10.0.2.2:8000`
- Same machine web/native bridge: `http://127.0.0.1:8000`
- Physical device: use your PC LAN IP, e.g. `http://192.168.1.20:8000`

Backend must be running and reachable from emulator/device:

```powershell
cd ..
python start_server.py
```

## Backend compatibility

The app is already wired to your current FastAPI response shapes:
- `delay_probability` or `predicted_delay.probability`
- `primary_route`, `alternate_routes`
- `driver_notification` or `driver_alert`
