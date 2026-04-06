# Database Schema - SQL Migrations

## Initial Schema Creation

### 1. Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'customer', -- customer, driver, admin, company
    phone VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_role CHECK (role IN ('customer', 'driver', 'admin', 'company'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);
```

### 2. Vehicles Table
```sql
CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registration VARCHAR(50) UNIQUE NOT NULL,
    license_plate VARCHAR(20) UNIQUE NOT NULL,
    vehicle_type VARCHAR(50) NOT NULL, -- bike, car, van, truck, etc
    capacity_kg DECIMAL(10, 2),
    capacity_liters DECIMAL(10, 2),
    status VARCHAR(50) DEFAULT 'active', -- active, maintenance, offline, sold
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    year INT,
    gps_device_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_status CHECK (status IN ('active', 'maintenance', 'offline', 'sold'))
);

CREATE INDEX idx_vehicles_status ON vehicles(status);
CREATE INDEX idx_vehicles_registration ON vehicles(registration);
```

### 3. Drivers Table
```sql
CREATE TABLE drivers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE SET NULL,
    license_number VARCHAR(50) UNIQUE NOT NULL,
    license_expiry DATE,
    status VARCHAR(50) DEFAULT 'offline', -- active, on_break, offline
    current_location_lat DECIMAL(10, 8),
    current_location_lon DECIMAL(11, 8),
    last_location_update TIMESTAMP,
    rating DECIMAL(3, 2) DEFAULT 5.0,
    trips_completed INT DEFAULT 0,
    avg_delay_minutes DECIMAL(10, 2) DEFAULT 0,
    total_distance_km DECIMAL(10, 2) DEFAULT 0,
    emergency_contact_phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_status CHECK (status IN ('active', 'on_break', 'offline')),
    CONSTRAINT valid_rating CHECK (rating >= 0 AND rating <= 5)
);

CREATE INDEX idx_drivers_user_id ON drivers(user_id);
CREATE INDEX idx_drivers_vehicle_id ON drivers(vehicle_id);
CREATE INDEX idx_drivers_status ON drivers(status);
CREATE INDEX idx_drivers_location ON drivers(current_location_lat, current_location_lon);
```

### 4. Trips Table
```sql
CREATE TABLE trips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    driver_id UUID REFERENCES drivers(id) ON DELETE SET NULL,
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, assigned, in_transit, completed, cancelled
    
    pickup_lat DECIMAL(10, 8) NOT NULL,
    pickup_lon DECIMAL(11, 8) NOT NULL,
    pickup_name VARCHAR(255),
    pickup_address TEXT,
    
    destination_lat DECIMAL(10, 8) NOT NULL,
    destination_lon DECIMAL(11, 8) NOT NULL,
    destination_name VARCHAR(255),
    destination_address TEXT,
    
    cargo_description TEXT,
    cargo_weight_kg DECIMAL(10, 2),
    cargo_volume_liters DECIMAL(10, 2),
    is_fragile BOOLEAN DEFAULT FALSE,
    requires_signature BOOLEAN DEFAULT FALSE,
    
    promised_delivery_time TIMESTAMP,
    actual_delivery_time TIMESTAMP,
    
    estimated_delay_mins INT,
    actual_delay_mins INT,
    
    cost_estimate DECIMAL(10, 2),
    cost_actual DECIMAL(10, 2),
    payment_status VARCHAR(50), -- pending, completed, refunded
    
    notes TEXT,
    special_instructions TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'assigned', 'in_transit', 'completed', 'cancelled'))
);

CREATE INDEX idx_trips_user_id ON trips(user_id);
CREATE INDEX idx_trips_driver_id ON trips(driver_id);
CREATE INDEX idx_trips_status ON trips(status);
CREATE INDEX idx_trips_created_at ON trips(created_at);
CREATE INDEX idx_trips_promised_delivery ON trips(promised_delivery_time);
```

### 5. Routes Table
```sql
CREATE TABLE routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    route_type VARCHAR(50) NOT NULL, -- primary, alternative_1, alternative_2
    
    distance_meters INT,
    duration_seconds INT,
    polyline TEXT, -- GeoJSON encoded route
    
    predicted_delay_mins INT,
    risk_score DECIMAL(5, 2), -- 0-100
    
    toll_cost DECIMAL(10, 2),
    fuel_estimate DECIMAL(10, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_type CHECK (route_type IN ('primary', 'alternative_1', 'alternative_2'))
);

CREATE INDEX idx_routes_trip_id ON routes(trip_id);
CREATE INDEX idx_routes_type ON routes(route_type);
```

### 6. Locations Table (High-frequency)
```sql
CREATE TABLE locations (
    id BIGSERIAL PRIMARY KEY,
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE SET NULL,
    
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    accuracy_meters DECIMAL(10, 2),
    speed_kmh DECIMAL(10, 2),
    heading DECIMAL(5, 2), -- 0-360 degrees
    
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_latitude CHECK (latitude >= -90 AND latitude <= 90),
    CONSTRAINT valid_longitude CHECK (longitude >= -180 AND longitude <= 180)
);

