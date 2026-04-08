import { PermissionsAndroid, Platform } from 'react-native';
import Geolocation from 'react-native-geolocation-service';
import BackgroundService from 'react-native-background-actions';
import { getAuthTokens, getWebSocketUrl } from './api';

const state = {
  watchId: null,
  socket: null,
  tripId: null,
  running: false,
};

const sleep = (time) => new Promise((resolve) => setTimeout(resolve, time));

const backgroundTask = async () => {
  while (BackgroundService.isRunning()) {
    await sleep(5000);
  }
};

const requestLocationPermissions = async () => {
  if (Platform.OS !== 'android') {
    return true;
  }

  const fine = await PermissionsAndroid.request(
    PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION
  );

  if (fine !== PermissionsAndroid.RESULTS.GRANTED) {
    return false;
  }

  if (Platform.Version >= 29) {
    await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.ACCESS_BACKGROUND_LOCATION
    );
  }

  return true;
};

const openSocket = async (tripId) => {
  const { accessToken } = await getAuthTokens();
  if (!accessToken) {
    return null;
  }

  const url = getWebSocketUrl(`/ws/trip/${tripId}`, accessToken);
  const socket = new WebSocket(url);

  socket.onopen = () => {
    // Connected.
  };

  socket.onerror = () => {
    // Keep watcher alive; socket reconnect can be retried by caller.
  };

  socket.onclose = () => {
    if (state.socket === socket) {
      state.socket = null;
    }
  };

  state.socket = socket;
  return socket;
};

const sendLocation = (coords) => {
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
    return;
  }

  const speedMs = typeof coords.speed === 'number' && coords.speed >= 0 ? coords.speed : 0;
  const speedKmh = Number((speedMs * 3.6).toFixed(1));

  state.socket.send(
    JSON.stringify({
      type: 'location_update',
      latitude: coords.latitude,
      longitude: coords.longitude,
      speed_kmh: speedKmh,
      heading: coords.heading ?? 0,
    })
  );
};

export const startLocationStreaming = async (tripId) => {
  if (!tripId) {
    return { ok: false, error: 'trip_id_required' };
  }

  if (state.running) {
    return { ok: true };
  }

  const granted = await requestLocationPermissions();
  if (!granted) {
    return { ok: false, error: 'location_permission_denied' };
  }

  await openSocket(tripId);

  await BackgroundService.start(backgroundTask, {
    taskName: 'TMSLocationTracking',
    taskTitle: 'TMS Tracking Active',
    taskDesc: 'Sharing location for active trip updates.',
    taskIcon: {
      name: 'ic_launcher',
      type: 'mipmap',
    },
    color: '#2196F3',
    linkingURI: 'tmspro://tracking',
    parameters: {},
  });

  state.tripId = tripId;
  state.watchId = Geolocation.watchPosition(
    (position) => {
      sendLocation(position.coords);
    },
    () => {
      // Ignore temporary GPS errors; watcher remains active.
    },
    {
      enableHighAccuracy: true,
      distanceFilter: 10,
      interval: 5000,
      fastestInterval: 3000,
      showsBackgroundLocationIndicator: true,
      forceRequestLocation: true,
    }
  );

  state.running = true;
  return { ok: true };
};

export const stopLocationStreaming = async () => {
  if (state.watchId !== null) {
    Geolocation.clearWatch(state.watchId);
    state.watchId = null;
  }

  if (state.socket) {
    try {
      state.socket.close();
    } catch {
      // Ignore close errors.
    }
    state.socket = null;
  }

  if (BackgroundService.isRunning()) {
    await BackgroundService.stop();
  }

  state.tripId = null;
  state.running = false;
  return { ok: true };
};

export const isLocationStreaming = () => state.running;
