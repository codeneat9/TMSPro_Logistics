"""
XGBoost with Engineered Trip Statistics Features
Extracts meaningful features from GPS trajectories that correlate with delays
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
    roc_auc_score, roc_curve, confusion_matrix, classification_report
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
print("🚀 XGBOOST WITH ENGINEERED TRIP FEATURES")
print(f"   Extracting trip statistics from GPS trajectories")
print(f"   Using {SUBSET_SIZE:,} samples")
print("=" * 80)

# ============================================================================
# STEP 1: Load GPS Sequences
# ============================================================================

print("\n📂 Loading GPS sequences...")
X_gps = np.load(DATA_PROCESSED / "X_sequences.npy")
y_labels = np.load(DATA_PROCESSED / "y_labels.npy")

print(f"✅ Loaded {len(X_gps):,} sequences, shape: {X_gps.shape}")
print(f"   Delay ratio: {y_labels.mean():.2%}")

# ============================================================================
# STEP 2: Extract Trip Statistics Features
# ============================================================================

print("\n🔧 Engineering trip-level features from GPS data...")

def calculate_trip_features(sequence):
    """Extract meaningful features from GPS trajectory"""
    # sequence shape: (10, 6) = [lon, lat, distance, speed, delta_lon, delta_lat]
    
    features = {}
    
    # Extract components
    lons = sequence[:, 0]
    lats = sequence[:, 1]
    distances = sequence[:, 2]
    speeds = sequence[:, 3]
    
    # Remove zero padding
    non_zero_mask = (lons != 0) | (lats != 0)
    valid_points = np.sum(non_zero_mask)
    
    if valid_points > 0:
        valid_speeds = speeds[non_zero_mask]
        valid_distances = distances[non_zero_mask]
        
        # Distance features
        features['total_distance'] = np.sum(valid_distances)
        features['avg_distance_per_step'] = np.mean(valid_distances) if len(valid_distances) > 0 else 0
        
        # Speed features
        features['avg_speed'] = np.mean(valid_speeds) if len(valid_speeds) > 0 else 0
        features['max_speed'] = np.max(valid_speeds) if len(valid_speeds) > 0 else 0
        features['min_speed'] = np.min(valid_speeds) if len(valid_speeds) > 0 else 0
        features['speed_variance'] = np.var(valid_speeds) if len(valid_speeds) > 1 else 0
        features['speed_std'] = np.std(valid_speeds) if len(valid_speeds) > 1 else 0
        
        # Stop detection (speed < 0.001)
        features['num_stops'] = np.sum(valid_speeds < 0.001)
        features['stop_ratio'] = features['num_stops'] / valid_points if valid_points > 0 else 0
        
        # Movement patterns
        features['acceleration_changes'] = np.sum(np.abs(np.diff(valid_speeds))) if len(valid_speeds) > 1 else 0
        
        # Route complexity (direction changes)
        if valid_points >= 3:
            delta_lons = np.diff(lons[non_zero_mask])
            delta_lats = np.diff(lats[non_zero_mask])
            angles = np.arctan2(delta_lats, delta_lons)
            angle_changes = np.abs(np.diff(angles))
            features['num_turns'] = np.sum(angle_changes > np.pi/4)  # Turns > 45 degrees
            features['route_complexity'] = np.sum(angle_changes)
        else:
            features['num_turns'] = 0
            features['route_complexity'] = 0
        
        # Geographic spread
        features['lon_range'] = np.max(lons[non_zero_mask]) - np.min(lons[non_zero_mask])
        features['lat_range'] = np.max(lats[non_zero_mask]) - np.min(lats[non_zero_mask])
        features['geographic_spread'] = features['lon_range'] + features['lat_range']
        
        # Start and end coordinates (for zone clustering)
        features['start_lon'] = lons[0]
        features['start_lat'] = lats[0]
        features['end_lon'] = lons[non_zero_mask][-1] if valid_points > 0 else 0
        features['end_lat'] = lats[non_zero_mask][-1] if valid_points > 0 else 0
        
        # Estimated trip duration (distance / avg_speed)
        if features['avg_speed'] > 0:
            features['estimated_duration'] = features['total_distance'] / features['avg_speed']
        else:
            features['estimated_duration'] = 0
        
        # Traffic indicators
        features['congestion_indicator'] = features['speed_variance'] * features['stop_ratio']
        
        # Trajectory length
        features['num_valid_points'] = valid_points
        
    else:
        # All zeros if invalid sequence
        for key in ['total_distance', 'avg_distance_per_step', 'avg_speed', 'max_speed', 
                    'min_speed', 'speed_variance', 'speed_std', 'num_stops', 'stop_ratio',
                    'acceleration_changes', 'num_turns', 'route_complexity', 'lon_range',
                    'lat_range', 'geographic_spread', 'start_lon', 'start_lat', 'end_lon',
                    'end_lat', 'estimated_duration', 'congestion_indicator', 'num_valid_points']:
            features[key] = 0
    
    return features

# Process all sequences
print("   Processing GPS trajectories...")
trip_features_list = []
for i, seq in enumerate(X_gps):
    if i % 100000 == 0 and i > 0:
        print(f"   Processed {i:,}/{len(X_gps):,} sequences...")
    trip_features_list.append(calculate_trip_features(seq))

# Convert to DataFrame then numpy
df_trip_features = pd.DataFrame(trip_features_list)
X_trip_stats = df_trip_features.values

print(f"\n✅ Extracted {X_trip_stats.shape[1]} trip statistics features:")
print(f"   {', '.join(df_trip_features.columns.tolist()[:10])}...")

# ============================================================================
# STEP 3: Extract Temporal Features
# ============================================================================

print("\n⏰ Extracting temporal features...")

df = pd.read_csv(
    DATA_RAW / "train.csv",
    usecols=['TIMESTAMP', 'DAY_TYPE', 'MISSING_DATA', 'POLYLINE']
)

df = df[df['MISSING_DATA'] == False].copy()
df['POLYLINE'] = df['POLYLINE'].astype(str)
df = df[df['POLYLINE'].str.len() > 2].reset_index(drop=True)
df = df.head(len(X_gps)).copy()

df['datetime'] = pd.to_datetime(df['TIMESTAMP'], unit='s')
df['hour'] = df['datetime'].dt.hour
df['day_of_week'] = df['datetime'].dt.dayofweek
df['month'] = df['datetime'].dt.month
df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
df['is_morning_rush'] = ((df['hour'] >= 7) & (df['hour'] <= 9)).astype(int)
df['is_evening_rush'] = ((df['hour'] >= 17) & (df['hour'] <= 19)).astype(int)
df['is_rush_hour'] = (df['is_morning_rush'] | df['is_evening_rush']).astype(int)
df['is_late_night'] = ((df['hour'] >= 22) | (df['hour'] <= 5)).astype(int)
df['is_business_hours'] = ((df['hour'] >= 9) & (df['hour'] <= 17) & (df['is_weekend'] == 0)).astype(int)
df['day_type'] = df['DAY_TYPE'].map({'A': 0, 'B': 1, 'C': 2}).fillna(0).astype(int)

temporal_cols = [
    'hour', 'day_of_week', 'month', 'is_weekend',
    'is_rush_hour', 'is_morning_rush', 'is_evening_rush',
    'is_late_night', 'is_business_hours', 'day_type'
]

X_temporal = df[temporal_cols].values

print(f"✅ Extracted {X_temporal.shape[1]} temporal features")

# ============================================================================
# STEP 4: Combine All Features
# ============================================================================

print("\n🔄 Combining all features...")

# Ensure alignment
min_len = min(len(X_trip_stats), len(X_temporal), len(y_labels))
X_trip_stats = X_trip_stats[:min_len]
X_temporal = X_temporal[:min_len]
y_labels = y_labels[:min_len]

# Combine: trip statistics + temporal
X_combined = np.concatenate([X_trip_stats, X_temporal], axis=1)

print(f"   Trip statistics: {X_trip_stats.shape[1]} features")
print(f"   Temporal: {X_temporal.shape[1]} features")
print(f"   Combined: {X_combined.shape}")

# Subset
if len(X_combined) > SUBSET_SIZE:
    print(f"\n✂️ Sampling {SUBSET_SIZE:,} random samples...")
    np.random.seed(42)
    idx = np.random.choice(len(X_combined), SUBSET_SIZE, replace=False)
    X_combined = X_combined[idx]
    y_labels = y_labels[idx]
    print(f"   Delay ratio: {y_labels.mean():.2%}")

# ============================================================================
# STEP 5: Train-Test Split
# ============================================================================

print("\n📊 Splitting data...")
X_train, X_test, y_train, y_test = train_test_split(
    X_combined, y_labels, test_size=0.2, random_state=42, stratify=y_labels
)

print(f"   Train: {len(X_train):,} ({(y_train==1).mean():.2%} delayed)")
print(f"   Test: {len(X_test):,} ({(y_test==1).mean():.2%} delayed)")

# Scale
scaler = StandardScaler()
X_train_sc = scaler.fit_transform(X_train)
X_test_sc = scaler.transform(X_test)

# ============================================================================
# STEP 6: Train XGBoost
# ============================================================================

print("\n🎯 Training XGBoost with engineered features...")

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
model.fit(
    X_train_sc, y_train,
    eval_set=[(X_test_sc, y_test)],
    verbose=20
)
train_time = time.time() - start

print(f"\n✅ Training completed in {train_time:.1f}s")

# ============================================================================
# STEP 7: Evaluate
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
print(f"📈 RESULTS - Engineered Features (Trip Stats + Temporal)")
print("=" * 80)
print(f"  Accuracy:  {acc:.4f}")
print(f"  Precision: {prec:.4f}")
print(f"  Recall:    {rec:.4f}")
print(f"  F1 Score:  {f1:.4f}")
print(f"  ROC-AUC:   {auc:.4f}  {'🎯 PRODUCTION READY!' if auc >= 0.65 else '✅ IMPROVED!' if auc >= 0.55 else '⚠️ Marginal' if auc > 0.50 else '❌ No improvement'}")
print("=" * 80)

print(f"\n📊 Confusion Matrix:")
print(f"   [[TN={cm[0,0]:,}  FP={cm[0,1]:,}]")
print(f"    [FN={cm[1,0]:,}  TP={cm[1,1]:,}]]")
print(f"\n   False Positive Rate: {fpr_rate:.1%}")

# Feature importance
print("\n🔍 TOP 20 MOST IMPORTANT FEATURES:")
all_feature_names = df_trip_features.columns.tolist() + temporal_cols
importances = model.feature_importances_
top_idx = np.argsort(importances)[-20:][::-1]

for idx in top_idx:
    print(f"   {all_feature_names[idx]:30s}: {importances[idx]:.4f}")

# ============================================================================
# STEP 8: Save
# ============================================================================

print("\n💾 Saving model and results...")

pickle.dump(model, open(MODELS_DIR / "xgboost_engineered.pkl", 'wb'))
pickle.dump(scaler, open(MODELS_DIR / "xgboost_engineered_scaler.pkl", 'wb'))

# Save feature names for production inference
with open(MODELS_DIR / "xgboost_engineered_features.json", 'w') as f:
    json.dump({
        'trip_features': df_trip_features.columns.tolist(),
        'temporal_features': temporal_cols,
        'all_features': all_feature_names,
        'num_features': len(all_feature_names)
    }, f, indent=2)

results = {
    'model': 'XGBoost with Engineered Trip Features',
    'samples': int(len(X_combined)),
    'features': {
        'trip_statistics': int(X_trip_stats.shape[1]),
        'temporal': int(X_temporal.shape[1]),
        'total': int(X_combined.shape[1])
    },
    'metrics': {
        'accuracy': float(acc),
        'precision': float(prec),
        'recall': float(rec),
        'f1': float(f1),
        'roc_auc': float(auc),
        'false_positive_rate': float(fpr_rate)
    },
    'confusion_matrix': {
        'TN': int(cm[0,0]),
        'FP': int(cm[0,1]),
        'FN': int(cm[1,0]),
        'TP': int(cm[1,1])
    },
    'training_time_seconds': float(train_time),
    'scale_pos_weight': float(scale_pos_weight),
    'top_features': [all_feature_names[i] for i in top_idx[:10]]
}

with open(MODELS_DIR / "xgboost_engineered_results.json", 'w') as f:
    json.dump(results, f, indent=2)

# ============================================================================
# STEP 9: Visualization
# ============================================================================

print("\n📊 Creating visualizations...")

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# ROC Curve
fpr, tpr, _ = roc_curve(y_test, y_proba)
axes[0, 0].plot(fpr, tpr, label=f'XGBoost Engineered (AUC={auc:.3f})', linewidth=2.5, color='#2E86AB')
axes[0, 0].plot([0, 1], [0, 1], 'k--', label='Random (AUC=0.500)', linewidth=1.5)
axes[0, 0].fill_between(fpr, tpr, alpha=0.2, color='#2E86AB')
axes[0, 0].set_xlabel('False Positive Rate', fontsize=11)
axes[0, 0].set_ylabel('True Positive Rate', fontsize=11)
axes[0, 0].set_title('ROC Curve - Engineered Features', fontsize=13, fontweight='bold')
axes[0, 0].legend(fontsize=10)
axes[0, 0].grid(alpha=0.3)

# Metrics Bar Chart
metrics = ['Accuracy', 'Precision', 'Recall', 'F1', 'AUC']
values = [acc, prec, rec, f1, auc]
colors = ['#06A77D' if v >= 0.65 else '#F77F00' if v >= 0.55 else '#D62828' for v in values]
bars = axes[0, 1].bar(metrics, values, color=colors, alpha=0.8, edgecolor='black', linewidth=1.2)
axes[0, 1].set_ylim(0, 1)
axes[0, 1].set_title('Performance Metrics', fontsize=13, fontweight='bold')
axes[0, 1].grid(alpha=0.3, axis='y')
axes[0, 1].set_ylabel('Score', fontsize=11)
for i, (v, bar) in enumerate(zip(values, bars)):
    axes[0, 1].text(i, v + 0.03, f'{v:.3f}', ha='center', fontsize=10, fontweight='bold')

# Feature Importance
top_20_idx = np.argsort(importances)[-20:]
top_20_names = [all_feature_names[i] for i in top_20_idx]
top_20_values = importances[top_20_idx]
colors_feat = ['#06A77D' if name in temporal_cols else '#2E86AB' for name in top_20_names]
axes[1, 0].barh(range(20), top_20_values, color=colors_feat, alpha=0.8, edgecolor='black', linewidth=0.8)
axes[1, 0].set_yticks(range(20))
axes[1, 0].set_yticklabels(top_20_names, fontsize=9)
axes[1, 0].set_xlabel('Feature Importance', fontsize=11)
axes[1, 0].set_title('Top 20 Most Important Features', fontsize=13, fontweight='bold')
axes[1, 0].grid(alpha=0.3, axis='x')

# Confusion Matrix Heatmap
im = axes[1, 1].imshow(cm, cmap='Blues', alpha=0.8)
axes[1, 1].set_xticks([0, 1])
axes[1, 1].set_yticks([0, 1])
axes[1, 1].set_xticklabels(['On-time', 'Delayed'], fontsize=10)
axes[1, 1].set_yticklabels(['On-time', 'Delayed'], fontsize=10)
axes[1, 1].set_xlabel('Predicted', fontsize=11)
axes[1, 1].set_ylabel('Actual', fontsize=11)
axes[1, 1].set_title('Confusion Matrix', fontsize=13, fontweight='bold')
for i in range(2):
    for j in range(2):
        text_color = 'white' if cm[i, j] > cm.max() / 2 else 'black'
        axes[1, 1].text(j, i, f'{cm[i, j]:,}', ha='center', va='center', 
                       fontsize=12, fontweight='bold', color=text_color)
plt.colorbar(im, ax=axes[1, 1])

plt.tight_layout()
plt.savefig(MODELS_DIR / "xgboost_engineered_evaluation.png", dpi=150, bbox_inches='tight')

print(f"   ✅ Model: xgboost_engineered.pkl")
print(f"   ✅ Scaler: xgboost_engineered_scaler.pkl")
print(f"   ✅ Features: xgboost_engineered_features.json")
print(f"   ✅ Results: xgboost_engineered_results.json")
print(f"   ✅ Plot: xgboost_engineered_evaluation.png")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("✅ TRAINING COMPLETE!")
print("=" * 80)

improvement = auc - 0.5015  # Previous temporal-only AUC
improvement_pct = (improvement / 0.5015) * 100

print(f"\n📊 Performance Improvement:")
print(f"   Previous (Temporal only):  AUC = 0.5015")
print(f"   Current (Engineered):      AUC = {auc:.4f}")
print(f"   Improvement:               +{improvement:.4f} ({improvement_pct:+.1f}%)")

if auc >= 0.65:
    print(f"\n✅ MODEL READY FOR PRODUCTION!")
    print(f"   • ROC-AUC ≥ 0.65 indicates reliable predictions")
    print(f"   • Deploy with confidence threshold 0.6-0.7")
    print(f"   • Monitor false positive rate in production")
elif auc >= 0.55:
    print(f"\n✅ SIGNIFICANT IMPROVEMENT - ACCEPTABLE FOR DEPLOYMENT")
    print(f"   • Use high confidence threshold (0.75+) to reduce false alarms")
    print(f"   • Combine with traffic API for hybrid approach")
    print(f"   • Collect production data for continuous improvement")
elif auc > 0.50:
    print(f"\n⚠️ MARGINAL IMPROVEMENT")
    print(f"   • Better than random but still limited")
    print(f"   • Recommend: Use traffic API as primary, ML as backup")
    print(f"   • Feature engineering helped but external data needed")
else:
    print(f"\n❌ NO IMPROVEMENT - EXTERNAL DATA REQUIRED")
    print(f"   • GPS features insufficient regardless of engineering")
    print(f"   • Must integrate: weather, real-time traffic, incidents")

print(f"\n💡 PRODUCTION RECOMMENDATION:")
print(f"   1. Use this XGBoost model as baseline/fallback")
print(f"   2. Integrate Google Maps Distance Matrix API for real-time")
print(f"   3. Hybrid: Show API prediction + ML confidence score")
print(f"   4. Log predictions vs actual for model improvements")
print("=" * 80)
