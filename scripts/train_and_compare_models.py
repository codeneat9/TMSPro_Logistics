"""
Production-Ready Model Training & Comparison
Trains 5 models with best practices and selects the best for deployment
"""

import json
import time
import pickle
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, 
    roc_auc_score, roc_curve, confusion_matrix, classification_report
)
import warnings
warnings.filterwarnings('ignore')

# Paths
DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"
MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Config
RANDOM_STATE = 42
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print("=" * 80)
print("🎯 PRODUCTION-READY MODEL TRAINING & COMPARISON")
print("=" * 80)
print(f"Device: {DEVICE}")
print(f"Random State: {RANDOM_STATE}")
print("=" * 80)

# ==================== Load Data ====================
print("\n📂 Loading data...")
X = np.load(DATA_PROCESSED / "X_sequences.npy")
y = np.load(DATA_PROCESSED / "y_labels.npy")

with open(DATA_PROCESSED / "metadata.json", 'r') as f:
    metadata = json.load(f)

print(f"✅ Loaded {len(X)} sequences")
print(f"   Shape: {X.shape}")
print(f"   Delay ratio: {y.mean():.2%}")
print(f"   Class 0 (On-time): {(y==0).sum():,}")
print(f"   Class 1 (Delayed): {(y==1).sum():,}")

# ==================== Data Preparation ====================
print("\n📊 Preparing data...")

# STAGE 1: Use stratified subset for fast model comparison
SUBSET_SIZE = 50000  # Reduced for faster training
print(f"\n🎯 STAGE 1: Fast model comparison on {SUBSET_SIZE:,} samples")
print(f"   (Best model will be retrained on full {len(X):,} samples in Stage 2)")

if len(X) > SUBSET_SIZE:
    from sklearn.model_selection import train_test_split as split_subset
    X_subset, _, y_subset, _ = split_subset(
        X, y, train_size=SUBSET_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"✅ Using stratified subset: {len(X_subset):,} samples")
    print(f"   Subset delay ratio: {y_subset.mean():.2%}")
else:
    X_subset, y_subset = X, y

X_full, y_full = X, y  # Save full dataset for Stage 2
X, y = X_subset, y_subset  # Use subset for comparison

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
)

print(f"Training samples: {len(X_train):,}")
print(f"Test samples: {len(X_test):,}")

# Flatten for traditional ML models
X_train_flat = X_train.reshape(X_train.shape[0], -1)
X_test_flat = X_test.reshape(X_test.shape[0], -1)

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train_flat)
X_test_scaled = scaler.transform(X_test_flat)

# Note: Using class_weight instead of SMOTE for faster training
print("\n⚖️  Using class_weight for balancing (faster than SMOTE on large datasets)")

# Store results
results = {}

# ==================== Model 1: Logistic Regression ====================
print("\n" + "=" * 80)
print("🔵 MODEL 1: Logistic Regression")
print("=" * 80)

start_time = time.time()

lr_model = LogisticRegression(
    max_iter=100,  # Reduced for speed
    class_weight='balanced',
    random_state=RANDOM_STATE,
    solver='lbfgs',  # Faster than saga
    penalty='l2',
    C=1.0,
    n_jobs=-1
)

lr_model.fit(X_train_scaled, y_train)
y_pred_lr = lr_model.predict(X_test_scaled)
y_pred_proba_lr = lr_model.predict_proba(X_test_scaled)[:, 1]

lr_time = time.time() - start_time

# Metrics
results['Logistic Regression'] = {
    'accuracy': accuracy_score(y_test, y_pred_lr),
    'precision': precision_score(y_test, y_pred_lr, zero_division=0),
    'recall': recall_score(y_test, y_pred_lr, zero_division=0),
    'f1': f1_score(y_test, y_pred_lr, zero_division=0),
    'roc_auc': roc_auc_score(y_test, y_pred_proba_lr),
    'training_time': lr_time,
    'predictions': y_pred_lr,
    'probabilities': y_pred_proba_lr
}

print(f"✅ Training completed in {lr_time:.2f}s")
print(f"   Accuracy:  {results['Logistic Regression']['accuracy']:.4f}")
print(f"   Precision: {results['Logistic Regression']['precision']:.4f}")
print(f"   Recall:    {results['Logistic Regression']['recall']:.4f}")
print(f"   F1 Score:  {results['Logistic Regression']['f1']:.4f}")
print(f"   ROC-AUC:   {results['Logistic Regression']['roc_auc']:.4f}")

