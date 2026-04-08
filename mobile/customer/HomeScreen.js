/**
 * Home Screen - Main dashboard
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { useAuth } from '../shared/AuthContext';
import { tripsAPI, healthCheck } from '../shared/api';

export const HomeScreen = ({ navigation }) => {
  const { state, signOut } = useAuth();
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [apiStatus, setApiStatus] = useState(null);
  const [selectedStatus, setSelectedStatus] = useState('all');

  const statusOptions = ['all', 'pending', 'assigned', 'in_progress', 'completed'];

  const loadTrips = async () => {
    try {
      const params = { limit: 20 };
      if (selectedStatus !== 'all') {
        params.status = selectedStatus;
      }

      const response = await tripsAPI.listTrips(params);
      setTrips(response.data.items || response.data || []);
    } catch (error) {
      console.error('Error loading trips:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const checkAPI = async () => {
    try {
      const status = await healthCheck();
      setApiStatus(status);
    } catch (error) {
      console.error('API health check failed:', error);
    }
  };

  useEffect(() => {
    loadTrips();
    checkAPI();
  }, [selectedStatus]);

  const onRefresh = () => {
    setRefreshing(true);
    loadTrips();
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Welcome, {state.user?.email?.split('@')[0]}!</Text>
          <Text style={styles.subText}>TMSPro Logistics Management</Text>
        </View>
        <TouchableOpacity
          style={styles.logoutButton}
          onPress={() => {
            signOut();
          }}
        >
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </View>

      {apiStatus && (
        <View style={styles.statusBar}>
          <Text style={styles.statusText}>
            ✓ Backend: {apiStatus.status}
          </Text>
        </View>
      )}

      <ScrollView
        style={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <TouchableOpacity
            style={styles.actionButton}
            onPress={() => navigation.navigate('CreateTrip')}
          >
            <Text style={styles.actionButtonText}>➕ New Trip</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.actionButton}
            onPress={() => navigation.getParent()?.navigate('Tracking')}
          >
            <Text style={styles.actionButtonText}>📍 Live Tracking</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Recent Trips</Text>
          <View style={styles.filterRow}>
            {statusOptions.map((option) => {
              const active = selectedStatus === option;
              return (
                <TouchableOpacity
                  key={option}
                  style={[styles.filterChip, active && styles.filterChipActive]}
                  onPress={() => setSelectedStatus(option)}
                >
                  <Text style={[styles.filterChipText, active && styles.filterChipTextActive]}>
                    {option.replace('_', ' ')}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {loading ? (
            <ActivityIndicator size="large" color="#2196F3" />
          ) : trips.length === 0 ? (
            <Text style={styles.emptyText}>No trips yet. Create one to get started!</Text>
          ) : (
            trips.slice(0, 5).map((trip) => (
              <TouchableOpacity
                key={trip.id}
                style={styles.tripCard}
                onPress={() => navigation.navigate('TripDetails', { tripId: trip.id })}
              >
                <View style={styles.tripCardLeft}>
                  <Text style={styles.tripId}>Trip {trip.id}</Text>
                  <Text style={styles.tripStatus}>{formatStatus(trip.status || 'pending')}</Text>
                  <Text style={styles.tripMeta}>
                    {trip.created_at ? new Date(trip.created_at).toLocaleString() : 'Recently created'}
                  </Text>
                </View>
                <View style={styles.tripCardRight}>
                  <View style={[styles.statusBadge, getStatusBadgeStyle(trip.status)]}>
                    <Text style={styles.statusBadgeText}>{formatStatus(trip.status || 'pending')}</Text>
                  </View>
                </View>
              </TouchableOpacity>
            ))
          )}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>App Info</Text>
          <View style={styles.infoBox}>
            <Text style={styles.infoText}>Version: 1.0.0</Text>
            <Text style={styles.infoText}>Role: {state.user?.role || 'customer'}</Text>
            <Text style={styles.infoText}>User: {state.user?.email}</Text>
          </View>
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#2196F3',
    paddingTop: 16,
    paddingHorizontal: 20,
    paddingBottom: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  greeting: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
  },
  subText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 4,
  },
  logoutButton: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 4,
  },
  logoutText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  statusBar: {
    backgroundColor: '#4CAF50',
    padding: 12,
    alignItems: 'center',
  },
  statusText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1a1a1a',
    marginBottom: 12,
  },
  actionButton: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    marginBottom: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#2196F3',
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#2196F3',
  },
  filterRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 12,
  },
  filterChip: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#d1d5db',
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: '#fff',
  },
  filterChipActive: {
    backgroundColor: '#2196F3',
    borderColor: '#2196F3',
  },
  filterChipText: {
    fontSize: 12,
    color: '#374151',
    textTransform: 'capitalize',
  },
  filterChipTextActive: {
    color: '#fff',
    fontWeight: '700',
  },
  tripCard: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    marginBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 2,
  },
  tripCardLeft: {
    flex: 1,
  },
  tripCardRight: {
    paddingLeft: 16,
  },
  tripId: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1a1a1a',
  },
  tripStatus: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
    textTransform: 'capitalize',
  },
  tripMeta: {
    fontSize: 11,
    color: '#9ca3af',
    marginTop: 4,
  },
  tripArrow: {
    fontSize: 18,
    color: '#2196F3',
  },
  statusBadge: {
    borderRadius: 12,
    paddingVertical: 4,
    paddingHorizontal: 8,
    backgroundColor: '#9ca3af',
  },
  statusBadgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'capitalize',
  },
  statusBadgePending: {
    backgroundColor: '#f59e0b',
  },
  statusBadgeAssigned: {
    backgroundColor: '#6366f1',
  },
  statusBadgeInProgress: {
    backgroundColor: '#22c55e',
  },
  statusBadgeCompleted: {
    backgroundColor: '#2563eb',
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    fontStyle: 'italic',
    padding: 16,
    textAlign: 'center',
  },
  infoBox: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
  },
  infoText: {
    fontSize: 13,
    color: '#666',
    marginBottom: 8,
    fontFamily: 'monospace',
  },
});

const formatStatus = (value) => value.replace(/_/g, ' ');

const getStatusBadgeStyle = (status) => {
  switch ((status || '').toLowerCase()) {
    case 'pending':
      return styles.statusBadgePending;
    case 'assigned':
      return styles.statusBadgeAssigned;
    case 'in_progress':
      return styles.statusBadgeInProgress;
    case 'completed':
      return styles.statusBadgeCompleted;
    default:
      return null;
  }
};
