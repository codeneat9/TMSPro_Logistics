"""
🚀 COMPREHENSIVE MODEL TRAINING
Train and compare 5 ML models on preprocessed taxi delay dataset

Models:
1. Logistic Regression
2. Random Forest
3. XGBoost
4. LightGBM
5. Neural Network (MLP)

Dataset has REAL delay features: travel_time, expected_time, speed metrics, etc.
"""

import pandas as pd
import numpy as np
import joblib
import json
import time
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                             f1_score, roc_auc_score, confusion_matrix, 
                             classification_report)

# Models
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
import lightgbm as lgb
from sklearn.neural_network import MLPClassifier

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns

# Paths
DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
MODELS_DIR = Path(__file__).parent.parent / "models"
DATASET_FILE = DATA_DIR / "preprocessed_taxi_delay_dataset1.csv"

# Config
SAMPLE_SIZE = 200000  # Reduced to 200K to avoid memory issues
TEST_SIZE = 0.2
RANDOM_STATE = 42

print("="*70)
print("🚀 COMPREHENSIVE MODEL TRAINING - PREPROCESSED DATASET")
print("="*70)

# ========================================
# 1. LOAD AND PREPROCESS DATA
# ========================================

print("\n📂 Loading dataset...")
print(f"   File: {DATASET_FILE}")

# Load data in chunks to manage memory
chunks = []
chunk_size = 100000
total_loaded = 0

for chunk in pd.read_csv(DATASET_FILE, chunksize=chunk_size):
    chunks.append(chunk)
    total_loaded += len(chunk)
    if total_loaded >= SAMPLE_SIZE:
        break
    print(f"   Loaded: {total_loaded:,} rows...", end='\r')

df = pd.concat(chunks, ignore_index=True)[:SAMPLE_SIZE]
print(f"\n✅ Loaded {len(df):,} rows, {len(df.columns)} columns")

# Check target distribution
print(f"\n🎯 Target Variable: 'delay_flag'")
print(f"   Distribution:")
print(df['delay_flag'].value_counts())
print(f"   Percentage:")
print(df['delay_flag'].value_counts(normalize=True) * 100)

# ========================================
# 2. FEATURE ENGINEERING
# ========================================

print("\n🔧 Feature Engineering...")

# ⚠️ IMPORTANT: Remove data leakage features
# These features are only available AFTER trip completion:
# - travel_time (actual duration - this IS the outcome we're predicting!)
# - avg_speed, speed_var, stop_count (calculated from completed trip)
# - num_points (only known after trip ends)

# Select features available BEFORE/AT START of trip
feature_columns = [
    'expected_time',    # Estimated time (available from route planning)
    'hour',             # Hour of day (known at trip start)
    'weekday',          # Day of week (known at trip start)
]

# Add engineered features (using only pre-trip information)
df['is_rush_hour'] = ((df['hour'] >= 7) & (df['hour'] <= 9)) | ((df['hour'] >= 16) & (df['hour'] <= 19))
df['is_weekend'] = df['weekday'].isin([5, 6]).astype(int)
df['is_morning'] = (df['hour'] >= 6) & (df['hour'] < 12)
df['is_afternoon'] = (df['hour'] >= 12) & (df['hour'] < 18)
df['is_evening'] = (df['hour'] >= 18) & (df['hour'] < 22)
df['is_night'] = (df['hour'] >= 22) | (df['hour'] < 6)

feature_columns.extend(['is_rush_hour', 'is_weekend', 'is_morning', 'is_afternoon', 'is_evening', 'is_night'])

# Encode categorical features
if 'CALL_TYPE' in df.columns:
    le_call = LabelEncoder()
    df['call_type_encoded'] = le_call.fit_transform(df['CALL_TYPE'].fillna('UNKNOWN'))
    feature_columns.append('call_type_encoded')

if 'DAY_TYPE' in df.columns:
    le_day = LabelEncoder()
    df['day_type_encoded'] = le_day.fit_transform(df['DAY_TYPE'].fillna('UNKNOWN'))
    feature_columns.append('day_type_encoded')

# Handle missing values
for col in feature_columns:
    if col in df.columns:
        df[col] = df[col].fillna(df[col].median() if df[col].dtype != 'object' else 'UNKNOWN')