# ==================== Model 2: Random Forest ====================
print("\n" + "=" * 80)
print("🌲 MODEL 2: Random Forest")
print("=" * 80)

start_time = time.time()

rf_model = RandomForestClassifier(
    n_estimators=100,  # Reduced for speed
    max_depth=15,
    min_samples_split=20,
    min_samples_leaf=10,
    class_weight='balanced',
    random_state=RANDOM_STATE,
    n_jobs=-1,
    max_features='sqrt'
)

rf_model.fit(X_train_scaled, y_train)
y_pred_rf = rf_model.predict(X_test_scaled)
y_pred_proba_rf = rf_model.predict_proba(X_test_scaled)[:, 1]

rf_time = time.time() - start_time

results['Random Forest'] = {
    'accuracy': accuracy_score(y_test, y_pred_rf),
    'precision': precision_score(y_test, y_pred_rf, zero_division=0),
    'recall': recall_score(y_test, y_pred_rf, zero_division=0),
    'f1': f1_score(y_test, y_pred_rf, zero_division=0),
    'roc_auc': roc_auc_score(y_test, y_pred_proba_rf),
    'training_time': rf_time,
    'predictions': y_pred_rf,
    'probabilities': y_pred_proba_rf
}

print(f"✅ Training completed in {rf_time:.2f}s")
print(f"   Accuracy:  {results['Random Forest']['accuracy']:.4f}")
print(f"   Precision: {results['Random Forest']['precision']:.4f}")
print(f"   Recall:    {results['Random Forest']['recall']:.4f}")
print(f"   F1 Score:  {results['Random Forest']['f1']:.4f}")
print(f"   ROC-AUC:   {results['Random Forest']['roc_auc']:.4f}")

# ==================== Model 3: Gradient Boosting ====================
print("\n" + "=" * 80)
print("📈 MODEL 3: Gradient Boosting")
print("=" * 80)

start_time = time.time()

gb_model = GradientBoostingClassifier(
    n_estimators=50,  # Reduced for speed
    learning_rate=0.1,
    max_depth=5,
    min_samples_split=20,
    min_samples_leaf=10,
    subsample=0.8,
    random_state=RANDOM_STATE
)

gb_model.fit(X_train_scaled, y_train)
y_pred_gb = gb_model.predict(X_test_scaled)
y_pred_proba_gb = gb_model.predict_proba(X_test_scaled)[:, 1]

gb_time = time.time() - start_time

results['Gradient Boosting'] = {
    'accuracy': accuracy_score(y_test, y_pred_gb),
    'precision': precision_score(y_test, y_pred_gb, zero_division=0),
    'recall': recall_score(y_test, y_pred_gb, zero_division=0),
    'f1': f1_score(y_test, y_pred_gb, zero_division=0),
    'roc_auc': roc_auc_score(y_test, y_pred_proba_gb),
    'training_time': gb_time,
    'predictions': y_pred_gb,
    'probabilities': y_pred_proba_gb
}

print(f"✅ Training completed in {gb_time:.2f}s")
print(f"   Accuracy:  {results['Gradient Boosting']['accuracy']:.4f}")
print(f"   Precision: {results['Gradient Boosting']['precision']:.4f}")
print(f"   Recall:    {results['Gradient Boosting']['recall']:.4f}")
print(f"   F1 Score:  {results['Gradient Boosting']['f1']:.4f}")
print(f"   ROC-AUC:   {results['Gradient Boosting']['roc_auc']:.4f}")

# ==================== Model 4: 1D CNN ====================
print("\n" + "=" * 80)
print("🧠 MODEL 4: 1D CNN")
print("=" * 80)

class CNN1D(nn.Module):
    def __init__(self, input_size):
        super(CNN1D, self).__init__()
        self.conv1 = nn.Conv1d(input_size, 64, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(64)
        self.conv2 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(128)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.dropout = nn.Dropout(0.3)
        self.fc = nn.Linear(128, 1)
        
    def forward(self, x):
        x = x.permute(0, 2, 1)  # (batch, seq, features) -> (batch, features, seq)
        x = torch.relu(self.bn1(self.conv1(x)))
        x = torch.relu(self.bn2(self.conv2(x)))
        x = self.pool(x).squeeze(-1)
        x = self.dropout(x)
        x = self.fc(x)
        return x

start_time = time.time()

# Prepare PyTorch data
X_train_tensor = torch.FloatTensor(X_train)
y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)
X_test_tensor = torch.FloatTensor(X_test)
y_test_tensor = torch.FloatTensor(y_test).unsqueeze(1)

