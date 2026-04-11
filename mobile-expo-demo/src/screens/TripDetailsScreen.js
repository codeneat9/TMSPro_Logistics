import React, { useMemo, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { InfoCard } from '../components/InfoCard';
import { RouteCard } from '../components/RouteCard';
import { generateTripPrediction, simulateReroute } from '../data/mockAiData';
import { useTrips } from '../store/TripContext';
import { StatusPill } from '../components/StatusPill';
import { getLocationById } from '../data/locations';
import { colors, fonts } from '../theme/designSystem';
import { OsmMapView } from '../components/OsmMapView';

function normalizePathCoordinates(rawCoordinates = []) {
  return (rawCoordinates || [])
    .map((point) => {
      const latitude = Number(point?.latitude ?? point?.lat);
      const longitude = Number(point?.longitude ?? point?.lng ?? point?.lon);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
      return { latitude, longitude };
    })
    .filter(Boolean);
}

export function TripDetailsScreen({ route }) {
  const { trips, selectRoute, runRerouteSimulation } = useTrips();
  const tripId = route.params?.tripId;
  const sourceParam = route.params?.source;
  const destinationParam = route.params?.destination;
  const incomingTripData = route.params?.tripData;

  const fallbackTrip = useMemo(() => {
    const fallbackSource = sourceParam || getLocationById('bangalore_dc');
    const fallbackDestination = destinationParam || getLocationById('chennai_port');

    return (
      incomingTripData ||
      generateTripPrediction({
        source: fallbackSource,
        destination: fallbackDestination,
        cargoWeightKg: route.params?.cargoWeightKg || 1000,
        weather: 'Clear',
        parcelType: 'General',
        fragility: 'Medium',
        priority: 'Standard',
        temperatureControlled: false,
        trafficIntensity: 'Moderate',
        trafficIncidentCount: 2,
      })
    );
  }, [incomingTripData, sourceParam, destinationParam, route.params?.cargoWeightKg]);

  const liveTrip = useMemo(() => trips.find((item) => item.tripId === tripId) || null, [trips, tripId]);
  const tripData = liveTrip || fallbackTrip;

  const [events, setEvents] = useState([]);
  const [event, setEvent] = useState(null);

  const selectedRouteId = tripData.selectedRouteId;
  const prediction = tripData.prediction;
  const source = tripData.source;
  const destination = tripData.destination;

  const selectedRoute = tripData.routes.find((routeOption) => routeOption.id === selectedRouteId) || tripData.routes[0];
  const currentStatus = liveTrip?.status || 'PREPARING';
  const statusStages = ['PREPARING', 'IN_TRANSIT', 'DELAYED', 'COMPLETED'];
  const currentStageIndex = Math.max(statusStages.indexOf(currentStatus), 0);
  const bestRoute = useMemo(() => {
    return [...tripData.routes].sort((a, b) => a.etaMinutes - b.etaMinutes)[0];
  }, [tripData.routes]);
  const selectedDelayOverBest = Math.max(selectedRoute.etaMinutes - bestRoute.etaMinutes, 0);

  const mapRegion = useMemo(() => {
    return {
      latitude: (source.latitude + destination.latitude) / 2,
      longitude: (source.longitude + destination.longitude) / 2,
      zoom: 7,
    };
  }, [source, destination]);

  const routePolylines = useMemo(() => {
    return tripData.routes
      .map((routeOption) => ({
        coordinates: normalizePathCoordinates(routeOption.pathCoordinates),
        color: routeOption.id === selectedRouteId ? '#4CC9FF' : '#59647B',
        weight: routeOption.id === selectedRouteId ? 4 : 2,
      }))
      .filter((line) => line.coordinates.length >= 2);
  }, [tripData.routes, selectedRouteId]);


  const onSelectRoute = (routeOption) => {
    if (tripData.tripId) {
      selectRoute(tripData.tripId, routeOption.id);
    }
  };

  const onRunReroute = async () => {
    if (!liveTrip) {
      const simulated = simulateReroute(tripData, selectedRouteId);
      setEvents(simulated.messages);
      return;
    }

    const reroute = await runRerouteSimulation(liveTrip.tripId);
    if (reroute) {
      setEvents(reroute.messages);
    }
  };

  const onSimulateEvent = (type) => {
    if (type === 'reset') {
      setEvent(null);
      return;
    }

    setEvent(type);

    if (type === 'crash') {
      Alert.alert('Crash Simulation', 'Emergency alert sent to control center.');
    } else if (type === 'theft') {
      Alert.alert('Theft Simulation', 'Unauthorized access event generated.');
    } else if (type === 'temperature') {
      Alert.alert('Temperature Simulation', 'High cargo temperature alert generated.');
    }
  };

  const mockGps = useMemo(() => {
    const lat = Number(((source.latitude + destination.latitude) / 2).toFixed(5));
    const lon = Number(((source.longitude + destination.longitude) / 2).toFixed(5));
    return `${lat}, ${lon}`;
  }, [source.latitude, source.longitude, destination.latitude, destination.longitude]);

  const simulationPayload = useMemo(() => {
    if (event === 'crash') {
      return {
        tone: 'danger',
        title: 'Crash Detected!',
        lines: [
          'Emergency alert sent to control center',
          `Mock GPS Location: ${mockGps}`,
        ],
      };
    }

    if (event === 'theft') {
      return {
        tone: 'warning',
        title: 'Unauthorized access detected',
        lines: [
          'Vehicle deviated from route',
          'Security team notified for intervention',
        ],
      };
    }

    if (event === 'temperature') {
      return {
        tone: 'info',
        title: 'High temperature detected',
        lines: [
          'Cargo safety at risk',
          'Cooling protocol triggered in simulation mode',
        ],
      };
    }

    return null;
  }, [event, mockGps]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.heading}>Shipment {tripData.tripId}</Text>
      <View style={styles.headerRow}>
        <Text style={styles.routeText}>{source.city} → {destination.city}</Text>
        <StatusPill status={currentStatus} />
      </View>

      <View style={styles.progressCard}>
        <Text style={styles.progressTitle}>Shipment Status</Text>
        <View style={styles.progressTrack}>
          {statusStages.map((stage, index) => (
            <View
              key={stage}
              style={[
                styles.progressSegment,
                index <= currentStageIndex ? styles.progressSegmentActive : null,
              ]}
            />
          ))}
        </View>
        <Text style={styles.progressLabel}>Current: {currentStatus.replace('_', ' ')}</Text>
      </View>

      <View style={styles.mapCard}>
        <OsmMapView
          center={mapRegion}
          markers={[
            {
              latitude: source.latitude,
              longitude: source.longitude,
              title: 'Source',
              description: source.city,
            },
            {
              latitude: destination.latitude,
              longitude: destination.longitude,
              title: 'Destination',
              description: destination.city,
            },
          ]}
          polylines={routePolylines}
          height={220}
        />
      </View>

      <View style={styles.telemetryCard}>
        <Text style={styles.telemetryTitle}>Traffic Intelligence</Text>
        <Text style={styles.telemetryLine}>Network Load: {prediction.corridorLoad || 'N/A'}</Text>
        <Text style={styles.telemetryLine}>Traffic Intensity: {prediction.trafficIntensity || 'Moderate'}</Text>
        <Text style={styles.telemetryLine}>Incidents Along Corridor: {prediction.incidentCount ?? 0}</Text>
        <Text style={styles.telemetryLine}>Traffic Delay Impact: +{prediction.trafficDelayMinutes ?? selectedDelayOverBest} min</Text>
        <Text style={styles.telemetryTitle}>Weather Snapshot</Text>
        <Text style={styles.telemetryLine}>Condition: {prediction.weather || prediction.weatherSnapshot?.weather || 'Clear'}</Text>
        <Text style={styles.telemetryLine}>Temperature: {prediction.weatherSnapshot?.temperature ?? '-'} C</Text>
        <Text style={styles.telemetryLine}>Wind: {prediction.weatherSnapshot?.windSpeed ?? '-'} km/h</Text>
      </View>

      <View style={styles.simulationCard}>
        <Text style={styles.simulationTitle}>Simulation Controls</Text>
        <View style={styles.simulationGrid}>
          <TouchableOpacity style={[styles.simButton, styles.simButtonDanger]} onPress={() => onSimulateEvent('crash')}>
            <Text style={styles.simButtonText}>Simulate Crash</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.simButton, styles.simButtonWarning]} onPress={() => onSimulateEvent('theft')}>
            <Text style={styles.simButtonText}>Simulate Theft</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.simButton, styles.simButtonInfo]} onPress={() => onSimulateEvent('temperature')}>
            <Text style={styles.simButtonText}>High Temperature</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.simButton, styles.simButtonReset]} onPress={() => onSimulateEvent('reset')}>
            <Text style={styles.simButtonText}>Reset</Text>
          </TouchableOpacity>
        </View>

        {simulationPayload ? (
          <View
            style={[
              styles.simulationAlert,
              simulationPayload.tone === 'danger'
                ? styles.simulationAlertDanger
                : simulationPayload.tone === 'warning'
                  ? styles.simulationAlertWarning
                  : styles.simulationAlertInfo,
            ]}
          >
            <Text style={styles.simulationAlertTitle}>{simulationPayload.title}</Text>
            {simulationPayload.lines.map((line) => (
              <Text key={line} style={styles.simulationAlertLine}>{line}</Text>
            ))}
          </View>
        ) : null}
      </View>

      <View style={styles.row}>
        <InfoCard
          title="Delay Probability"
          value={`${(prediction.delayProbability * 100).toFixed(0)}%`}
          subtitle={prediction.modelTag || 'AI prediction'}
          tone={prediction.risk === 'High' ? 'red' : 'blue'}
        />
        <InfoCard title="Risk" value={prediction.risk} subtitle={prediction.selectedRoute} tone={prediction.risk === 'Low' ? 'green' : 'red'} />
      </View>

      <View style={styles.row}>
        <InfoCard title="Cost Estimate" value={prediction.cost} subtitle="Fuel + toll + delay factor" tone="blue" />
        <InfoCard title="ETA" value={prediction.eta} subtitle={prediction.improvement || 'Current route ETA'} tone="green" />
      </View>

      <Text style={styles.sectionTitle}>Alternative Routes ({tripData.routes.length} Available)</Text>
      <Text style={styles.altRouteHint}>
        Best ETA: {bestRoute.name} ({bestRoute.eta})
      </Text>
      {tripData.routes.map((routeOption) => (
        <RouteCard
          key={routeOption.id}
          route={routeOption}
          isSelected={selectedRouteId === routeOption.id}
          onPress={() => onSelectRoute(routeOption)}
        />
      ))}

      <Text style={styles.sectionTitle}>Dispatch Status</Text>
      <View style={styles.statusCard}>
        <Text style={styles.statusLabel}>Current Status</Text>
        <StatusPill status={currentStatus} />
      </View>

      <TouchableOpacity style={styles.startButton} onPress={onRunReroute}>
        <Text style={styles.startButtonText}>Run Dynamic Reroute Analysis</Text>
      </TouchableOpacity>

      {events.length > 0 ? (
        <View style={styles.alertCard}>
          <Text style={styles.alertTitle}>Live AI Events</Text>
          {events.map((eventText) => (
            <Text key={eventText} style={styles.alertItem}>• {eventText}</Text>
          ))}
          <Text style={styles.alertFooter}>Current route: {selectedRoute.name}</Text>
        </View>
      ) : null}

      {liveTrip?.statusTimeline?.length ? (
        <View style={styles.timelineCard}>
          <Text style={styles.alertTitle}>Status Timeline</Text>
          {liveTrip.statusTimeline.slice(0, 5).map((entry) => (
            <Text key={`${entry.status}-${entry.at}`} style={styles.timelineItem}>
              {entry.status.replace('_', ' ')} • {new Date(entry.at).toLocaleTimeString()} • {entry.note}
            </Text>
          ))}
        </View>
      ) : null}

      <View style={styles.legendBox}>
        <Text style={styles.legendText}>Red: delay warnings | Green: safer route | Blue: route metrics</Text>
      </View>
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
  heading: {
    color: colors.text,
    fontFamily: fonts.heading,
    fontSize: 20,
    marginBottom: 8,
    letterSpacing: 0.7,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  routeText: {
    color: colors.textMuted,
    fontSize: 16,
    fontFamily: fonts.bodyStrong,
    flex: 1,
    marginRight: 8,
  },
  mapCard: {
    borderRadius: 12,
    overflow: 'hidden',
    borderColor: colors.border,
    borderWidth: 1,
  },
  row: {
    marginTop: 14,
    flexDirection: 'row',
    gap: 10,
  },
  sectionTitle: {
    marginTop: 20,
    marginBottom: 10,
    color: colors.text,
    fontFamily: fonts.bodyStrong,
    fontSize: 16,
  },
  progressCard: {
    marginTop: 8,
    borderRadius: 12,
    backgroundColor: '#0D162A',
    borderColor: colors.border,
    borderWidth: 1,
    padding: 12,
  },
  progressTitle: {
    color: colors.text,
    fontFamily: fonts.bodyStrong,
    fontSize: 15,
    marginBottom: 8,
  },
  progressTrack: {
    flexDirection: 'row',
    gap: 6,
  },
  progressSegment: {
    flex: 1,
    height: 8,
    borderRadius: 999,
    backgroundColor: '#2A3C5E',
  },
  progressSegmentActive: {
    backgroundColor: '#42B8FF',
  },
  progressLabel: {
    marginTop: 8,
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 14,
  },
  telemetryCard: {
    marginTop: 12,
    borderRadius: 12,
    backgroundColor: '#0D162A',
    borderColor: colors.border,
    borderWidth: 1,
    padding: 12,
  },
  telemetryTitle: {
    color: colors.text,
    fontFamily: fonts.bodyStrong,
    fontSize: 15,
    marginBottom: 6,
  },
  telemetryLine: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 14,
    marginBottom: 3,
  },
  simulationCard: {
    marginTop: 12,
    borderRadius: 12,
    backgroundColor: '#0D162A',
    borderColor: colors.border,
    borderWidth: 1,
    padding: 12,
  },
  simulationTitle: {
    color: colors.text,
    fontFamily: fonts.bodyStrong,
    fontSize: 16,
    marginBottom: 10,
  },
  simulationGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 8,
  },
  simButton: {
    width: '48%',
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 10,
    borderWidth: 1,
    alignItems: 'center',
    marginBottom: 4,
  },
  simButtonDanger: {
    backgroundColor: '#3A1319',
    borderColor: '#B63849',
  },
  simButtonWarning: {
    backgroundColor: '#3A2E11',
    borderColor: '#B68F2E',
  },
  simButtonInfo: {
    backgroundColor: '#10263D',
    borderColor: '#2D7BC7',
  },
  simButtonReset: {
    backgroundColor: '#1D2A3C',
    borderColor: '#556C8A',
  },
  simButtonText: {
    color: '#EAF4FF',
    fontFamily: fonts.bodyStrong,
    fontSize: 14,
    textAlign: 'center',
  },
  simulationAlert: {
    marginTop: 10,
    borderRadius: 10,
    borderWidth: 1,
    padding: 10,
  },
  simulationAlertDanger: {
    backgroundColor: '#32131B',
    borderColor: '#C7485C',
  },
  simulationAlertWarning: {
    backgroundColor: '#322714',
    borderColor: '#C69B3D',
  },
  simulationAlertInfo: {
    backgroundColor: '#12253A',
    borderColor: '#3C8AD7',
  },
  simulationAlertTitle: {
    color: '#F2F7FF',
    fontFamily: fonts.bodyStrong,
    fontSize: 15,
    marginBottom: 6,
  },
  simulationAlertLine: {
    color: '#D8E6F8',
    fontFamily: fonts.body,
    fontSize: 13,
    marginBottom: 2,
  },
  altRouteHint: {
    color: '#9BCBFF',
    fontFamily: fonts.body,
    fontSize: 14,
    marginBottom: 8,
  },
  statusCard: {
    backgroundColor: '#0E1B33',
    borderRadius: 10,
    borderColor: '#2E446A',
    borderWidth: 1,
    paddingVertical: 12,
    paddingHorizontal: 12,
    marginBottom: 4,
  },
  statusLabel: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 14,
    marginBottom: 8,
  },
  startButton: {
    marginTop: 10,
    backgroundColor: colors.accentStrong,
    borderRadius: 10,
    alignItems: 'center',
    paddingVertical: 14,
  },
  startButtonText: {
    color: colors.text,
    fontFamily: fonts.bodyStrong,
    fontSize: 16,
  },
  alertCard: {
    marginTop: 14,
    borderWidth: 1,
    borderColor: '#61324A',
    backgroundColor: '#291522',
    borderRadius: 12,
    padding: 14,
  },
  alertTitle: {
    color: '#FFADC2',
    fontFamily: fonts.bodyStrong,
    marginBottom: 8,
  },
  alertItem: {
    color: '#FFD1DF',
    marginBottom: 4,
    fontSize: 14,
    fontFamily: fonts.body,
  },
  alertFooter: {
    color: '#FFADC2',
    fontFamily: fonts.bodyStrong,
    marginTop: 8,
  },
  timelineCard: {
    marginTop: 14,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: '#0D1526',
    borderRadius: 12,
    padding: 14,
  },
  timelineItem: {
    color: colors.textMuted,
    marginBottom: 6,
    fontSize: 14,
    fontFamily: fonts.body,
  },
  legendBox: {
    marginTop: 14,
    backgroundColor: '#111A2D',
    borderColor: '#2A3C5E',
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
  },
  legendText: {
    color: colors.textMuted,
    fontSize: 14,
    fontFamily: fonts.body,
  },
});
