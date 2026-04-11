import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from 'react-native';
import { generateTripPrediction } from '../data/mockAiData';

export function CreateTripScreen({ navigation }) {
  const [source, setSource] = useState('Bangalore DC');
  const [destination, setDestination] = useState('Chennai Port');
  const [cargoWeightKg, setCargoWeightKg] = useState('1250');
  const [vehicleId, setVehicleId] = useState('KA-09-TMS-4412');

  const handleContinue = () => {
    const weight = Number(cargoWeightKg) || 1000;
    const tripData = generateTripPrediction({
      source,
      destination,
      cargoWeightKg: weight,
    });

    navigation.navigate('TripDetails', {
      source,
      destination,
      cargoWeightKg: weight,
      vehicleId,
      tripData,
    });
  };

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Source</Text>
      <TextInput
        style={styles.input}
        value={source}
        onChangeText={setSource}
        placeholder="Enter pickup location"
      />

      <Text style={styles.label}>Destination</Text>
      <TextInput
        style={styles.input}
        value={destination}
        onChangeText={setDestination}
        placeholder="Enter drop location"
      />

      <Text style={styles.label}>Cargo Weight (kg)</Text>
      <TextInput
        style={styles.input}
        value={cargoWeightKg}
        onChangeText={setCargoWeightKg}
        placeholder="Enter cargo weight"
        keyboardType="numeric"
      />

      <Text style={styles.label}>Vehicle ID</Text>
      <TextInput
        style={styles.input}
        value={vehicleId}
        onChangeText={setVehicleId}
        placeholder="Enter assigned vehicle"
        autoCapitalize="characters"
      />

      <TouchableOpacity style={styles.button} onPress={handleContinue}>
        <Text style={styles.buttonText}>Generate Trip (Mock AI)</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F7FA',
    padding: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#334E68',
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#D9E2EC',
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 16,
  },
  button: {
    marginTop: 12,
    backgroundColor: '#0B3D91',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  buttonText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 16,
  },
});
