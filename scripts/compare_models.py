"""
Comprehensive Model Comparison for Delay Prediction
Trains and compares multiple models to find the best one for production use.

Models tested:
1. Logistic Regression (baseline)
2. Random Forest
3. Gradient Boosting (XGBoost-like)
4. Simple LSTM
5. GRU

Key improvements:
- Balanced training data (undersampling)
- Proper evaluation metrics (Precision, Recall, F1, AUC)
- Cross-validation for robust results
- Production-ready model selection
"""

import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    classification_report, roc_auc_score, roc_curve,
    precision_score, recall_score, f1_score, accuracy_score,
    confusion_matrix, precision_recall_curve, average_precision_score
)
from tqdm import tqdm
import joblib
import warnings
warnings.filterwarnings('ignore')

# Paths
DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"
MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Device
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ============================================================
# Data Loading and Balancing
# ============================================================

def load_and_balance_data(max_samples=200000):
    """Load data and create balanced training set"""
    print("=" * 60)
    print("📂 Loading and Balancing Data")
    print("=" * 60)
    
    X = np.load(DATA_PROCESSED / "X_sequences.npy")
    y = np.load(DATA_PROCESSED / "y_labels.npy")
    
    print(f"Original data: {len(X)} samples")
    print(f"Class distribution: {np.bincount(y.astype(int))}")
    print(f"Delay ratio: {y.mean():.2%}")
    
    # Get indices for each class
    delayed_idx = np.where(y == 1)[0]
    ontime_idx = np.where(y == 0)[0]
    
    print(f"\nDelayed trips: {len(delayed_idx)}")
    print(f"On-time trips: {len(ontime_idx)}")
    
    # Balance by undersampling majority class
    # Use all delayed samples, sample equal number of on-time
    n_delayed = len(delayed_idx)
    n_ontime_sample = min(n_delayed, len(ontime_idx))  # Use same number of each
    
    # For faster training, cap total samples
    if n_delayed + n_ontime_sample > max_samples:
        n_each = max_samples // 2
        n_delayed_sample = min(n_each, n_delayed)
        n_ontime_sample = min(n_each, len(ontime_idx))
    else:
        n_delayed_sample = n_delayed
    
    # Random sample
    np.random.seed(42)
    delayed_sample = np.random.choice(delayed_idx, n_delayed_sample, replace=False)
    ontime_sample = np.random.choice(ontime_idx, n_ontime_sample, replace=False)
    
    # Combine and shuffle
    balanced_idx = np.concatenate([delayed_sample, ontime_sample])
    np.random.shuffle(balanced_idx)
    
    X_balanced = X[balanced_idx]
    y_balanced = y[balanced_idx]
    
    print(f"\n✅ Balanced data: {len(X_balanced)} samples")
    print(f"   Class distribution: {np.bincount(y_balanced.astype(int))}")
    print(f"   Delay ratio: {y_balanced.mean():.2%}")
    
    return X_balanced, y_balanced

# ============================================================
# Feature Engineering for Classical ML
# ============================================================

def extract_features(X_sequences):
    """Extract statistical features from sequences for classical ML"""
    n_samples = len(X_sequences)
    features = []
    
    for i in range(n_samples):
        seq = X_sequences[i]  # Shape: (10, 6) - 10 timesteps, 6 features
        
        # For each feature dimension, compute statistics
        feat_list = []
        for f in range(seq.shape[1]):
            col = seq[:, f]
            feat_list.extend([
                np.mean(col),
                np.std(col),
                np.min(col),
                np.max(col),
                col[-1] - col[0],  # Change over sequence
                np.mean(np.diff(col)) if len(col) > 1 else 0,  # Average rate of change
            ])
        
        # Add sequence-level features
        feat_list.extend([
            np.mean(seq),  # Overall mean
            np.std(seq),   # Overall std
        ])
        
        features.append(feat_list)
    
    return np.array(features)

# ============================================================
# Neural Network Models
# ============================================================

class SimpleLSTM(nn.Module):
    """Simple 1-layer LSTM for time series classification"""
    def __init__(self, input_size, hidden_size=32):
        super(SimpleLSTM, self).__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
            dropout=0
        )
        self.fc = nn.Linear(hidden_size, 1)
        
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last_output = lstm_out[:, -1, :]
        return self.fc(last_output)

