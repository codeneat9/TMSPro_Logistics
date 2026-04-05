import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  Switch,
  View,
} from 'react-native';
import { StatusBar as ExpoStatusBar } from 'expo-status-bar';
import AsyncStorage from '@react-native-async-storage/async-storage';
import MapView, { Marker, Polyline } from 'react-native-maps';
import * as Location from 'expo-location';
import * as Notifications from 'expo-notifications';

const STAGES = ['assigned', 'at_pickup', 'picked_up', 'in_transit', 'delivered'];
const STAGE_LABELS = {
  assigned: 'Assigned',
  at_pickup: 'At Pickup',
  picked_up: 'Picked Up',
  in_transit: 'In Transit',
  delivered: 'Delivered',
};

const defaultForm = {
  apiBase: 'http://127.0.0.1:8000',
  pickupLat: '38.7075',
  pickupLon: '-9.1371',
  destinationLat: '38.6620',
  destinationLon: '-9.2155',
  taxiId: '20000589',
  callType: 'A',
  temp: '22',
  precip: '0',
  wind: '5',
  strategy: 'balanced',
  shipmentId: 'SHP-10027',
  serviceLevel: 'standard',
  cargoType: 'parcel',
  stopCount: '1',
  loadWeight: '320',
  vehicleCapacity: '900',
  promisedByMinutes: '90',
};

const SESSION_KEY = 'tms_mobile_session_v1';
const HISTORY_KEY = 'tms_mobile_trip_history_v1';

const defaultLogin = {
  username: 'driver1',
  password: 'demo123',
  role: 'logistics',
};

const initialRegion = {
  latitude: 38.689,
  longitude: -9.17,
  latitudeDelta: 0.12,
  longitudeDelta: 0.12,
};

