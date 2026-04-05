# Embedded AI for Offline Delay Prediction in Transportation Management Systems

## Project Overview

This project builds a **fully offline-capable, edge-based Transportation Management System (TMS)** with:

- **Edge AI Module**: LSTM/GRU delay prediction running offline (ONNX/TFLite)
- **Local Replanning Engine**: Alternate route and emergency mode recommendation
- **Route Planning Module**: OSMnx + OpenStreetMap for offline route computation
- **Cloud Sync Module**: Flask/FastAPI backend for optional cloud sync
- **Mobile Application**: Flutter/React Native UI for ETA, routes, costs, and risks

## Core Problem

Current TMS solutions (FourKites, project44) are cloud-dependent and fail when:
- Internet is unavailable
- Latency is high
- Vehicle is in remote areas
- Real-time local decisions are needed

## Project Objectives

✅ Predict transportation delays in real time (offline)  
✅ Recommend alternate routes using map visualization  
✅ Recommend emergency transport modes (road/rail/air)  
✅ Sync with cloud only when network is available  
✅ Provide mobile app for ETA, routes, costs, and risks  

## Project Structure

```
embedded-tms-ai/
├── data/
│   ├── raw/              # Raw Kaggle dataset files
│   └── processed/        # Preprocessed features and sequences
├── models/               # Trained models (baseline, LSTM/GRU, ONNX/TFLite)
├── edge/                 # Edge inference scripts
├── routing/              # OSMnx route planning and visualization
├── cloud/                # Flask/FastAPI backend
├── mobile/               # Mobile app (Flutter/React Native)
├── notebooks/            # Jupyter notebooks for exploration and experiments
├── scripts/              # Utility scripts (download, preprocess, train)
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Dataset

**Porto Taxi Trajectory Dataset** (or similar GPS/trajectory dataset from Kaggle)

- GPS coordinates, timestamps, speed
- Used to create time-series sequences
- Labeled for delays using ETA deviation threshold

## Setup Instructions

### 1. Prerequisites

- Python 3.8+ (Python 3.14 detected)
- Kaggle API credentials (`kaggle.json` in `C:\Users\Bruger\.kaggle\`)
- VS Code with Python extension

### 2. Install Dependencies

```powershell
cd C:\Users\Bruger\embedded-tms-ai
python -m pip install -r requirements.txt
```

### 3. Download Dataset

```powershell
# Option A: Using the download script
python scripts\download_kaggle_dataset.py

# Option B: Manual download
kaggle datasets download -d owner/dataset-name -p .\data\raw --unzip
```

### 4. Run Preprocessing

```powershell
python scripts\preprocess_data.py
```

### 5. Train Baseline Models

```powershell
python scripts\train_baseline.py
```

### 6. Train LSTM/GRU Model

```powershell
python scripts\train_lstm.py
```

### 7. Convert to ONNX/TFLite

```powershell
python scripts\convert_model.py
```

### 8. Run Edge Inference

```powershell
python edge\inference.py
```

### 9. Compute Routes (OSMnx)

```powershell
python routing\compute_routes.py
```

### 10. Start Cloud Backend

```powershell
cd cloud
python app.py
```

## Development Roadmap

- [x] Setup Kaggle API
- [x] Create project structure
- [ ] Download and explore dataset
- [ ] Preprocess GPS data and create time-series sequences
- [ ] Train baseline models (Logistic Regression, Random Forest)
- [ ] Train LSTM/GRU model
- [ ] Convert model to ONNX/TFLite
- [ ] Build edge inference script
- [ ] Implement OSMnx route computation
- [ ] Visualize alternate routes
- [ ] Build Flask/FastAPI backend
- [ ] Build mobile app UI

## Key Technologies

- **Machine Learning**: scikit-learn, TensorFlow/PyTorch
- **Edge AI**: ONNX Runtime, TensorFlow Lite
- **Routing**: OSMnx, NetworkX, Folium
- **Backend**: Flask/FastAPI, SQLite/PostgreSQL
- **Mobile**: Flutter or React Native
- **Data**: Pandas, NumPy, Matplotlib, Seaborn

## Contact & Contributions

This is an industry-grade intelligent transport assistant prototype. Contributions welcome!

## License

MIT License (or specify your license)