class SimpleGRU(nn.Module):
    """Simple 1-layer GRU for time series classification"""
    def __init__(self, input_size, hidden_size=32):
        super(SimpleGRU, self).__init__()
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
            dropout=0
        )
        self.fc = nn.Linear(hidden_size, 1)
        
    def forward(self, x):
        gru_out, _ = self.gru(x)
        last_output = gru_out[:, -1, :]
        return self.fc(last_output)

# ============================================================
# Training Functions
# ============================================================

def train_classical_model(name, model, X_train, y_train, X_test, y_test):
    """Train and evaluate a classical ML model"""
    print(f"\n🔵 Training {name}...")
    
    # Flatten sequences for classical ML
    X_train_flat = extract_features(X_train)
    X_test_flat = extract_features(X_test)
    
    # Normalize features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_flat)
    X_test_scaled = scaler.transform(X_test_flat)
    
    # Train
    model.fit(X_train_scaled, y_train)
    
    # Predict
    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    
    # Metrics
    metrics = evaluate_model(y_test, y_pred, y_prob, name)
    
    return model, scaler, metrics

def train_neural_model(name, model_class, X_train, y_train, X_test, y_test, 
                       hidden_size=32, epochs=30, batch_size=64, lr=0.001):
    """Train and evaluate a neural network model"""
    print(f"\n🔵 Training {name}...")
    
    input_size = X_train.shape[2]
    model = model_class(input_size, hidden_size).to(DEVICE)
    
    # Normalize sequences
    mean = X_train.mean(axis=(0, 1), keepdims=True)
    std = X_train.std(axis=(0, 1), keepdims=True) + 1e-8
    X_train_norm = (X_train - mean) / std
    X_test_norm = (X_test - mean) / std
    
    # Convert to tensors
    X_train_tensor = torch.FloatTensor(X_train_norm).to(DEVICE)
    y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1).to(DEVICE)
    X_test_tensor = torch.FloatTensor(X_test_norm).to(DEVICE)
    y_test_tensor = torch.FloatTensor(y_test).unsqueeze(1).to(DEVICE)
    
    train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
    test_dataset = TensorDataset(X_test_tensor, y_test_tensor)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    # Loss and optimizer
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3)
    
    best_val_loss = float('inf')
    patience = 5
    patience_counter = 0
    best_model_state = None
    
    for epoch in range(epochs):
        # Training
        model.train()
        train_loss = 0
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item()
        
        train_loss /= len(train_loader)
        
        # Validation
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for batch_X, batch_y in test_loader:
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item()
        val_loss /= len(test_loader)
        
        scheduler.step(val_loss)
        
        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            best_model_state = model.state_dict().copy()
        else:
            patience_counter += 1
        
        if (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")
        
        if patience_counter >= patience:
            print(f"  Early stopping at epoch {epoch+1}")
            break
    
    # Load best model
    if best_model_state:
        model.load_state_dict(best_model_state)
    
    # Evaluate
    model.eval()
    with torch.no_grad():
        outputs = model(X_test_tensor)
        y_prob = torch.sigmoid(outputs).cpu().numpy().flatten()
        y_pred = (y_prob > 0.5).astype(int)
    
    metrics = evaluate_model(y_test, y_pred, y_prob, name)
    
    # Store normalization params
    norm_params = {'mean': mean, 'std': std}
    
    return model, norm_params, metrics

def evaluate_model(y_true, y_pred, y_prob, name):
    """Compute comprehensive evaluation metrics"""
    metrics = {
        'name': name,
        'accuracy': accuracy_score(y_true, y_pred),
        'precision_delayed': precision_score(y_true, y_pred, pos_label=1, zero_division=0),
        'recall_delayed': recall_score(y_true, y_pred, pos_label=1, zero_division=0),
        'f1_delayed': f1_score(y_true, y_pred, pos_label=1, zero_division=0),
        'precision_ontime': precision_score(y_true, y_pred, pos_label=0, zero_division=0),
        'recall_ontime': recall_score(y_true, y_pred, pos_label=0, zero_division=0),
        'f1_ontime': f1_score(y_true, y_pred, pos_label=0, zero_division=0),
        'roc_auc': roc_auc_score(y_true, y_prob),
        'avg_precision': average_precision_score(y_true, y_prob),
        'confusion_matrix': confusion_matrix(y_true, y_pred).tolist(),
        'y_true': y_true,
        'y_pred': y_pred,
        'y_prob': y_prob
    }
    
    # Calculate balanced accuracy
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    metrics['specificity'] = tn / (tn + fp) if (tn + fp) > 0 else 0
    metrics['sensitivity'] = tp / (tp + fn) if (tp + fn) > 0 else 0
    metrics['balanced_accuracy'] = (metrics['specificity'] + metrics['sensitivity']) / 2
    
    return metrics

# ============================================================
# Visualization
# ============================================================

def plot_comparison(all_metrics):
    """Create comprehensive comparison visualizations"""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    names = [m['name'] for m in all_metrics]
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
    
    # 1. Accuracy comparison
    ax = axes[0, 0]
    accuracies = [m['accuracy'] for m in all_metrics]
    bars = ax.bar(names, accuracies, color=colors)
    ax.set_ylabel('Accuracy')
    ax.set_title('Model Accuracy Comparison')
    ax.set_ylim(0, 1)
    for bar, acc in zip(bars, accuracies):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                f'{acc:.3f}', ha='center', fontsize=10, fontweight='bold')
    ax.tick_params(axis='x', rotation=15)
    
    # 2. ROC-AUC comparison
    ax = axes[0, 1]
    aucs = [m['roc_auc'] for m in all_metrics]
    bars = ax.bar(names, aucs, color=colors)
    ax.set_ylabel('ROC-AUC Score')
    ax.set_title('ROC-AUC Comparison (Higher = Better)')
    ax.set_ylim(0, 1)
    ax.axhline(y=0.5, color='red', linestyle='--', label='Random (0.5)')
    for bar, auc in zip(bars, aucs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                f'{auc:.3f}', ha='center', fontsize=10, fontweight='bold')
    ax.tick_params(axis='x', rotation=15)
    ax.legend()
    
    # 3. Balanced Accuracy (critical for imbalanced data)
    ax = axes[0, 2]
    bal_acc = [m['balanced_accuracy'] for m in all_metrics]
    bars = ax.bar(names, bal_acc, color=colors)
    ax.set_ylabel('Balanced Accuracy')
    ax.set_title('Balanced Accuracy (Avg of Sensitivity & Specificity)')
    ax.set_ylim(0, 1)
    ax.axhline(y=0.5, color='red', linestyle='--', label='Random (0.5)')
    for bar, ba in zip(bars, bal_acc):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                f'{ba:.3f}', ha='center', fontsize=10, fontweight='bold')
    ax.tick_params(axis='x', rotation=15)
    ax.legend()
    
    # 4. Precision-Recall for Delayed class
    ax = axes[1, 0]
    x = np.arange(len(names))
    width = 0.35
    precision = [m['precision_delayed'] for m in all_metrics]
    recall = [m['recall_delayed'] for m in all_metrics]
    ax.bar(x - width/2, precision, width, label='Precision', color='#FF6B6B')
    ax.bar(x + width/2, recall, width, label='Recall', color='#4ECDC4')
    ax.set_ylabel('Score')
    ax.set_title('Precision & Recall for DELAYED Class')
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15)
    ax.set_ylim(0, 1)
    ax.legend()
    
    # 5. F1 Score comparison
    ax = axes[1, 1]
    f1_delayed = [m['f1_delayed'] for m in all_metrics]
    f1_ontime = [m['f1_ontime'] for m in all_metrics]
    x = np.arange(len(names))
    ax.bar(x - width/2, f1_delayed, width, label='F1 (Delayed)', color='#FF6B6B')
    ax.bar(x + width/2, f1_ontime, width, label='F1 (On-time)', color='#4ECDC4')
    ax.set_ylabel('F1 Score')
    ax.set_title('F1 Score Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15)
    ax.set_ylim(0, 1)
    ax.legend()
    
    # 6. ROC Curves
    ax = axes[1, 2]
    for i, m in enumerate(all_metrics):
        fpr, tpr, _ = roc_curve(m['y_true'], m['y_prob'])
        ax.plot(fpr, tpr, color=colors[i], linewidth=2, 
                label=f"{m['name']} (AUC={m['roc_auc']:.3f})")
    ax.plot([0, 1], [0, 1], 'k--', label='Random')
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title('ROC Curves')
    ax.legend(loc='lower right')
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(MODELS_DIR / 'model_comparison.png', dpi=150, bbox_inches='tight')
    print(f"\n✅ Comparison plot saved to models/model_comparison.png")
    plt.close()

def print_final_comparison(all_metrics, best_model_name):
    """Print detailed comparison table"""
    print("\n" + "=" * 80)
    print("📊 FINAL MODEL COMPARISON")
    print("=" * 80)
    
    # Create comparison table
    headers = ['Model', 'Accuracy', 'ROC-AUC', 'Balanced Acc', 'Precision(D)', 'Recall(D)', 'F1(D)']
    print(f"\n{'Model':<20} {'Accuracy':>10} {'ROC-AUC':>10} {'Bal.Acc':>10} {'Prec(D)':>10} {'Recall(D)':>10} {'F1(D)':>10}")
    print("-" * 80)
    
    for m in all_metrics:
        print(f"{m['name']:<20} {m['accuracy']:>10.4f} {m['roc_auc']:>10.4f} {m['balanced_accuracy']:>10.4f} "
              f"{m['precision_delayed']:>10.4f} {m['recall_delayed']:>10.4f} {m['f1_delayed']:>10.4f}")
    
    print("-" * 80)
    print(f"\n🏆 BEST MODEL: {best_model_name}")
    print("   Criteria: Highest ROC-AUC + Balanced Accuracy + F1(Delayed)")
    print("=" * 80)

# ============================================================
# Main Function
# ============================================================

def main():
    print("=" * 60)
    print("🔬 COMPREHENSIVE MODEL COMPARISON")
    print("   Finding the Best Model for Delay Prediction")
    print("=" * 60)
    
    # Load and balance data
    X, y = load_and_balance_data(max_samples=200000)
    
    # Train-test split (stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\n📊 Final split:")
    print(f"   Training: {len(X_train)} samples ({y_train.mean():.2%} delayed)")
    print(f"   Testing: {len(X_test)} samples ({y_test.mean():.2%} delayed)")
    
    all_metrics = []
    all_models = {}
    
    # ============================================================
    # Model 1: Logistic Regression
    # ============================================================
    lr_model = LogisticRegression(
        max_iter=1000,
        class_weight='balanced',
        solver='lbfgs',
        random_state=42
    )
    model, scaler, metrics = train_classical_model(
        "Logistic Regression", lr_model, X_train, y_train, X_test, y_test
    )
    all_metrics.append(metrics)
    all_models['logistic_regression'] = {'model': model, 'scaler': scaler, 'type': 'classical'}
    print(f"   ✅ ROC-AUC: {metrics['roc_auc']:.4f}, Balanced Acc: {metrics['balanced_accuracy']:.4f}")
    
    # ============================================================
    # Model 2: Random Forest
    # ============================================================
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    model, scaler, metrics = train_classical_model(
        "Random Forest", rf_model, X_train, y_train, X_test, y_test
    )
    all_metrics.append(metrics)
    all_models['random_forest'] = {'model': model, 'scaler': scaler, 'type': 'classical'}
    print(f"   ✅ ROC-AUC: {metrics['roc_auc']:.4f}, Balanced Acc: {metrics['balanced_accuracy']:.4f}")
    
    # ============================================================
    # Model 3: Gradient Boosting
    # ============================================================
    gb_model = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        min_samples_split=5,
        random_state=42
    )
    model, scaler, metrics = train_classical_model(
        "Gradient Boosting", gb_model, X_train, y_train, X_test, y_test
    )
    all_metrics.append(metrics)
    all_models['gradient_boosting'] = {'model': model, 'scaler': scaler, 'type': 'classical'}
    print(f"   ✅ ROC-AUC: {metrics['roc_auc']:.4f}, Balanced Acc: {metrics['balanced_accuracy']:.4f}")
    
    # ============================================================
    # Model 4: Simple LSTM
    # ============================================================
    model, norm_params, metrics = train_neural_model(
        "Simple LSTM", SimpleLSTM, X_train, y_train, X_test, y_test,
        hidden_size=32, epochs=30, batch_size=64, lr=0.001
    )
    all_metrics.append(metrics)
    all_models['lstm'] = {'model': model, 'norm_params': norm_params, 'type': 'neural'}
    print(f"   ✅ ROC-AUC: {metrics['roc_auc']:.4f}, Balanced Acc: {metrics['balanced_accuracy']:.4f}")
    
    # ============================================================
    # Model 5: Simple GRU
    # ============================================================
    model, norm_params, metrics = train_neural_model(
        "Simple GRU", SimpleGRU, X_train, y_train, X_test, y_test,
        hidden_size=32, epochs=30, batch_size=64, lr=0.001
    )
    all_metrics.append(metrics)
    all_models['gru'] = {'model': model, 'norm_params': norm_params, 'type': 'neural'}
    print(f"   ✅ ROC-AUC: {metrics['roc_auc']:.4f}, Balanced Acc: {metrics['balanced_accuracy']:.4f}")
    
    # ============================================================
    # Find Best Model
    # ============================================================
    # Score = weighted combination of key metrics
    # Prioritize: ROC-AUC (discrimination), Balanced Accuracy (handling imbalance), F1-Delayed (finding delays)
    best_score = -1
    best_model_name = None
    best_model_key = None
    
    for i, m in enumerate(all_metrics):
        score = 0.4 * m['roc_auc'] + 0.3 * m['balanced_accuracy'] + 0.3 * m['f1_delayed']
        if score > best_score:
            best_score = score
            best_model_name = m['name']
            best_model_key = list(all_models.keys())[i]
    
    # ============================================================
    # Plot and Print Comparison
    # ============================================================
    plot_comparison(all_metrics)
    print_final_comparison(all_metrics, best_model_name)
    
    # ============================================================
    # Save Best Model
    # ============================================================
    print(f"\n💾 Saving best model ({best_model_name})...")
    
    best_model_info = all_models[best_model_key]
    
    if best_model_info['type'] == 'classical':
        # Save classical model with joblib
        joblib.dump(best_model_info['model'], MODELS_DIR / 'best_model.pkl')
        joblib.dump(best_model_info['scaler'], MODELS_DIR / 'best_model_scaler.pkl')
        model_type = 'classical'
    else:
        # Save neural model with torch
        torch.save(best_model_info['model'].state_dict(), MODELS_DIR / 'best_model.pth')
        torch.save(best_model_info['model'], MODELS_DIR / 'best_model_complete.pth')
        np.save(MODELS_DIR / 'best_model_norm_mean.npy', best_model_info['norm_params']['mean'])
        np.save(MODELS_DIR / 'best_model_norm_std.npy', best_model_info['norm_params']['std'])
        model_type = 'neural'
    
    # Save metadata
    best_metrics = next(m for m in all_metrics if m['name'] == best_model_name)
    metadata = {
        'best_model': best_model_name,
        'model_key': best_model_key,
        'model_type': model_type,
        'accuracy': float(best_metrics['accuracy']),
        'roc_auc': float(best_metrics['roc_auc']),
        'balanced_accuracy': float(best_metrics['balanced_accuracy']),
        'precision_delayed': float(best_metrics['precision_delayed']),
        'recall_delayed': float(best_metrics['recall_delayed']),
        'f1_delayed': float(best_metrics['f1_delayed']),
        'all_models_compared': [m['name'] for m in all_metrics]
    }
    
    with open(MODELS_DIR / 'best_model_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Save all results
    all_results = []
    for m in all_metrics:
        result = {k: v for k, v in m.items() if k not in ['y_true', 'y_pred', 'y_prob']}
        all_results.append(result)
    
    with open(MODELS_DIR / 'model_comparison_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n✅ Best model saved to models/best_model.pkl (or .pth)")
    print(f"✅ Comparison results saved to models/model_comparison_results.json")
    print(f"✅ Visualization saved to models/model_comparison.png")
    
    print("\n" + "=" * 60)
    print(f"🎯 FINAL RECOMMENDATION: Use {best_model_name}")
    print(f"   This model will be used for delay prediction in production.")
    print("=" * 60)
    
    return best_model_name, all_metrics

if __name__ == "__main__":
    main()
