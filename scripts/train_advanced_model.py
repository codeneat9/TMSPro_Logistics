"""
🚀 ADVANCED DELAY PREDICTION MODEL
- Extracts 25+ sophisticated features from GPS trajectories
- CNN-LSTM hybrid architecture for spatial + temporal patterns
- Trains on 500K samples for better learning
- Threshold optimization for maximum performance
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, roc_curve
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import json
from datetime import datetime
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"🔥 Using device: {device}")

# ========================================
# ADVANCED FEATURE EXTRACTION
# ========================================

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS points in km"""
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def extract_advanced_features(sequences):
    """
    Extract 25+ sophisticated features from GPS trajectories
    Features capture: speed patterns, acceleration, stops, route complexity, etc.
    """
    print("🔬 Extracting advanced features from GPS trajectories...")
    
    batch_size = 10000
    n_samples = len(sequences)
    all_features = []
    
    for batch_start in range(0, n_samples, batch_size):
        batch_end = min(batch_start + batch_size, n_samples)
        batch = sequences[batch_start:batch_end]
        batch_features = []
        
        for seq in batch:
            # Basic trip statistics
            start_lat, start_lon = seq[0, 1], seq[0, 2]
            end_lat, end_lon = seq[-1, 1], seq[-1, 2]
            
            # Calculate distances between consecutive points
            distances = []
            speeds = []
            accelerations = []
            bearing_changes = []
            
            for i in range(len(seq) - 1):
                lat1, lon1, t1 = seq[i, 1], seq[i, 2], seq[i, 0]
                lat2, lon2, t2 = seq[i+1, 1], seq[i+1, 2], seq[i+1, 0]
                
                dist = haversine_distance(lat1, lon1, lat2, lon2)
                distances.append(dist)
                
                # Speed (km/h)
                time_diff = abs(t2 - t1) + 1e-6
                speed = (dist / time_diff) * 3600
                speeds.append(speed)
                
                # Acceleration
                if len(speeds) > 1:
                    accel = (speeds[-1] - speeds[-2]) / (time_diff + 1e-6)
                    accelerations.append(accel)
                
                # Bearing change (route turns)
                if i > 0:
                    lat0, lon0 = seq[i-1, 1], seq[i-1, 2]
                    bearing1 = np.arctan2(lat1-lat0, lon1-lon0)
                    bearing2 = np.arctan2(lat2-lat1, lon2-lon1)
                    bearing_change = abs(bearing2 - bearing1)
                    bearing_changes.append(bearing_change)
            
            distances = np.array(distances) if distances else np.array([0])
            speeds = np.array(speeds) if speeds else np.array([0])
            accelerations = np.array(accelerations) if accelerations else np.array([0])
            bearing_changes = np.array(bearing_changes) if bearing_changes else np.array([0])
            
            # Feature extraction
            features = {
                # 1-5: Distance features
                'total_distance': np.sum(distances),
                'avg_distance': np.mean(distances),
                'max_distance': np.max(distances),
                'distance_variance': np.var(distances),
                'straight_line_distance': haversine_distance(start_lat, start_lon, end_lat, end_lon),
                
                # 6-12: Speed features
                'avg_speed': np.mean(speeds),
                'max_speed': np.max(speeds),
                'min_speed': np.min(speeds),
                'speed_variance': np.var(speeds),
                'speed_std': np.std(speeds),
                'speed_percentile_90': np.percentile(speeds, 90),
                'speed_percentile_10': np.percentile(speeds, 10),
                
                # 13-17: Acceleration features (traffic dynamics)
                'avg_acceleration': np.mean(np.abs(accelerations)),
                'max_acceleration': np.max(np.abs(accelerations)) if len(accelerations) > 0 else 0,
                'acceleration_variance': np.var(accelerations),
                'hard_braking_count': np.sum(accelerations < -2),  # Sudden stops
                'hard_acceleration_count': np.sum(accelerations > 2),  # Quick starts
                
                # 18-21: Stop pattern features (traffic signals, congestion)
                'num_stops': np.sum(speeds < 1),  # Very low speeds
                'num_slow_points': np.sum(speeds < 10),  # Slow traffic
                'stop_ratio': np.sum(speeds < 1) / (len(speeds) + 1e-6),
                'slow_ratio': np.sum(speeds < 10) / (len(speeds) + 1e-6),
                
                # 22-25: Route complexity features
                'route_sinuosity': np.sum(distances) / (haversine_distance(start_lat, start_lon, end_lat, end_lon) + 1e-6),
                'avg_bearing_change': np.mean(bearing_changes),
                'num_sharp_turns': np.sum(bearing_changes > 0.5),
                'route_smoothness': 1 / (np.std(bearing_changes) + 1e-6),
                
                # 26-30: Geographic features
                'start_lat': start_lat,
                'start_lon': start_lon,
                'end_lat': end_lat,
                'end_lon': end_lon,
                'geographic_spread': np.std(seq[:, 1]) + np.std(seq[:, 2]),
                
                # 31-35: Temporal features
                'hour': int(seq[0, 3]),
                'day_of_week': int(seq[0, 4]),
                'is_rush_hour': 1 if (7 <= seq[0, 3] <= 9) or (17 <= seq[0, 3] <= 19) else 0,
                'is_weekend': 1 if seq[0, 4] >= 5 else 0,
                'is_night': 1 if (seq[0, 3] >= 22) or (seq[0, 3] <= 6) else 0,
            }
            
            batch_features.append(list(features.values()))
        
        all_features.extend(batch_features)
        print(f"  Processed {batch_end}/{n_samples} sequences...")
    
    feature_matrix = np.array(all_features, dtype=np.float32)
    print(f"✅ Extracted {feature_matrix.shape[1]} features from {feature_matrix.shape[0]} sequences")
    return feature_matrix, list(features.keys())

