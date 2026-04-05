"""
Train PyTorch LSTM/GRU Model for Delay Prediction
Deep learning approach for time-series delay forecasting
"""

import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, roc_curve
from tqdm import tqdm

# Paths
DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"
MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Optimized Hyperparameters for 1.48M samples
HIDDEN_SIZE = 128  # Increased capacity for complex patterns
NUM_LAYERS = 2
DROPOUT = 0.4  # Slightly higher dropout for larger model
LEARNING_RATE = 0.001  # Lower LR for more stable training
BATCH_SIZE = 256  # Much larger for faster training on big dataset
EPOCHS = 15  # Reduced since larger batches converge faster
PATIENCE = 4  # Early stopping patience
WARMUP_EPOCHS = 2  # Gradual learning rate warmup
FOCAL_GAMMA = 2.0  # Focal loss focusing parameter
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class FocalLoss(nn.Module):
    """Focal Loss for addressing class imbalance
    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)
    """
    def __init__(self, alpha=0.25, gamma=2.0):
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma
        
    def forward(self, inputs, targets):
        # inputs are logits, apply sigmoid
        BCE_loss = nn.functional.binary_cross_entropy_with_logits(inputs, targets, reduction='none')
        pt = torch.exp(-BCE_loss)  # pt = p if y=1, 1-p if y=0
        F_loss = self.alpha * (1-pt)**self.gamma * BCE_loss
        return F_loss.mean()

class LSTMModel(nn.Module):
    """Enhanced LSTM model for delay prediction"""
    def __init__(self, input_size, hidden_size, num_layers, dropout=0.3):
        super(LSTMModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True
        )
        
        # Add batch normalization
        self.batch_norm = nn.BatchNorm1d(hidden_size)
        
        # Add intermediate layer
        self.fc1 = nn.Linear(hidden_size, hidden_size // 2)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(hidden_size // 2, 1)
        # NO sigmoid - using logits for BCEWithLogitsLoss
        
    def forward(self, x):
        # x shape: (batch_size, seq_len, input_size)
        lstm_out, _ = self.lstm(x)
        # Take the last time step
        last_output = lstm_out[:, -1, :]
        
        # Batch normalization
        last_output = self.batch_norm(last_output)
        
        # Intermediate layer with dropout
        out = self.fc1(last_output)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        # Return logits (no sigmoid)
        return out

class GRUModel(nn.Module):
    """Enhanced GRU model for delay prediction"""
    def __init__(self, input_size, hidden_size, num_layers, dropout=0.3):
        super(GRUModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True
        )
        
        # Add batch normalization
        self.batch_norm = nn.BatchNorm1d(hidden_size)
        
        # Add intermediate layer
        self.fc1 = nn.Linear(hidden_size, hidden_size // 2)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(hidden_size // 2, 1)
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x):
        # x shape: (batch_size, seq_len, input_size)
        gru_out, _ = self.gru(x)
        # Take the last time step
        last_output = gru_out[:, -1, :]
        
        # Batch normalization
        last_output = self.batch_norm(last_output)
        
        # Intermediate layer with dropout
        out = self.fc1(last_output)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.sigmoid(out)
        return out

def load_data():
    """Load preprocessed sequences"""
    print("📂 Loading processed data...")
    X = np.load(DATA_PROCESSED / "X_sequences.npy")
    y = np.load(DATA_PROCESSED / "y_labels.npy")
    
    with open(DATA_PROCESSED / "metadata.json", 'r') as f:
        metadata = json.load(f)
    
    print(f"✅ Loaded {len(X)} sequences")
    print(f"   Shape: {X.shape}")
    print(f"   Delay ratio: {metadata['delay_ratio']:.2%}")
    
    return X, y, metadata

def prepare_dataloaders(X, y, batch_size=BATCH_SIZE):
    """Prepare PyTorch DataLoaders with weighted sampling for class balance"""
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Convert to PyTorch tensors
    X_train_tensor = torch.FloatTensor(X_train)
    y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)
    X_test_tensor = torch.FloatTensor(X_test)
    y_test_tensor = torch.FloatTensor(y_test).unsqueeze(1)
    
    # Create datasets
    train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
    test_dataset = TensorDataset(X_test_tensor, y_test_tensor)
    
    # Create weighted sampler to oversample minority class (delayed trips)
    class_counts = np.bincount(y_train.astype(int))
    class_weights = 1.0 / class_counts
    sample_weights = np.array([class_weights[int(label)] for label in y_train])
    sampler = WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(sample_weights),
        replacement=True
    )
    
    # Create dataloaders (train uses sampler, test shuffles normally)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, sampler=sampler)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    print(f"\n📊 Dataset split:")
    print(f"   Training: {len(X_train)} samples ({y_train.mean():.2%} delayed)")
    print(f"   Testing: {len(X_test)} samples ({y_test.mean():.2%} delayed)")
    
    return train_loader, test_loader, X_test, y_test

