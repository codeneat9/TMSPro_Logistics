function hashText(text) {
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 33 + text.charCodeAt(i)) % 100000;
  }
  return hash;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function toRiskLabel(probability) {
  if (probability >= 0.75) return 'High';
  if (probability >= 0.5) return 'Medium';
  return 'Low';
}

function formatInr(value) {
  return `INR ${Math.round(value).toLocaleString('en-IN')}`;
}

function minutesToEta(minutes) {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
}

function estimateDistanceKm(source, destination) {
  const latDiff = Math.abs(source.latitude - destination.latitude);
  const lngDiff = Math.abs(source.longitude - destination.longitude);
  const km = Math.sqrt(latDiff * latDiff + lngDiff * lngDiff) * 111;
  return Math.max(34, km);
}

function buildPath(source, destination, arcStrength = 0.2) {
  const midLat = (source.latitude + destination.latitude) / 2;
  const midLng = (source.longitude + destination.longitude) / 2;
  const latOffset = (destination.longitude - source.longitude) * arcStrength;
  const lngOffset = (source.latitude - destination.latitude) * arcStrength;

  return [
    { latitude: source.latitude, longitude: source.longitude },
    { latitude: midLat + latOffset, longitude: midLng + lngOffset },
    { latitude: destination.latitude, longitude: destination.longitude },
  ];
}