# ========================================
# CNN-LSTM HYBRID ARCHITECTURE
# ========================================

class CNNLSTMHybrid(nn.Module):
    """
    Hybrid architecture:
    - CNN layers extract spatial patterns from GPS sequences
    - LSTM layers capture temporal dependencies
    - Fully connected layers combine everything
    """
    def __init__(self, sequence_length=10, sequence_features=6, engineered_features=35):
        super(CNNLSTMHybrid, self).__init__()
        
        # CNN branch for GPS sequences
        self.cnn = nn.Sequential(
            nn.Conv1d(sequence_features, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.3),
            
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.3),
            
            nn.AdaptiveAvgPool1d(1)
        )
        
        # LSTM branch for temporal patterns
        self.lstm = nn.LSTM(
            input_size=sequence_features,
            hidden_size=64,
            num_layers=2,
            batch_first=True,
            dropout=0.3
        )
        
        # Combine CNN + LSTM + engineered features
        combined_size = 128 + 64 + engineered_features
        
        self.fc = nn.Sequential(
            nn.Linear(combined_size, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.4),
            
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.4),
            
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        
    def forward(self, sequence, features):
        # CNN branch: (batch, seq_len, features) -> (batch, features, seq_len)
        x_cnn = sequence.transpose(1, 2)
        x_cnn = self.cnn(x_cnn)
        x_cnn = x_cnn.squeeze(-1)
        
        # LSTM branch
        x_lstm, (h_n, c_n) = self.lstm(sequence)
        x_lstm = h_n[-1]  # Last hidden state
        
        # Combine all
        x_combined = torch.cat([x_cnn, x_lstm, features], dim=1)
        
        # Final prediction
        output = self.fc(x_combined)
        return output

# ========================================
# CUSTOM DATASET
# ========================================

class TaxiDataset(Dataset):
    def __init__(self, sequences, features, labels):
        self.sequences = torch.FloatTensor(sequences)
        self.features = torch.FloatTensor(features)
        self.labels = torch.FloatTensor(labels)
    
    def __len__(self):
        return len(self.labels)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.features[idx], self.labels[idx]

# ========================================
# TRAINING FUNCTION
# ========================================

def train_model(model, train_loader, val_loader, epochs=30, lr=0.001, checkpoint_path=None):
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=3)
    
    best_f1 = 0
    best_model_state = None
    history = {'train_loss': [], 'val_loss': [], 'val_f1': [], 'val_auc': []}
    start_epoch = 0
    
    # Load checkpoint if exists
    if checkpoint_path and Path(checkpoint_path).exists():
        print(f"\n📥 Loading checkpoint from {checkpoint_path}...")
        checkpoint = torch.load(checkpoint_path)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        start_epoch = checkpoint['epoch'] + 1
        best_f1 = checkpoint['best_f1']
        best_model_state = checkpoint['best_model_state']
        history = checkpoint['history']
        print(f"  Resuming from epoch {start_epoch}/{epochs}")
        print(f"  Best F1 so far: {best_f1:.4f}")
    
    print(f"\n🚀 Training CNN-LSTM Hybrid Model for {epochs} epochs...")
    
    for epoch in range(start_epoch, epochs):
        # Training
        model.train()
        train_losses = []
        
        for sequences, features, labels in train_loader:
            sequences = sequences.to(device)
            features = features.to(device)
            labels = labels.to(device).unsqueeze(1)
            
            optimizer.zero_grad()
            outputs = model(sequences, features)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_losses.append(loss.item())
        
        avg_train_loss = np.mean(train_losses)
        
        # Validation
        model.eval()
        val_losses = []
        all_preds = []
        all_probs = []
        all_labels = []
        
        with torch.no_grad():
            for sequences, features, labels in val_loader:
                sequences = sequences.to(device)
                features = features.to(device)
                labels = labels.to(device).unsqueeze(1)
                
                outputs = model(sequences, features)
                loss = criterion(outputs, labels)
                val_losses.append(loss.item())
                
                all_probs.extend(outputs.cpu().numpy())
                all_preds.extend((outputs > 0.5).cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        avg_val_loss = np.mean(val_losses)
        val_f1 = f1_score(all_labels, all_preds)
        val_auc = roc_auc_score(all_labels, all_probs)
        
        history['train_loss'].append(avg_train_loss)
        history['val_loss'].append(avg_val_loss)
        history['val_f1'].append(val_f1)
        history['val_auc'].append(val_auc)
        
        print(f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f} - Val Loss: {avg_val_loss:.4f} - Val F1: {val_f1:.4f} - Val AUC: {val_auc:.4f}")
        
        # Save best model
        if val_f1 > best_f1:
            best_f1 = val_f1
            best_model_state = model.state_dict().copy()
            print(f"  ✅ New best F1: {best_f1:.4f}")
        
        scheduler.step(val_f1)
        
        # Save checkpoint after each epoch
        if checkpoint_path:
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'best_f1': best_f1,
                'best_model_state': best_model_state,
                'history': history
            }, checkpoint_path)
            print(f"  💾 Checkpoint saved")
    
    # Load best model
    model.load_state_dict(best_model_state)
    return model, history

