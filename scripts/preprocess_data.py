"""
Data Preprocessing Pipeline for TMS AI
- Clean GPS trajectory data
- Extract features (speed, distance, time)
- Create time-series sequences
- Label delays based on ETA deviation
"""

import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from tqdm import tqdm

# Paths
DATA_RAW = Path(__file__).parent.parent / "data" / "raw"
DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# Configuration
SEQUENCE_LENGTH = 10  # Number of time steps for LSTM input
DELAY_THRESHOLD_MINUTES = 15  # Threshold to label a trip as delayed
SPEED_THRESHOLD_KMH = 5  # Speed below this is considered stopped/congested

def load_raw_data():
    """Load raw taxi trajectory data"""
    print("📂 Loading raw data...")
    
    # Find CSV files in raw data directory
    csv_files = list(DATA_RAW.glob("*.csv"))
    
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {DATA_RAW}")
    
    print(f"Found {len(csv_files)} CSV file(s)")
    
    # Load the first CSV (adjust based on your dataset structure)
    df = pd.read_csv(csv_files[0])
    print(f"✅ Loaded {len(df)} records from {csv_files[0].name}")
    print(f"Columns: {list(df.columns)}")
    
    return df

def parse_polyline(polyline_str):
    """
    Parse GPS polyline from JSON string to list of (lat, lon) tuples
    Porto Taxi dataset stores trajectories as JSON arrays
    """
    try:
        coords = json.loads(polyline_str)
        return [(lat, lon) for lon, lat in coords]  # Note: some datasets use [lon, lat]
    except:
        return []

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS points in kilometers"""
    R = 6371  # Earth radius in km
    
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c

def extract_features_from_trajectory(trajectory, timestamp):
    """
    Extract features from a single trajectory
    Returns a dataframe with time-series features
    """
    if len(trajectory) < 2:
        return None
    
    features = []
    
    for i in range(1, len(trajectory)):
        lat1, lon1 = trajectory[i-1]
        lat2, lon2 = trajectory[i]
        
        # Calculate distance and speed
        distance = calculate_haversine_distance(lat1, lon1, lat2, lon2)
        time_diff = 15  # Assume 15 seconds between GPS points (adjust based on dataset)
        speed = (distance / time_diff) * 3600  # km/h
        
        # Extract time features
        current_time = timestamp + timedelta(seconds=i * time_diff)
        
        features.append({
            'lat': lat2,
            'lon': lon2,
            'distance_km': distance,
            'speed_kmh': speed,
            'hour': current_time.hour,
            'day_of_week': current_time.weekday(),
            'is_weekend': 1 if current_time.weekday() >= 5 else 0,
            'is_stopped': 1 if speed < SPEED_THRESHOLD_KMH else 0,
        })
    
    return pd.DataFrame(features)

def label_delays(df):
    """
    Label trips as delayed or on-time
    Based on ETA deviation (can be calculated from trip duration vs. expected)
    """
    # Simplified delay labeling (customize based on your dataset)
    # Example: if trip took longer than expected based on distance/avg speed
    
    if 'TRAVEL_TIME' in df.columns:
        # Porto dataset has TRAVEL_TIME in seconds
        df['expected_time'] = df['distance_km'] / 30 * 3600  # Assume 30 km/h avg speed
        df['delay_minutes'] = (df['TRAVEL_TIME'] - df['expected_time']) / 60
        df['is_delayed'] = (df['delay_minutes'] > DELAY_THRESHOLD_MINUTES).astype(int)
    else:
        # Placeholder: random labeling for demo (replace with real logic)
        df['is_delayed'] = np.random.choice([0, 1], size=len(df), p=[0.7, 0.3])
    
    return df

def create_sequences(df, sequence_length=SEQUENCE_LENGTH):
    """
    Create time-series sequences for LSTM input
    Returns X (sequences) and y (labels)
    """
    feature_columns = ['speed_kmh', 'distance_km', 'hour', 'day_of_week', 
                       'is_weekend', 'is_stopped']
    
    X, y = [], []
    
    # Group by trip_id if available
    if 'TRIP_ID' in df.columns:
        grouped = df.groupby('TRIP_ID')
    else:
        # Create artificial trip IDs based on gaps
        df['TRIP_ID'] = (df.index // 50)  # Group every 50 rows
        grouped = df.groupby('TRIP_ID')
    
    for trip_id, group in tqdm(grouped, desc="Creating sequences"):
        if len(group) < sequence_length:
            continue
        
        features = group[feature_columns].values
        
        # Create sliding windows
        for i in range(len(features) - sequence_length):
            X.append(features[i:i+sequence_length])
            # Label is based on whether delay occurs in next step
            y.append(group.iloc[i+sequence_length]['is_delayed'] if 'is_delayed' in group.columns else 0)
    
    return np.array(X), np.array(y)

def main():
    """Main preprocessing pipeline"""
    print("=" * 60)
    print("🔧 TMS AI Data Preprocessing Pipeline")
    print("=" * 60)
    
    # Load raw data
    df_raw = load_raw_data()
    
    # Show sample
    print("\n📊 Sample data:")
    print(df_raw.head())
    
    # Process based on dataset structure
    # For Porto Taxi dataset with POLYLINE column
    if 'POLYLINE' in df_raw.columns:
        print("\n🗺️  Processing GPS trajectories...")
        
        # Parse polylines and extract features
        all_features = []
        
        for idx, row in tqdm(df_raw.head(50000).iterrows(), total=50000, desc="Processing trips"):
            trajectory = parse_polyline(row['POLYLINE'])
            
            if not trajectory:
                continue
            
            timestamp = datetime.fromtimestamp(row['TIMESTAMP']) if 'TIMESTAMP' in row else datetime.now()
            trip_features = extract_features_from_trajectory(trajectory, timestamp)
            
            if trip_features is not None:
                trip_features['TRIP_ID'] = idx
                if 'TRAVEL_TIME' in row:
                    trip_features['TRAVEL_TIME'] = row['TRAVEL_TIME']
                all_features.append(trip_features)
        
        # Combine all features
        df_features = pd.concat(all_features, ignore_index=True)
        print(f"✅ Extracted features from {len(all_features)} trips")
    
    else:
        # Generic processing for other dataset structures
        print("\n⚙️  Processing generic trajectory data...")
        df_features = df_raw.copy()
    
    # Calculate total distance per trip
    if 'TRIP_ID' in df_features.columns:
        df_features['distance_km'] = df_features.groupby('TRIP_ID')['distance_km'].transform('sum')
    
    # Label delays
    print("\n🏷️  Labeling delays...")
    df_features = label_delays(df_features)
    
    # Save processed features
    features_path = DATA_PROCESSED / "features.csv"
    df_features.to_csv(features_path, index=False)
    print(f"✅ Saved features to {features_path}")
    
    # Create sequences for LSTM
    print(f"\n📦 Creating sequences (length={SEQUENCE_LENGTH})...")
    X, y = create_sequences(df_features)
    
    # Save sequences
    np.save(DATA_PROCESSED / "X_sequences.npy", X)
    np.save(DATA_PROCESSED / "y_labels.npy", y)
    
    print(f"✅ Created {len(X)} sequences")
    print(f"   X shape: {X.shape}")
    print(f"   y shape: {y.shape}")
    print(f"   Delay ratio: {y.mean():.2%}")
    
    # Save metadata
    metadata = {
        'sequence_length': SEQUENCE_LENGTH,
        'n_samples': len(X),
        'n_features': X.shape[2],
        'delay_ratio': float(y.mean()),
        'feature_columns': ['speed_kmh', 'distance_km', 'hour', 'day_of_week', 'is_weekend', 'is_stopped']
    }
    
    with open(DATA_PROCESSED / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("\n" + "=" * 60)
    print("✅ Preprocessing complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