print(f"✅ Using {len(feature_columns)} features")
print(f"   Features: {feature_columns}")

# Prepare X and y
X = df[feature_columns].copy()
y = df['delay_flag'].values

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
)

print(f"\n📊 Data Split:")
print(f"   Train: {len(X_train):,} samples")
print(f"   Test:  {len(X_test):,} samples")
print(f"   Delay rate - Train: {np.mean(y_train)*100:.2f}%, Test: {np.mean(y_test)*100:.2f}%")

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ========================================
# 3. TRAIN MODELS
# ========================================

results = []
models = {}

def evaluate_model(name, model, X_train, y_train, X_test, y_test, training_time):
    """Evaluate model and return metrics"""
    print(f"\n📊 Evaluating {name}...")
    
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else y_pred
    
    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)
    
    print(f"   Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")
    print(f"   F1 Score:  {f1:.4f}")
    print(f"   ROC-AUC:   {auc:.4f}")
    print(f"   Training Time: {training_time:.2f}s")
    
    return {
        'model': name,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'roc_auc': auc,
        'training_time': training_time,
        'confusion_matrix': cm.tolist()
    }

print("\n" + "="*70)
print("🤖 TRAINING MODELS")
print("="*70)

# ========================================
# MODEL 1: LOGISTIC REGRESSION
# ========================================

print("\n1️⃣ Logistic Regression")
start = time.time()
lr_model = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE, n_jobs=1)  # n_jobs=1 to avoid memory issues
lr_model.fit(X_train_scaled, y_train)
lr_time = time.time() - start
print(f"✅ Trained in {lr_time:.2f}s")

models['logistic_regression'] = lr_model
results.append(evaluate_model('Logistic Regression', lr_model, X_train_scaled, y_train, X_test_scaled, y_test, lr_time))

# ========================================
# MODEL 2: RANDOM FOREST
# ========================================

print("\n2️⃣ Random Forest")
start = time.time()
rf_model = RandomForestClassifier(
    n_estimators=100,
    max_depth=15,
    min_samples_split=10,
    random_state=RANDOM_STATE,
    n_jobs=-1,
    verbose=0
)
rf_model.fit(X_train, y_train)
rf_time = time.time() - start
print(f"✅ Trained in {rf_time:.2f}s")

models['random_forest'] = rf_model
results.append(evaluate_model('Random Forest', rf_model, X_train, y_train, X_test, y_test, rf_time))

# ========================================
# MODEL 3: XGBOOST
# ========================================

print("\n3️⃣ XGBoost")
start = time.time()
xgb_model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=7,
    learning_rate=0.1,
    random_state=RANDOM_STATE,
    n_jobs=-1,
    eval_metric='logloss'
)
xgb_model.fit(X_train, y_train, verbose=False)
xgb_time = time.time() - start
print(f"✅ Trained in {xgb_time:.2f}s")

models['xgboost'] = xgb_model
results.append(evaluate_model('XGBoost', xgb_model, X_train, y_train, X_test, y_test, xgb_time))

# ========================================
# MODEL 4: LIGHTGBM
# ========================================

print("\n4️⃣ LightGBM")
start = time.time()
lgb_model = lgb.LGBMClassifier(
    n_estimators=100,
    max_depth=7,
    learning_rate=0.1,
    random_state=RANDOM_STATE,
    n_jobs=-1,
    verbose=-1
)
lgb_model.fit(X_train, y_train)
lgb_time = time.time() - start
print(f"✅ Trained in {lgb_time:.2f}s")

models['lightgbm'] = lgb_model
results.append(evaluate_model('LightGBM', lgb_model, X_train, y_train, X_test, y_test, lgb_time))

# ========================================
# MODEL 5: NEURAL NETWORK (MLP)
# ========================================

print("\n5️⃣ Neural Network (MLP)")
start = time.time()
mlp_model = MLPClassifier(
    hidden_layer_sizes=(128, 64, 32),
    activation='relu',
    max_iter=100,
    random_state=RANDOM_STATE,
    early_stopping=True,
    validation_fraction=0.1,
    verbose=False
)
mlp_model.fit(X_train_scaled, y_train)
mlp_time = time.time() - start
print(f"✅ Trained in {mlp_time:.2f}s")

