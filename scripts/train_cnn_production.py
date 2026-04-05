"""
Stage 2: Retrain best model (1D CNN) on FULL dataset for production
"""

import json
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

# Paths
DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"
MODELS_DIR = Path(__file__).parent.parent / "models"
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print("=" * 80)
print("🚀 STAGE 2: Training 1D CNN on FULL Dataset")
print("=" * 80)
print(f"Device: {DEVICE}")

# Model definition
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
        x = x.permute(0, 2, 1) 
        x = torch.relu(self.bn1(self.conv1(x)))
        x = torch.relu(self.bn2(self.conv2(x)))
        x = self.pool(x).squeeze(-1)
        x = self.dropout(x)
        x = self.fc(x)
        return x

# Load full dataset
print("\n📂 Loading FULL dataset...")
X = np.load(DATA_PROCESSED / "X_sequences.npy")
y = np.load(DATA_PROCESSED / "y_labels.npy")

print(f"✅ Loaded {len(X):,} sequences")
print(f"   Shape: {X.shape}")
print(f"   Delay ratio: {y.mean():.2%}")

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n📊 Dataset split:")
print(f"   Training: {len(X_train):,} samples")
print(f"   Test: {len(X_test):,} samples")

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
print(f"\n🧠 Training 1D CNN on full dataset...")
print(f"   Batch size: 512")
print(f"   Epochs: 15")

model = CNN1D(X_train.shape[2]).to(DEVICE)
criterion = nn.BCEWithLogitsLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

start_time = time.time()

epochs = 15
for epoch in range(epochs):
    model.train()
    epoch_loss = 0
    for batch_X, batch_y in train_loader:
        batch_X, batch_y = batch_X.to(DEVICE), batch_y.to(DEVICE)
        optimizer.zero_grad()
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()
        epoch_loss += loss.item()
    print(f"  Epoch {epoch+1}/{epochs} - Loss: {epoch_loss/len(train_loader):.4f}")

training_time = time.time() - start_time

# Evaluate
print(f"\n📊 Evaluating...")
model.eval()
all_preds = []
all_proba = []

with torch.no_grad():
    for batch_X, batch_y in test_loader:
        batch_X = batch_X.to(DEVICE)
        outputs = model(batch_X)
        probs = torch.sigmoid(outputs)
        preds = (probs > 0.5).float()
        all_preds.extend(preds.cpu().numpy())
        all_proba.extend(probs.cpu().numpy())

y_pred = np.array(all_preds).flatten()
y_proba = np.array(all_proba).flatten()

# Metrics
accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, zero_division=0)
recall = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)
roc_auc = roc_auc_score(y_test, y_proba)

print("\n" + "=" * 80)
print("🏆 PRODUCTION MODEL PERFORMANCE (FULL DATASET)")
print("=" * 80)
print(f"Model: 1D CNN")
print(f"Training time: {training_time:.2f}s ({training_time/60:.1f} minutes)")
print(f"Training samples: {len(X_train):,}")
print(f"Test samples: {len(X_test):,}")
print(f"\n📊 Final Metrics:")
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

# Save production model
print(f"\n💾 Saving production model...")
torch.save(model.state_dict(), MODELS_DIR / 'cnn_production_model.pth')
torch.save(model, MODELS_DIR / 'cnn_production_model_complete.pth')

# Save model info
with open(MODELS_DIR / "cnn_production_info.json", 'w') as f:
    json.dump({
        'model_type': '1D CNN',
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'training_time_seconds': training_time,
        'hyperparameters': {
            'input_channels': X_train.shape[2],
            'conv1_filters': 64,
            'conv2_filters': 128,
            'dropout': 0.3,
            'batch_size': 512,
            'epochs': 15,
            'learning_rate': 0.001
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
        'files': ['cnn_production_model.pth', 'cnn_production_model_complete.pth']
    }, f, indent=2)

print("\n" + "=" * 80)
print("✅ PRODUCTION MODEL READY!")
print("=" * 80)
print(f"📁 Files saved:")
print(f"   - cnn_production_model.pth")
print(f"   - cnn_production_model_complete.pth")
print(f"   - cnn_production_info.json")
print(f"\n🏆 PRODUCTION MODEL: 1D CNN")
print(f"   ✅ Trained on {len(X_train):,} samples")
print(f"   ✅ F1 Score: {f1:.4f}")
print(f"   ✅ ROC-AUC: {roc_auc:.4f}")
print(f"   ✅ Ready for production deployment")
print("=" * 80)
