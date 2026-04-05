"""
XGBoost with Engineered Trip Features - FAST VERSION
Process only subset first, then extract features
"""

import json
import time
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, confusion_matrix
)
import xgboost as xgb
import matplotlib.pyplot as plt

# Paths
DATA_RAW = Path(__file__).parent.parent / "data" / "raw"
DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"
MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

SUBSET_SIZE = 300000

print("=" * 80)
print("🚀 XGBOOST WITH ENGINEERED TRIP FEATURES (Fast Version)")
print(f"   Processing {SUBSET_SIZE:,} samples only")
print("=" * 80)

# ============================================================================
# STEP 1: Sample subset FIRST
# ============================================================================

print("\n📂 Loading and sampling GPS sequences...")
X_gps = np.load(DATA_PROCESSED / "X_sequences.npy")
y_labels = np.load(DATA_PROCESSED / "y_labels.npy")

print(f"✅ Loaded {len(X_gps):,} total sequences")

# Sample subset immediately
np.random.seed(42)
idx = np.random.choice(len(X_gps), min(SUBSET_SIZE, len(X_gps)), replace=False)
X_gps_subset = X_gps[idx]
y_subset = y_labels[idx]

print(f"✅ Sampled {len(X_gps_subset):,} sequences for training")
print(f"   Delay ratio: {y_subset.mean():.2%}")

# ============================================================================
# STEP 2: Extract Trip Features (only on subset)
# ============================================================================

print("\n🔧 Engineering trip statistics from GPS trajectories...")

trip_features = []

for i, seq in enumerate(X_gps_subset):
    if i % 50000 == 0 and i > 0:
        print(f"   Processed {i:,}/{len(X_gps_subset):,}...")
    
    # seq shape: (10, 6) = [lon, lat, distance, speed, delta_lon, delta_lat]
    lons, lats, distances, speeds = seq[:, 0], seq[:, 1], seq[:, 2], seq[:, 3]
    
    # Valid points
    valid_mask = (lons != 0) | (lats != 0)
    n_valid = np.sum(valid_mask)
    
    if n_valid > 0:
        v_speeds = speeds[valid_mask]
        v_dist = distances[valid_mask]
        
        # Speed statistics
        avg_speed = np.mean(v_speeds)
        max_speed = np.max(v_speeds)
        speed_std = np.std(v_speeds) if len(v_speeds) > 1 else 0
        speed_var = np.var(v_speeds) if len(v_speeds) > 1 else 0
        
        # Distance statistics
        total_dist = np.sum(v_dist)
        avg_dist_step = np.mean(v_dist) if len(v_dist) > 0 else 0
        
        # Stop detection
        num_stops = np.sum(v_speeds < 0.001)
        stop_ratio = num_stops / n_valid
        
        # Acceleration variability
        accel_changes = np.sum(np.abs(np.diff(v_speeds))) if len(v_speeds) > 1 else 0
        
        # Route complexity
        if n_valid >= 3:
            v_lons = lons[valid_mask]
            v_lats = lats[valid_mask]
            delta_lon = np.diff(v_lons)
            delta_lat = np.diff(v_lats)
            angles = np.arctan2(delta_lat, delta_lon)
            angle_diff = np.abs(np.diff(angles))
            num_turns = np.sum(angle_diff > np.pi/4)
            route_complexity = np.sum(angle_diff)
        else:
            num_turns = 0
            route_complexity = 0
        
        # Geographic extent
        lon_range = np.ptp(lons[valid_mask])
        lat_range = np.ptp(lats[valid_mask])
        geo_spread = lon_range + lat_range
        
        # Start/end coords
        start_lon, start_lat = lons[0], lats[0]
        end_lon = lons[valid_mask][-1] if n_valid > 0 else 0
        end_lat = lats[valid_mask][-1] if n_valid > 0 else 0
        
        # Estimated duration
        est_duration = total_dist / avg_speed if avg_speed > 0 else 0
        
        # Congestion indicator
        congestion = speed_var * stop_ratio
        
        features = [
            total_dist, avg_dist_step, avg_speed, max_speed, speed_std, speed_var,
            num_stops, stop_ratio, accel_changes, num_turns, route_complexity,
            lon_range, lat_range, geo_spread, start_lon, start_lat, end_lon, end_lat,
            est_duration, congestion, n_valid
        ]
    else:
        features = [0] * 21
    
    trip_features.append(features)

X_trip = np.array(trip_features)

feature_names_trip = [
    'total_distance', 'avg_distance_per_step', 'avg_speed', 'max_speed',
    'speed_std', 'speed_variance', 'num_stops', 'stop_ratio',
    'acceleration_changes', 'num_turns', 'route_complexity',
    'lon_range', 'lat_range', 'geographic_spread',
    'start_lon', 'start_lat', 'end_lon', 'end_lat',
    'estimated_duration', 'congestion_indicator', 'num_valid_points'
]

print(f"\n✅ Extracted {X_trip.shape[1]} trip features")
print(f"   Features: {', '.join(feature_names_trip[:8])}...")