-- Critical: Time-series index for efficient queries
CREATE INDEX idx_locations_trip_timestamp ON locations(trip_id, timestamp DESC);
CREATE INDEX idx_locations_driver_timestamp ON locations(driver_id, timestamp DESC);
CREATE INDEX idx_locations_timestamp ON locations(timestamp DESC);
CREATE INDEX idx_locations_geo ON locations(latitude, longitude);

-- For time-series data, consider partitioning by date
-- ALTER TABLE locations PARTITION BY RANGE (EXTRACT(EPOCH FROM timestamp));
```

### 7. Notifications Table
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trip_id UUID REFERENCES trips(id) ON DELETE SET NULL,
    
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) NOT NULL, -- alert, update, info, warning
    priority VARCHAR(50) DEFAULT 'normal', -- low, normal, high, critical
    
    action_type VARCHAR(100), -- accept_reroute, view_delivery, rate_driver, etc
    action_data JSONB, -- Additional data for action
    
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_type CHECK (type IN ('alert', 'update', 'info', 'warning')),
    CONSTRAINT valid_priority CHECK (priority IN ('low', 'normal', 'high', 'critical'))
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
```

### 8. Feedback Table
```sql
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    
    rating INT NOT NULL, -- 1-5
    comment TEXT,
    categories JSONB, -- {cleanliness: 5, professionalism: 4, ...}
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_rating CHECK (rating >= 1 AND rating <= 5)
);

CREATE INDEX idx_feedback_trip_id ON feedback(trip_id);
CREATE INDEX idx_feedback_driver_id ON feedback(driver_id);
CREATE INDEX idx_feedback_user_id ON feedback(user_id);
```

### 9. Analytics Table
```sql
CREATE TABLE analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    
    predicted_delay_mins INT,
    actual_delay_mins INT,
    
    route_distance_actual_meters INT,
    route_time_actual_seconds INT,
    
    predicted_risk_score DECIMAL(5, 2),
    efficiency_score DECIMAL(5, 2),
    
    cost_per_km DECIMAL(10, 4),
    fuel_used_liters DECIMAL(10, 2),
    
    weather_condition VARCHAR(100),
    traffic_condition VARCHAR(100),
    
    ai_recommendation VARCHAR(255),
    ai_confidence DECIMAL(5, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_analytics_trip_id ON analytics(trip_id);
CREATE INDEX idx_analytics_driver_id ON analytics(driver_id);
CREATE INDEX idx_analytics_created_at ON analytics(created_at);
```

### 10. Geofences Table
```sql
CREATE TABLE geofences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    center_latitude DECIMAL(10, 8) NOT NULL,
    center_longitude DECIMAL(11, 8) NOT NULL,
    radius_meters INT NOT NULL,
    
    type VARCHAR(50) DEFAULT 'alert', -- alert, restricted, zone, depot
    action_on_enter VARCHAR(100), -- notify, alert, restrict
    action_on_exit VARCHAR(100),
    
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_type CHECK (type IN ('alert', 'restricted', 'zone', 'depot'))
);

CREATE INDEX idx_geofences_company_id ON geofences(company_id);
CREATE INDEX idx_geofences_location ON geofences(center_latitude, center_longitude);
CREATE INDEX idx_geofences_is_active ON geofences(is_active);
```

### 11. Compliance Logs Table
```sql
CREATE TABLE compliance_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID REFERENCES trips(id) ON DELETE SET NULL,
    driver_id UUID REFERENCES drivers(id) ON DELETE SET NULL,
    
    event_type VARCHAR(100) NOT NULL, -- duty_hours, speed_violation, traffic_incident, etc
    severity VARCHAR(50), -- info, warning, critical
    
    details JSONB, -- Flexible JSON storage
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_severity CHECK (severity IN ('info', 'warning', 'critical'))
);

CREATE INDEX idx_compliance_logs_trip ON compliance_logs(trip_id);
CREATE INDEX idx_compliance_logs_driver ON compliance_logs(driver_id);
CREATE INDEX idx_compliance_logs_timestamp ON compliance_logs(timestamp DESC);
```

### 12. API Keys Table
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    name VARCHAR(255),
    key_hash VARCHAR(255) NOT NULL UNIQUE, -- Hashed for security
    
    scope VARCHAR(50) DEFAULT 'read', -- read, write, admin
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    
    CONSTRAINT valid_scope CHECK (scope IN ('read', 'write', 'admin'))
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);
```

## Migration Instructions

1. **Create database** in Supabase
2. **Run all SQL scripts** above in order
3. **Enable RLS (Row Level Security)** for sensitive tables
4. **Create functions** for auto-updating `updated_at` timestamps
5. **Set up views** for aggregated analytics

```sql
-- Auto-update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_drivers_updated_at BEFORE UPDATE ON drivers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trips_updated_at BEFORE UPDATE ON trips
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ... repeat for other tables
```

## Backup & Recovery

- **Daily automated backups** via Supabase
- **Point-in-time recovery** enabled
- **Regular restore tests** (monthly)
