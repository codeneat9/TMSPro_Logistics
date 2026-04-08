/**
 * Trip Details Screen
 * Displays detailed information about a specific trip
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { tripsAPI } from '../shared/api';

export const TripDetailsScreen = ({ route, navigation }) => {
  const { tripId } = route.params;
  const [trip, setTrip] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTripDetails();
  }, [tripId]);

  const fetchTripDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await tripsAPI.getTrip(tripId);
      setTrip(response.data);
    } catch (err) {
      setError(err.message || 'Failed to load trip details');
      console.error('Trip details error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = async (newStatus) => {
    if (!trip) return;

    try {
      const response = await tripsAPI.updateTrip(tripId, { status: newStatus });
      setTrip(response.data);
      Alert.alert('Success', `Trip status updated to ${newStatus}`);
    } catch (err) {
      Alert.alert('Error', err.message || 'Failed to update status');
    }
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#2196F3" />
        <Text style={styles.loadingText}>Loading trip details...</Text>
      </View>
    );
  }

  if (error || !trip) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>{error || 'Trip not found'}</Text>
        <TouchableOpacity
          style={styles.retryButton}
          onPress={fetchTripDetails}
        >
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      {/* Trip Header */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Trip Information</Text>
        <View style={styles.infoRow}>
          <Text style={styles.label}>Trip ID:</Text>
          <Text style={styles.value}>{trip.id || trip.trip_id || 'N/A'}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.label}>Status:</Text>
          <Text style={[styles.value, { color: getStatusColor(trip.status) }]}>
            {trip.status?.charAt(0).toUpperCase() + trip.status?.slice(1) || 'Unknown'}
          </Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.label}>Created:</Text>
          <Text style={styles.value}>
            {trip.created_at ? new Date(trip.created_at).toLocaleDateString() : 'N/A'}
          </Text>
        </View>
      </View>

      {/* Locations */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Locations</Text>
        <View style={styles.locationCard}>
          <Text style={styles.locationLabel}>📍 Pickup</Text>
          <Text style={styles.locationValue}>
            {trip.pickup_location || `${trip.pickup_lat}, ${trip.pickup_lng}` || 'N/A'}
          </Text>
        </View>
        <View style={styles.locationCard}>
          <Text style={styles.locationLabel}>🎯 Destination</Text>
          <Text style={styles.locationValue}>
            {trip.destination_location || `${trip.dropoff_lat}, ${trip.dropoff_lng}` || 'N/A'}
          </Text>
        </View>
      </View>

      {/* Trip Details */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Trip Details</Text>
        {trip.estimated_duration && (
          <View style={styles.infoRow}>
            <Text style={styles.label}>Estimated Duration:</Text>
            <Text style={styles.value}>{trip.estimated_duration} minutes</Text>
          </View>
        )}
        {trip.distance && (
          <View style={styles.infoRow}>
            <Text style={styles.label}>Distance:</Text>
            <Text style={styles.value}>{trip.distance} km</Text>
          </View>
        )}
        {trip.assigned_driver && (
          <View style={styles.infoRow}>
            <Text style={styles.label}>Assigned Driver:</Text>
            <Text style={styles.value}>{trip.assigned_driver}</Text>
          </View>
        )}
        {trip.estimated_cost && (
          <View style={styles.infoRow}>
            <Text style={styles.label}>Estimated Cost:</Text>
            <Text style={styles.value}>${trip.estimated_cost.toFixed(2)}</Text>
          </View>
        )}
      </View>

      {/* Status Update Actions */}
      {trip.status !== 'completed' && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Actions</Text>
          <View style={styles.buttonRow}>
            {trip.status === 'pending' && (
              <TouchableOpacity
                style={[styles.statusButton, styles.buttonPrimary]}
                onPress={() => handleStatusUpdate('confirmed')}
              >
                <Text style={styles.buttonText}>Confirm</Text>
              </TouchableOpacity>
            )}
            {(trip.status === 'pending' || trip.status === 'confirmed') && (
              <TouchableOpacity
                style={[styles.statusButton, styles.buttonSuccess]}
                onPress={() => handleStatusUpdate('in_progress')}
              >
                <Text style={styles.buttonText}>Start Trip</Text>
              </TouchableOpacity>
            )}
            {trip.status === 'in_progress' && (
              <TouchableOpacity
                style={[styles.statusButton, styles.buttonSuccess]}
                onPress={() => handleStatusUpdate('completed')}
              >
                <Text style={styles.buttonText}>Complete</Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity
              style={[styles.statusButton, styles.buttonDanger]}
              onPress={() => handleStatusUpdate('cancelled')}
            >
              <Text style={styles.buttonText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* Notes */}
      {trip.notes && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Notes</Text>
          <Text style={styles.notesText}>{trip.notes}</Text>
        </View>
      )}

      {/* Spacer */}
      <View style={{ height: 40 }} />
    </ScrollView>
  );
};

const getStatusColor = (status) => {
  switch (status?.toLowerCase()) {
    case 'pending':
      return '#FFA500';
    case 'confirmed':
      return '#2196F3';
    case 'in_progress':
      return '#4CAF50';
    case 'completed':
      return '#4CAF50';
    case 'cancelled':
      return '#FF6B6B';
    default:
      return '#999';
  }
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  section: {
    backgroundColor: '#fff',
    marginVertical: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
    marginBottom: 12,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  label: {
    fontSize: 14,
    color: '#666',
    fontWeight: '500',
  },
  value: {
    fontSize: 14,
    color: '#333',
    fontWeight: '600',
    flex: 1,
    textAlign: 'right',
  },
  locationCard: {
    backgroundColor: '#f9f9f9',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#2196F3',
  },
  locationLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  locationValue: {
    fontSize: 13,
    color: '#666',
  },
  loadingText: {
    marginTop: 12,
    color: '#666',
    fontSize: 14,
  },
  errorText: {
    color: '#FF6B6B',
    fontSize: 16,
    textAlign: 'center',
    marginVertical: 16,
  },
  retryButton: {
    backgroundColor: '#2196F3',
    borderRadius: 8,
    paddingHorizontal: 24,
    paddingVertical: 12,
    alignSelf: 'center',
    marginTop: 16,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 8,
    flexWrap: 'wrap',
  },
  statusButton: {
    flex: 1,
    minWidth: 120,
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  buttonPrimary: {
    backgroundColor: '#2196F3',
  },
  buttonSuccess: {
    backgroundColor: '#4CAF50',
  },
  buttonDanger: {
    backgroundColor: '#FF6B6B',
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 13,
  },
  notesText: {
    fontSize: 14,
    color: '#555',
    lineHeight: 20,
  },
});