# Class weights for sampler
class_counts = np.bincount(y_train.astype(int))
class_weights = 1.0 / class_counts
sample_weights = [class_weights[int(label)] for label in y_train]
sampler = WeightedRandomSampler(sample_weights, len(sample_weights))

train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
test_dataset = TensorDataset(X_test_tensor, y_test_tensor)

train_loader = DataLoader(train_dataset, batch_size=512, sampler=sampler)
test_loader = DataLoader(test_dataset, batch_size=512, shuffle=False)

# Train CNN
cnn_model = CNN1D(X_train.shape[2]).to(DEVICE)
criterion = nn.BCEWithLogitsLoss()
optimizer = optim.Adam(cnn_model.parameters(), lr=0.001)

epochs = 5  # Reduced for speed in Stage 1
for epoch in range(epochs):
    cnn_model.train()
    for batch_X, batch_y in train_loader:
        batch_X, batch_y = batch_X.to(DEVICE), batch_y.to(DEVICE)
        optimizer.zero_grad()
        outputs = cnn_model(batch_X)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()

# Evaluate CNN
cnn_model.eval()
all_preds_cnn = []
all_proba_cnn = []

with torch.no_grad():
    for batch_X, batch_y in test_loader:
        batch_X = batch_X.to(DEVICE)
        outputs = cnn_model(batch_X)
        probs = torch.sigmoid(outputs)
        preds = (probs > 0.5).float()
        all_preds_cnn.extend(preds.cpu().numpy())
        all_proba_cnn.extend(probs.cpu().numpy())

y_pred_cnn = np.array(all_preds_cnn).flatten()
y_pred_proba_cnn = np.array(all_proba_cnn).flatten()

cnn_time = time.time() - start_time

results['1D CNN'] = {
    'accuracy': accuracy_score(y_test, y_pred_cnn),
    'precision': precision_score(y_test, y_pred_cnn, zero_division=0),
    'recall': recall_score(y_test, y_pred_cnn, zero_division=0),
    'f1': f1_score(y_test, y_pred_cnn, zero_division=0),
    'roc_auc': roc_auc_score(y_test, y_pred_proba_cnn),
    'training_time': cnn_time,
    'predictions': y_pred_cnn,
    'probabilities': y_pred_proba_cnn
}

print(f"✅ Training completed in {cnn_time:.2f}s")
print(f"   Accuracy:  {results['1D CNN']['accuracy']:.4f}")
print(f"   Precision: {results['1D CNN']['precision']:.4f}")
print(f"   Recall:    {results['1D CNN']['recall']:.4f}")
print(f"   F1 Score:  {results['1D CNN']['f1']:.4f}")
print(f"   ROC-AUC:   {results['1D CNN']['roc_auc']:.4f}")

# ==================== Model 5: LSTM ====================
print("\n" + "=" * 80)
print("🔄 MODEL 5: LSTM")
print("=" * 80)