export function generateTripPrediction(input) {
  const source = input.source;
  const destination = input.destination;
  const trafficIntensity = input.trafficIntensity || 'Moderate';
  const trafficIncidentCount = Number(input.trafficIncidentCount ?? 1);
  const seed = hashText(
    `${source.id}-${destination.id}-${input.cargoWeightKg}-${input.weather}-${trafficIntensity}-${trafficIncidentCount}`
  );
  const distanceKm = estimateDistanceKm(source, destination);
  const routeAlternatives = Array.isArray(input.routeAlternatives) ? input.routeAlternatives : null;

  const weatherPenalty = input.weather === 'Rain' ? 0.05 : input.weather === 'Storm' ? 0.09 : 0.02;
  const fragilityPenalty = input.fragility === 'High' ? 0.06 : input.fragility === 'Medium' ? 0.03 : 0.01;
  const trafficPenalty =
    trafficIntensity === 'Severe'
      ? 0.16
      : trafficIntensity === 'Heavy'
        ? 0.1
        : trafficIntensity === 'Low'
          ? 0.02
          : 0.06;
  const incidentPenalty = clamp(trafficIncidentCount * 0.015, 0.0, 0.09);
  const temperaturePenalty = input.temperatureControlled ? 0.04 : 0;

  const baselineProbability = clamp(
    0.24 +
      weatherPenalty +
      fragilityPenalty +
      temperaturePenalty +
      trafficPenalty +
      incidentPenalty +
      (seed % 8) / 100,
    0.18,
    0.62
  );
  const baselineEtaMinutes = Math.round(distanceKm * 1.6 + 70 + (seed % 25) + trafficIncidentCount * 6);
  const trafficDelayMinutes =
    (trafficIntensity === 'Severe' ? 34 : trafficIntensity === 'Heavy' ? 22 : trafficIntensity === 'Low' ? 6 : 14) +
    trafficIncidentCount * 4;
  const baseCost = Math.round(distanceKm * 18 + Number(input.cargoWeightKg) * 0.35 + 850);
  const trafficIndex = clamp(
    35 + (trafficIntensity === 'Severe' ? 42 : trafficIntensity === 'Heavy' ? 32 : trafficIntensity === 'Low' ? 14 : 24) + seed % 12,
    0,
    100
  );

  const routeA = {
    id: 'A',
    name: 'Route A (National Corridor)',
    etaMinutes: baselineEtaMinutes + 16,
    costValue: baseCost + 160,
    delayProbability: clamp(baselineProbability + 0.12, 0.3, 0.96),
    distanceKm: Math.round(distanceKm + 18),
    pathCoordinates: buildPath(source, destination, 0.34),
  };

  const routeB = {
    id: 'B',
    name: 'Route B (Adaptive Priority Lane)',
    etaMinutes: baselineEtaMinutes,
    costValue: baseCost + 70,
    delayProbability: clamp(baselineProbability - 0.09, 0.24, 0.9),
    distanceKm: Math.round(distanceKm + 5),
    pathCoordinates: buildPath(source, destination, 0.18),
  };

  const routeC = {
    id: 'C',
    name: 'Route C (Cost Optimized)',
    etaMinutes: baselineEtaMinutes + 24,
    costValue: baseCost - 95,
    delayProbability: clamp(baselineProbability + 0.03, 0.28, 0.95),
    distanceKm: Math.round(distanceKm + 11),
    pathCoordinates: buildPath(source, destination, -0.2),
  };

  const computedRoutes = [routeA, routeB, routeC];
  const routeSeed = routeAlternatives && routeAlternatives.length ? routeAlternatives : computedRoutes;

  const routes = routeSeed.map((route, index) => {
    const etaMinutes = route.etaMinutes || baselineEtaMinutes + index * 9;
    const costValue = route.costValue || baseCost + index * 60;
    const delayProbability =
      route.delayProbability ||
      clamp(baselineProbability + (index === 1 ? -0.04 : index === 2 ? 0.03 : 0.01), 0.18, 0.66);

    return {
      ...route,
      id: route.id || String.fromCharCode(65 + index),
      name:
        route.name ||
        (index === 0
          ? 'Route A (Primary OSM)'
          : index === 1
            ? 'Route B (Alternative OSM)'
            : 'Route C (Alternative OSM)'),
      etaMinutes,
      costValue,
      delayProbability,
      distanceKm: route.distanceKm || Math.round(distanceKm + index * 6),
      pathCoordinates: route.pathCoordinates || computedRoutes[index]?.pathCoordinates || computedRoutes[0].pathCoordinates,
      eta: minutesToEta(etaMinutes),
      cost: formatInr(costValue),
      risk: toRiskLabel(delayProbability),
    };
  });

  const selected = routes[0];

  return {
    tripId: `TRIP-${seed}`,
    source,
    destination,
    cargoWeightKg: Number(input.cargoWeightKg),
    selectedRouteId: 'A',
    routes,
    prediction: {
      delayProbability: selected.delayProbability,
      risk: selected.risk,
      cost: selected.cost,
      eta: selected.eta,
      selectedRoute: selected.name,
      trafficIndex,
      incidentCount: trafficIncidentCount,
      trafficIntensity,
      corridorLoad: `${trafficIndex}% network load`,
      trafficDelayMinutes,
      weather: input.weather,
      weatherSnapshot: input.weatherSnapshot || null,
      trafficSnapshot: input.trafficSnapshot || null,
      modelTag: 'Operations Intelligence v2.4',
    },
  };
}

export function simulateReroute(tripData, selectedRouteId) {
  const selected = tripData.routes.find((route) => route.id === selectedRouteId) || tripData.routes[0];
  const adaptive = tripData.routes.find((route) => route.id === 'B') || tripData.routes[1];
  const improvement = Math.max(selected.etaMinutes - adaptive.etaMinutes, 8);

  return {
    alertTitle: 'Dynamic reroute activated',
    messages: [
      'Delay risk crossed threshold',
      'Congestion pattern detected ahead',
      `Switched to ${adaptive.name}`,
      `ETA improvement: ${improvement} mins`,
    ],
    nextRouteId: adaptive.id,
    prediction: {
      delayProbability: adaptive.delayProbability,
      risk: adaptive.risk,
      cost: adaptive.cost,
      eta: adaptive.eta,
      selectedRoute: adaptive.name,
      improvement: `${improvement} mins faster`,
    },
  };
}
