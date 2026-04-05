"""
Alternative: Generate Synthetic Taxi Trajectory Data
Use this if Kaggle download is stuck or too slow.
This creates realistic GPS trajectory data for testing the pipeline.
"""

import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path

# Output path
DATA_RAW = Path(__file__).parent.parent / "data" / "raw"
DATA_RAW.mkdir(parents=True, exist_ok=True)

# Configuration
N_TRIPS = 10000  # Number of taxi trips to generate
CITY_CENTER_LAT = 41.1579  # Porto, Portugal latitude
CITY_CENTER_LON = -8.6291  # Porto, Portugal longitude
CITY_RADIUS_KM = 10  # Radius of city in km

np.random.seed(42)

def generate_gps_trajectory(start_lat, start_lon, end_lat, end_lon, num_points=50):
    """Generate a GPS trajectory between two points"""
    lats = np.linspace(start_lat, end_lat, num_points)
    lons = np.linspace(start_lon, end_lon, num_points)
    
    # Add some noise to make it realistic
    lats += np.random.normal(0, 0.001, num_points)
    lons += np.random.normal(0, 0.001, num_points)
    
    # Return as list of [lon, lat] (Porto dataset format)
    return [[float(lon), float(lat)] for lat, lon in zip(lats, lons)]

def generate_trip():
    """Generate one taxi trip"""
    # Random start and end points within city
    angle_start = np.random.uniform(0, 2 * np.pi)
    dist_start = np.random.uniform(0, CITY_RADIUS_KM) / 111  # Convert km to degrees
    
    start_lat = CITY_CENTER_LAT + dist_start * np.cos(angle_start)
    start_lon = CITY_CENTER_LON + dist_start * np.sin(angle_start)
    
    angle_end = np.random.uniform(0, 2 * np.pi)
    dist_end = np.random.uniform(0, CITY_RADIUS_KM) / 111
    
    end_lat = CITY_CENTER_LAT + dist_end * np.cos(angle_end)
    end_lon = CITY_CENTER_LON + dist_end * np.sin(angle_end)
    
    # Calculate distance and time
    distance_km = dist_start * 111 + np.random.uniform(1, 20)  # Rough estimate
    avg_speed_kmh = np.random.uniform(15, 50)  # City driving speed
    travel_time_sec = int((distance_km / avg_speed_kmh) * 3600)
    
    # Generate trajectory
    num_points = max(10, int(travel_time_sec / 15))  # One point every 15 seconds
    polyline = generate_gps_trajectory(start_lat, start_lon, end_lat, end_lon, num_points)
    
    # Random timestamp in 2013-2014 (Porto dataset time period)
    base_timestamp = datetime(2013, 7, 1).timestamp()
    timestamp = int(base_timestamp + np.random.uniform(0, 365 * 24 * 3600))
    
    return {
        'TRIP_ID': None,  # Will be set as index
        'CALL_TYPE': np.random.choice(['A', 'B', 'C']),
        'ORIGIN_CALL': int(np.random.uniform(1, 1000)) if np.random.rand() > 0.5 else np.nan,
        'ORIGIN_STAND': int(np.random.uniform(1, 64)) if np.random.rand() > 0.3 else np.nan,
        'TAXI_ID': int(np.random.uniform(20000000, 20001000)),
        'TIMESTAMP': timestamp,
        'DAY_TYPE': np.random.choice(['A', 'B', 'C']),
        'MISSING_DATA': False,
        'POLYLINE': json.dumps(polyline),
        'TRAVEL_TIME': travel_time_sec
    }

def main():
    print("=" * 60)
    print("🚕 Generating Synthetic Taxi Trajectory Data")
    print("=" * 60)
    print(f"\n📊 Configuration:")
    print(f"   Number of trips: {N_TRIPS:,}")
    print(f"   City center: ({CITY_CENTER_LAT}, {CITY_CENTER_LON})")
    print(f"   City radius: {CITY_RADIUS_KM} km")
    
    print(f"\n🔧 Generating trips...")
    trips = []
    for i in range(N_TRIPS):
        if (i + 1) % 1000 == 0:
            print(f"   Generated {i + 1:,} / {N_TRIPS:,} trips...")
        trips.append(generate_trip())
    
    # Create DataFrame
    df = pd.DataFrame(trips)
    df['TRIP_ID'] = df.index
    
    # Reorder columns to match Porto dataset
    columns = ['TRIP_ID', 'CALL_TYPE', 'ORIGIN_CALL', 'ORIGIN_STAND', 
               'TAXI_ID', 'TIMESTAMP', 'DAY_TYPE', 'MISSING_DATA', 
               'POLYLINE', 'TRAVEL_TIME']
    df = df[columns]
    
    # Save to CSV
    output_path = DATA_RAW / "train.csv"
    df.to_csv(output_path, index=False)
    
    print(f"\n✅ Dataset generated successfully!")
    print(f"📁 Saved to: {output_path}")
    print(f"📊 File size: {output_path.stat().st_size / (1024*1024):.2f} MB")
    print(f"📝 Rows: {len(df):,}")
    print(f"📝 Columns: {len(df.columns)}")
    
    print("\n📋 Sample data:")
    print(df.head())
    
    print("\n" + "=" * 60)
    print("✅ Ready to run preprocessing!")
    print("Next: python scripts\\preprocess_data.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
