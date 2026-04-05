"""
Train Baseline ML Models
- Logistic Regression
- Random Forest
- Evaluate and compare performance
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
import joblib

# Paths
DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"
MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def load_processed_data():
    """Load preprocessed sequences and labels"""
    print("📂 Loading processed data...")
    
    X = np.load(DATA_PROCESSED / "X_sequences.npy")
    y = np.load(DATA_PROCESSED / "y_labels.npy")
    
    with open(DATA_PROCESSED / "metadata.json", 'r') as f:
        metadata = json.load(f)
    
    print(f"✅ Loaded {len(X)} sequences")
    print(f"   Shape: {X.shape}")
    print(f"   Delay ratio: {metadata['delay_ratio']:.2%}")
    
    return X, y, metadata

def flatten_sequences(X):
    """Flatten sequences for traditional ML models"""
    n_samples, seq_len, n_features = X.shape
    return X.reshape(n_samples, seq_len * n_features)

def train_logistic_regression(X_train, y_train, X_test, y_test):
    """Train Logistic Regression model"""
    print("\n🔵 Training Logistic Regression...")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model
    model = LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')
    model.fit(X_train_scaled, y_train)
    
    # Predictions
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    # Evaluate
    print("\n📊 Logistic Regression Results:")
    print(classification_report(y_test, y_pred, target_names=['On-Time', 'Delayed']))
    
    auc = roc_auc_score(y_test, y_proba)
    print(f"ROC-AUC Score: {auc:.4f}")
    
    # Save model
    joblib.dump(model, MODELS_DIR / "logistic_regression.pkl")
    joblib.dump(scaler, MODELS_DIR / "scaler_lr.pkl")
    print(f"✅ Model saved to {MODELS_DIR / 'logistic_regression.pkl'}")
    
    return model, scaler, y_pred, y_proba, auc

def train_random_forest(X_train, y_train, X_test, y_test):
    """Train Random Forest model"""
    print("\n🌲 Training Random Forest...")
    
    # Train model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced',
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    # Predictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    # Evaluate
    print("\n📊 Random Forest Results:")
    print(classification_report(y_test, y_pred, target_names=['On-Time', 'Delayed']))
    
    auc = roc_auc_score(y_test, y_proba)
    print(f"ROC-AUC Score: {auc:.4f}")
    
    # Feature importance
    print("\n🔍 Top 10 Feature Importances:")
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:10]
    for i, idx in enumerate(indices, 1):
        print(f"{i}. Feature {idx}: {importances[idx]:.4f}")
    
    # Save model
    joblib.dump(model, MODELS_DIR / "random_forest.pkl")
    print(f"✅ Model saved to {MODELS_DIR / 'random_forest.pkl'}")
    
    return model, y_pred, y_proba, auc

def plot_results(y_test, lr_proba, rf_proba, lr_auc, rf_auc):
    """Plot ROC curves and confusion matrices"""
    print("\n📈 Generating plots...")
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # ROC Curves
    ax1 = axes[0]
    
    # Logistic Regression
    fpr_lr, tpr_lr, _ = roc_curve(y_test, lr_proba)
    ax1.plot(fpr_lr, tpr_lr, label=f'Logistic Regression (AUC={lr_auc:.3f})', linewidth=2)
    
    # Random Forest
    fpr_rf, tpr_rf, _ = roc_curve(y_test, rf_proba)
    ax1.plot(fpr_rf, tpr_rf, label=f'Random Forest (AUC={rf_auc:.3f})', linewidth=2)
    
    # Diagonal
    ax1.plot([0, 1], [0, 1], 'k--', label='Random Classifier')
    
    ax1.set_xlabel('False Positive Rate')
    ax1.set_ylabel('True Positive Rate')
    ax1.set_title('ROC Curves - Baseline Models')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Confusion Matrix (Random Forest)
    ax2 = axes[1]
    rf_model = joblib.load(MODELS_DIR / "random_forest.pkl")
    y_pred_rf = rf_model.predict(flatten_sequences(np.load(DATA_PROCESSED / "X_sequences.npy")))
    
    # Use only test set for confusion matrix
    test_size = len(y_test)
    cm = confusion_matrix(y_test, y_pred_rf[-test_size:])
    
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax2,
                xticklabels=['On-Time', 'Delayed'],
                yticklabels=['On-Time', 'Delayed'])
    ax2.set_xlabel('Predicted')
    ax2.set_ylabel('Actual')
    ax2.set_title('Confusion Matrix - Random Forest')
    
    plt.tight_layout()
    plt.savefig(MODELS_DIR / 'baseline_results.png', dpi=150, bbox_inches='tight')
    print(f"✅ Plot saved to {MODELS_DIR / 'baseline_results.png'}")
    
    plt.show()

def main():
    """Main training pipeline"""
    print("=" * 60)
    print("🤖 Training Baseline ML Models for Delay Prediction")
    print("=" * 60)
    
    # Load data
    X, y, metadata = load_processed_data()
    
    # Flatten sequences for traditional ML
    X_flat = flatten_sequences(X)
    print(f"\n📐 Flattened shape: {X_flat.shape}")
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_flat, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\n📊 Dataset split:")
    print(f"   Training: {len(X_train)} samples ({y_train.mean():.2%} delayed)")
    print(f"   Testing: {len(X_test)} samples ({y_test.mean():.2%} delayed)")
    
    # Train Logistic Regression
    lr_model, scaler, lr_pred, lr_proba, lr_auc = train_logistic_regression(
        X_train, y_train, X_test, y_test
    )
    
    # Train Random Forest
    rf_model, rf_pred, rf_proba, rf_auc = train_random_forest(
        X_train, y_train, X_test, y_test
    )
    
    # Plot results
    plot_results(y_test, lr_proba, rf_proba, lr_auc, rf_auc)
    
    # Save results
    results = {
        'logistic_regression': {
            'auc': float(lr_auc),
            'model_path': 'logistic_regression.pkl'
        },
        'random_forest': {
            'auc': float(rf_auc),
            'model_path': 'random_forest.pkl'
        },
        'best_model': 'random_forest' if rf_auc > lr_auc else 'logistic_regression'
    }
    
    with open(MODELS_DIR / 'baseline_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("✅ Baseline training complete!")
    print(f"📊 Best model: {results['best_model'].upper()}")
    print("=" * 60)

if __name__ == "__main__":
    main()
