import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Switch,
  Modal,
  ActivityIndicator,
} from 'react-native';
import { Picker } from '@react-native-picker/picker';
import { LinearGradient } from 'expo-linear-gradient';

import { useTrips } from '../store/TripContext';
import { colors, fonts, shadows } from '../theme/designSystem';
import {
  geocodeAddress,
  searchAddresses,
  getOsrmRouteAlternatives,
  getTomTomTraffic,
  getWeatherAlongRoute,
} from '../services/routingIntel';
import { OsmMapView } from '../components/OsmMapView';

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const PARCEL_TYPE_OPTIONS = ['General', 'Electronics', 'Pharma', 'Perishable', 'Fragile Goods', 'Documents'];
const FRAGILITY_OPTIONS = ['Low', 'Medium', 'High'];
const PRIORITY_OPTIONS = ['Standard', 'Urgent', 'Critical'];
const PICKER_DROPDOWN_TEXT_COLOR = '#0F172A';

export function CreateTripScreen({ navigation }) {
  const { createTrip } = useTrips();

  const [sourceAddress, setSourceAddress] = useState('');
  const [destinationAddress, setDestinationAddress] = useState('');
  const [sourceSuggestions, setSourceSuggestions] = useState([]);
  const [destinationSuggestions, setDestinationSuggestions] = useState([]);
  const [sourceSearching, setSourceSearching] = useState(false);
  const [destinationSearching, setDestinationSearching] = useState(false);
  const [sourceTouched, setSourceTouched] = useState(false);
  const [destinationTouched, setDestinationTouched] = useState(false);
  const [selectedSource, setSelectedSource] = useState(null);
  const [selectedDestination, setSelectedDestination] = useState(null);
  const [cargoWeightKg, setCargoWeightKg] = useState('1250');
  const [parcelType, setParcelType] = useState('General');
  const [fragility, setFragility] = useState('Medium');
  const [priority, setPriority] = useState('Standard');
  const [temperatureControlled, setTemperatureControlled] = useState(false);

  const [planning, setPlanning] = useState(false);
  const [loadingStep, setLoadingStep] = useState('Preparing route intelligence...');
  const [error, setError] = useState('');
  const sourceSearchTimerRef = useRef(null);
  const destinationSearchTimerRef = useRef(null);

  const [intel, setIntel] = useState(null);

  const mapRegion = useMemo(() => {
    if (!intel?.source || !intel?.destination) {
      return {
        latitude: 20.5937,
        longitude: 78.9629,
        zoom: 5,
      };
    }

    return {
      latitude: (intel.source.latitude + intel.destination.latitude) / 2,
      longitude: (intel.source.longitude + intel.destination.longitude) / 2,
      zoom: 7,
    };
  }, [intel]);

  const canSubmit = sourceAddress.trim() && destinationAddress.trim() && !planning;

  useEffect(() => {
    return () => {
      if (sourceSearchTimerRef.current) clearTimeout(sourceSearchTimerRef.current);
      if (destinationSearchTimerRef.current) clearTimeout(destinationSearchTimerRef.current);
    };
  }, []);

  const onSourceChange = async (text) => {
    setSourceAddress(text);
    setSelectedSource(null);
    setSourceTouched(true);

    if (sourceSearchTimerRef.current) clearTimeout(sourceSearchTimerRef.current);
    if ((text || '').trim().length < 1) {
      setSourceSuggestions([]);
      setSourceSearching(false);
      return;
    }

    sourceSearchTimerRef.current = setTimeout(async () => {
      try {
        setSourceSearching(true);
        const suggestions = await searchAddresses(text);
        setSourceSuggestions(suggestions);
      } catch {
        setSourceSuggestions([]);
      } finally {
        setSourceSearching(false);
      }
    }, 300);
  };

  const onDestinationChange = async (text) => {
    setDestinationAddress(text);
    setSelectedDestination(null);
    setDestinationTouched(true);

    if (destinationSearchTimerRef.current) clearTimeout(destinationSearchTimerRef.current);
    if ((text || '').trim().length < 1) {
      setDestinationSuggestions([]);
      setDestinationSearching(false);
      return;
    }

    destinationSearchTimerRef.current = setTimeout(async () => {
      try {
        setDestinationSearching(true);
        const suggestions = await searchAddresses(text);
        setDestinationSuggestions(suggestions);
      } catch {
        setDestinationSuggestions([]);
      } finally {
        setDestinationSearching(false);
      }
    }, 300);
  };

  const analyzeRoute = async () => {
    if (!sourceAddress.trim() || !destinationAddress.trim()) {
      throw new Error('Enter both source and destination addresses.');
    }

    const source = selectedSource || (await geocodeAddress(sourceAddress));
    const destination = selectedDestination || (await geocodeAddress(destinationAddress));
    const routeAlternatives = await getOsrmRouteAlternatives(source, destination);
    const weatherSnapshot = await getWeatherAlongRoute(source, destination);
    const trafficSnapshot = await getTomTomTraffic(source, destination);

    const builtIntel = {
      source,
      destination,
      routeAlternatives,
      weatherSnapshot,
      trafficSnapshot,
    };
    setIntel(builtIntel);
    return builtIntel;
  };

  const onAnalyzePreview = async () => {
    setError('');
    setPlanning(true);
    try {
      setLoadingStep('Geocoding source and destination via OpenStreetMap...');
      await wait(300);
      const builtIntel = await analyzeRoute();
      setLoadingStep('Preview ready from OSM + live weather + traffic feeds.');
      await wait(400);
      setIntel(builtIntel);
    } catch (previewError) {
      setError(previewError.message || 'Unable to analyze route');
    } finally {
      setPlanning(false);
    }
  };

  const onGenerate = async () => {
    if (!canSubmit) return;

    setPlanning(true);
    setError('');

    try {
      const orchestrationSteps = [
        'Resolving exact addresses with OpenStreetMap geocoder...',
        'Pulling primary and alternative paths from OSM/OSRM...',
        'Fetching live weather context along route corridor...',
        'Analyzing live traffic state with TomTom flow APIs...',
        'Running delay model and finalizing dispatch package...',
      ];

      for (const step of orchestrationSteps) {
        setLoadingStep(step);
        await wait(700);
      }

      const builtIntel = intel || (await analyzeRoute());

      const tripData = await createTrip({
        source: builtIntel.source,
        destination: builtIntel.destination,
        cargoWeightKg: Number(cargoWeightKg) || 1000,
        weather: builtIntel.weatherSnapshot.weather,
        weatherSnapshot: builtIntel.weatherSnapshot,
        parcelType,
        fragility,
        priority,
        temperatureControlled,
        trafficIntensity: builtIntel.trafficSnapshot.trafficIntensity,
        trafficIncidentCount: builtIntel.trafficSnapshot.incidentCount,
        trafficSnapshot: builtIntel.trafficSnapshot,
        routeAlternatives: builtIntel.routeAlternatives,
      });

      navigation.navigate('TripDetails', { tripId: tripData.tripId });
    } catch (submitError) {
      setError(submitError.message || 'Failed to create trip plan');
    } finally {
      setPlanning(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <LinearGradient colors={['#101A2E', '#122847', '#0D315B']} style={styles.heroCard}>
        <Text style={styles.sectionTitle}>Shipment Planning Matrix</Text>
        <Text style={styles.sectionSubtitle}>Address-based planning with OpenStreetMap, weather, and live traffic intelligence.</Text>
      </LinearGradient>

      <View style={styles.formCard}>
        <Text style={styles.label}>Source Address</Text>
        <TextInput
          style={styles.input}
          value={sourceAddress}
          onChangeText={onSourceChange}
          onFocus={() => {
            setSourceTouched(true);
            if (!selectedSource && sourceAddress.trim().length >= 1) onSourceChange(sourceAddress);
          }}
          placeholder="Enter pickup address"
          placeholderTextColor={colors.textDim}
        />
        {sourceSuggestions.length > 0 ? (
          <View style={styles.suggestionsWrap}>
            {sourceSuggestions.slice(0, 6).map((item, index) => (
              <TouchableOpacity
                key={`source-${item.id}-${item.latitude}-${item.longitude}-${index}`}
                style={styles.suggestionItem}
                onPress={() => {
                  setSourceAddress(item.name);
                  setSelectedSource(item);
                  setSourceSuggestions([]);
                }}
              >
                <Text style={styles.suggestionText}>{item.name}</Text>
              </TouchableOpacity>
            ))}
          </View>
        ) : sourceSearching ? (
          <View style={styles.suggestionsWrap}>
            <Text style={styles.suggestionHint}>Searching addresses...</Text>
          </View>
        ) : sourceTouched && !selectedSource && sourceAddress.trim().length >= 1 ? (
          <View style={styles.suggestionsWrap}>
            <Text style={styles.suggestionHint}>No matches yet. Try a nearby city name.</Text>
          </View>
        ) : null}

        <Text style={styles.label}>Destination Address</Text>
        <TextInput
          style={styles.input}
          value={destinationAddress}
          onChangeText={onDestinationChange}
          onFocus={() => {
            setDestinationTouched(true);
            if (!selectedDestination && destinationAddress.trim().length >= 1) onDestinationChange(destinationAddress);
          }}
          placeholder="Enter delivery address"
          placeholderTextColor={colors.textDim}
        />
        {destinationSuggestions.length > 0 ? (
          <View style={styles.suggestionsWrap}>
            {destinationSuggestions.slice(0, 6).map((item, index) => (
              <TouchableOpacity
                key={`destination-${item.id}-${item.latitude}-${item.longitude}-${index}`}
                style={styles.suggestionItem}
                onPress={() => {
                  setDestinationAddress(item.name);
                  setSelectedDestination(item);
                  setDestinationSuggestions([]);
                }}
              >
                <Text style={styles.suggestionText}>{item.name}</Text>
              </TouchableOpacity>
            ))}
          </View>
        ) : destinationSearching ? (
          <View style={styles.suggestionsWrap}>
            <Text style={styles.suggestionHint}>Searching addresses...</Text>
          </View>
        ) : destinationTouched && !selectedDestination && destinationAddress.trim().length >= 1 ? (
          <View style={styles.suggestionsWrap}>
            <Text style={styles.suggestionHint}>No matches yet. Try a nearby city name.</Text>
          </View>
        ) : null}

        <Text style={styles.label}>Cargo Weight (kg)</Text>
        <TextInput
          style={styles.input}
          value={cargoWeightKg}
          onChangeText={setCargoWeightKg}
          placeholder="Enter cargo weight"
          placeholderTextColor={colors.textDim}
          keyboardType="numeric"
        />

        <Text style={styles.label}>Parcel Type</Text>
        <View style={styles.pickerWrap}>
          <Picker selectedValue={parcelType} onValueChange={setParcelType} dropdownIconColor={colors.text} style={styles.picker}>
            {PARCEL_TYPE_OPTIONS.map((option) => (
              <Picker.Item key={option} label={option} value={option} color={PICKER_DROPDOWN_TEXT_COLOR} />
            ))}
          </Picker>
        </View>

        <Text style={styles.label}>Fragility</Text>
        <View style={styles.pickerWrap}>
          <Picker selectedValue={fragility} onValueChange={setFragility} dropdownIconColor={colors.text} style={styles.picker}>
            {FRAGILITY_OPTIONS.map((option) => (
              <Picker.Item key={option} label={option} value={option} color={PICKER_DROPDOWN_TEXT_COLOR} />
            ))}
          </Picker>
        </View>

        <Text style={styles.label}>Priority</Text>
        <View style={styles.pickerWrap}>
          <Picker selectedValue={priority} onValueChange={setPriority} dropdownIconColor={colors.text} style={styles.picker}>
            {PRIORITY_OPTIONS.map((option) => (
              <Picker.Item key={option} label={option} value={option} color={PICKER_DROPDOWN_TEXT_COLOR} />
            ))}
          </Picker>
        </View>

        <View style={styles.switchRow}>
          <Text style={styles.label}>Temperature Controlled</Text>
          <Switch value={temperatureControlled} onValueChange={setTemperatureControlled} trackColor={{ false: '#2B3E64', true: '#1D8CFF' }} />
        </View>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <TouchableOpacity style={styles.secondaryButton} onPress={onAnalyzePreview} disabled={!canSubmit}>
          <Text style={styles.secondaryText}>Analyze Route Preview</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.sectionTitle}>OpenStreetMap Route Preview</Text>
      <View style={styles.mapCard}>
        <OsmMapView
          center={mapRegion}
          markers={
            intel
              ? [
                  {
                    latitude: intel.source.latitude,
                    longitude: intel.source.longitude,
                    title: 'Source',
                    description: intel.source.name,
                  },
                  {
                    latitude: intel.destination.latitude,
                    longitude: intel.destination.longitude,
                    title: 'Destination',
                    description: intel.destination.name,
                  },
                ]
              : []
          }
          polylines={(intel?.routeAlternatives || []).map((route, index) => ({
            coordinates: route.pathCoordinates,
            color: index === 0 ? '#4CC9FF' : '#6B7FA8',
            weight: index === 0 ? 4 : 2,
          }))}
          height={220}
        />
      </View>

      {intel ? (
        <View style={styles.summaryCard}>
          <Text style={styles.summaryTitle}>Live Intelligence Snapshot</Text>
          <Text style={styles.summaryLine}>Weather: {intel.weatherSnapshot.weather}</Text>
          <Text style={styles.summaryLine}>Temperature: {intel.weatherSnapshot.temperature} C</Text>
          <Text style={styles.summaryLine}>Wind Speed: {intel.weatherSnapshot.windSpeed} km/h</Text>
          <Text style={styles.summaryLine}>Traffic Intensity: {intel.trafficSnapshot.trafficIntensity}</Text>
          <Text style={styles.summaryLine}>Traffic Delay: +{intel.trafficSnapshot.trafficDelayMinutes} min</Text>
          <Text style={styles.summaryLine}>Routes Found: {intel.routeAlternatives.length}</Text>
        </View>
      ) : null}

      <TouchableOpacity style={[styles.button, !canSubmit && styles.buttonDisabled]} onPress={onGenerate} disabled={!canSubmit}>
        <Text style={styles.buttonText}>Create Shipment Plan</Text>
      </TouchableOpacity>

      <Modal transparent visible={planning} animationType="fade">
        <View style={styles.loadingOverlay}>
          <View style={styles.loadingCard}>
            <ActivityIndicator size="large" color={colors.accent} />
            <Text style={styles.loadingTitle}>Running Intelligence Pipeline</Text>
            <Text style={styles.loadingStep}>{loadingStep}</Text>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  contentContainer: {
    padding: 18,
    paddingBottom: 28,
  },
  heroCard: {
    borderRadius: 14,
    marginBottom: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    ...shadows.card,
  },
  sectionTitle: {
    fontSize: 18,
    fontFamily: fonts.heading,
    color: colors.text,
    marginBottom: 6,
    letterSpacing: 0.8,
  },
  sectionSubtitle: {
    color: colors.textMuted,
    fontSize: 14,
    fontFamily: fonts.body,
  },
  formCard: {
    backgroundColor: colors.panel,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    padding: 14,
    marginBottom: 14,
  },
  label: {
    fontSize: 15,
    color: colors.text,
    fontFamily: fonts.bodyStrong,
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#0A1324',
    borderWidth: 1,
    borderColor: '#2A3C5E',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 14,
    color: colors.text,
    fontFamily: fonts.body,
    fontSize: 16,
  },
  suggestionsWrap: {
    borderWidth: 1,
    borderColor: '#2A3C5E',
    borderRadius: 10,
    backgroundColor: '#0A1324',
    marginTop: -6,
    marginBottom: 12,
    maxHeight: 180,
  },
  suggestionItem: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#1B2A45',
  },
  suggestionText: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 14,
  },
  suggestionHint: {
    color: colors.textDim,
    fontFamily: fonts.body,
    fontSize: 13,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 4,
  },
  pickerWrap: {
    backgroundColor: '#0A1324',
    borderWidth: 1,
    borderColor: '#2A3C5E',
    borderRadius: 10,
    marginBottom: 14,
    overflow: 'hidden',
  },
  picker: {
    color: colors.text,
    fontFamily: fonts.body,
    height: 52,
  },
  secondaryButton: {
    backgroundColor: '#173056',
    borderRadius: 10,
    alignItems: 'center',
    paddingVertical: 12,
    marginTop: 6,
  },
  secondaryText: {
    color: '#A8CCFF',
    fontFamily: fonts.bodyStrong,
    fontSize: 15,
  },
  mapCard: {
    borderRadius: 14,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: 14,
  },
  map: {
    height: 220,
    width: '100%',
  },
  summaryCard: {
    backgroundColor: '#0C1425',
    borderRadius: 14,
    padding: 14,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: colors.border,
  },
  summaryTitle: {
    color: colors.text,
    fontFamily: fonts.bodyStrong,
    fontSize: 15,
    marginBottom: 8,
  },
  summaryLine: {
    color: colors.textMuted,
    marginBottom: 4,
    fontSize: 14,
    fontFamily: fonts.body,
  },
  button: {
    backgroundColor: colors.accentStrong,
    borderRadius: 10,
    alignItems: 'center',
    paddingVertical: 14,
  },
  buttonDisabled: {
    opacity: 0.45,
  },
  buttonText: {
    color: colors.text,
    fontFamily: fonts.bodyStrong,
    fontSize: 18,
  },
  errorText: {
    color: colors.danger,
    marginTop: 4,
    marginBottom: 8,
    fontFamily: fonts.body,
  },
  loadingOverlay: {
    flex: 1,
    backgroundColor: 'rgba(3, 8, 18, 0.78)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingCard: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: '#0C1426',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    padding: 18,
    alignItems: 'center',
  },
  loadingTitle: {
    marginTop: 10,
    color: colors.text,
    fontFamily: fonts.heading,
    fontSize: 16,
    marginBottom: 6,
    letterSpacing: 0.7,
  },
  loadingStep: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 14,
    textAlign: 'center',
  },
});
