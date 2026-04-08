/**
 * API Client for TMSPro Backend
 * Centralized API communication with authentication
 */

import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { jwtDecode } from 'jwt-decode';
import { Platform } from 'react-native';

// Set this to your PC LAN IP when testing on a physical phone, e.g. '192.168.1.8'.
const MANUAL_LAN_IP = '';

const RESOLVED_HOST = MANUAL_LAN_IP
  ? `http://${MANUAL_LAN_IP}:8001`
  : null;

const DEFAULT_BACKEND_BASE = Platform.select({
  android: RESOLVED_HOST || 'http://10.0.2.2:8001',
  default: RESOLVED_HOST || 'http://127.0.0.1:8001',
});

// Configure your backend URL here (can be replaced with env-based config later)
const API_URL = `${DEFAULT_BACKEND_BASE}/api`;
const HEALTH_CHECK_URL = `${DEFAULT_BACKEND_BASE}/health`;
const WS_BASE_URL = DEFAULT_BACKEND_BASE.replace(/^http/i, 'ws');

// Create axios instance with default config
const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor to add auth token
 */
api.interceptors.request.use(
  async (config) => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('Error getting token:', error);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Response interceptor to handle auth errors
 */
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 Unauthorized
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = await AsyncStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_URL}/auth/refresh-token`, {
            refresh_token: refreshToken,
          });

          // Save new tokens
          await AsyncStorage.setItem('access_token', response.data.access_token);
          if (response.data.refresh_token) {
            await AsyncStorage.setItem('refresh_token', response.data.refresh_token);
          }

          // Retry original request
          api.defaults.headers.common.Authorization = `Bearer ${response.data.access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, clear auth and redirect
        await clearAuth();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Auth APIs
 */
export const authAPI = {
  register: (email, password, fullName, phone) =>
    api.post('/auth/register', { email, password, full_name: fullName, phone, role: 'customer' }),

  login: (email, password) =>
    api.post('/auth/login', { email, password }),

  refreshToken: (refreshToken) =>
    api.post('/auth/refresh-token', { refresh_token: refreshToken }),

  me: () =>
    api.get('/auth/me'),
};

/**
 * Trips APIs
 */
export const tripsAPI = {
  createTrip: (tripData) =>
    api.post('/trips', tripData),

  getTrip: (tripId) =>
    api.get(`/trips/${tripId}`),

  listTrips: (params) =>
    api.get('/trips', { params }),

  updateTrip: (tripId, data) =>
    api.patch(`/trips/${tripId}`, data),

  assignDriver: (tripId, data) =>
    api.post(`/trips/${tripId}/assign-driver`, data),

  startTrip: (tripId) =>
    api.post(`/trips/${tripId}/start`),

  completeTrip: (tripId) =>
    api.post(`/trips/${tripId}/complete`),
};

/**
 * Drivers APIs
 */
export const driversAPI = {
  createProfile: (driverData) =>
    api.post('/drivers', driverData),

  getProfile: () =>
    api.get('/drivers/profile'),

  getDriver: (driverId) =>
    api.get(`/drivers/${driverId}`),

  listDrivers: (params) =>
    api.get('/drivers', { params }),

  updateStatus: (driverId, status) =>
    api.patch(`/drivers/${driverId}/status`, { status }),

  updateLocation: (driverId, lat, lng) =>
    api.post(`/drivers/${driverId}/location`, { latitude: lat, longitude: lng }),

  getNearbyDrivers: (lat, lng, radius) =>
    api.get('/drivers/nearby', { params: { latitude: lat, longitude: lng, radius } }),
};

/**
 * Locations APIs
 */
export const locationsAPI = {
  recordLocation: (tripId, locationData) =>
    api.post('/locations', { trip_id: tripId, ...locationData }),

  getTripLocations: (tripId, params) =>
    api.get(`/locations/${tripId}`, { params }),

  getRecentLocations: (tripId, minutes) =>
    api.get(`/locations/${tripId}/recent`, { params: { minutes } }),

  getLatestLocation: (tripId) =>
    api.get(`/locations/${tripId}/latest`),

  getTripStats: (tripId) =>
    api.get(`/locations/${tripId}/stats`),

  getSpeedingEvents: (tripId, speedLimit) =>
    api.get(`/locations/${tripId}/speed-violations`, { params: { speed_limit: speedLimit } }),
};

/**
 * Routes APIs
 */
export const routesAPI = {
  createRoute: (routeData) =>
    api.post('/routes', routeData),

  getRoute: (routeId) =>
    api.get(`/routes/${routeId}`),

  getTripRoutes: (tripId) =>
    api.get(`/routes/trip/${tripId}`),

  getOptimalRoute: (tripId) =>
    api.post(`/routes/trip/${tripId}/optimal`),

  getAlternativeRoutes: (tripId) =>
    api.post(`/routes/trip/${tripId}/alternatives`),

  selectRoute: (tripId, routeId) =>
    api.post(`/routes/trip/${tripId}/select/${routeId}`),

  predictDelay: (delayData) =>
    api.post('/routes/predict-delay', delayData),

  calculateRisk: (riskData) =>
    api.post('/routes/calculate-risk', riskData),

  estimateCost: (costData) =>
    api.post('/routes/estimate-cost', costData),
};

/**
 * Notifications APIs
 */
export const notificationsAPI = {
  registerDeviceToken: (token, platform = Platform.OS) =>
    api.post('/notifications/device-token', { token, platform }),

  listMyNotifications: (params) =>
    api.get('/notifications/me', { params }),

  markAsRead: (notificationId) =>
    api.patch(`/notifications/${notificationId}/read`),
};

/**
 * Health check and utility functions
 */
export const healthCheck = async () => {
  try {
    const response = await axios.get(HEALTH_CHECK_URL);
    return response.data;
  } catch (error) {
    return null;
  }
};

/**
 * Auth state management
 */
export const setAuthTokens = async (accessToken, refreshToken) => {
  await AsyncStorage.setItem('access_token', accessToken);
  if (refreshToken) {
    await AsyncStorage.setItem('refresh_token', refreshToken);
  }
  if (accessToken) {
    api.defaults.headers.common.Authorization = `Bearer ${accessToken}`;
  }
};

export const getAuthTokens = async () => {
  const accessToken = await AsyncStorage.getItem('access_token');
  const refreshToken = await AsyncStorage.getItem('refresh_token');
  return { accessToken, refreshToken };
};

export const getWebSocketUrl = (path, token) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const base = `${WS_BASE_URL}${normalizedPath}`;
  if (!token) {
    return base;
  }
  const separator = base.includes('?') ? '&' : '?';
  return `${base}${separator}token=${encodeURIComponent(token)}`;
};

export const hasValidToken = async () => {
  const token = await AsyncStorage.getItem('access_token');
  if (!token) return false;

  try {
    const decoded = jwtDecode(token);
    return decoded.exp * 1000 > Date.now();
  } catch {
    return false;
  }
};

export const clearAuth = async () => {
  await AsyncStorage.removeItem('access_token');
  await AsyncStorage.removeItem('refresh_token');
  delete api.defaults.headers.common.Authorization;
};

export const getUser = async () => {
  try {
    const response = await authAPI.me();
    return response.data;
  } catch {
    try {
      const token = await AsyncStorage.getItem('access_token');
      if (!token) return null;
      const decoded = jwtDecode(token);
      return {
        id: decoded.sub,
        email: decoded.email || null,
        role: decoded.role || null,
      };
    } catch {
      return null;
    }
  }
};

export default api;
