# Dataset Download Alternatives

## Problem: Kaggle Download Stuck at 44%

The Porto Taxi dataset is very large (515MB compressed → 1.9GB uncompressed) and may time out on slow connections.

## Solution Options

### Option 1: Generate Synthetic Data (Fastest - Recommended for Testing)

Generate realistic synthetic taxi trajectory data to test the entire pipeline:

```powershell
cd C:\Users\Bruger\embedded-tms-ai
python scripts\generate_synthetic_data.py
```

**Pros:**
- ✅ Instant (generates 10,000 trips in ~30 seconds)
- ✅ Same format as Porto dataset
- ✅ Realistic GPS trajectories
- ✅ Perfect for testing and development

**Cons:**
- ❌ Not real data (but good enough for building the system)

### Option 2: Use a Smaller Alternative Dataset

Try a smaller taxi dataset from Kaggle:

```powershell
# NYC Taxi Trip Duration (smaller)
kaggle competitions download -c nyc-taxi-trip-duration -p .\data\raw

# Or 10K Taxi Trips Portugal
kaggle datasets download -d jsyousef/data-of-10000-taxi-trips-in-portugal -p .\data\raw --unzip
```

### Option 3: Manual Download from Kaggle Website

1. Go to: https://www.kaggle.com/datasets/crailtap/taxi-trajectory
2. Click "Download" button
3. Wait for download to complete
4. Extract `train.csv` to `C:\Users\Bruger\embedded-tms-ai\data\raw\`

### Option 4: Resume Stuck Download

Cancel the stuck download (Ctrl+C) and retry with the CLI:

```powershell
# Cancel stuck download (press Ctrl+C in terminal)
# Then retry:
cd C:\Users\Bruger\embedded-tms-ai
kaggle datasets download -d crailtap/taxi-trajectory -p .\data\raw --unzip
```

### Option 5: Download with Timeout/Retry Logic

```powershell
# Try with curl (if available)
curl -L -o data\raw\taxi-trajectory.zip https://www.kaggle.com/datasets/crailtap/taxi-trajectory/download
```

## Recommended Workflow

**For immediate testing and development:**
```powershell
# 1. Generate synthetic data (30 seconds)
python scripts\generate_synthetic_data.py

# 2. Run preprocessing
python scripts\preprocess_data.py

# 3. Train baseline models
python scripts\train_baseline.py

# 4. Later: download real data when you have stable internet
```

**For production/real analysis:**
- Download the real Porto Taxi dataset manually from Kaggle website
- Replace synthetic data with real data
- Re-run preprocessing and training

## What to Do Now

**Choice A - Quick Start (Recommended):**
```powershell
python scripts\generate_synthetic_data.py
python scripts\preprocess_data.py
python scripts\train_baseline.py
```

**Choice B - Wait for Real Data:**
- Cancel stuck download
- Try downloading manually from Kaggle website
- Or retry with better internet connection

---

**The synthetic data approach lets you build and test your entire TMS system immediately, then swap in real data later for production!**
