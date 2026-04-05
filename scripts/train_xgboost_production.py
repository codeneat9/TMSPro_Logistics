"""
Train production-ready XGBoost model for delay prediction
XGBoost handles class imbalance better than other algorithms
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
DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"
MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("🚀 TRAINING PRODUCTION XGBoost MODEL")
print("=" * 80)

# Load data
print("\n📂 Loading data...")
X = np.load(DATA_PROCESSED / "X_sequences.npy")
y = np.load(DATA_PROCESSED / "y_labels.npy")

print(f"✅ Loaded {len(X)} sequences")
print(f"   Shape: {X.shape}")
print(f"   Delay ratio: {y.mean():.2%}")
print(f"   Class 0 (On-time): {(y==0).sum():,}")
print(f"   Class 1 (Delayed): {(y==1).sum():,}")

# Flatten sequences for XGBoost
X_flat = X.reshape(X.shape[0], -1)
print(f"\n📊 Flattened shape: {X_flat.shape}")

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X_flat, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n📊 Dataset split:")
print(f"   Training: {len(X_train):,} samples ({y_train.mean():.2%} delayed)")
print(f"   Test: {len(X_test):,} samples ({y_test.mean():.2%} delayed)")

# Scale features
print("\n⚙️  Scaling features...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Calculate scale_pos_weight for class imbalance
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
print(f"\n⚖️  Class balance:")
print(f"   scale_pos_weight: {scale_pos_weight:.2f}")

# Train XGBoost 
print("\n🚀 Training XGBoost...")
start_time = time.time()

model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,  # Handle class imbalance
    eval_metric='logloss',
    random_state=42,
    n_jobs=-1,
    tree_method='hist'  # Faster training
)

#  Train with early stopping
eval_set = [(X_test_scaled, y_test)]
model.fit(
    X_train_scaled, y_train,
    eval_set=eval_set,
    verbose=True
)

training_time = time.time() - start_time

# Predictions
print("\n📊 Evaluating model...")
y_pred = model.predict(X_test_scaled)
y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]

# Metrics
accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, zero_division=0)
recall = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)
roc_auc = roc_auc_score(y_test, y_pred_proba)

print("\n" + "=" * 80)
print("🏆 PRODUCTION MODEL PERFORMANCE")
print("=" * 80)
print(f"Training time: {training_time:.2f}s")
print(f"\n📊 Metrics:")
print(f"   Accuracy:  {accuracy:.4f}")
print(f"   Precision: {precision:.4f}")
print(f"   Recall:    {recall:.4f}")
print(f"   F1 Score:  {f1:.4f}")
print(f"   ROC-AUC:   {roc_auc:.4f}")

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
print(f"\n📋 Confusion Matrix:")
print(f"   True Negatives:  {cm[0,0]:,} (correctly predicted on-time)")
print(f"   False Positives: {cm[0,1]:,} (predicted delayed, actually on-time)")
print(f"   False Negatives: {cm[1,0]:,} (predicted on-time, actually delayed)")
print(f"   True Positives:  {cm[1,1]:,} (correctly predicted delayed)")

# Classification Report
print(f"\n📝 Detailed Report:")
print(classification_report(y_test, y_pred, target_names=['On-Time', 'Delayed']))

# Feature Importance
feature_importance = model.feature_importances_
top_10_idx = np.argsort(feature_importance)[-10:]
print(f"\n🔝 Top 10 Most Important Features:")
for i, idx in enumerate(top_10_idx[::-1], 1):
    print(f"   {i}. Feature {idx}: {feature_importance[idx]:.4f}")

# Save model
print(f"\n💾 Saving production model...")
with open(MODELS_DIR / 'xgboost_production_model.pkl', 'wb') as f:
    pickle.dump(model, f)

with open(MODELS_DIR / 'xgboost_production_scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

# Save model info
model_info = {
    'model_type': 'XGBoost',
    'training_samples': len(X_train),
    'test_samples': len(X_test),
    'training_time_seconds': training_time,
    'hyperparameters': {
        'n_estimators': 200,
        'max_depth': 6,
        'learning_rate': 0.1,
        'scale_pos_weight': float(scale_pos_weight)
    },
    'metrics': {
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1),
        'roc_auc': float(roc_auc)
    },
    'confusion_matrix': {
        'true_negatives': int(cm[0,0]),
        'false_positives': int(cm[0,1]),
        'false_negatives': int(cm[1,0]),
        'true_positives': int(cm[1,1])
    },
    'files': ['xgboost_production_model.pkl', 'xgboost_production_scaler.pkl']
}

with open(MODELS_DIR / 'xgboost_production_info.json', 'w') as f:
    json.dump(model_info, f, indent=2)

# Plot ROC Curve
plt.figure(figsize=(10, 8))
fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
plt.plot(fpr, tpr, label=f'XGBoost (AUC={roc_auc:.3f})', linewidth=2)
plt.plot([0, 1], [0, 1], 'k--', label='Random')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curve - XGBoost Production Model', fontsize=14, fontweight='bold')
plt.legend()
plt.grid(alpha=0.3)
plt.savefig(MODELS_DIR / 'xgboost_roc_curve.png', dpi=150, bbox_inches='tight')
print(f"✅ ROC curve saved")

# Plot Confusion Matrix
plt.figure(figsize=(8, 6))
plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
plt.title('Confusion Matrix', fontsize=14, fontweight='bold')
plt.colorbar()
tick_marks = np.arange(2)
plt.xticks(tick_marks, ['On-Time', 'Delayed'])
plt.yticks(tick_marks, ['On-Time', 'Delayed'])

for i in range(2):
    for j in range(2):
        plt.text(j, i, format(cm[i, j], ',d'),
                ha="center", va="center",
                color="white" if cm[i, j] > cm.max() / 2 else "black",
                fontsize=12, fontweight='bold')

plt.ylabel('True Label')
plt.xlabel('Predicted Label')
plt.tight_layout()
plt.savefig(MODELS_DIR / 'xgboost_confusion_matrix.png', dpi=150, bbox_inches='tight')
print(f"✅ Confusion matrix saved")

print("\n" + "=" * 80)
print("✅ PRODUCTION MODEL READY!")
print("=" * 80)
print(f"📁 Files saved:")
print(f"   - xgboost_production_model.pkl")
print(f"   - xgboost_production_scaler.pkl")
print(f"   - xgboost_production_info.json")
print(f"   - xgboost_roc_curve.png")
print(f"   - xgboost_confusion_matrix.png")
print(f"\n🏆 Model Type: XGBoost")
print(f"   ✅ F1 Score: {f1:.4f}")
print(f"   ✅ ROC-AUC: {roc_auc:.4f}")
print(f"   ✅ Trained on {len(X_train):,} samples")
print(f"   ✅ Ready for production deployment")
print("=" * 80)