class SimpleLSTM(nn.Module):
    def __init__(self, input_size, hidden_size=64):
        super(SimpleLSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.dropout = nn.Dropout(0.3)
        self.fc = nn.Linear(hidden_size, 1)
        
    def forward(self, x):
        _, (hidden, _) = self.lstm(x)
        x = self.dropout(hidden[-1])
        x = self.fc(x)
        return x

start_time = time.time()

# Train LSTM
lstm_model = SimpleLSTM(X_train.shape[2]).to(DEVICE)
criterion = nn.BCEWithLogitsLoss()
optimizer = optim.Adam(lstm_model.parameters(), lr=0.001)

epochs = 5  # Reduced for speed in Stage 1
for epoch in range(epochs):
    lstm_model.train()
    for batch_X, batch_y in train_loader:
        batch_X, batch_y = batch_X.to(DEVICE), batch_y.to(DEVICE)
        optimizer.zero_grad()
        outputs = lstm_model(batch_X)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()

# Evaluate LSTM
lstm_model.eval()
all_preds_lstm = []
all_proba_lstm = []

with torch.no_grad():
    for batch_X, batch_y in test_loader:
        batch_X = batch_X.to(DEVICE)
        outputs = lstm_model(batch_X)
        probs = torch.sigmoid(outputs)
        preds = (probs > 0.5).float()
        all_preds_lstm.extend(preds.cpu().numpy())
        all_proba_lstm.extend(probs.cpu().numpy())

y_pred_lstm = np.array(all_preds_lstm).flatten()
y_pred_proba_lstm = np.array(all_proba_lstm).flatten()

lstm_time = time.time() - start_time

results['LSTM'] = {
    'accuracy': accuracy_score(y_test, y_pred_lstm),
    'precision': precision_score(y_test, y_pred_lstm, zero_division=0),
    'recall': recall_score(y_test, y_pred_lstm, zero_division=0),
    'f1': f1_score(y_test, y_pred_lstm, zero_division=0),
    'roc_auc': roc_auc_score(y_test, y_pred_proba_lstm),
    'training_time': lstm_time,
    'predictions': y_pred_lstm,
    'probabilities': y_pred_proba_lstm
}

print(f"✅ Training completed in {lstm_time:.2f}s")
print(f"   Accuracy:  {results['LSTM']['accuracy']:.4f}")
print(f"   Precision: {results['LSTM']['precision']:.4f}")
print(f"   Recall:    {results['LSTM']['recall']:.4f}")
print(f"   F1 Score:  {results['LSTM']['f1']:.4f}")
print(f"   ROC-AUC:   {results['LSTM']['roc_auc']:.4f}")

# ==================== COMPARISON ====================
print("\n" + "=" * 80)
print("📊 MODEL COMPARISON")
print("=" * 80)

# Create comparison table
comparison_df = pd.DataFrame({
    'Model': list(results.keys()),
    'Accuracy': [results[m]['accuracy'] for m in results],
    'Precision': [results[m]['precision'] for m in results],
    'Recall': [results[m]['recall'] for m in results],
    'F1 Score': [results[m]['f1'] for m in results],
    'ROC-AUC': [results[m]['roc_auc'] for m in results],
    'Training Time (s)': [results[m]['training_time'] for m in results]
})

comparison_df = comparison_df.round(4)
print("\n" + comparison_df.to_string(index=False))

# Find best model based on F1 score (balanced metric)
best_model_name = comparison_df.loc[comparison_df['F1 Score'].idxmax(), 'Model']
print("\n" + "=" * 80)
print(f"🏆 BEST MODEL: {best_model_name}")
print("=" * 80)
print(f"Selected based on highest F1 Score: {results[best_model_name]['f1']:.4f}")
print(f"\n{best_model_name} Performance:")
print(f"   ✅ Accuracy:  {results[best_model_name]['accuracy']:.4f}")
print(f"   ✅ Precision: {results[best_model_name]['precision']:.4f}")
print(f"   ✅ Recall:    {results[best_model_name]['recall']:.4f}")
print(f"   ✅ F1 Score:  {results[best_model_name]['f1']:.4f}")
print(f"   ✅ ROC-AUC:   {results[best_model_name]['roc_auc']:.4f}")

# Confusion Matrix for best model
print(f"\nConfusion Matrix ({best_model_name}):")
cm = confusion_matrix(y_test, results[best_model_name]['predictions'])
print(cm)
print(f"\nTrue Negatives:  {cm[0,0]:,}")
print(f"False Positives: {cm[0,1]:,}")
print(f"False Negatives: {cm[1,0]:,}")
print(f"True Positives:  {cm[1,1]:,}")

# Save results
comparison_df.to_csv(MODELS_DIR / "model_comparison.csv", index=False)
with open(MODELS_DIR / "best_model_info.json", 'w') as f:
    json.dump({
        'best_model': best_model_name,
        'metrics': {k: float(v) if not isinstance(v, (list, np.ndarray)) else None 
                   for k, v in results[best_model_name].items()},
        'selection_criteria': 'F1 Score',
        'all_models': {m: {k: float(v) if not isinstance(v, (list, np.ndarray)) else None 
                          for k, v in results[m].items()} 
                      for m in results}
    }, f, indent=2)

# Plot comparison
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Accuracy
axes[0, 0].bar(comparison_df['Model'], comparison_df['Accuracy'], color='skyblue')
axes[0, 0].set_title('Accuracy Comparison', fontsize=14, fontweight='bold')
axes[0, 0].set_ylabel('Accuracy')
axes[0, 0].tick_params(axis='x', rotation=45)
axes[0, 0].grid(axis='y', alpha=0.3)

# F1 Score
axes[0, 1].bar(comparison_df['Model'], comparison_df['F1 Score'], color='lightgreen')
axes[0, 1].set_title('F1 Score Comparison', fontsize=14, fontweight='bold')
axes[0, 1].set_ylabel('F1 Score')
axes[0, 1].tick_params(axis='x', rotation=45)
axes[0, 1].grid(axis='y', alpha=0.3)

# ROC-AUC
axes[1, 0].bar(comparison_df['Model'], comparison_df['ROC-AUC'], color='salmon')
axes[1, 0].set_title('ROC-AUC Comparison', fontsize=14, fontweight='bold')
axes[1, 0].set_ylabel('ROC-AUC')
axes[1, 0].tick_params(axis='x', rotation=45)
axes[1, 0].grid(axis='y', alpha=0.3)

# Training Time
axes[1, 1].bar(comparison_df['Model'], comparison_df['Training Time (s)'], color='plum')
axes[1, 1].set_title('Training Time Comparison', fontsize=14, fontweight='bold')
axes[1, 1].set_ylabel('Time (seconds)')
axes[1, 1].tick_params(axis='x', rotation=45)
axes[1, 1].grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(MODELS_DIR / 'model_comparison.png', dpi=150, bbox_inches='tight')
print(f"\n✅ Comparison plot saved: {MODELS_DIR / 'model_comparison.png'}")

# ROC Curves
plt.figure(figsize=(10, 8))
for model_name in results:
    fpr, tpr, _ = roc_curve(y_test, results[model_name]['probabilities'])
    plt.plot(fpr, tpr, label=f"{model_name} (AUC={results[model_name]['roc_auc']:.3f})", linewidth=2)

plt.plot([0, 1], [0, 1], 'k--', label='Random')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curves - All Models', fontsize=14, fontweight='bold')
plt.legend()
plt.grid(alpha=0.3)
plt.savefig(MODELS_DIR / 'roc_curves_comparison.png', dpi=150, bbox_inches='tight')
print(f"✅ ROC curves saved: {MODELS_DIR / 'roc_curves_comparison.png'}")

# ==================== STAGE 2: Retrain Best Model on Full Dataset ====================
print("\n" + "=" * 80)
print("🚀 STAGE 2: Retraining best model on FULL dataset")
print("=" * 80)
print(f"Best model from Stage 1: {best_model_name}")
print(f"Retraining on {len(X_full):,} samples (vs {len(X_subset):,} in Stage 1)")

# Prepare full dataset
X_train_full, X_test_full, y_train_full, y_test_full = train_test_split(
    X_full, y_full, test_size=0.2, random_state=RANDOM_STATE, stratify=y_full
)

print(f"Full training set: {len(X_train_full):,} samples")
print(f"Full test set: {len(X_test_full):,} samples")

import pickle

if best_model_name == 'Logistic Regression':
    X_train_full_flat = X_train_full.reshape(X_train_full.shape[0], -1)
    X_test_full_flat = X_test_full.reshape(X_test_full.shape[0], -1)
    scaler_full = StandardScaler()
    X_train_full_scaled = scaler_full.fit_transform(X_train_full_flat)
    X_test_full_scaled = scaler_full.transform(X_test_full_flat)
    
    print("\n🔵 Training Logistic Regression on full dataset...")
    final_model = LogisticRegression(
        max_iter=1000, class_weight='balanced', random_state=RANDOM_STATE,
        solver='saga', penalty='l2', C=0.1, n_jobs=-1
    )
    final_model.fit(X_train_full_scaled, y_train_full)
    y_pred_final = final_model.predict(X_test_full_scaled)
    y_proba_final = final_model.predict_proba(X_test_full_scaled)[:, 1]
    
    with open(MODELS_DIR / 'production_model.pkl', 'wb') as f:
        pickle.dump(final_model, f)
    with open(MODELS_DIR / 'production_scaler.pkl', 'wb') as f:
        pickle.dump(scaler_full, f)

elif best_model_name == 'Random Forest':
    X_train_full_flat = X_train_full.reshape(X_train_full.shape[0], -1)
    X_test_full_flat = X_test_full.reshape(X_test_full.shape[0], -1)
    scaler_full = StandardScaler()
    X_train_full_scaled = scaler_full.fit_transform(X_train_full_flat)
    X_test_full_scaled = scaler_full.transform(X_test_full_flat)
    
    print("\n🌲 Training Random Forest on full dataset...")
    final_model = RandomForestClassifier(
        n_estimators=200, max_depth=20, min_samples_split=10,
        min_samples_leaf=5, class_weight='balanced', random_state=RANDOM_STATE,
        n_jobs=-1, max_features='sqrt'
    )
    final_model.fit(X_train_full_scaled, y_train_full)
    y_pred_final = final_model.predict(X_test_full_scaled)
    y_proba_final = final_model.predict_proba(X_test_full_scaled)[:, 1]
    
    with open(MODELS_DIR / 'production_model.pkl', 'wb') as f:
        pickle.dump(final_model, f)
    with open(MODELS_DIR / 'production_scaler.pkl', 'wb') as f:
        pickle.dump(scaler_full, f)

elif best_model_name == 'Gradient Boosting':
    X_train_full_flat = X_train_full.reshape(X_train_full.shape[0], -1)
    X_test_full_flat = X_test_full.reshape(X_test_full.shape[0], -1)
    scaler_full = StandardScaler()
    X_train_full_scaled = scaler_full.fit_transform(X_train_full_flat)
    X_test_full_scaled = scaler_full.transform(X_test_full_flat)
    
    print("\n📈 Training Gradient Boosting on full dataset...")
    final_model = GradientBoostingClassifier(
        n_estimators=150, learning_rate=0.1, max_depth=7,
        min_samples_split=10, min_samples_leaf=5, subsample=0.8,
        random_state=RANDOM_STATE
    )
    final_model.fit(X_train_full_scaled, y_train_full)
    y_pred_final = final_model.predict(X_test_full_scaled)
    y_proba_final = final_model.predict_proba(X_test_full_scaled)[:, 1]
    
    with open(MODELS_DIR / 'production_model.pkl', 'wb') as f:
        pickle.dump(final_model, f)
    with open(MODELS_DIR / 'production_scaler.pkl', 'wb') as f:
        pickle.dump(scaler_full, f)

elif best_model_name in ['1D CNN', 'LSTM']:
    X_train_full_tensor = torch.FloatTensor(X_train_full)
    y_train_full_tensor = torch.FloatTensor(y_train_full).unsqueeze(1)
    X_test_full_tensor = torch.FloatTensor(X_test_full)
    y_test_full_tensor = torch.FloatTensor(y_test_full).unsqueeze(1)
    
    class_counts_full = np.bincount(y_train_full.astype(int))
    class_weights_full = 1.0 / class_counts_full
    sample_weights_full = [class_weights_full[int(label)] for label in y_train_full]
    sampler_full = WeightedRandomSampler(sample_weights_full, len(sample_weights_full))
    
    train_dataset_full = TensorDataset(X_train_full_tensor, y_train_full_tensor)
    test_dataset_full = TensorDataset(X_test_full_tensor, y_test_full_tensor)
    
    train_loader_full = DataLoader(train_dataset_full, batch_size=512, sampler=sampler_full)
    test_loader_full = DataLoader(test_dataset_full, batch_size=512, shuffle=False)
    
    if best_model_name == '1D CNN':
        print("\n🧠 Training 1D CNN on full dataset...")
        final_model = CNN1D(X_train_full.shape[2]).to(DEVICE)
    else:
        print("\n🔄 Training LSTM on full dataset...")
        final_model = SimpleLSTM(X_train_full.shape[2]).to(DEVICE)
    
    criterion_final = nn.BCEWithLogitsLoss()
    optimizer_final = optim.Adam(final_model.parameters(), lr=0.001)
    
    epochs_full = 15
    for epoch in range(epochs_full):
        final_model.train()
        epoch_loss = 0
        for batch_X, batch_y in train_loader_full:
            batch_X, batch_y = batch_X.to(DEVICE), batch_y.to(DEVICE)
            optimizer_final.zero_grad()
            outputs = final_model(batch_X)
            loss = criterion_final(outputs, batch_y)
            loss.backward()
            optimizer_final.step()
            epoch_loss += loss.item()
        print(f"  Epoch {epoch+1}/{epochs_full} - Loss: {epoch_loss/len(train_loader_full):.4f}")
    
    final_model.eval()
    all_preds_final = []
    all_proba_final = []
    with torch.no_grad():
        for batch_X, batch_y in test_loader_full:
            batch_X = batch_X.to(DEVICE)
            outputs = final_model(batch_X)
            probs = torch.sigmoid(outputs)
            preds = (probs > 0.5).float()
            all_preds_final.extend(preds.cpu().numpy())
            all_proba_final.extend(probs.cpu().numpy())
    
    y_pred_final = np.array(all_preds_final).flatten()
    y_proba_final = np.array(all_proba_final).flatten()
    
    torch.save(final_model.state_dict(), MODELS_DIR / 'production_model.pth')
    torch.save(final_model, MODELS_DIR / 'production_model_complete.pth')

# Final production model metrics
final_accuracy = accuracy_score(y_test_full, y_pred_final)
final_precision = precision_score(y_test_full, y_pred_final, zero_division=0)
final_recall = recall_score(y_test_full, y_pred_final, zero_division=0)
final_f1 = f1_score(y_test_full, y_pred_final, zero_division=0)
final_roc_auc = roc_auc_score(y_test_full, y_proba_final)

print("\n" + "=" * 80)
print("🏆 PRODUCTION MODEL PERFORMANCE (FULL DATASET)")
print("=" * 80)
print(f"Model: {best_model_name}")
print(f"Training samples: {len(X_train_full):,}")
print(f"Test samples: {len(X_test_full):,}")
print(f"\n📊 Final Metrics:")
print(f"   Accuracy:  {final_accuracy:.4f}")
print(f"   Precision: {final_precision:.4f}")
print(f"   Recall:    {final_recall:.4f}")
print(f"   F1 Score:  {final_f1:.4f}")
print(f"   ROC-AUC:   {final_roc_auc:.4f}")

print(f"\n📈 Comparison to Stage 1 (subset):")
print(f"   Stage 1 F1: {results[best_model_name]['f1']:.4f}")
print(f"   Stage 2 F1: {final_f1:.4f}")
print(f"   Improvement: {(final_f1 - results[best_model_name]['f1']) * 100:+.2f}%")

# Save production model info
with open(MODELS_DIR / "production_model_info.json", 'w') as f:
    json.dump({
        'model_type': best_model_name,
        'training_samples': len(X_train_full),
        'test_samples': len(X_test_full),
        'metrics': {
            'accuracy': float(final_accuracy),
            'precision': float(final_precision),
            'recall': float(final_recall),
            'f1_score': float(final_f1),
            'roc_auc': float(final_roc_auc)
        },
        'files': ['production_model.pkl', 'production_scaler.pkl'] if best_model_name in ['Logistic Regression', 'Random Forest', 'Gradient Boosting'] else ['production_model.pth', 'production_model_complete.pth']
    }, f, indent=2)

print("\n" + "=" * 80)
print("✅ MODEL TRAINING & COMPARISON COMPLETE!")
print("=" * 80)
print("=" * 80)
print(f"📁 Results saved in: {MODELS_DIR}")
print(f"   Stage 1 Comparison:")
print(f"   - model_comparison.csv")
print(f"   - best_model_info.json")
print(f"   - model_comparison.png")
print(f"   - roc_curves_comparison.png")
print(f"\n   Stage 2 Production Model:")
print(f"   - production_model.pkl (or .pth for deep learning)")
print(f"   - production_scaler.pkl (for traditional ML)")
print(f"   - production_model_info.json")
print(f"\n🏆 PRODUCTION MODEL: {best_model_name}")
print(f"   ✅ Trained on full {len(X_train_full):,} samples")
print(f"   ✅ F1 Score: {final_f1:.4f}")
print(f"   ✅ ROC-AUC: {final_roc_auc:.4f}")
print(f"   ✅ Ready for ONNX conversion and edge deployment")
print("=" * 80)