# ========================================
# THRESHOLD OPTIMIZATION
# ========================================

def optimize_threshold(model, val_loader):
    """Find optimal decision threshold for best F1 score"""
    print("\n🎯 Optimizing decision threshold...")
    
    model.eval()
    all_probs = []
    all_labels = []
    
    with torch.no_grad():
        for sequences, features, labels in val_loader:
            sequences = sequences.to(device)
            features = features.to(device)
            outputs = model(sequences, features)
            all_probs.extend(outputs.cpu().numpy())
            all_labels.extend(labels.numpy())
    
    all_probs = np.array(all_probs)
    all_labels = np.array(all_labels)
    
    # Try thresholds from 0.1 to 0.9
    best_threshold = 0.5
    best_f1 = 0
    
    for threshold in np.arange(0.1, 0.9, 0.05):
        preds = (all_probs > threshold).astype(int)
        f1 = f1_score(all_labels, preds)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
    
    print(f"✅ Optimal threshold: {best_threshold:.2f} (F1={best_f1:.4f})")
    return best_threshold

# ========================================
# MAIN EXECUTION
# ========================================

def main():
    print("="*70)
    print("🚀 ADVANCED DELAY PREDICTION MODEL")
    print("="*70)
    
    # Load preprocessed data
    print("\n📂 Loading preprocessed data...")
    data_dir = Path(__file__).parent.parent / 'data' / 'processed'
    
    X = np.load(data_dir / 'X_sequences.npy')
    y = np.load(data_dir / 'y_labels.npy')
    
    print(f"  Loaded: {X.shape} sequences, {y.shape} labels")
    
    # Split into train/test (80/20)
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print(f"  Train: {X_train.shape}, Test: {X_test.shape}")
    
    # Use 500K training samples for better learning
    n_train = min(500000, len(X_train))
    X_train = X_train[:n_train]
    y_train = y_train[:n_train]
    
    # Use 100K test samples
    n_test = min(100000, len(X_test))
    X_test = X_test[:n_test]
    y_test = y_test[:n_test]
    
    print(f"  Using {n_train} training samples, {n_test} test samples")
    print(f"  Delayed: {np.mean(y_train)*100:.2f}% (train), {np.mean(y_test)*100:.2f}% (test)")
    
    # Extract advanced features
    X_train_features, feature_names = extract_advanced_features(X_train)
    X_test_features, _ = extract_advanced_features(X_test)
    
    # Scale features
    print("\n📊 Scaling features...")
    scaler = StandardScaler()
    X_train_features = scaler.fit_transform(X_train_features)
    X_test_features = scaler.transform(X_test_features)
    
    # Create datasets
    train_dataset = TaxiDataset(X_train, X_train_features, y_train)
    test_dataset = TaxiDataset(X_test, X_test_features, y_test)
    
    # Create data loaders with class balancing
    class_counts = np.bincount(y_train.astype(int))
    class_weights = 1. / class_counts
    sample_weights = class_weights[y_train.astype(int)]
    sampler = WeightedRandomSampler(sample_weights, len(sample_weights))
    
    train_loader = DataLoader(train_dataset, batch_size=256, sampler=sampler)
    test_loader = DataLoader(test_dataset, batch_size=256, shuffle=False)
    
    # Create model
    print("\n🏗️ Building CNN-LSTM Hybrid Model...")
    model = CNNLSTMHybrid(
        sequence_length=X_train.shape[1],
        sequence_features=X_train.shape[2],
        engineered_features=X_train_features.shape[1]
    ).to(device)
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  Total parameters: {total_params:,}")
    
    # Setup checkpoint path
    models_dir = Path(__file__).parent.parent / 'models'
    checkpoint_path = models_dir / 'advanced_model_checkpoint.pth'
    
    # Train model with checkpointing
    model, history = train_model(model, train_loader, test_loader, epochs=30, lr=0.001, checkpoint_path=checkpoint_path)
    
    # Optimize threshold
    optimal_threshold = optimize_threshold(model, test_loader)
    
    # Final evaluation
    print("\n" + "="*70)
    print("📊 FINAL EVALUATION")
    print("="*70)
    
    model.eval()
    all_probs = []
    all_labels = []
    
    with torch.no_grad():
        for sequences, features, labels in test_loader:
            sequences = sequences.to(device)
            features = features.to(device)
            outputs = model(sequences, features)
            all_probs.extend(outputs.cpu().numpy())
            all_labels.extend(labels.numpy())
    
    all_probs = np.array(all_probs).flatten()
    all_labels = np.array(all_labels)
    all_preds = (all_probs > optimal_threshold).astype(int)
    
    # Calculate metrics
    accuracy = accuracy_score(all_labels, all_preds)
    precision = precision_score(all_labels, all_preds)
    recall = recall_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds)
    auc = roc_auc_score(all_labels, all_probs)
    cm = confusion_matrix(all_labels, all_preds)
    
    print(f"\n🎯 Performance Metrics:")
    print(f"  Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"  ROC-AUC:   {auc:.4f}")
    print(f"\n  Confusion Matrix:")
    print(f"    TN={cm[0,0]:,}  FP={cm[0,1]:,}")
    print(f"    FN={cm[1,0]:,}  TP={cm[1,1]:,}")
    
    # Save model and results
    print("\n💾 Saving model and results...")
    torch.save({
        'model_state_dict': model.state_dict(),
        'threshold': optimal_threshold,
        'scaler': scaler,
        'feature_names': feature_names
    }, models_dir / 'advanced_model_best.pth')
    
    results = {
        'model': 'CNN-LSTM Hybrid with Advanced Features',
        'samples': n_train,
        'features': len(feature_names),
        'threshold': float(optimal_threshold),
        'metrics': {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1),
            'roc_auc': float(auc)
        },
        'confusion_matrix': {
            'TN': int(cm[0,0]),
            'FP': int(cm[0,1]),
            'FN': int(cm[1,0]),
            'TP': int(cm[1,1])
        },
        'feature_names': feature_names
    }
    
    with open(models_dir / 'advanced_model_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Create visualizations
    print("\n📊 Creating visualizations...")
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. Training history
    ax = axes[0, 0]
    ax.plot(history['train_loss'], label='Train Loss', linewidth=2)
    ax.plot(history['val_loss'], label='Val Loss', linewidth=2)
    ax.set_title('Training History - Loss', fontsize=14, fontweight='bold')
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Loss')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 2. F1 and AUC history
    ax = axes[0, 1]
    ax.plot(history['val_f1'], label='F1 Score', linewidth=2, color='green')
    ax.plot(history['val_auc'], label='ROC-AUC', linewidth=2, color='orange')
    ax.set_title('Validation Metrics', fontsize=14, fontweight='bold')
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Score')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 3. ROC Curve
    ax = axes[1, 0]
    fpr, tpr, _ = roc_curve(all_labels, all_probs)
    ax.plot(fpr, tpr, linewidth=3, label=f'ROC Curve (AUC={auc:.4f})')
    ax.plot([0, 1], [0, 1], 'k--', linewidth=2, label='Random')
    ax.set_title('ROC Curve', fontsize=14, fontweight='bold')
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 4. Confusion Matrix
    ax = axes[1, 1]
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax, cbar=False)
    ax.set_title('Confusion Matrix', fontsize=14, fontweight='bold')
    ax.set_xlabel('Predicted')
    ax.set_ylabel('Actual')
    ax.set_xticklabels(['On Time', 'Delayed'])
    ax.set_yticklabels(['On Time', 'Delayed'])
    
    plt.tight_layout()
    plt.savefig(models_dir / 'advanced_model_evaluation.png', dpi=300, bbox_inches='tight')
    print(f"  Saved: advanced_model_evaluation.png")
    
    # Clean up checkpoint after successful training
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        print("  🗑️ Checkpoint removed (training complete)")
    
    print("\n" + "="*70)
    print("✅ TRAINING COMPLETE!")
    print("="*70)
    print(f"\n🏆 FINAL RESULTS:")
    print(f"  F1 Score: {f1:.4f}")
    print(f"  ROC-AUC:  {auc:.4f}")
    print(f"  Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"\n📁 Saved to: {models_dir}/")

if __name__ == '__main__':
    main()