function toNum(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function badgeType(value, warnThreshold, dangerThreshold) {
  if (value >= dangerThreshold) return 'danger';
  if (value >= warnThreshold) return 'warn';
  return 'ok';
}

function App() {
  const [login, setLogin] = useState(defaultLogin);
  const [session, setSession] = useState(null);
  const [hydrating, setHydrating] = useState(true);
  const [form, setForm] = useState(defaultForm);
  const [stage, setStage] = useState('assigned');
  const [loading, setLoading] = useState(false);
  const [trip, setTrip] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [tripHistory, setTripHistory] = useState([]);
  const [cloudKpis, setCloudKpis] = useState(null);
  const [syncStatus, setSyncStatus] = useState('local-only');
  const [currentView, setCurrentView] = useState('operations');
  const [gpsEnabled, setGpsEnabled] = useState(false);
  const [locationPermission, setLocationPermission] = useState(false);
  const [notifPermission, setNotifPermission] = useState(false);
  const [liveLocation, setLiveLocation] = useState(null);
  const locationSubRef = useRef(null);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const sessionRaw = await AsyncStorage.getItem(SESSION_KEY);
        const historyRaw = await AsyncStorage.getItem(HISTORY_KEY);
        if (sessionRaw) {
          const parsedSession = JSON.parse(sessionRaw);
          setSession(parsedSession);
          setCurrentView(parsedSession.role === 'customer' ? 'customer' : 'operations');
        }
        if (historyRaw) {
          const parsedHistory = JSON.parse(historyRaw);
          if (Array.isArray(parsedHistory)) {
            setTripHistory(parsedHistory);
          }
        }
      } catch {
        // Ignore bad cache and continue with defaults.
      } finally {
        setHydrating(false);
      }
    };

    bootstrap();
  }, []);

  useEffect(() => {
    return () => {
      if (locationSubRef.current) {
        locationSubRef.current.remove();
      }
    };
  }, []);

  const delayProbability = useMemo(() => {
    if (!trip) return 0;
    const p = trip.delay_probability ?? trip.predicted_delay?.probability ?? 0;
    return toNum(p, 0);
  }, [trip]);

  const adjustedEtaMin = useMemo(() => {
    if (!trip) return 0;
    const base = toNum(trip.primary_route?.estimated_time_min, 0);
    const delayFactor = 1 + delayProbability * 0.35;
    return base * delayFactor;
  }, [trip, delayProbability]);

  const logistics = useMemo(() => {
    const promisedByMinutes = Math.max(0, toNum(form.promisedByMinutes, 90));
    const slackMin = promisedByMinutes - adjustedEtaMin;
    const utilization = Math.min(200, (Math.max(0, toNum(form.loadWeight, 0)) / Math.max(1, toNum(form.vehicleCapacity, 1))) * 100);

    let slaStatus = 'On Track';
    if (slackMin < 0) slaStatus = 'Breach';
    else if (slackMin < 20) slaStatus = 'At Risk';

    const serviceBase = form.serviceLevel === 'same_day' ? 85 : form.serviceLevel === 'express' ? 70 : 55;
    const slaBoost = slaStatus === 'Breach' ? 20 : slaStatus === 'At Risk' ? 10 : 0;
    const utilBoost = utilization >= 90 ? 8 : utilization >= 75 ? 4 : 0;
    const dispatchPriority = Math.max(1, Math.min(99, Math.round(serviceBase + delayProbability * 25 + slaBoost + utilBoost)));

    return {
      slackMin,
      utilization,
      slaStatus,
      dispatchPriority,
    };
  }, [form.loadWeight, form.promisedByMinutes, form.serviceLevel, form.vehicleCapacity, adjustedEtaMin, delayProbability]);

  const mapRegion = useMemo(() => {
    if (liveLocation) {
      return {
        latitude: liveLocation.latitude,
        longitude: liveLocation.longitude,
        latitudeDelta: 0.06,
        longitudeDelta: 0.06,
      };
    }

    if (trip?.pickup?.lat && trip?.pickup?.lon) {
      return {
        latitude: toNum(trip.pickup.lat, initialRegion.latitude),
        longitude: toNum(trip.pickup.lon, initialRegion.longitude),
        latitudeDelta: 0.08,
        longitudeDelta: 0.08,
      };
    }

    return initialRegion;
  }, [liveLocation, trip]);

  const routeLines = useMemo(() => {
    if (!trip) return [];

    const lines = [];
    if (trip.primary_route?.coordinates?.length) {
      lines.push({
        key: 'primary',
        name: trip.primary_route.route_name || 'Primary',
        color: '#1cc7a7',
        width: 5,
        coordinates: trip.primary_route.coordinates.map((point) => ({
          latitude: toNum(point[0]),
          longitude: toNum(point[1]),
        })),
      });
    }

    const alternates = Array.isArray(trip.alternate_routes) ? trip.alternate_routes.slice(0, 2) : [];
    alternates.forEach((route, idx) => {
      if (route?.coordinates?.length) {
        lines.push({
          key: `alt-${idx}`,
          name: route.route_name || `Alternative ${idx + 1}`,
          color: idx === 0 ? '#ffd166' : '#f78c6b',
          width: 4,
          coordinates: route.coordinates.map((point) => ({
            latitude: toNum(point[0]),
            longitude: toNum(point[1]),
          })),
        });
      }
    });

    return lines;
  }, [trip]);

  const pushAlert = (level, message) => {
    setAlerts((prev) => [{ id: Date.now(), level, message }, ...prev].slice(0, 8));
  };

  const requestNotificationPermission = async () => {
    const existing = await Notifications.getPermissionsAsync();
    if (existing.status === 'granted') {
      setNotifPermission(true);
      return true;
    }
    const requested = await Notifications.requestPermissionsAsync();
    const granted = requested.status === 'granted';
    setNotifPermission(granted);
    return granted;
  };

  const notifyLocal = async (title, body) => {
    const allowed = notifPermission || (await requestNotificationPermission());
    if (!allowed) return;

    await Notifications.scheduleNotificationAsync({
      content: { title, body },
      trigger: null,
    });
  };

  const requestLocationPermission = async () => {
    const existing = await Location.getForegroundPermissionsAsync();
    if (existing.status === 'granted') {
      setLocationPermission(true);
      return true;
    }
    const requested = await Location.requestForegroundPermissionsAsync();
    const granted = requested.status === 'granted';
    setLocationPermission(granted);
    return granted;
  };

  const toggleGpsTracking = async (enabled) => {
    setGpsEnabled(enabled);

    if (!enabled) {
      if (locationSubRef.current) {
        locationSubRef.current.remove();
        locationSubRef.current = null;
      }
      pushAlert('ok', 'Live GPS tracking paused.');
      return;
    }

    const granted = await requestLocationPermission();
    if (!granted) {
      setGpsEnabled(false);
      Alert.alert('Location Permission Required', 'Enable location permission to use live GPS tracking.');
      return;
    }

    const sub = await Location.watchPositionAsync(
      {
        accuracy: Location.Accuracy.Balanced,
        timeInterval: 4000,
        distanceInterval: 10,
      },
      (position) => {
        const coords = position.coords;
        const next = {
          latitude: coords.latitude,
          longitude: coords.longitude,
          speed: coords.speed,
          heading: coords.heading,
          timestamp: position.timestamp,
        };
        setLiveLocation(next);
      }
    );

    locationSubRef.current = sub;
    pushAlert('ok', 'Live GPS tracking started.');
  };

  const persistHistory = async (item) => {
    const next = [item, ...tripHistory].slice(0, 40);
    setTripHistory(next);
    await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(next));
    return next;
  };

  const fetchCloudKpis = async (base, userId) => {
    if (!base || !userId) return;
    try {
      const response = await fetch(`${base}/mobile/sync/kpis/${encodeURIComponent(userId)}`);
      if (!response.ok) return;
      const data = await response.json();
      setCloudKpis(data.kpis || null);
      setSyncStatus('cloud-connected');
    } catch {
      setSyncStatus('cloud-unreachable');
    }
  };

  const cloudLogin = async (base, user, pass, role) => {
    const response = await fetch(`${base}/mobile/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: user, password: pass, role }),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `HTTP ${response.status}`);
    }

    return response.json();
  };

  const syncTripToCloud = async (base, sessionData, data, localRecord) => {
    if (!base || !sessionData?.userId || !data) return false;

    const payload = {
      trip_id: data.trip_id || localRecord.tripId,
      user_id: sessionData.userId,
      role: sessionData.role,
      shipment_id: form.shipmentId,
      delay_probability: toNum(data.predicted_delay?.probability, 0),
      distance_km: toNum(data.primary_route?.distance_km, 0),
      eta_min: toNum(data.primary_route?.estimated_time_min, 0),
      sla_status: logistics.slaStatus,
      dispatch_priority: logistics.dispatchPriority,
      metadata: {
        stage,
        strategy: form.strategy,
        service_level: form.serviceLevel,
        cargo_type: form.cargoType,
      },
    };

    const response = await fetch(`${base}/mobile/sync/trip`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `HTTP ${response.status}`);
    }

    return true;
  };

  const loginUser = async () => {
    if (!login.username.trim() || !login.password.trim()) {
      Alert.alert('Login Error', 'Username and password are required.');
      return;
    }

    const base = form.apiBase.trim().replace(/\/$/, '');
    let nextSession;

    try {
      const cloudSession = await cloudLogin(base, login.username.trim(), login.password.trim(), login.role);
      nextSession = {
        userId: cloudSession.user_id,
        role: cloudSession.role,
        token: cloudSession.token,
        signedInAt: Date.now(),
      };
      setSyncStatus('cloud-connected');
    } catch {
      nextSession = {
        userId: login.username.trim(),
        role: login.role,
        token: `demo-${Date.now()}`,
        signedInAt: Date.now(),
      };
      setSyncStatus('cloud-unreachable');
      pushAlert('warn', 'Cloud login unavailable, using local offline session.');
    }

    await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(nextSession));
    setSession(nextSession);
    setCurrentView(nextSession.role === 'customer' ? 'customer' : 'operations');
    fetchCloudKpis(base, nextSession.userId);
    pushAlert('ok', `Signed in as ${nextSession.userId}.`);
  };

  const logout = async () => {
    await AsyncStorage.removeItem(SESSION_KEY);
    if (locationSubRef.current) {
      locationSubRef.current.remove();
      locationSubRef.current = null;
    }
    setGpsEnabled(false);
    setSession(null);
    setTrip(null);
    setCloudKpis(null);
    setSyncStatus('local-only');
  };

  const updateField = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const submitPlan = async () => {
    const base = form.apiBase.trim().replace(/\/$/, '');
    const payload = {
      trip_id: `MOBILE-${Date.now()}`,
      driver_id: 'DRV-MOBILE-001',
      pickup_lat: toNum(form.pickupLat),
      pickup_lon: toNum(form.pickupLon),
      destination_lat: toNum(form.destinationLat),
      destination_lon: toNum(form.destinationLon),
      pickup_timestamp: Math.floor(Date.now() / 1000),
      taxi_id: Math.floor(toNum(form.taxiId, 20000589)),
      call_type: form.callType || 'A',
      day_type: 'B',
      temperature_2m: toNum(form.temp, 22),
      precipitation: toNum(form.precip, 0),
      windspeed_10m: toNum(form.wind, 5),
      strategy: form.strategy || 'balanced',
    };

    setLoading(true);
    try {
      const response = await fetch(`${base}/dashboard/plan-trip`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setTrip(data);
      pushAlert('ok', 'Trip planned successfully from mobile app.');

      const localRecord = {
        tripId: data.trip_id || payload.trip_id,
        createdAt: Date.now(),
        delayProbability: toNum(data.predicted_delay?.probability, 0),
        distanceKm: toNum(data.primary_route?.distance_km, 0),
        etaMin: toNum(data.primary_route?.estimated_time_min, 0),
        userId: session?.userId || 'anonymous',
      };

      await persistHistory({
        ...localRecord,
      });

      try {
        const synced = await syncTripToCloud(base, session, data, localRecord);
        if (synced) {
          setSyncStatus('cloud-connected');
          await fetchCloudKpis(base, session?.userId);
        }
      } catch {
        setSyncStatus('cloud-unreachable');
        pushAlert('warn', 'Cloud sync failed. Trip saved locally for later sync.');
      }

      const p = toNum(data.delay_probability ?? data.predicted_delay?.probability ?? 0);
      if (p >= 0.75) {
        pushAlert('danger', 'Critical delay risk detected for this shipment.');
        await notifyLocal('Critical Delay Risk', 'Shipment delay risk is high. Review reroute recommendation now.');
      } else if (p >= 0.5) {
        pushAlert('warn', 'Moderate delay risk detected, monitor closely.');
        await notifyLocal('Moderate Delay Risk', 'This shipment may be delayed. Keep monitoring route conditions.');
      }

      if (data.reroute_recommendation?.should_reroute) {
        await notifyLocal('Reroute Recommended', 'AI agent suggests switching route to protect SLA.');
      }
    } catch (err) {
      pushAlert('danger', `Planning failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const setWorkflowStage = (nextStage) => {
    setStage(nextStage);
    pushAlert('ok', `Workflow updated to ${STAGE_LABELS[nextStage]}.`);
    if (nextStage === 'delivered') {
      pushAlert('ok', 'Delivery completed. Capture proof-of-delivery in next step.');
    }
  };

  const renderOperationsView = () => {
    return (
      <>
        <Card title="API Connection">
          <Label text="API Base URL" />
          <Input value={form.apiBase} onChangeText={(v) => updateField('apiBase', v)} placeholder="http://192.168.1.10:8000" />
          <Text style={styles.helper}>Use your PC local IP for real devices. Example: http://192.168.x.x:8000</Text>
        </Card>

        <Card title="Trip Coordinates">
          <Row>
            <Field label="Pickup Lat" value={form.pickupLat} onChange={(v) => updateField('pickupLat', v)} />
            <Field label="Pickup Lon" value={form.pickupLon} onChange={(v) => updateField('pickupLon', v)} />
          </Row>
          <Row>
            <Field label="Dest Lat" value={form.destinationLat} onChange={(v) => updateField('destinationLat', v)} />
            <Field label="Dest Lon" value={form.destinationLon} onChange={(v) => updateField('destinationLon', v)} />
          </Row>
        </Card>

        <Card title="Logistics Operations">
          <Row>
            <Field label="Shipment ID" value={form.shipmentId} onChange={(v) => updateField('shipmentId', v)} />
            <Field label="Service" value={form.serviceLevel} onChange={(v) => updateField('serviceLevel', v)} />
          </Row>
          <Row>
            <Field label="Cargo" value={form.cargoType} onChange={(v) => updateField('cargoType', v)} />
            <Field label="Stops" value={form.stopCount} onChange={(v) => updateField('stopCount', v)} />
          </Row>
          <Row>
            <Field label="Load (kg)" value={form.loadWeight} onChange={(v) => updateField('loadWeight', v)} />
            <Field label="Capacity (kg)" value={form.vehicleCapacity} onChange={(v) => updateField('vehicleCapacity', v)} />
          </Row>
          <Row>
            <Field label="Promised In (min)" value={form.promisedByMinutes} onChange={(v) => updateField('promisedByMinutes', v)} />
            <Field label="Strategy" value={form.strategy} onChange={(v) => updateField('strategy', v)} />
          </Row>

          <Pressable style={styles.primaryButton} onPress={submitPlan} disabled={loading}>
            {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>Plan Shipment Trip</Text>}
          </Pressable>
        </Card>

        <Card title="Shipment Workflow">
          <View style={styles.stageWrap}>
            {STAGES.map((s) => (
              <Pressable
                key={s}
                onPress={() => setWorkflowStage(s)}
                style={[styles.stagePill, s === stage ? styles.stagePillActive : null]}
              >
                <Text style={[styles.stageText, s === stage ? styles.stageTextActive : null]}>{STAGE_LABELS[s]}</Text>
              </Pressable>
            ))}
          </View>
        </Card>

        <Card title="Operations KPIs">
          <Kpi label="Dispatch Priority" value={`${logistics.dispatchPriority}/99`} type={badgeType(logistics.dispatchPriority, 75, 90)} />
          <Kpi label="Load Utilization" value={`${logistics.utilization.toFixed(0)}%`} type={badgeType(logistics.utilization, 80, 95)} />
          <Kpi
            label="SLA Slack"
            value={`${logistics.slackMin >= 0 ? '+' : ''}${logistics.slackMin.toFixed(0)} min`}
            type={logistics.slackMin < 0 ? 'danger' : logistics.slackMin < 20 ? 'warn' : 'ok'}
          />
          <Kpi label="SLA Status" value={logistics.slaStatus} type={logistics.slaStatus === 'Breach' ? 'danger' : logistics.slaStatus === 'At Risk' ? 'warn' : 'ok'} />
        </Card>
      </>
    );
  };

  const renderCustomerView = () => {
    return (
      <>
        <Card title="Parcel Tracking">
          <Kpi label="Shipment" value={form.shipmentId} type="ok" />
          <Kpi label="Current Stage" value={STAGE_LABELS[stage]} type="ok" />
          <Kpi
            label="Delay Risk"
            value={`${(delayProbability * 100).toFixed(1)}%`}
            type={delayProbability >= 0.75 ? 'danger' : delayProbability >= 0.5 ? 'warn' : 'ok'}
          />
          <Kpi label="ETA" value={`${adjustedEtaMin.toFixed(1)} min`} type="ok" />
          <Text style={styles.smallText}>This customer flow focuses on shipment status and delivery confidence.</Text>
        </Card>

        <Card title="Customer Notifications">
          <Text style={styles.smallText}>
            Alerts are sent for reroute decisions and high delay risk so customers stay informed automatically.
          </Text>
        </Card>
      </>
    );
  };

  if (hydrating) {
    return (
      <SafeAreaView style={styles.safeAreaLoading}>
        <ActivityIndicator color="#1cc7a7" size="large" />
        <Text style={styles.loadingText}>Loading mobile workspace...</Text>
      </SafeAreaView>
    );
  }

  if (!session) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <ExpoStatusBar style="light" />
        <StatusBar barStyle="light-content" />
        <ScrollView contentContainerStyle={styles.container}>
          <Text style={styles.headerTitle}>TMS Logistics Mobile</Text>
          <Text style={styles.headerSub}>Sign in as customer or logistics operator</Text>

          <Card title="Sign In">
            <Field label="Username" value={login.username} onChange={(v) => setLogin((prev) => ({ ...prev, username: v }))} />
            <Field label="Password" value={login.password} onChange={(v) => setLogin((prev) => ({ ...prev, password: v }))} />
            <Label text="Role" />
            <View style={styles.segmentWrap}>
              <Pressable
                style={[styles.segmentButton, login.role === 'customer' ? styles.segmentButtonActive : null]}
                onPress={() => setLogin((prev) => ({ ...prev, role: 'customer' }))}
              >
                <Text style={styles.segmentText}>Customer</Text>
              </Pressable>
              <Pressable
                style={[styles.segmentButton, login.role === 'logistics' ? styles.segmentButtonActive : null]}
                onPress={() => setLogin((prev) => ({ ...prev, role: 'logistics' }))}
              >
                <Text style={styles.segmentText}>Logistics</Text>
              </Pressable>
            </View>

            <Pressable style={styles.primaryButton} onPress={loginUser}>
              <Text style={styles.primaryButtonText}>Sign In</Text>
            </Pressable>
            <Text style={styles.helper}>Demo credentials: any username + password. Role controls default UI flow.</Text>
          </Card>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <ExpoStatusBar style="light" />
      <StatusBar barStyle="light-content" />
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.headerTitle}>TMS Logistics Mobile</Text>
        <Text style={styles.headerSub}>Signed in as {session.userId} ({session.role})</Text>

        <Card title="Workspace Controls">
          <Label text="View" />
          <View style={styles.segmentWrap}>
            <Pressable
              style={[styles.segmentButton, currentView === 'customer' ? styles.segmentButtonActive : null]}
              onPress={() => setCurrentView('customer')}
            >
              <Text style={styles.segmentText}>Customer</Text>
            </Pressable>
            <Pressable
              style={[styles.segmentButton, currentView === 'operations' ? styles.segmentButtonActive : null]}
              onPress={() => setCurrentView('operations')}
            >
              <Text style={styles.segmentText}>Logistics</Text>
            </Pressable>
          </View>

          <View style={styles.switchRow}>
            <Text style={styles.kpiLabel}>Live GPS Tracking</Text>
            <Switch
              value={gpsEnabled}
              onValueChange={toggleGpsTracking}
              trackColor={{ false: '#355b8e', true: '#1cc7a7' }}
              thumbColor="#f3f8ff"
            />
          </View>
          <Text style={styles.helper}>Location: {locationPermission ? 'granted' : 'not granted'} | Notifications: {notifPermission ? 'granted' : 'not granted'}</Text>
          <Pressable style={styles.secondaryButton} onPress={logout}>
            <Text style={styles.secondaryButtonText}>Sign Out</Text>
          </Pressable>
        </Card>

        {currentView === 'operations' ? renderOperationsView() : renderCustomerView()}

        <Card title="Route Visualization">
          <MapView style={styles.map} initialRegion={initialRegion} region={mapRegion}>
            {trip?.pickup ? (
              <Marker
                coordinate={{
                  latitude: toNum(trip.pickup.lat),
                  longitude: toNum(trip.pickup.lon),
                }}
                title="Pickup"
                pinColor="#35d19b"
              />
            ) : null}
            {trip?.destination ? (
              <Marker
                coordinate={{
                  latitude: toNum(trip.destination.lat),
                  longitude: toNum(trip.destination.lon),
                }}
                title="Destination"
                pinColor="#f06464"
              />
            ) : null}
            {liveLocation ? <Marker coordinate={liveLocation} title="Live Vehicle" pinColor="#2c87ff" /> : null}
            {routeLines.map((line) => (
              <Polyline key={line.key} coordinates={line.coordinates} strokeColor={line.color} strokeWidth={line.width} />
            ))}
          </MapView>
          {routeLines.length === 0 ? <Text style={styles.smallText}>Plan a trip to render primary + 2 alternate routes.</Text> : null}
          {routeLines.map((line) => (
            <Kpi key={line.key} label={line.name} value={`${line.coordinates.length} points`} type="ok" />
          ))}
        </Card>

        {trip ? (
          <Card title="Planned Trip Summary">
            <Kpi label="Delay Risk" value={`${(delayProbability * 100).toFixed(1)}%`} type={delayProbability >= 0.75 ? 'danger' : delayProbability >= 0.5 ? 'warn' : 'ok'} />
            <Kpi label="Distance" value={`${toNum(trip.primary_route?.distance_km, 0).toFixed(2)} km`} type="ok" />
            <Kpi label="Adjusted ETA" value={`${adjustedEtaMin.toFixed(1)} min`} type="ok" />
            <Kpi label="Alt Routes" value={`${(trip.alternate_routes || []).length}`} type="ok" />
            <Text style={styles.smallText}>{trip.driver_notification || trip.driver_alert || 'No driver notification.'}</Text>
          </Card>
        ) : null}

        <Card title="Cloud Sync Snapshot">
          <Kpi label="Trip History" value={`${tripHistory.length} records`} type="ok" />
          <Kpi label="Driver" value={session.userId} type="ok" />
          <Kpi label="Role" value={session.role} type="ok" />
          <Kpi label="Sync" value={syncStatus} type={syncStatus === 'cloud-connected' ? 'ok' : syncStatus === 'cloud-unreachable' ? 'warn' : 'ok'} />
          <Kpi label="Cloud Trips" value={`${cloudKpis?.trip_count ?? 0}`} type="ok" />
          <Kpi label="At Risk" value={`${cloudKpis?.at_risk_trips ?? 0}`} type={(cloudKpis?.at_risk_trips ?? 0) > 0 ? 'warn' : 'ok'} />
          <Text style={styles.smallText}>Trip history persists locally and syncs to cloud when backend connectivity is available.</Text>
        </Card>

        <Card title="Operational Alerts">
          {alerts.length === 0 ? <Text style={styles.smallText}>No alerts yet.</Text> : null}
          {alerts.map((item) => (
            <View key={item.id} style={styles.alertItem}>
              <Text style={[styles.alertDot, styles[`dot_${item.level}`]]}>●</Text>
              <Text style={styles.alertText}>{item.message}</Text>
            </View>
          ))}
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

function Card({ title, children }) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>{title}</Text>
      {children}
    </View>
  );
}

