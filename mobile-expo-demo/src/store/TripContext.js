import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { Alert } from 'react-native';

import { generateTripPrediction, simulateReroute } from '../data/mockAiData';
import { getLocationById } from '../data/locations';
import { useAuth } from './AuthContext';
import {
  getNotificationSupportLabel,
  initNotifications,
  scheduleLocalNotification,
} from '../services/notifications';
import { sendSmsTripUpdate } from '../services/notificationsApi';

const TripContext = createContext(null);
const ENABLE_PHONE_DELIVERY = String(process.env.EXPO_PUBLIC_ENABLE_PHONE_NOTIFICATIONS || 'false').toLowerCase() === 'true';

function createId(prefix) {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

async function fireLocalNotification(title, body) {
  return scheduleLocalNotification(title, body);
}

export function TripProvider({ children }) {
  const { accessToken, user } = useAuth();
  const [trips, setTrips] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [notificationMode, setNotificationMode] = useState('Initializing alerts...');
  const [activeBanner, setActiveBanner] = useState(null);
  const bannerTimerRef = useRef(null);

  useEffect(() => {
    const initializeNotificationLayer = async () => {
      const ready = await initNotifications();
      if (ready) {
        setNotificationMode('Local push alerts enabled');
      } else {
        setNotificationMode(getNotificationSupportLabel());
      }
    };

    initializeNotificationLayer();
  }, []);

  const pushAlert = async (tripId, status, title, message) => {
    const alert = {
      id: createId('ALT'),
      tripId,
      status,
      title,
      message,
      createdAt: new Date().toISOString(),
      read: false,
    };

    setAlerts((prev) => [alert, ...prev]);
    setActiveBanner(alert);

    if (bannerTimerRef.current) {
      clearTimeout(bannerTimerRef.current);
    }
    bannerTimerRef.current = setTimeout(() => {
      setActiveBanner(null);
    }, 4200);

    const delivered = await fireLocalNotification(title, message);

    if (ENABLE_PHONE_DELIVERY) {
      const smsResult = await sendSmsTripUpdate({
        accessToken,
        phone: user?.phone,
        tripId,
        status,
        title,
        message,
      });

      if (smsResult && smsResult.sent === false) {
        const reason = smsResult.reason || smsResult.result || 'unknown_error';
        Alert.alert('Phone notification not delivered', `Reason: ${reason}`);
      }
    }

    if (!delivered) {
      Alert.alert(title, message);
    }
  };

  const createTrip = async (planInput) => {
    const source = planInput.source || getLocationById(planInput.sourceId);
    const destination = planInput.destination || getLocationById(planInput.destinationId);

    const generated = generateTripPrediction({
      source,
      destination,
      cargoWeightKg: planInput.cargoWeightKg,
      weather: planInput.weather,
      parcelType: planInput.parcelType,
      fragility: planInput.fragility,
      priority: planInput.priority,
      temperatureControlled: planInput.temperatureControlled,
      trafficIntensity: planInput.trafficIntensity,
      trafficIncidentCount: planInput.trafficIncidentCount,
      routeAlternatives: planInput.routeAlternatives,
      weatherSnapshot: planInput.weatherSnapshot,
      trafficSnapshot: planInput.trafficSnapshot,
    });

    const trip = {
      ...generated,
      planInput,
      status: 'PREPARING',
      statusTimeline: [
        {
          status: 'PREPARING',
          at: new Date().toISOString(),
          note: 'Shipment order accepted and preparing dispatch documents.',
        },
      ],
    };

    setTrips((prev) => [trip, ...prev]);
    await pushAlert(
      trip.tripId,
      'PREPARING',
      'Trip Created',
      `${source.city} to ${destination.city} is now preparing for dispatch.`
    );

    setTimeout(async () => {
      setTrips((prev) =>
        prev.map((item) => {
          if (item.tripId !== trip.tripId) return item;
          return {
            ...item,
            status: 'IN_TRANSIT',
            statusTimeline: [
              {
                status: 'IN_TRANSIT',
                at: new Date().toISOString(),
                note: 'Vehicle departed and is now in transit.',
              },
              ...item.statusTimeline,
            ],
          };
        })
      );

      await pushAlert(
        trip.tripId,
        'IN_TRANSIT',
        'Trip In Transit',
        `${source.city} to ${destination.city} has departed and is now moving.`
      );
    }, 4500);

    return trip;
  };

  const updateTripStatus = async (tripId, nextStatus) => {
    let statusMessage = 'Status updated.';
    if (nextStatus === 'IN_TRANSIT') statusMessage = 'Vehicle departed from source facility.';
    if (nextStatus === 'DELAYED') statusMessage = 'Delay detected due to corridor congestion.';
    if (nextStatus === 'ON_HOLD') statusMessage = 'Trip on hold pending operations clearance.';
    if (nextStatus === 'COMPLETED') statusMessage = 'Trip completed and delivered successfully.';

    setTrips((prev) =>
      prev.map((trip) => {
        if (trip.tripId !== tripId) return trip;
        return {
          ...trip,
          status: nextStatus,
          statusTimeline: [
            {
              status: nextStatus,
              at: new Date().toISOString(),
              note: statusMessage,
            },
            ...trip.statusTimeline,
          ],
        };
      })
    );

    await pushAlert(tripId, nextStatus, `Trip ${nextStatus.replace('_', ' ')}`, statusMessage);
  };

  const selectRoute = (tripId, routeId) => {
    setTrips((prev) =>
      prev.map((trip) => {
        if (trip.tripId !== tripId) return trip;
        const selected = trip.routes.find((route) => route.id === routeId) || trip.routes[0];
        return {
          ...trip,
          selectedRouteId: routeId,
          prediction: {
            ...trip.prediction,
            delayProbability: selected.delayProbability,
            risk: selected.risk,
            cost: selected.cost,
            eta: selected.eta,
            selectedRoute: selected.name,
            improvement: null,
          },
        };
      })
    );
  };

  const runRerouteSimulation = async (tripId) => {
    let reroutePayload = null;

    setTrips((prev) =>
      prev.map((trip) => {
        if (trip.tripId !== tripId) return trip;
        const reroute = simulateReroute(trip, trip.selectedRouteId);
        reroutePayload = reroute;
        return {
          ...trip,
          selectedRouteId: reroute.nextRouteId,
          prediction: {
            ...trip.prediction,
            ...reroute.prediction,
          },
          status: 'DELAYED',
          statusTimeline: [
            {
              status: 'DELAYED',
              at: new Date().toISOString(),
              note: reroute.messages.join(' | '),
            },
            ...trip.statusTimeline,
          ],
        };
      })
    );

    if (reroutePayload) {
      await pushAlert(tripId, 'DELAYED', reroutePayload.alertTitle, reroutePayload.messages.join(' | '));
    }

    return reroutePayload;
  };

  const markAlertRead = (alertId) => {
    setAlerts((prev) => prev.map((alert) => (alert.id === alertId ? { ...alert, read: true } : alert)));
  };

  const value = useMemo(
    () => ({
      trips,
      alerts,
      activeBanner,
      createTrip,
      updateTripStatus,
      selectRoute,
      runRerouteSimulation,
      markAlertRead,
      notificationMode,
    }),
    [trips, alerts, activeBanner, notificationMode]
  );

  return <TripContext.Provider value={value}>{children}</TripContext.Provider>;
}

export function useTrips() {
  const context = useContext(TripContext);
  if (!context) {
    throw new Error('useTrips must be used inside TripProvider');
  }
  return context;
}