def train_model(model, train_loader, criterion, optimizer, device):
    """Train model for one epoch"""
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    
    pbar = tqdm(train_loader, desc='Training', leave=False)
    for batch_X, batch_y in pbar:
        batch_X, batch_y = batch_X.to(device), batch_y.to(device)
        
        # Forward pass
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        
        # Gradient clipping to prevent exploding gradients
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        optimizer.step()
        
        # Statistics
        total_loss += loss.item()
        # Apply sigmoid to logits for prediction
        probs = torch.sigmoid(outputs)
        predicted = (probs > 0.5).float()
        correct += (predicted == batch_y).sum().item()
        total += batch_y.size(0)
        
        # Update progress bar
        pbar.set_postfix({'loss': f'{loss.item():.4f}', 'acc': f'{correct/total:.4f}'})
    
    avg_loss = total_loss / len(train_loader)
    accuracy = correct / total
    return avg_loss, accuracy

def evaluate_model(model, test_loader, criterion, device):
    """Evaluate model on test set"""
    model.eval()
    total_loss = 0
    correct = 0
    total = 0
    all_preds = []
    all_labels = []
    all_probs = []
    
    with torch.no_grad():
        for batch_X, batch_y in tqdm(test_loader, desc='Evaluating', leave=False):
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            
            total_loss += loss.item()
            # Apply sigmoid to logits for prediction
            probs = torch.sigmoid(outputs)
            predicted = (probs > 0.5).float()
            correct += (predicted == batch_y).sum().item()
            total += batch_y.size(0)
            
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(batch_y.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
    
    avg_loss = total_loss / len(test_loader)
    accuracy = correct / total
    
    return avg_loss, accuracy, np.array(all_preds), np.array(all_labels), np.array(all_probs)

def plot_training_history(train_losses, val_losses, train_accs, val_accs, model_name):
    """Plot training history"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Loss
    ax1.plot(train_losses, label='Train Loss', linewidth=2)
    ax1.plot(val_losses, label='Val Loss', linewidth=2)
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.set_title(f'{model_name} - Training Loss')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Accuracy
    ax2.plot(train_accs, label='Train Accuracy', linewidth=2)
    ax2.plot(val_accs, label='Val Accuracy', linewidth=2)
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy')
    ax2.set_title(f'{model_name} - Training Accuracy')
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(MODELS_DIR / f'{model_name.lower()}_training_history.png', dpi=150, bbox_inches='tight')
    print(f"✅ Training history plot saved")
    plt.close()

def main():
    print("=" * 60)
    print("🧠 Training Deep Learning Models (PyTorch)")
    print("=" * 60)
    print(f"Device: {DEVICE}")
    print(f"Hidden size: {HIDDEN_SIZE}")
    print(f"Num layers: {NUM_LAYERS}")
    print(f"Dropout: {DROPOUT}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Epochs: {EPOCHS}")
    print("=" * 60)
    
    # Load data
    X, y, metadata = load_data()
    input_size = X.shape[2]
    
    # Prepare dataloaders
    train_loader, test_loader, X_test, y_test = prepare_dataloaders(X, y)
    
    # Calculate focal loss alpha parameter (weight for positive class)
    class_counts = np.bincount(y.astype(int))
    # Alpha = proportion of negative class (to give more weight to positive/delayed)
    focal_alpha = class_counts[0] / (class_counts[0] + class_counts[1])
    print(f"\n⚖️ Class imbalance: {class_counts[0]} on-time, {class_counts[1]} delayed")
    print(f"   Focal Loss alpha: {focal_alpha:.3f}, gamma: {FOCAL_GAMMA}")
    print(f"   Using WeightedRandomSampler to oversample delayed trips")
    
    # Train LSTM
    print("\n🔵 Training LSTM Model...")
    lstm_model = LSTMModel(input_size, HIDDEN_SIZE, NUM_LAYERS, DROPOUT).to(DEVICE)
    
    # Initialize final layer bias to account for class imbalance
    # bias = log(p/(1-p)) where p = proportion of positive class
    init_bias = np.log(class_counts[1] / class_counts[0])
    nn.init.constant_(lstm_model.fc2.bias, init_bias)
    
    # Use Focal Loss (designed for extreme class imbalance)
    criterion = FocalLoss(alpha=focal_alpha, gamma=FOCAL_GAMMA)
    
    optimizer = optim.AdamW(lstm_model.parameters(), lr=LEARNING_RATE, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2)
    
    lstm_train_losses, lstm_val_losses = [], []
    lstm_train_accs, lstm_val_accs = [], []
    best_val_loss = float('inf')
    patience_counter = 0
    
    for epoch in range(EPOCHS):
        # Learning rate warmup for first few epochs
        if epoch < WARMUP_EPOCHS:
            warmup_lr = LEARNING_RATE * (epoch + 1) / WARMUP_EPOCHS
            for param_group in optimizer.param_groups:
                param_group['lr'] = warmup_lr
        
        train_loss, train_acc = train_model(lstm_model, train_loader, criterion, optimizer, DEVICE)
        val_loss, val_acc, _, _, _ = evaluate_model(lstm_model, test_loader, criterion, DEVICE)
        
        lstm_train_losses.append(train_loss)
        lstm_val_losses.append(val_loss)
        lstm_train_accs.append(train_acc)
        lstm_val_accs.append(val_acc)
        
        # Learning rate scheduling (after warmup)
        if epoch >= WARMUP_EPOCHS:
            scheduler.step(val_loss)
        
        current_lr = optimizer.param_groups[0]['lr']
        print(f"Epoch {epoch+1}/{EPOCHS} - Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}, "
              f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}, LR: {current_lr:.6f}")
        
        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(lstm_model.state_dict(), MODELS_DIR / "lstm_model_best.pth")
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                print(f"⏹️ Early stopping triggered after {epoch+1} epochs")
                break
    
    # Load best model
    lstm_model.load_state_dict(torch.load(MODELS_DIR / "lstm_model_best.pth"))
    
    # Final evaluation
    _, _, lstm_preds, lstm_labels, lstm_probs = evaluate_model(lstm_model, test_loader, criterion, DEVICE)
    lstm_auc = roc_auc_score(lstm_labels, lstm_probs)
    
    print(f"\n📊 LSTM Final Results:")
    print(classification_report(lstm_labels, lstm_preds, target_names=['On-Time', 'Delayed']))
    print(f"ROC-AUC Score: {lstm_auc:.4f}")
    
    # Save model
    torch.save(lstm_model.state_dict(), MODELS_DIR / "lstm_model.pth")
    torch.save(lstm_model, MODELS_DIR / "lstm_model_complete.pth")
    print(f"✅ LSTM model saved")
    
    # Plot training history
    plot_training_history(lstm_train_losses, lstm_val_losses, lstm_train_accs, lstm_val_accs, "LSTM")
    
    # Train GRU
    print("\n🟢 Training GRU Model...")
    gru_model = GRUModel(input_size, HIDDEN_SIZE, NUM_LAYERS, DROPOUT).to(DEVICE)
    
    # Initialize GRU final layer bias same way
    nn.init.constant_(gru_model.fc2.bias, init_bias)
    
    optimizer_gru = optim.AdamW(gru_model.parameters(), lr=LEARNING_RATE, weight_decay=1e-5)
    scheduler_gru = optim.lr_scheduler.ReduceLROnPlateau(optimizer_gru, mode='min', factor=0.5, patience=2)
    
    gru_train_losses, gru_val_losses = [], []
    gru_train_accs, gru_val_accs = [], []
    best_val_loss_gru = float('inf')
    patience_counter_gru = 0
    
    for epoch in range(EPOCHS):
        # Learning rate warmup for first few epochs
        if epoch < WARMUP_EPOCHS:
            warmup_lr = LEARNING_RATE * (epoch + 1) / WARMUP_EPOCHS
            for param_group in optimizer_gru.param_groups:
                param_group['lr'] = warmup_lr
        
        train_loss, train_acc = train_model(gru_model, train_loader, criterion, optimizer_gru, DEVICE)
        val_loss, val_acc, _, _, _ = evaluate_model(gru_model, test_loader, criterion, DEVICE)
        
        gru_train_losses.append(train_loss)
        gru_val_losses.append(val_loss)
        gru_train_accs.append(train_acc)
        gru_val_accs.append(val_acc)
        
        # Learning rate scheduling (after warmup)
        if epoch >= WARMUP_EPOCHS:
            scheduler_gru.step(val_loss)
        
        current_lr = optimizer_gru.param_groups[0]['lr']
        print(f"Epoch {epoch+1}/{EPOCHS} - Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}, "
              f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}, LR: {current_lr:.6f}")
        
        # Early stopping
        if val_loss < best_val_loss_gru:
            best_val_loss_gru = val_loss
            patience_counter_gru = 0
            torch.save(gru_model.state_dict(), MODELS_DIR / "gru_model_best.pth")
        else:
            patience_counter_gru += 1
            if patience_counter_gru >= PATIENCE:
                print(f"⏹️ Early stopping triggered after {epoch+1} epochs")
                break
    
    # Load best model
    gru_model.load_state_dict(torch.load(MODELS_DIR / "gru_model_best.pth"))
    
    # Final evaluation
    _, _, gru_preds, gru_labels, gru_probs = evaluate_model(gru_model, test_loader, criterion, DEVICE)
    gru_auc = roc_auc_score(gru_labels, gru_probs)
    
    print(f"\n📊 GRU Final Results:")
    print(classification_report(gru_labels, gru_preds, target_names=['On-Time', 'Delayed']))
    print(f"ROC-AUC Score: {gru_auc:.4f}")
    
    # Save model
    torch.save(gru_model.state_dict(), MODELS_DIR / "gru_model.pth")
    torch.save(gru_model, MODELS_DIR / "gru_model_complete.pth")
    print(f"✅ GRU model saved")
    
    # Plot training history
    plot_training_history(gru_train_losses, gru_val_losses, gru_train_accs, gru_val_accs, "GRU")
    
    # Save results
    results = {
        'lstm': {
            'auc': float(lstm_auc),
            'final_train_acc': float(lstm_train_accs[-1]),
            'final_val_acc': float(lstm_val_accs[-1]),
            'model_path': 'lstm_model.pth'
        },
        'gru': {
            'auc': float(gru_auc),
            'final_train_acc': float(gru_train_accs[-1]),
            'final_val_acc': float(gru_val_accs[-1]),
            'model_path': 'gru_model.pth'
        },
        'best_model': 'lstm' if lstm_auc > gru_auc else 'gru',
        'hyperparameters': {
            'hidden_size': HIDDEN_SIZE,
            'num_layers': NUM_LAYERS,
            'dropout': DROPOUT,
            'learning_rate': LEARNING_RATE,
            'batch_size': BATCH_SIZE,
            'epochs': EPOCHS
        }
    }
    
    with open(MODELS_DIR / 'deep_learning_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("✅ Deep learning training complete!")
    print(f"📊 Best model: {results['best_model'].upper()}")
    print(f"   LSTM AUC: {lstm_auc:.4f}")
    print(f"   GRU AUC: {gru_auc:.4f}")
    print("=" * 60)
    print("\n📋 Next steps:")
    print("   1. Convert to ONNX: python scripts\\convert_to_onnx.py")
    print("   2. Build edge inference: python edge\\inference.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
