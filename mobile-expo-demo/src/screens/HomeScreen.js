import React, { useMemo } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { InfoCard } from '../components/InfoCard';
import { StatusPill } from '../components/StatusPill';
import { generateTripPrediction } from '../data/mockAiData';
import { useTrips } from '../store/TripContext';
import { colors, fonts, shadows } from '../theme/designSystem';

export function HomeScreen({ navigation }) {
  const { trips, alerts, notificationMode } = useTrips();

  const quickPreview = useMemo(
    () =>
      generateTripPrediction({
        source: {
          id: 'mumbai_wh',
          city: 'Mumbai',
          latitude: 19.076,
          longitude: 72.8777,
        },
        destination: {
          id: 'pune_hub',
          city: 'Pune',
          latitude: 18.5204,
          longitude: 73.8567,
        },
        cargoWeightKg: 1320,
        weather: 'Clear',
        parcelType: 'General',
        fragility: 'Medium',
        priority: 'Standard',
        temperatureControlled: false,
        trafficIntensity: 'Moderate',
        trafficIncidentCount: 2,
      }),
    []
  );

  const totalTrips = trips.length;
  const delayedTrips = trips.filter((trip) => trip.status === 'DELAYED').length;
  const activeTrips = trips.filter((trip) => trip.status === 'IN_TRANSIT' || trip.status === 'DELAYED').length;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <LinearGradient colors={['#101A2E', '#122847', '#103568']} style={styles.heroCard}>
        <Text style={styles.heading}>Operations Command Center</Text>
        <Text style={styles.text}>Live route optimization, traffic intelligence, and shipment risk telemetry</Text>
        <Text style={styles.notificationMode}>Alerts: {notificationMode}</Text>
      </LinearGradient>

      <View style={styles.cardRow}>
        <InfoCard title="Active Trips" value={`${activeTrips}`} subtitle={`${totalTrips} total shipments`} tone="blue" />
        <InfoCard title="Delayed" value={`${delayedTrips}`} subtitle={`Risk ${quickPreview.prediction.risk}`} tone={delayedTrips > 0 ? 'red' : 'green'} />
      </View>

      <TouchableOpacity style={styles.primaryButton} onPress={() => navigation.navigate('CreateTrip')}>
        <Text style={styles.primaryText}>Plan New Shipment</Text>
      </TouchableOpacity>

      <Text style={styles.sectionTitle}>Active Shipments</Text>
      {trips.slice(0, 4).length === 0 ? <Text style={styles.emptyText}>No active shipments yet. Create your first trip.</Text> : null}
      {trips.slice(0, 4).map((item) => (
          <TouchableOpacity
            key={item.tripId}
            style={styles.tripCard}
            onPress={() => navigation.navigate('TripDetails', { tripId: item.tripId })}
          >
            <View style={styles.tripHeader}>
              <Text style={styles.tripTitle}>{item.source.city} → {item.destination.city}</Text>
              <StatusPill status={item.status} />
            </View>
            <Text style={styles.tripMeta}>{item.prediction.selectedRoute}</Text>
            <Text style={styles.tripMeta}>ETA {item.prediction.eta} • {item.prediction.cost}</Text>
          </TouchableOpacity>
      ))}

      <Text style={styles.sectionTitle}>Recent Alerts</Text>
      {alerts.slice(0, 3).length === 0 ? <Text style={styles.emptyText}>No alerts yet.</Text> : null}
      {alerts.slice(0, 3).map((item) => (
          <View key={item.id} style={styles.alertRow}>
            <Text style={styles.alertTitle}>{item.title}</Text>
            <Text style={styles.alertMessage}>{item.message}</Text>
          </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  contentContainer: {
    padding: 20,
    paddingBottom: 32,
  },
  heroCard: {
    borderRadius: 16,
    padding: 18,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    ...shadows.card,
  },
  heading: {
    color: colors.text,
    fontFamily: fonts.heading,
    fontSize: 21,
    marginBottom: 6,
    letterSpacing: 0.7,
  },
  text: {
    color: colors.textMuted,
    fontSize: 14,
    fontFamily: fonts.body,
  },
  notificationMode: {
    marginTop: 8,
    color: '#8FD9FF',
    fontFamily: fonts.bodyStrong,
    fontSize: 13,
  },
  cardRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 12,
  },
  primaryButton: {
    backgroundColor: colors.accentStrong,
    borderRadius: 10,
    alignItems: 'center',
    paddingVertical: 14,
    marginBottom: 14,
  },
  primaryText: {
    color: colors.text,
    fontFamily: fonts.bodyStrong,
    fontSize: 18,
    letterSpacing: 0.5,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 16,
    fontFamily: fonts.bodyStrong,
    marginBottom: 8,
    marginTop: 6,
    letterSpacing: 0.5,
  },
  tripCard: {
    backgroundColor: colors.panel,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  tripHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  tripTitle: {
    color: colors.text,
    fontFamily: fonts.bodyStrong,
    fontSize: 16,
    flex: 1,
    marginRight: 8,
  },
  tripMeta: {
    color: colors.textMuted,
    fontSize: 14,
    fontFamily: fonts.body,
    marginBottom: 2,
  },
  alertRow: {
    backgroundColor: '#1A1222',
    borderColor: '#4E2E57',
    borderWidth: 1,
    borderRadius: 12,
    padding: 10,
    marginBottom: 8,
  },
  alertTitle: {
    color: '#FF9BB3',
    fontFamily: fonts.bodyStrong,
    marginBottom: 2,
    fontSize: 14,
  },
  alertMessage: {
    color: colors.textMuted,
    fontSize: 13,
    fontFamily: fonts.body,
  },
  emptyText: {
    color: colors.textDim,
    fontSize: 14,
    fontFamily: fonts.body,
    marginBottom: 8,
  },
});
