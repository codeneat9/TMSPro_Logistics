import { API_BASE_URL } from './apiClient';

const INDIA_FALLBACK_CITIES = [
  'Mumbai, Maharashtra, India',
  'Delhi, Delhi, India',
  'Bengaluru, Karnataka, India',
  'Hyderabad, Telangana, India',
  'Ahmedabad, Gujarat, India',
  'Chennai, Tamil Nadu, India',
  'Kolkata, West Bengal, India',
  'Surat, Gujarat, India',
  'Pune, Maharashtra, India',
  'Jaipur, Rajasthan, India',
  'Lucknow, Uttar Pradesh, India',
  'Kanpur, Uttar Pradesh, India',
  'Nagpur, Maharashtra, India',
  'Indore, Madhya Pradesh, India',
  'Bhopal, Madhya Pradesh, India',
  'Patna, Bihar, India',
  'Vadodara, Gujarat, India',
  'Ludhiana, Punjab, India',
  'Agra, Uttar Pradesh, India',
  'Nashik, Maharashtra, India',
];

function estimateTrafficIntensity(currentKmh, freeFlowKmh) {
  if (!currentKmh || !freeFlowKmh) return 'Moderate';
  const ratio = currentKmh / freeFlowKmh;
  if (ratio < 0.45) return 'Severe';
  if (ratio < 0.65) return 'Heavy';
  if (ratio < 0.85) return 'Moderate';
  return 'Low';
}

export async function geocodeAddress(address) {
  const items = await searchAddresses(address);
  if (!items.length) throw new Error(`Unable to locate address: ${address}`);
  return items[0];
}

export async function searchAddresses(query) {
  const q = (query || '').trim();
  if (!q || q.length < 1) return [];

  try {
    const encoded = encodeURIComponent(q);
    const backendResponse = await fetch(`${API_BASE_URL}/api/routes/address-suggestions?q=${encoded}&country=in`);
    if (backendResponse.ok) {
      const payload = await backendResponse.json();
      if (Array.isArray(payload?.items)) return payload.items;
    }
  } catch {
    // Continue with direct provider fallback below.
  }

  const encoded = encodeURIComponent(q);
  let mapped = [];

  try {
    const res = await fetch(`https://photon.komoot.io/api/?q=${encoded}&limit=8&lang=en`);
    const data = await res.json();
    const features = Array.isArray(data?.features) ? data.features : [];
    mapped = features
      .map((feature, idx) => {
        const props = feature?.properties || {};
        const coords = feature?.geometry?.coordinates || [];
        if (!Array.isArray(coords) || coords.length < 2) return null;
        const nameParts = [props.name, props.city, props.state, props.country].filter(Boolean);
        return {
          id: `photon-${props.osm_type || 'x'}-${props.osm_id || idx}`,
          name: nameParts.length ? nameParts.join(', ') : q,
          city: props.city || props.name || q,
          latitude: Number(coords[1]),
          longitude: Number(coords[0]),
          country_code: String(props.countrycode || '').toLowerCase(),
        };
      })
      .filter(Boolean);
  } catch {
    mapped = [];
  }

  const inIndia = mapped.filter((item) => item.country_code === 'in');
  const candidates = (inIndia.length ? inIndia : mapped).slice(0, 8);
  if (candidates.length > 0) return candidates;

  // Deterministic fallback so the UI still provides usable address options when network providers fail.
  const lower = q.toLowerCase();
  return INDIA_FALLBACK_CITIES.filter((name) => name.toLowerCase().includes(lower))
    .slice(0, 8)
    .map((name, idx) => ({
      id: `fallback-${idx}-${name}`,
      name,
      city: name.split(',')[0],
      latitude: 20.5937,
      longitude: 78.9629,
      country_code: 'in',
      isFallback: true,
    }));
}

function mapOsrmRoutes(osrmRoutes) {
  return osrmRoutes.slice(0, 3).map((route, idx) => {
    const coordinates = (route.geometry?.coordinates || []).map(([lon, lat]) => ({ latitude: lat, longitude: lon }));
    return {
      id: String.fromCharCode(65 + idx),
      name: idx === 0 ? 'Route A (Primary OSM)' : idx === 1 ? 'Route B (Alternative OSM)' : 'Route C (Alternative OSM)',
      etaMinutes: Math.round(route.duration / 60),
      distanceKm: Math.round(route.distance / 1000),
      pathCoordinates: coordinates,
    };
  });
}

export async function getOsrmRouteAlternatives(source, destination) {
  const url = `https://router.project-osrm.org/route/v1/driving/${source.longitude},${source.latitude};${destination.longitude},${destination.latitude}?overview=full&geometries=geojson&alternatives=true&steps=false`;
  const res = await fetch(url);
  const data = await res.json();
  if (data.code !== 'Ok' || !Array.isArray(data.routes) || data.routes.length === 0) {
    throw new Error('OSRM route lookup failed');
  }

  const mapped = mapOsrmRoutes(data.routes);
  if (mapped.length === 1) {
    mapped.push({ ...mapped[0], id: 'B', name: 'Route B (Fallback OSM)', etaMinutes: mapped[0].etaMinutes + 7 });
    mapped.push({ ...mapped[0], id: 'C', name: 'Route C (Fallback OSM)', etaMinutes: mapped[0].etaMinutes + 13 });
  } else if (mapped.length === 2) {
    mapped.push({ ...mapped[1], id: 'C', name: 'Route C (Fallback OSM)', etaMinutes: mapped[1].etaMinutes + 8 });
  }

  return mapped.slice(0, 3);
}

export async function getWeatherAlongRoute(source, destination) {
  const lat = ((source.latitude + destination.latitude) / 2).toFixed(4);
  const lon = ((source.longitude + destination.longitude) / 2).toFixed(4);
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,precipitation,wind_speed_10m,weather_code`;
  const res = await fetch(url);
  const data = await res.json();
  const current = data?.current || {};

  const precipitation = Number(current.precipitation || 0);
  let weather = 'Clear';
  if (precipitation > 3) weather = 'Storm';
  else if (precipitation > 0.2) weather = 'Rain';

  return {
    weather,
    temperature: Number(current.temperature_2m ?? 0),
    windSpeed: Number(current.wind_speed_10m ?? 0),
    precipitation,
  };
}

export async function getTomTomTraffic(source, destination) {
  const key = process.env.EXPO_PUBLIC_TOMTOM_API_KEY;
  if (!key) {
    return {
      trafficIntensity: 'Moderate',
      trafficDelayMinutes: 12,
      incidentCount: 1,
      source: 'estimated',
    };
  }

  const point = `${((source.latitude + destination.latitude) / 2).toFixed(4)},${((source.longitude + destination.longitude) / 2).toFixed(4)}`;
  const url = `https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key=${key}&point=${point}`;
  const res = await fetch(url);
  const data = await res.json();
  const flow = data?.flowSegmentData || {};
  const currentKmh = Number(flow.currentSpeed || 0);
  const freeFlowKmh = Number(flow.freeFlowSpeed || 0);
  const trafficIntensity = estimateTrafficIntensity(currentKmh, freeFlowKmh);
  const delay = freeFlowKmh > 0 ? Math.max(Math.round(((freeFlowKmh - currentKmh) / freeFlowKmh) * 28), 0) : 12;

  return {
    trafficIntensity,
    trafficDelayMinutes: delay,
    incidentCount: delay > 15 ? 2 : 1,
    source: 'tomtom',
  };
}