# ============================================================================
# STEP 3: Extract Temporal Features (matching subset)
# ============================================================================

print("\n⏰ Extracting temporal features...")

df = pd.read_csv(
    DATA_RAW / "train.csv",
    usecols=['TIMESTAMP', 'DAY_TYPE', 'MISSING_DATA', 'POLYLINE']
)

df = df[df['MISSING_DATA'] == False].copy()
df['POLYLINE'] = df['POLYLINE'].astype(str)
df = df[df['POLYLINE'].str.len() > 2].reset_index(drop=True)

# Match the indices with filtered df length
valid_idx = idx[idx < len(df)]
if len(valid_idx) < len(idx):
    print(f"   ⚠️ Adjusted indices: {len(idx)} → {len(valid_idx)} to match filtered data")
    # Trim trip features and labels to match
    X_trip = X_trip[:len(valid_idx)]
    y_subset = y_subset[:len(valid_idx)]

# Get temporal features
df_subset = df.iloc[valid_idx].copy()

df_subset['datetime'] = pd.to_datetime(df_subset['TIMESTAMP'], unit='s')
df_subset['hour'] = df_subset['datetime'].dt.hour
df_subset['day_of_week'] = df_subset['datetime'].dt.dayofweek
df_subset['month'] = df_subset['datetime'].dt.month
df_subset['is_weekend'] = (df_subset['day_of_week'] >= 5).astype(int)
df_subset['is_morning_rush'] = ((df_subset['hour'] >= 7) & (df_subset['hour'] <= 9)).astype(int)
df_subset['is_evening_rush'] = ((df_subset['hour'] >= 17) & (df_subset['hour'] <= 19)).astype(int)
df_subset['is_rush_hour'] = (df_subset['is_morning_rush'] | df_subset['is_evening_rush']).astype(int)
df_subset['is_late_night'] = ((df_subset['hour'] >= 22) | (df_subset['hour'] <= 5)).astype(int)
df_subset['is_business_hours'] = ((df_subset['hour'] >= 9) & (df_subset['hour'] <= 17) & (df_subset['is_weekend'] == 0)).astype(int)
df_subset['day_type'] = df_subset['DAY_TYPE'].map({'A': 0, 'B': 1, 'C': 2}).fillna(0).astype(int)

temporal_cols = [
    'hour', 'day_of_week', 'month', 'is_weekend',
    'is_rush_hour', 'is_morning_rush', 'is_evening_rush',
    'is_late_night', 'is_business_hours', 'day_type'
]

X_temporal = df_subset[temporal_cols].values

print(f"✅ Extracted {X_temporal.shape[1]} temporal features")

# ============================================================================
# STEP 4: Combine Features
# ============================================================================

print("\n🔄 Combining trip + temporal features...")

X_combined = np.concatenate([X_trip, X_temporal], axis=1)

print(f"   Trip features: {X_trip.shape[1]}")
print(f"   Temporal features: {X_temporal.shape[1]}")
print(f"   Total: {X_combined.shape}")

# ============================================================================
# STEP 5: Train XGBoost
# ============================================================================

print("\n📊 Train-test split...")
X_train, X_test, y_train, y_test = train_test_split(
    X_combined, y_subset, test_size=0.2, random_state=42, stratify=y_subset
)

print(f"   Train: {len(X_train):,} ({(y_train==1).mean():.2%} delayed)")
print(f"   Test: {len(X_test):,} ({(y_test==1).mean():.2%} delayed)")

scaler = StandardScaler()
X_train_sc = scaler.fit_transform(X_train)
X_test_sc = scaler.transform(X_test)

print("\n🎯 Training XGBoost...")

scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
print(f"   scale_pos_weight: {scale_pos_weight:.2f}")

model = xgb.XGBClassifier(
    n_estimators=250,
    max_depth=8,
    learning_rate=0.05,
    scale_pos_weight=scale_pos_weight,
    tree_method='hist',
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    gamma=0.1,
    random_state=42,
    n_jobs=-1,
    eval_metric='auc'
)

start = time.time()
model.fit(X_train_sc, y_train, eval_set=[(X_test_sc, y_test)], verbose=25)
train_time = time.time() - start

print(f"\n✅ Training done in {train_time:.1f}s")

# ============================================================================
# STEP 6: Evaluate
# ============================================================================

print("\n📊 EVALUATION")

y_pred = model.predict(X_test_sc)
y_proba = model.predict_proba(X_test_sc)[:, 1]

acc = accuracy_score(y_test, y_pred)
prec = precision_score(y_test, y_pred, zero_division=0)
rec = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_proba)

cm = confusion_matrix(y_test, y_pred)
fpr_rate = cm[0, 1] / (cm[0, 0] + cm[0, 1]) if (cm[0, 0] + cm[0, 1]) > 0 else 0

print("=" * 80)
print("📈 FINAL RESULTS - Engineered Trip Features")
print("=" * 80)
print(f"  Accuracy:  {acc:.4f}")
print(f"  Precision: {prec:.4f}")
print(f"  Recall:    {rec:.4f}")
print(f"  F1 Score:  {f1:.4f}")
print(f"  ROC-AUC:   {auc:.4f}  {'🎯 PRODUCTION!' if auc >= 0.65 else '✅ IMPROVED!' if auc >= 0.55 else '⚠️ Marginal' if auc > 0.51 else '❌ No change'}")
print("=" * 80)