function Row({ children }) {
  return <View style={styles.row}>{children}</View>;
}

function Field({ label, value, onChange }) {
  return (
    <View style={styles.field}>
      <Label text={label} />
      <Input value={value} onChangeText={onChange} />
    </View>
  );
}

function Label({ text }) {
  return <Text style={styles.label}>{text}</Text>;
}

function Input({ value, onChangeText, placeholder }) {
  return (
    <TextInput
      style={styles.input}
      value={value}
      onChangeText={onChangeText}
      placeholder={placeholder}
      placeholderTextColor="#86a0c9"
    />
  );
}

function Kpi({ label, value, type }) {
  return (
    <View style={styles.kpiRow}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={[styles.kpiValue, styles[`kpi_${type}`]]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safeAreaLoading: {
    flex: 1,
    backgroundColor: '#071325',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  safeArea: {
    flex: 1,
    backgroundColor: '#071325',
  },
  loadingText: {
    color: '#dceaff',
    fontSize: 13,
  },
  container: {
    padding: 16,
    gap: 12,
    paddingBottom: 28,
  },
  headerTitle: {
    color: '#eff6ff',
    fontSize: 24,
    fontWeight: '800',
  },
  headerSub: {
    color: '#a8c0e6',
    marginTop: 2,
    marginBottom: 4,
  },
  card: {
    backgroundColor: '#10213d',
    borderWidth: 1,
    borderColor: '#2b4f82',
    borderRadius: 14,
    padding: 12,
    gap: 8,
  },
  cardTitle: {
    color: '#dceaff',
    fontWeight: '800',
    fontSize: 13,
    letterSpacing: 0.4,
    textTransform: 'uppercase',
  },
  row: {
    flexDirection: 'row',
    gap: 8,
  },
  field: {
    flex: 1,
  },
  label: {
    color: '#a8c0e6',
    fontSize: 11,
    marginBottom: 4,
  },
  input: {
    borderWidth: 1,
    borderColor: '#355b8e',
    borderRadius: 10,
    color: '#eff6ff',
    backgroundColor: '#0a1b33',
    paddingHorizontal: 10,
    paddingVertical: 9,
    fontSize: 13,
  },
  helper: {
    color: '#87a0c8',
    fontSize: 11,
  },
  segmentWrap: {
    flexDirection: 'row',
    gap: 8,
  },
  segmentButton: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#426ea5',
    paddingVertical: 9,
    alignItems: 'center',
    backgroundColor: '#0b1a31',
  },
  segmentButtonActive: {
    backgroundColor: '#0e5dc4',
    borderColor: '#6eb3ff',
  },
  segmentText: {
    color: '#deecff',
    fontWeight: '700',
    fontSize: 12,
  },
  primaryButton: {
    marginTop: 8,
    backgroundColor: '#2c87ff',
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#fff',
    fontWeight: '700',
  },
  secondaryButton: {
    marginTop: 8,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#4f709f',
    paddingVertical: 10,
    alignItems: 'center',
    backgroundColor: '#0b1f3a',
  },
  secondaryButtonText: {
    color: '#dbe8fc',
    fontWeight: '700',
  },
  switchRow: {
    marginTop: 6,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  stageWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  stagePill: {
    borderWidth: 1,
    borderColor: '#456aa1',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: '#0b1a31',
  },
  stagePillActive: {
    backgroundColor: '#0e5dc4',
    borderColor: '#70b9ff',
  },
  stageText: {
    color: '#bad0ef',
    fontSize: 11,
    fontWeight: '600',
  },
  stageTextActive: {
    color: '#f4f9ff',
  },
  kpiRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: '#1f365d',
  },
  kpiLabel: {
    color: '#a9c2e6',
    fontSize: 12,
  },
  kpiValue: {
    fontWeight: '700',
    fontSize: 12,
  },
  kpi_ok: {
    color: '#6be6a6',
  },
  kpi_warn: {
    color: '#ffd27f',
  },
  kpi_danger: {
    color: '#ff8a8c',
  },
  smallText: {
    color: '#bdd0ee',
    fontSize: 12,
    marginTop: 4,
  },
  map: {
    width: '100%',
    height: 240,
    borderRadius: 10,
  },
  alertItem: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'flex-start',
    marginBottom: 6,
  },
  alertDot: {
    fontSize: 12,
    marginTop: 1,
  },
  dot_ok: {
    color: '#6be6a6',
  },
  dot_warn: {
    color: '#ffd27f',
  },
  dot_danger: {
    color: '#ff8a8c',
  },
  alertText: {
    color: '#d8e8ff',
    flex: 1,
    fontSize: 12,
  },
});

export default App;
