# Step 8 Kickoff: React Native CLI Bare Workflow

This project is now configured to run from React Native CLI scripts first.

## What Was Changed

- `main` entry switched to `index.js` in `package.json`
- New native entry file `index.js` added with `AppRegistry.registerComponent`
- Scripts switched to:
  - `npm run start` -> Metro via React Native CLI
  - `npm run ios` -> native iOS run
  - `npm run android` -> native Android run
- Legacy Expo scripts were preserved under `legacy:expo:*` for transition safety
- Added required dev dependency: `@react-native/metro-config`

## One-Time Native Project Bootstrap

Run these commands from the `mobile` folder.

```powershell
# 1) Ensure dependencies are installed
npm install

# 2) Generate native ios/android folders from current app code
npx react-native@latest init TmsNativeShell --version 0.76.0 --skip-install

# 3) Copy generated native folders into this project root
Copy-Item -Recurse -Force .\TmsNativeShell\android .\android
Copy-Item -Recurse -Force .\TmsNativeShell\ios .\ios
Copy-Item -Force .\TmsNativeShell\metro.config.js .\metro.config.js
Copy-Item -Force .\TmsNativeShell\react-native.config.js .\react-native.config.js

# 4) Cleanup temp shell
Remove-Item -Recurse -Force .\TmsNativeShell
```

## iOS Setup Notes

```powershell
cd ios
pod install
cd ..
npm run ios
```

## Android Setup Notes

```powershell
npm run android
```

If Android run fails, ensure these are configured on Windows:

- Android SDK + platform tools installed
- `adb` available on PATH
- At least one Android emulator (AVD) created or a physical device connected
- JDK installed and `JAVA_HOME` set

## Migration Guardrails

- Keep using existing app code in `App.js`, `customer/`, `logistics/`, and `shared/`
- Replace Expo-only modules gradually (if any are added later)
- Keep API/base URL configuration unchanged for now

## Host Platform Notes

- iOS native build requires macOS + Xcode. On Windows, `npm run ios` will fail because `xcodebuild` is unavailable.
- On Windows, validate bare workflow with `npm run start` and `npm run android`.

## Definition of Done for Step 8 Start

- Metro starts via `npm run start`
- Native app launches via `npm run ios` or `npm run android`
- Auth flow renders from the same `App.js`
- Existing Step 4-7 backend integration continues to work
