import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import MapView, { Marker, Polyline } from 'react-native-maps';
import { getAuthTokens, getWebSocketUrl, locationsAPI, tripsAPI } from '../shared/api';
import { isLocationStreaming, startLocationStreaming, stopLocationStreaming } from '../shared/locationTracking';

export const TrackingScreen = () => {
  const mapRef = useRef(null);
  const wsRef = useRef(null);
  const wsPingRef = useRef(null);

  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTrip, setActiveTrip] = useState(null);
  const [tripId, setTripId] = useState(null);
  const [latestLocation, setLatestLocation] = useState(null);
  const [stats, setStats] = useState(null);
  const [routeCoordinates, setRouteCoordinates] = useState([]);
  const [error, setError] = useState('');
  const [wsConnected, setWsConnected] = useState(false);
  const [locationStreaming, setLocationStreaming] = useState(isLocationStreaming());

  const closeTripSocket = useCallback(() => {
    if (wsPingRef.current) {
      clearInterval(wsPingRef.current);
      wsPingRef.current = null;
    }

    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch {
        // Ignore close errors.
      }
      wsRef.current = null;
    }

    setWsConnected(false);
  }, []);

  const fitMapToRoute = useCallback((coords, vehiclePoint) => {
    if (!mapRef.current) {
      return;
    }

    const points = [...coords];
    if (vehiclePoint) {
      points.push(vehiclePoint);
    }

    if (points.length < 2) {
      return;
    }

    mapRef.current.fitToCoordinates(points, {
      edgePadding: { top: 70, right: 50, bottom: 70, left: 50 },
      animated: true,
    });
  }, []);

  const connectTripSocket = useCallback(async (newTripId) => {
    closeTripSocket();

    const { accessToken } = await getAuthTokens();
    if (!accessToken || !newTripId) {
      return;
    }

    const url = getWebSocketUrl(`/ws/trip/${newTripId}`, accessToken);
    const socket = new WebSocket(url);
    wsRef.current = socket;

    socket.onopen = () => {
      setWsConnected(true);
      wsPingRef.current = setInterval(() => {
        try {
          socket.send(JSON.stringify({ type: 'ping' }));
        } catch {
          // Ignore ping errors.
        }
      }, 20000);
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'location_update') {
          const point = {
            latitude: Number(payload.latitude),
            longitude: Number(payload.longitude),
            speed_kmh: payload.speed_kmh,
            heading: payload.heading,
            recorded_at: payload.timestamp || new Date().toISOString(),
          };
          setLatestLocation(point);

          fitMapToRoute(routeCoordinates, {
            latitude: point.latitude,
            longitude: point.longitude,
          });
        }
      } catch {
        // Ignore malformed websocket messages.
      }
    };

    socket.onerror = () => {
      setWsConnected(false);
    };

    socket.onclose = () => {
      setWsConnected(false);
      if (wsPingRef.current) {
        clearInterval(wsPingRef.current);
        wsPingRef.current = null;
      }
    };
  }, [closeTripSocket, fitMapToRoute, routeCoordinates]);

  useEffect(() => {
    loadLatestTracking();

    const intervalId = setInterval(() => {
      loadLatestTracking();
    }, 15000);

    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    if (tripId) {
      connectTripSocket(tripId);
    } else {
      closeTripSocket();
    }

    return () => {
      closeTripSocket();
    };
  }, [tripId, connectTripSocket, closeTripSocket]);

  const loadLatestTracking = async () => {
    setError('');
    setLoading(true);

    try {
      const tripsResponse = await tripsAPI.listTrips({ limit: 1, status: 'in_progress' });
      const activeTrip = tripsResponse.data?.items?.[0] || null;

      if (!activeTrip) {
        setActiveTrip(null);
        setTripId(null);
        setLatestLocation(null);
        setStats(null);
        setRouteCoordinates([]);
        return;
      }

      setActiveTrip(activeTrip);
      setTripId(activeTrip.id);

      const [tripResponse, locationResponse, statsResponse] = await Promise.all([
        tripsAPI.getTrip(activeTrip.id),
        locationsAPI.getLatestLocation(activeTrip.id),
        locationsAPI.getTripStats(activeTrip.id),
      ]);

      setLatestLocation(locationResponse.data);
      setStats(statsResponse.data);
      const coordinates = buildRouteCoordinates(tripResponse.data);
      setRouteCoordinates(coordinates);

      if (locationResponse.data) {
        fitMapToRoute(coordinates, {
          latitude: locationResponse.data.latitude,
          longitude: locationResponse.data.longitude,
        });
      } else {
        fitMapToRoute(coordinates, null);
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setLatestLocation(null);
        setStats(null);
        setRouteCoordinates([]);
        setError('No location points recorded for this trip yet');
      } else {
        setError(err.response?.data?.detail || 'Could not load tracking data');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const rows = useMemo(() => {
    if (!latestLocation) {
      return [];
    }

    return [
      { key: 'lat', label: 'Latitude', value: String(latestLocation.latitude) },
      { key: 'lng', label: 'Longitude', value: String(latestLocation.longitude) },
      { key: 'speed', label: 'Speed', value: `${latestLocation.speed_kmh ?? 0} km/h` },
      { key: 'heading', label: 'Heading', value: `${latestLocation.heading ?? 0} deg` },
      {
        key: 'recorded',
        label: 'Recorded At',
        value: latestLocation.recorded_at
          ? new Date(latestLocation.recorded_at).toLocaleString()
          : 'Unknown',
      },
    ];
  }, [latestLocation]);

  const mapRegion = useMemo(() => {
    if (latestLocation) {
      return {
        latitude: latestLocation.latitude,
        longitude: latestLocation.longitude,
        latitudeDelta: 0.03,
        longitudeDelta: 0.03,
      };
    }

    if (activeTrip?.pickup_lat && activeTrip?.pickup_lng) {
      return {
        latitude: activeTrip.pickup_lat,
        longitude: activeTrip.pickup_lng,
        latitudeDelta: 0.12,
        longitudeDelta: 0.12,
      };
    }

    return {
      latitude: 38.7223,
      longitude: -9.1393,
      latitudeDelta: 0.2,
      longitudeDelta: 0.2,
    };
  }, [activeTrip, latestLocation]);

  const onRefresh = () => {
    setRefreshing(true);
    loadLatestTracking();
  };

  const toggleLocationStreaming = async () => {
    if (!tripId) {
      return;
    }

    if (locationStreaming) {
      await stopLocationStreaming();
      setLocationStreaming(false);
      return;
    }

    const result = await startLocationStreaming(tripId);
    if (result.ok) {
      setLocationStreaming(true);
      return;
    }

    if (result.error === 'location_permission_denied') {
      setError('Location permission denied for background tracking');
    } else {
      setError('Could not start background location tracking');
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Live Tracking</Text>
        <Text style={styles.subtitle}>Latest in-progress trip telemetry</Text>
        <Text style={[styles.socketStatus, wsConnected ? styles.socketConnected : styles.socketDisconnected]}>
          {wsConnected ? 'Live WebSocket connected' : 'WebSocket offline (polling fallback)'}
        </Text>
      </View>

      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={loadLatestTracking}
        disabled={loading}
      >
        <Text style={styles.buttonText}>{tripId ? 'Refresh Tracking' : 'Load Tracking'}</Text>
      </TouchableOpacity>

      {tripId ? (
        <TouchableOpacity
          style={[styles.button, locationStreaming ? styles.stopButton : styles.startButton]}
          onPress={toggleLocationStreaming}
        >
          <Text style={styles.buttonText}>
            {locationStreaming ? 'Stop Background Tracking' : 'Start Background Tracking'}
          </Text>
        </TouchableOpacity>
      ) : null}

      {loading && !refreshing ? <ActivityIndicator size="large" color="#2196F3" /> : null}

      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      {!loading && !tripId ? (
        <Text style={styles.emptyText}>No in-progress trips found yet.</Text>
      ) : null}

      {tripId ? (
        <ScrollView
          style={styles.card}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        >
          <Text style={styles.cardTitle}>Trip #{tripId}</Text>

          <View style={styles.mapContainer}>
            <MapView style={styles.map} initialRegion={mapRegion} region={mapRegion}>
              {activeTrip?.pickup_lat && activeTrip?.pickup_lng ? (
                <Marker
                  coordinate={{ latitude: activeTrip.pickup_lat, longitude: activeTrip.pickup_lng }}
                  title="Pickup"
                  pinColor="#22c55e"
                />
              ) : null}

              {activeTrip?.dropoff_lat && activeTrip?.dropoff_lng ? (
                <Marker
                  coordinate={{ latitude: activeTrip.dropoff_lat, longitude: activeTrip.dropoff_lng }}
                  title="Destination"
                  pinColor="#2563eb"
                />
              ) : null}

              {latestLocation ? (
                <Marker
                  coordinate={{ latitude: latestLocation.latitude, longitude: latestLocation.longitude }}
                  title="Vehicle"
                  description={`Speed: ${latestLocation.speed_kmh ?? 0} km/h`}
                  pinColor="#ef4444"
                />
              ) : null}

              {routeCoordinates.length >= 2 ? (
                <Polyline
                  coordinates={routeCoordinates}
                  strokeWidth={4}
                  strokeColor="#0ea5e9"
                />
              ) : null}
            </MapView>
          </View>

          {rows.map((item) => (
            <View key={item.key} style={styles.row}>
              <Text style={styles.rowLabel}>{item.label}</Text>
              <Text style={styles.rowValue}>{item.value}</Text>
            </View>
          ))}

          {stats ? (
            <View style={styles.statsBox}>
              <Text style={styles.statsTitle}>Trip Stats</Text>
              <Text style={styles.statsText}>Distance: {stats.distance_km?.toFixed?.(2) ?? stats.distance_km} km</Text>
              <Text style={styles.statsText}>Average Speed: {stats.average_speed_kmh?.toFixed?.(1) ?? stats.average_speed_kmh} km/h</Text>
              <Text style={styles.statsText}>Speed Violations: {stats.speeding_events_count ?? 0}</Text>
            </View>
          ) : null}

          {!routeCoordinates.length ? (
            <Text style={styles.helperText}>
              Route line will appear after route data is available.
            </Text>
          ) : null}
        </ScrollView>
      ) : null}
    </View>
  );
};

const buildRouteCoordinates = (trip) => {
  if (!trip) {
    return [];
  }

  const route = Array.isArray(trip.routes) ? trip.routes[0] : null;
  const polyline = route?.polyline;

  if (typeof polyline === 'string' && polyline && !polyline.startsWith('fallback:')) {
    const decoded = decodeEncodedPolyline(polyline);
    if (decoded.length >= 2) {
      return decoded;
    }
  }

  if (typeof polyline === 'string' && polyline.startsWith('fallback:')) {
    const parts = polyline.replace('fallback:', '').split('|');
    const first = parseLatLng(parts[0]);
    const second = parseLatLng(parts[1]);
    return [first, second].filter(Boolean);
  }

  if (trip.pickup_lat && trip.pickup_lng && trip.dropoff_lat && trip.dropoff_lng) {
    return [
      { latitude: trip.pickup_lat, longitude: trip.pickup_lng },
      { latitude: trip.dropoff_lat, longitude: trip.dropoff_lng },
    ];
  }

  return [];
};

const decodeEncodedPolyline = (encoded) => {
  let index = 0;
  let lat = 0;
  let lng = 0;
  const coordinates = [];

  while (index < encoded.length) {
    let shift = 0;
    let result = 0;
    let byte = null;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20 && index < encoded.length + 1);

    const deltaLat = (result & 1) ? ~(result >> 1) : (result >> 1);
    lat += deltaLat;

    shift = 0;
    result = 0;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20 && index < encoded.length + 1);

    const deltaLng = (result & 1) ? ~(result >> 1) : (result >> 1);
    lng += deltaLng;

    coordinates.push({
      latitude: lat / 1e5,
      longitude: lng / 1e5,
    });
  }

  return coordinates;
};

const parseLatLng = (value) => {
  if (!value) {
    return null;
  }

  const [lat, lng] = value.split(',').map((item) => Number(item));
  if (Number.isNaN(lat) || Number.isNaN(lng)) {
    return null;
  }

  return { latitude: lat, longitude: lng };
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 16,
  },
  header: {
    marginBottom: 14,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1a1a1a',
  },
  subtitle: {
    marginTop: 4,
    color: '#666',
  },
  socketStatus: {
    marginTop: 6,
    fontSize: 12,
    fontWeight: '600',
  },
  socketConnected: {
    color: '#15803d',
  },
  socketDisconnected: {
    color: '#92400e',
  },
  button: {
    backgroundColor: '#2196F3',
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
    marginBottom: 16,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
  },
  startButton: {
    backgroundColor: '#16a34a',
  },
  stopButton: {
    backgroundColor: '#dc2626',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 14,
    flex: 1,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 10,
    color: '#333',
  },
  mapContainer: {
    borderRadius: 10,
    overflow: 'hidden',
    marginBottom: 12,
  },
  map: {
    width: '100%',
    height: 250,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  rowLabel: {
    color: '#666',
    fontWeight: '500',
  },
  rowValue: {
    color: '#222',
    fontWeight: '600',
  },
  statsBox: {
    marginTop: 16,
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#eef6ff',
  },
  statsTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#1a1a1a',
    marginBottom: 6,
  },
  statsText: {
    color: '#2e3f55',
    marginBottom: 4,
  },
  helperText: {
    marginTop: 10,
    color: '#6b7280',
    fontSize: 12,
  },
  emptyText: {
    marginTop: 20,
    color: '#777',
    textAlign: 'center',
  },
  errorText: {
    color: '#c62828',
    marginBottom: 10,
  },
});
