import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { InfoCard } from '../components/InfoCard';
import { RouteCard } from '../components/RouteCard';
import { generateTripPrediction, simulateReroute } from '../data/mockAiData';

export function TripDetailsScreen({ route }) {
  const source = route.params?.source || 'Unknown source';
  const destination = route.params?.destination || 'Unknown destination';
  const incomingTripData = route.params?.tripData;

  const initialTripData = useMemo(
    () =>
      incomingTripData ||
      generateTripPrediction({
        source,
        destination,
        cargoWeightKg: route.params?.cargoWeightKg || 1000,
      }),
    [incomingTripData, source, destination, route.params?.cargoWeightKg]
  );

  const [selectedRouteId, setSelectedRouteId] = useState(initialTripData.selectedRouteId);
  const [prediction, setPrediction] = useState(initialTripData.prediction);
  const [aiEvents, setAiEvents] = useState([]);
  const [isStarted, setIsStarted] = useState(false);

  const selectedRoute = initialTripData.routes.find((r) => r.id === selectedRouteId) || initialTripData.routes[0];

  const selectRoute = (routeOption) => {
    setSelectedRouteId(routeOption.id);
    setPrediction({
      ...prediction,
      delayProbability: routeOption.delayProbability,
      risk: routeOption.risk,
      cost: routeOption.cost,
      eta: routeOption.eta,
      selectedRoute: routeOption.name,
    });
  };

  const handleStartTrip = () => {
    const reroute = simulateReroute({
      ...initialTripData,
      selectedRouteId,
    });

    setIsStarted(true);
    setSelectedRouteId(reroute.nextRouteId);
    setPrediction((prev) => ({ ...prev, ...reroute.prediction }));
    setAiEvents(reroute.messages);

    Alert.alert(reroute.alertTitle, 'AI switched the route to reduce delay risk.', [
      { text: 'OK' },
    ]);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.heading}>Trip #{initialTripData.tripId}</Text>
      <Text style={styles.routeText}>From: {source}</Text>
      <Text style={styles.routeText}>To: {destination}</Text>

      <View style={styles.metricsRow}>
        <InfoCard
          title="Delay Probability"
          value={`${(prediction.delayProbability * 100).toFixed(0)}%`}
          subtitle={prediction.modelTag || 'AI score'}
          tone={prediction.risk === 'High' ? 'red' : 'blue'}
        />
        <InfoCard title="Risk" value={prediction.risk} subtitle={prediction.selectedRoute} tone={prediction.risk === 'Low' ? 'green' : 'red'} />
      </View>

      <View style={styles.metricsRow}>
        <InfoCard title="Estimated Cost" value={prediction.cost} subtitle="Fuel + toll + delay factor" tone="blue" />
        <InfoCard title="ETA" value={prediction.eta} subtitle={prediction.improvement || 'Baseline route'} tone="green" />
      </View>

      <Text style={styles.sectionTitle}>Route Options</Text>
      {initialTripData.routes.map((routeOption) => (
        <RouteCard
          key={routeOption.id}
          route={routeOption}
          isSelected={selectedRouteId === routeOption.id}
          onPress={() => selectRoute(routeOption)}
        />
      ))}

      <TouchableOpacity style={styles.startButton} onPress={handleStartTrip}>
        <Text style={styles.startButtonText}>{isStarted ? 'Run AI Reroute Check Again' : 'Start Trip (Simulate AI)'}</Text>
      </TouchableOpacity>

      {aiEvents.length > 0 ? (
        <View style={styles.alertCard}>
          <Text style={styles.alertHeading}>AI Live Alerts</Text>
          {aiEvents.map((message) => (
            <Text key={message} style={styles.alertItem}>• {message}</Text>
          ))}
          <Text style={styles.alertFooter}>Current active route: {selectedRoute.name}</Text>
        </View>
      ) : null}

      <View style={styles.legendRow}>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: '#FFE0E0' }]} />
          <Text style={styles.legendText}>Red: delay risk</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: '#DFF7E8' }]} />
          <Text style={styles.legendText}>Green: safer/optimized</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: '#DBECFF' }]} />
          <Text style={styles.legendText}>Blue: route details</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F7FA',
  },
  contentContainer: {
    padding: 20,
    paddingBottom: 36,
  },
  heading: {
    fontSize: 20,
    fontWeight: '700',
    color: '#0B3D91',
    marginBottom: 10,
  },
  routeText: {
    fontSize: 15,
    color: '#334E68',
    marginBottom: 4,
  },
  metricsRow: {
    marginTop: 14,
    flexDirection: 'row',
    gap: 10,
  },
  sectionTitle: {
    marginTop: 20,
    fontSize: 16,
    fontWeight: '700',
    color: '#102A43',
    marginBottom: 10,
  },
  startButton: {
    marginTop: 8,
    backgroundColor: '#0B3D91',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  startButtonText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 15,
  },
  alertCard: {
    marginTop: 14,
    backgroundColor: '#FFEAEA',
    borderColor: '#FFB3B3',
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
  },
  alertHeading: {
    color: '#9B1C1C',
    fontWeight: '800',
    fontSize: 15,
    marginBottom: 8,
  },
  alertItem: {
    color: '#7F1D1D',
    fontSize: 14,
    marginBottom: 4,
  },
  alertFooter: {
    marginTop: 8,
    color: '#7F1D1D',
    fontWeight: '700',
  },
  legendRow: {
    marginTop: 18,
    gap: 8,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  legendDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#B8C4D0',
    marginRight: 8,
  },
  legendText: {
    color: '#486581',
    fontSize: 13,
  },
});