print(f"\nConfusion Matrix:")
print(f"  [[TN={cm[0,0]:,}  FP={cm[0,1]:,}]")
print(f"   [FN={cm[1,0]:,}  TP={cm[1,1]:,}]]")
print(f"\n  False Positive Rate: {fpr_rate:.1%}")

# Feature importance
print("\n🔍 TOP 20 FEATURES:")
all_names = feature_names_trip + temporal_cols
importances = model.feature_importances_
top_idx = np.argsort(importances)[-20:][::-1]

for i, idx in enumerate(top_idx, 1):
    print(f"  {i:2d}. {all_names[idx]:30s}: {importances[idx]:.4f}")

# ============================================================================
# STEP 7: Save
# ============================================================================

print("\n💾 Saving...")

pickle.dump(model, open(MODELS_DIR / "xgboost_final.pkl", 'wb'))
pickle.dump(scaler, open(MODELS_DIR / "xgboost_final_scaler.pkl", 'wb'))

with open(MODELS_DIR / "xgboost_final_features.json", 'w') as f:
    json.dump({
        'trip_features': feature_names_trip,
        'temporal_features': temporal_cols,
        'all_features': all_names
    }, f, indent=2)

results = {
    'model': 'XGBoost - Engineered Features',
    'samples': len(X_combined),
    'features': {'trip': len(feature_names_trip), 'temporal': len(temporal_cols), 'total': len(all_names)},
    'metrics': {
        'accuracy': float(acc), 'precision': float(prec), 'recall': float(rec),
        'f1': float(f1), 'roc_auc': float(auc), 'fpr': float(fpr_rate)
    },
    'confusion_matrix': {'TN': int(cm[0,0]), 'FP': int(cm[0,1]), 'FN': int(cm[1,0]), 'TP': int(cm[1,1])},
    'training_time_sec': float(train_time),
    'top_features': [all_names[i] for i in top_idx[:10]]
}

with open(MODELS_DIR / "xgboost_final_results.json", 'w') as f:
    json.dump(results, f, indent=2)

# Quick plot
fig, ax = plt.subplots(1, 2, figsize=(14, 5))

fpr, tpr, _ = roc_curve(y_test, y_proba)
ax[0].plot(fpr, tpr, label=f'XGBoost (AUC={auc:.3f})', linewidth=2.5)
ax[0].plot([0, 1], [0, 1], 'k--', label='Random')
ax[0].set_title('ROC Curve - Engineered Features', fontweight='bold')
ax[0].set_xlabel('False Positive Rate')
ax[0].set_ylabel('True Positive Rate')
ax[0].legend()
ax[0].grid(alpha=0.3)

metrics = ['Accuracy', 'Precision', 'Recall', 'F1', 'AUC']
values = [acc, prec, rec, f1, auc]
colors = ['green' if v >= 0.65 else 'orange' if v >= 0.55 else 'red' for v in values]
ax[1].bar(metrics, values, color=colors, alpha=0.7)
ax[1].set_ylim(0, 1)
ax[1].set_title('Performance Metrics', fontweight='bold')
ax[1].grid(alpha=0.3, axis='y')
for i, v in enumerate(values):
    ax[1].text(i, v + 0.02, f'{v:.3f}', ha='center', fontweight='bold')

plt.tight_layout()
plt.savefig(MODELS_DIR / "xgboost_final_eval.png", dpi=150)

print("  ✅ xgboost_final.pkl")
print("  ✅ xgboost_final_results.json")
print("  ✅ xgboost_final_eval.png")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
improvement = auc - 0.5015
print(f"📊 IMPROVEMENT OVER BASELINE:")
print(f"   Previous (GPS+Temporal): 0.5015")
print(f"   Current (Engineered):    {auc:.4f}  ({improvement:+.4f})")

if auc >= 0.65:
    print(f"\n✅ PRODUCTION READY!")
    print(f"   Deploy with confidence threshold 0.6-0.7")
elif auc >= 0.55:
    print(f"\n✅ SIGNIFICANT IMPROVEMENT - Deploy with caution")
    print(f"   Use high threshold (0.75+) or hybrid with traffic API")
elif auc > 0.51:
    print(f"\n⚠️ MARGINAL IMPROVEMENT")
    print(f"   Feature engineering helped slightly")
    print(f"   Recommend: Traffic API primary, ML backup")
else:
    print(f"\n❌ NO IMPROVEMENT")
    print(f"   GPS data insufficient even with feature engineering")

print(f"\n💡 PRODUCTION STRATEGY:")
print(f"   1. XGBoost model: Baseline delay prediction")
print(f"   2. Google Maps API: Real-time traffic-based ETA")
print(f"   3. Hybrid approach: Show both predictions")
print(f"   4. Log actuals for continuous model improvement")
print("=" * 80)