models['neural_network'] = mlp_model
results.append(evaluate_model('Neural Network', mlp_model, X_train_scaled, y_train, X_test_scaled, y_test, mlp_time))

# ========================================
# 4. COMPARE RESULTS
# ========================================

print("\n" + "="*70)
print("📊 MODEL COMPARISON")
print("="*70)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('f1_score', ascending=False)

print("\n🏆 Results ranked by F1 Score:")
print(results_df[['model', 'accuracy', 'precision', 'recall', 'f1_score', 'roc_auc', 'training_time']])

best_model_name = results_df.iloc[0]['model']
best_f1 = results_df.iloc[0]['f1_score']
best_auc = results_df.iloc[0]['roc_auc']

print(f"\n🥇 BEST MODEL: {best_model_name}")
print(f"   F1 Score: {best_f1:.4f}")
print(f"   ROC-AUC:  {best_auc:.4f}")

# ========================================
# 5. SAVE RESULTS
# ========================================

print("\n💾 Saving models and results...")

# Save comparison
MODELS_DIR.mkdir(exist_ok=True)
results_df.to_csv(MODELS_DIR / 'preprocessed_model_comparison.csv', index=False)
print(f"✅ Saved: preprocessed_model_comparison.csv")

# Save best model
best_model_key = best_model_name.lower().replace(' ', '_')
best_model = models[best_model_key]

joblib.dump(best_model, MODELS_DIR / f'best_model_{best_model_key}.pkl')
joblib.dump(scaler, MODELS_DIR / f'scaler_{best_model_key}.pkl')
print(f"✅ Saved: best_model_{best_model_key}.pkl")

# Save feature names
feature_info = {
    'feature_columns': feature_columns,
    'best_model': best_model_name,
    'metrics': results_df.iloc[0].to_dict()
}

with open(MODELS_DIR / 'feature_info.json', 'w') as f:
    json.dump(feature_info, f, indent=2)
print(f"✅ Saved: feature_info.json")

# ========================================
# 6. CREATE VISUALIZATIONS
# ========================================

print("\n📊 Creating visualizations...")

fig, axes = plt.subplots(2, 2, figsize=(15, 12))

# 1. F1 Score comparison
ax = axes[0, 0]
results_df_sorted = results_df.sort_values('f1_score')
ax.barh(results_df_sorted['model'], results_df_sorted['f1_score'], color='skyblue')
ax.set_xlabel('F1 Score')
ax.set_title('Model Comparison - F1 Score', fontweight='bold')
ax.grid(axis='x', alpha=0.3)

# 2. ROC-AUC comparison
ax = axes[0, 1]
ax.barh(results_df_sorted['model'], results_df_sorted['roc_auc'], color='lightcoral')
ax.set_xlabel('ROC-AUC')
ax.set_title('Model Comparison - ROC-AUC', fontweight='bold')
ax.grid(axis='x', alpha=0.3)

# 3. Training time comparison
ax = axes[1, 0]
ax.barh(results_df_sorted['model'], results_df_sorted['training_time'], color='lightgreen')
ax.set_xlabel('Training Time (seconds)')
ax.set_title('Model Training Time', fontweight='bold')
ax.grid(axis='x', alpha=0.3)

# 4. All metrics heatmap
ax = axes[1, 1]
metrics_for_heatmap = results_df[['model', 'accuracy', 'precision', 'recall', 'f1_score', 'roc_auc']].set_index('model')
sns.heatmap(metrics_for_heatmap, annot=True, fmt='.3f', cmap='RdYlGn', ax=ax, cbar_kws={'label': 'Score'})
ax.set_title('Metrics Heatmap', fontweight='bold')

plt.tight_layout()
plt.savefig(MODELS_DIR / 'preprocessed_model_comparison.png', dpi=300, bbox_inches='tight')
print(f"✅ Saved: preprocessed_model_comparison.png")

print("\n" + "="*70)
print("✅ TRAINING COMPLETE!")
print("="*70)
print(f"\n🎯 RECOMMENDATION: Use {best_model_name} for delay prediction")
print(f"   - Best F1 Score: {best_f1:.4f}")
print(f"   - ROC-AUC: {best_auc:.4f}")
print(f"\n📁 All models saved to: {MODELS_DIR}/")
