/**
 * Create Trip Screen
 * Form for creating a new trip with pickup and destination
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { tripsAPI } from '../shared/api';
import { useAuth } from '../shared/AuthContext';

export const CreateTripScreen = ({ navigation }) => {
  const { state } = useAuth();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    pickupLocation: '',
    pickupLat: '',
    pickupLon: '',
    destinationLocation: '',
    destinationLat: '',
    destinationLon: '',
    description: '',
    cargoWeight: '',
    passengerCount: '1',
  });

  const updateForm = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }));
  };

  const validateForm = () => {
    const { pickupLocation, destinationLocation, passengerCount } = form;
    
    if (!pickupLocation.trim()) {
      Alert.alert('Validation Error', 'Please enter pickup location');
      return false;
    }
    if (!destinationLocation.trim()) {
      Alert.alert('Validation Error', 'Please enter destination');
      return false;
    }
    if (!passengerCount || parseInt(passengerCount) < 1) {
      Alert.alert('Validation Error', 'Please enter valid passenger count');
      return false;
    }
    
    return true;
  };

  const handleCreateTrip = async () => {
    if (!validateForm()) return;

    setLoading(true);
    try {
      const tripData = {
        pickup_lat: form.pickupLat ? parseFloat(form.pickupLat) : 0,
        pickup_lng: form.pickupLon ? parseFloat(form.pickupLon) : 0,
        dropoff_lat: form.destinationLat ? parseFloat(form.destinationLat) : 0,
        dropoff_lng: form.destinationLon ? parseFloat(form.destinationLon) : 0,
        cargo_description: form.description || `${form.pickupLocation} -> ${form.destinationLocation}`,
        cargo_weight_kg: form.cargoWeight ? parseFloat(form.cargoWeight) : undefined,
      };

      const response = await tripsAPI.createTrip(tripData);
      const result = response.data;
      
      Alert.alert(
        'Trip Created',
        `Trip #${result.id || 'created'} confirmed!`,
        [
          {
            text: 'View Trip',
            onPress: () => {
              navigation.navigate('HomeTab', {
                screen: 'HomeScreen',
                params: { tripId: result.id },
              });
            },
          },
          {
            text: 'Create Another',
            onPress: () => setForm({
              pickupLocation: '',
              pickupLat: '',
              pickupLon: '',
              destinationLocation: '',
              destinationLat: '',
              destinationLon: '',
              description: '',
              cargoWeight: '',
              passengerCount: '1',
            }),
          },
        ]
      );
    } catch (err) {
      Alert.alert('Error', err.message || 'Failed to create trip');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Create New Trip</Text>
        <Text style={styles.subtitle}>
          Traveling as {state.user?.email || 'Guest'}
        </Text>
      </View>

      {/* Pickup Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>📍 Pickup Location</Text>
        
        <View style={styles.formGroup}>
          <Text style={styles.label}>Pickup Address</Text>
          <TextInput
            style={styles.input}
            placeholder="e.g., 123 Main St, City"
            value={form.pickupLocation}
            onChangeText={(text) => updateForm('pickupLocation', text)}
            editable={!loading}
          />
        </View>

        <View style={styles.coordRow}>
          <View style={[styles.formGroup, { flex: 1, marginRight: 8 }]}>
            <Text style={styles.label}>Latitude</Text>
            <TextInput
              style={styles.input}
              placeholder="0.0000"
              value={form.pickupLat}
              onChangeText={(text) => updateForm('pickupLat', text)}
              keyboardType="decimal-pad"
              editable={!loading}
            />
          </View>
          <View style={[styles.formGroup, { flex: 1 }]}>
            <Text style={styles.label}>Longitude</Text>
            <TextInput
              style={styles.input}
              placeholder="0.0000"
              value={form.pickupLon}
              onChangeText={(text) => updateForm('pickupLon', text)}
              keyboardType="decimal-pad"
              editable={!loading}
            />
          </View>
        </View>
      </View>

      {/* Destination Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>🎯 Destination</Text>
        
        <View style={styles.formGroup}>
          <Text style={styles.label}>Destination Address</Text>
          <TextInput
            style={styles.input}
            placeholder="e.g., 456 Oak Ave, City"
            value={form.destinationLocation}
            onChangeText={(text) => updateForm('destinationLocation', text)}
            editable={!loading}
          />
        </View>

        <View style={styles.coordRow}>
          <View style={[styles.formGroup, { flex: 1, marginRight: 8 }]}>
            <Text style={styles.label}>Latitude</Text>
            <TextInput
              style={styles.input}
              placeholder="0.0000"
              value={form.destinationLat}
              onChangeText={(text) => updateForm('destinationLat', text)}
              keyboardType="decimal-pad"
              editable={!loading}
            />
          </View>
          <View style={[styles.formGroup, { flex: 1 }]}>
            <Text style={styles.label}>Longitude</Text>
            <TextInput
              style={styles.input}
              placeholder="0.0000"
              value={form.destinationLon}
              onChangeText={(text) => updateForm('destinationLon', text)}
              keyboardType="decimal-pad"
              editable={!loading}
            />
          </View>
        </View>
      </View>

      {/* Trip Details */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>📋 Trip Details</Text>
        
        <View style={styles.formGroup}>
          <Text style={styles.label}>Number of Passengers</Text>
          <TextInput
            style={styles.input}
            placeholder="1"
            value={form.passengerCount}
            onChangeText={(text) => updateForm('passengerCount', text)}
            keyboardType="number-pad"
            editable={!loading}
          />
        </View>

        <View style={styles.formGroup}>
          <Text style={styles.label}>Cargo Weight (optional, kg)</Text>
          <TextInput
            style={styles.input}
            placeholder="0.0"
            value={form.cargoWeight}
            onChangeText={(text) => updateForm('cargoWeight', text)}
            keyboardType="decimal-pad"
            editable={!loading}
          />
        </View>

        <View style={styles.formGroup}>
          <Text style={styles.label}>Description (optional)</Text>
          <TextInput
            style={[styles.input, { minHeight: 80 }]}
            placeholder="Add any special instructions or notes..."
            value={form.description}
            onChangeText={(text) => updateForm('description', text)}
            multiline={true}
            numberOfLines={4}
            editable={!loading}
          />
        </View>
      </View>

      {/* Action Buttons */}
      <View style={styles.buttonContainer}>
        <TouchableOpacity
          style={[styles.button, styles.cancelButton]}
          onPress={() => navigation.goBack()}
          disabled={loading}
        >
          <Text style={styles.cancelButtonText}>Cancel</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, styles.submitButton, loading && styles.buttonDisabled]}
          onPress={handleCreateTrip}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.submitButtonText}>Create Trip</Text>
          )}
        </TouchableOpacity>
      </View>

      {/* Spacer */}
      <View style={{ height: 40 }} />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#fff',
    paddingHorizontal: 16,
    paddingVertical: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#333',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 13,
    color: '#999',
  },
  section: {
    backgroundColor: '#fff',
    marginVertical: 8,
    paddingHorizontal: 16,
    paddingVertical: 16,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#333',
    marginBottom: 16,
  },
  formGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: '#555',
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#f9f9f9',
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: '#333',
  },
  coordRow: {
    flexDirection: 'row',
    gap: 0,
  },
  buttonContainer: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
  },
  button: {
    flex: 1,
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cancelButton: {
    backgroundColor: '#f0f0f0',
    borderWidth: 1,
    borderColor: '#ddd',
  },
  cancelButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
  },
  submitButton: {
    backgroundColor: '#2196F3',
  },
  submitButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
});
