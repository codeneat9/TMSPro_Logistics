import React, { useMemo } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { InfoCard } from '../components/InfoCard';
import { generateTripPrediction } from '../data/mockAiData';

export function HomeScreen({ navigation }) {
  const latestMock = useMemo(
    () =>
      generateTripPrediction({
        source: 'Mumbai Warehouse',
        destination: 'Pune Retail Hub',
        cargoWeightKg: 1280,
      }),
    []
  );

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>Demo Control Center</Text>
      <Text style={styles.text}>AI-powered mock insights are generated locally for demo mode.</Text>

      <View style={styles.cardRow}>
        <InfoCard
          title="Delay Probability"
          value={`${(latestMock.prediction.delayProbability * 100).toFixed(0)}%`}
          subtitle={latestMock.prediction.modelTag}
          tone={latestMock.prediction.risk === 'High' ? 'red' : 'blue'}
        />
        <InfoCard
          title="Current Risk"
          value={latestMock.prediction.risk}
          subtitle={`ETA ${latestMock.prediction.eta}`}
          tone={latestMock.prediction.risk === 'Low' ? 'green' : 'red'}
        />
      </View>

      <TouchableOpacity
        style={styles.primaryButton}
        onPress={() => navigation.navigate('CreateTrip')}
      >
        <Text style={styles.primaryButtonText}>Create New Trip</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.secondaryButton}
        onPress={() =>
          navigation.navigate('TripDetails', {
            source: latestMock.source,
            destination: latestMock.destination,
            cargoWeightKg: latestMock.cargoWeightKg,
            tripData: latestMock,
          })
        }
      >
        <Text style={styles.secondaryButtonText}>Open Last Trip (Mock)</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#F5F7FA',
  },
  heading: {
    fontSize: 24,
    fontWeight: '700',
    color: '#0B3D91',
    marginBottom: 10,
  },
  text: {
    fontSize: 15,
    color: '#4A5568',
    marginBottom: 18,
  },
  cardRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 18,
  },
  primaryButton: {
    backgroundColor: '#0B3D91',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 12,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 16,
  },
  secondaryButton: {
    backgroundColor: '#FFFFFF',
    borderColor: '#0B3D91',
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: '#0B3D91',
    fontWeight: '700',
    fontSize: 16,
  },
});
