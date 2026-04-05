# Quick Start Guide - Embedded AI TMS Project

## ✅ Setup Complete!

Your project structure is ready. Here's how to proceed:

## 📁 Project Structure Created

```
embedded-tms-ai/
├── data/
│   ├── raw/              # Raw Kaggle dataset files
│   └── processed/        # Preprocessed features and sequences
├── models/               # Trained models
├── edge/                 # Edge inference scripts
├── routing/              # OSMnx route planning
├── cloud/                # Flask/FastAPI backend
├── mobile/               # Mobile app
├── notebooks/            # Jupyter notebooks
│   └── 01_data_exploration.ipynb  ✅ Created
├── scripts/
│   ├── download_kaggle_dataset.py  ✅ Created
│   ├── preprocess_data.py          ✅ Created
│   └── train_baseline.py           ✅ Created
├── requirements.txt      ✅ Created
└── README.md            ✅ Created
```

## 🚀 Next Steps (Run in PowerShell)

### Step 1: Navigate to Project Directory
```powershell
cd C:\Users\Bruger\embedded-tms-ai
```

### Step 2: Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

**Note:** This will take a few minutes. Main packages include:
- pandas, numpy, scikit-learn (data & ML)
- tensorflow, torch (deep learning)
- onnx, onnxruntime (edge deployment)
- osmnx, folium (routing & visualization)
- flask, fastapi (backend)
- kaggle (dataset download)

### Step 3: Download Dataset
```powershell
python scripts\download_kaggle_dataset.py
```

**What this does:**
- Authenticates with Kaggle API using your `kaggle.json`
- Downloads Porto Taxi Trajectory dataset
- Extracts files to `data/raw/`
- Shows file sizes and counts

**Alternative:** Open and run the Jupyter notebook `notebooks\01_data_exploration.ipynb` to download and explore interactively.

### Step 4: Preprocess Data
```powershell
python scripts\preprocess_data.py
```

**What this does:**
- Parses GPS trajectories from JSON polylines
- Calculates speed, distance, and time features
- Creates time-series sequences for LSTM input
- Labels delays based on ETA deviation (>15 min threshold)
- Saves processed data to `data/processed/`

**Output files:**
- `features.csv` - Extracted features per trip
- `X_sequences.npy` - Time-series sequences (shape: [n_samples, sequence_length, n_features])
- `y_labels.npy` - Binary delay labels
- `metadata.json` - Dataset metadata

### Step 5: Train Baseline Models
```powershell
python scripts\train_baseline.py
```

**What this does:**
- Trains Logistic Regression and Random Forest
- Evaluates on test set (80/20 split)
- Generates ROC curves and confusion matrices
- Saves models to `models/` directory
- Creates `baseline_results.json` with performance metrics

### Step 6: Explore Data (Jupyter Notebook)
```powershell
jupyter notebook notebooks\01_data_exploration.ipynb
```

**What's in the notebook:**
- Interactive data loading and exploration
- GPS trajectory visualization
- Temporal pattern analysis (hour, day of week)
- Speed and distance distribution plots
- Delay labeling and statistics

## 📊 Expected Outputs

After running the scripts, you should have:

1. **Raw Data** (`data/raw/`)
   - `train.csv` or similar (GPS trajectories)

2. **Processed Data** (`data/processed/`)
   - `features.csv` - Trip-level features
   - `X_sequences.npy` - LSTM input sequences
   - `y_labels.npy` - Delay labels
   - `metadata.json` - Dataset info

3. **Models** (`models/`)
   - `logistic_regression.pkl` - Baseline LR model
   - `random_forest.pkl` - Baseline RF model
   - `scaler_lr.pkl` - Feature scaler
   - `baseline_results.png` - Performance plots
   - `baseline_results.json` - Metrics summary

## 🔧 Troubleshooting

### Kaggle API Authentication Error
```powershell
# Verify kaggle.json location
ls C:\Users\Bruger\.kaggle\kaggle.json

# Test authentication
kaggle datasets list --page 1 --size 5
```

### Module Not Found Error
```powershell
# Reinstall dependencies
python -m pip install --upgrade -r requirements.txt
```

### Out of Memory Error (Large Dataset)
- Edit `preprocess_data.py` line 155 to use smaller sample:
  ```python
  sample_df = df.head(5000).copy()  # Reduce from 1000 to 5000
  ```

### Dataset Not Found
- Check dataset name in `scripts/download_kaggle_dataset.py` (line 11)
- Try alternative: `"jsyousef/data-of-10000-taxi-trips-in-portugal"`

## 📈 Next Phase: Deep Learning & Edge AI

Once baseline models are trained, proceed to:

### 🟦 Step 6: Build LSTM/GRU Model
Create `scripts/train_lstm.py` to build deep learning model

### 🟦 Step 7: Convert to ONNX/TFLite
Create `scripts/convert_model.py` for edge deployment

### 🟦 Step 8: Build Edge Inference
Create `edge/inference.py` for offline prediction

### 🟦 Step 9: OSMnx Routing
Create `routing/compute_routes.py` for alternate routes

### 🟦 Step 10: Route Visualization
Create `routing/visualize_routes.py` for map display

### 🟦 Step 11: Cloud Backend
Create `cloud/app.py` (Flask/FastAPI)

### 🟦 Step 12: Mobile App
Create mobile UI in `mobile/` directory

## 💡 Tips

- **Start small:** Use a subset of data (1000-5000 trips) for initial testing
- **Jupyter first:** Run the notebook to understand the data before running scripts
- **Save checkpoints:** Scripts save intermediate outputs so you can resume
- **Monitor memory:** GPS trajectory processing can be memory-intensive
- **Iterate quickly:** Test with small samples, then scale up

## 📚 Resources

- Porto Taxi Dataset: https://www.kaggle.com/datasets/crailtap/taxi-trajectory
- OSMnx Documentation: https://osmnx.readthedocs.io/
- TensorFlow Lite: https://www.tensorflow.org/lite
- ONNX Runtime: https://onnxruntime.ai/

---

**You're all set! Start with Step 2 (install dependencies) and work through the steps sequentially.**

If you encounter issues, check the troubleshooting section or ask for help.

Good luck building your Embedded AI TMS! 🚀
