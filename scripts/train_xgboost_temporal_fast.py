"""
Fast XGBoost with Temporal Features
Uses preprocessed GPS sequences + temporal features from raw data
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

# Use subset for speed
SUBSET_SIZE = 300000

print("=" * 80)
print("🚀 XGBOOST WITH TEMPORAL FEATURES (Fast Version)")
print(f"   Using {SUBSET_SIZE:,} samples")
print("=" * 80)

# ============================================================================
# STEP 1: Load GPS Sequences
# ============================================================================

print("\n📂 Loading preprocessed GPS sequences...")
X_gps = np.load(DATA_PROCESSED / "X_sequences.npy")
y_labels = np.load(DATA_PROCESSED / "y_labels.npy")

print(f"✅ Loaded {len(X_gps):,} GPS sequences, shape: {X_gps.shape}")
print(f"   Delay ratio: {y_labels.mean():.2%}")

# ============================================================================
# STEP 2: Extract Temporal Features (FAST - no parsing)
# ============================================================================

print("\n⏰ Extracting temporal features from timestamps...")

# Load only columns we need
df = pd.read_csv(
    DATA_RAW / "train.csv",
    usecols=['TIMESTAMP', 'DAY_TYPE', 'MISSING_DATA', 'POLYLINE']
)

print(f"✅ Loaded {len(df):,} records")

# Filter (same as preprocessing)
df = df[df['MISSING_DATA'] == False].copy()
df['POLYLINE'] = df['POLYLINE'].astype(str)
df = df[df['POLYLINE'].str.len() > 2].reset_index(drop=True)

# Take first N matching preprocessed data
df = df.head(len(X_gps)).copy()

print(f"✅ Filtered to {len(df):,} valid trips")

# Extract temporal features
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
print(f"   {', '.join(temporal_cols)}")

# ================================================================================
# STEP 3: Combine and Subset
# ============================================================================

print("\n🔄 Combining GPS + temporal features...")

# Flatten GPS
X_gps_flat = X_gps.reshape(X_gps.shape[0], -1)

# Ensure alignment
min_len = min(len(X_gps_flat), len(X_temporal))
X_gps_flat = X_gps_flat[:min_len]
X_temporal = X_temporal[:min_len]
y_labels = y_labels[:min_len]

# Combine
X_combined = np.concatenate([X_gps_flat, X_temporal], axis=1)

print(f"   GPS features: {X_gps_flat.shape[1]}")
print(f"   Temporal features: {X_temporal.shape[1]}")
print(f"   Combined: {X_combined.shape}")

# Random subset
if len(X_combined) > SUBSET_SIZE:
    print(f"\n✂️ Sampling {SUBSET_SIZE:,} random samples...")
    np.random.seed(42)
    idx = np.random.choice(len(X_combined), SUBSET_SIZE, replace=False)
    X_combined = X_combined[idx]
    y_labels = y_labels[idx]
    print(f"   Delay ratio: {y_labels.mean():.2%}")

# ============================================================================
# STEP 4: Train-Test Split
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
# STEP 5: Train XGBoost
# ============================================================================

print("\n🎯 Training XGBoost...")

scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
print(f"   scale_pos_weight: {scale_pos_weight:.2f}")

model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=7,
    learning_rate=0.05,
    scale_pos_weight=scale_pos_weight,
    tree_method='hist',
    subsample=0.8,
    colsample_bytree=0.8,
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

print("=" * 70)
print(f"📈 RESULTS (GPS + Temporal Features)")
print("=" * 70)
print(f"  Accuracy:  {acc:.4f}")  
print(f"  Precision: {prec:.4f}")
print(f"  Recall:    {rec:.4f}")
print(f"  F1 Score:  {f1:.4f}")
print(f"  ROC-AUC:   {auc:.4f}  {'🎯 GOOD!' if auc >= 0.65 else '⚠️ Needs improvement' if auc >= 0.55 else '❌ Poor'}")
print("=" * 70)

print(f"\n📊 Confusion Matrix:")
print(f"   [[TN={cm[0,0]:,}  FP={cm[0,1]:,}]")
print(f"    [FN={cm[1,0]:,}  TP={cm[1,1]:,}]]")
print(f"\n   False Positive Rate: {fpr_rate:.1%}")

# Feature importance
print("\n🔍 TOP 15 FEATURES:")
gps_names = [f'gps_{i}' for i in range(X_gps_flat.shape[1])]
all_names = gps_names + temporal_cols
importances = model.feature_importances_
top_idx = np.argsort(importances)[-15:][::-1]

for idx in top_idx:
    print(f"   {all_names[idx]:25s}: {importances[idx]:.4f}")

# ============================================================================
# STEP 7: Save
# ============================================================================

print("\n💾 Saving...")

pickle.dump(model, open(MODELS_DIR / "xgboost_temporal.pkl", 'wb'))
pickle.dump(scaler, open(MODELS_DIR / "xgboost_temporal_scaler.pkl", 'wb'))

results = {
    'model': 'XGBoost with GPS + Temporal Features',
    'samples': int(len(X_combined)),
    'features': {
        'gps': int(X_gps_flat.shape[1]),
        'temporal': int(X_temporal.shape[1]),
        'total': int(X_combined.shape[1]),
        'temporal_list': temporal_cols
    },
    'metrics': {
        'accuracy': float(acc),
        'precision': float(prec),
        'recall': float(rec),
        'f1': float(f1),
        'roc_auc': float(auc),
        'false_positive_rate': float(fpr_rate)
    },
    'confusion_matrix': {'TN': int(cm[0,0]), 'FP': int(cm[0,1]), 'FN': int(cm[1,0]), 'TP': int(cm[1,1])},
    'training_time_seconds': float(train_time),
    'scale_pos_weight': float(scale_pos_weight)
}

with open(MODELS_DIR / "xgboost_temporal_results.json", 'w') as f:
    json.dump(results, f, indent=2)

# Plot
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# ROC
fpr, tpr, _ = roc_curve(y_test, y_proba)
axes[0].plot(fpr, tpr, label=f'XGBoost (AUC={auc:.3f})', linewidth=2.5)
axes[0].plot([0, 1], [0, 1], 'k--', label='Random')
axes[0].set_xlabel('False Positive Rate')
axes[0].set_ylabel('True Positive Rate')
axes[0].set_title('ROC Curve')
axes[0].legend()
axes[0].grid(alpha=0.3)

# Metrics
metrics = ['Accuracy', 'Precision', 'Recall', 'F1', 'AUC']
values = [acc, prec, rec, f1, auc]
colors = ['green' if v >= 0.6 else 'orange' if v >= 0.5 else 'red' for v in values]
axes[1].bar(metrics, values, color=colors, alpha=0.7)
axes[1].set_ylim(0, 1)
axes[1].set_title('Performance Metrics')
axes[1].grid(alpha=0.3, axis='y')
for i, v in enumerate(values):
    axes[1].text(i, v + 0.02, f'{v:.3f}', ha='center')

plt.tight_layout()
plt.savefig(MODELS_DIR / "xgboost_temporal_eval.png", dpi=150, bbox_inches='tight')

print(f"   ✅ Model: xgboost_temporal.pkl")
print(f"   ✅ Results: xgboost_temporal_results.json")
print(f"   ✅ Plot: xgboost_temporal_eval.png")

print("\n" + "=" * 70)
if auc >= 0.65:
    print("✅ MODEL READY FOR PRODUCTION!")
    print("   Next: Deploy with confidence threshold 0.7+")
elif auc >= 0.55:
    print("⚠️ MODEL IMPROVED BUT NEEDS MORE FEATURES")
    print("   Recommendation: Add weather + real-time traffic data")
else:
    print("❌ MODEL UNDERPERFORMING")
    print("   GPS + temporal features insufficient")
    print("   Need: weather, traffic, road type, events")
print("=" * 70)
