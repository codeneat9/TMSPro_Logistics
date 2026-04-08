# Phase 2 Mobile App - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- **Backend**: Running on port 8001 (Start with: `python run_server.py`)
- **Node.js**: v22+ installed
- **Mobile Device/Simulator**: iOS simulator or Android emulator (or physical device)

---

## Step 1: Start Backend
```bash
# Terminal 1
cd backend
python run_server.py

# Verify: http://localhost:8001/health should return {"status":"healthy"}
```

---

## Step 2: Start Mobile App
```bash
# Terminal 2
cd mobile
npx expo start
```

Expo will display a QR code and options:
```
i   - iOS Simulator
a   - Android Emulator
w   - Web Browser
s   - Send link via Expo Go
q   - Quit
```

---

## Step 3: Test User Flow

### 1. **Register** (First Time)
- Press `i` (iOS) or `a` (Android)
- Wait for simulator to load
- Click **"Sign up"** link on login screen
- Fill in form:
  - Full Name: `John Doe`
  - Email: `john@example.com`
  - Phone: `555-1234`
  - Password: `mypassword123`
  - Confirm Password: `mypassword123`
- Tap **"Create Account"**
- You should auto-Login and see Dashboard

### 2. **Login** (Already Registered)
- Click **"Sign in"**
- Enter credentials from registration
- Tap **"Login"**
- Should see Dashboard

### 3. **Dashboard**
- View welcome message with your email
- See backend status (green if healthy)
- View recent trips (empty if first time)
- Buttons: "New Trip", "Live Tracking"

### 4. **Create New Trip**
- Tap **"➕ New Trip"** button
- Fill in:
  - **Pickup**: "123 Main St, Downtown"
  - **Destination**: "456 Oak Ave, Airport"
  - **Passengers**: `1`
  - **Cargo Weight**: (optional) `50`
- Tap **"Create Trip"**
- Confirm success - trip created!
- Options: "View Trip" or "Create Another"

### 5. **View Trip Details**
- From home, tap on recent trip card
- See trip info:
  - Status with color
  - Locations
  - Assigned driver (if any)
  - Estimated cost
- Status buttons: Confirm, Start, Complete, Cancel

### 6. **Logout**
- Tap **"Logout"** button in top right of header
- Returns to login screen

---

## 🔧 Troubleshooting

### Issue: "Cannot connect to backend"
**Solution:**
1. Verify backend is running: `curl http://localhost:8001/health`
2. Check API URL in `mobile/shared/api.js` (baseURL should be `http://localhost:8001/api`)
3. If using physical device, replace `localhost` with your machine's IP: `http://192.168.x.x:8001/api`

### Issue: "Module not found" errors
**Solution:**
```bash
cd mobile
npm install
```

### Issue: "Expo not found"
**Solution:**
```bash
npm install -g expo-cli
```

### Issue: Simulator doesn't start
**Solution:**
- iOS: Ensure Xcode command line tools installed (`xcode-select --install`)
- Android: Open Android Studio and start emulator first, then `npx expo start`

---

## 📱 Testing on Physical Device

### Using Expo Go App
1. Install Expo Go from App Store or Play Store
2. In terminal where Expo is running, press `s`
3. Scan QR code with Expo Go app
4. App loads on your device

### Important for Physical Device
Update the API base URL in `mobile/shared/api.js`:
```javascript
// Line 5:
const instance = axios.create({
  baseURL: 'http://YOUR_MACHINE_IP:8001/api',  // Replace with your PC's IP
  // ... rest of config
});
```

Find your IP:
- **Windows**: `ipconfig` → look for IPv4 Address (192.168.x.x)
- **Mac/Linux**: `ifconfig` → look for inet address

---

## 📝 API Test Credentials

Any email/password combination works in development!

Examples:
- Email: `test@test.com` | Password: `password123`
- Email: `demo@demo.com` | Password: `demo123456`
- Email: `user@app.com` | Password: `user1234567`

⚠️ Password must be at least 8 characters.

---

## 🎯 What's Working

✅ User authentication (register/login)
✅ Navigation between screens
✅ Create new trips
✅ View trip details
✅ Health check indicator
✅ Pull-to-refresh
✅ Form validation
✅ Error handling

---

## 🚧 Coming Soon

🔄 Real-time trip updates (WebSocket)
🔄 Google Maps integration
🔄 Live location tracking
🔄 Push notifications
🔄 Trip history
🔄 User profile management

---

## 💡 Development Tips

### Hot Reload
Changes to JavaScript files auto-reload. Just save the file!
- If stuck, press `r` in Expo terminal to manually reload
- For issues, press `c` to clear cache then reload

### Debug Console
Open Safari (iOS) or Chrome DevTools (Android):
- **iOS**: Safari → Develop → {Device} → {Simulator}
- **Android**: Chrome → `chrome://inspect`

### View API Requests
In Chrome DevTools → Network tab, you'll see all API calls with responses.

---

## 📞 Support

**Common Issues**:
1. Backend not running → App shows health status as unhealthy
2. Network error → Check firewall/VPN settings
3. Form validation → Click field and read error message
4. Navigation stuck → Press `r` to reload app

**Emergency Reset**:
```bash
# In mobile directory:
npm install
npx expo start -c  # -c clears cache
```

---

## 🎓 Next: Add More Features

Once basic flow works, you can:

1. **Map Integration** - Import TripTrackingScreen
2. **WebSocket** - Real-time trip updates
3. **Location Services** - Background GPS tracking
4. **Notifications** - Push alerts for trip events
5. **Driver App** - Switch to logistics/ folder variant

See [PHASE_2_MOBILE_STATUS.md](./PHASE_2_MOBILE_STATUS.md) for full roadmap.

---

**You're all set! 🎉 Start with Step 1 above and test the app!**
