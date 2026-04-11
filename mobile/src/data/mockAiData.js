function hashText(text) {
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) % 100000;
  }
  return hash;
}

function toRiskLabel(probability) {
  if (probability >= 0.75) return 'High';
  if (probability >= 0.5) return 'Medium';
  return 'Low';
}

function formatRupees(value) {
  return `INR ${Math.round(value).toLocaleString('en-IN')}`;
}

function minutesToEta(minutes) {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
}

export function generateTripPrediction(input) {
  const seed = hashText(`${input.source}-${input.destination}-${input.cargoWeightKg}`);
  const baseMinutes = 120 + (seed % 70);
  const baseCost = 980 + (seed % 800);

  const routeA = {
    id: 'A',
    name: 'Route A',
    etaMinutes: baseMinutes + 18,
    costValue: baseCost + 120,
    delayProbability: 0.72,
  };

  const routeB = {
    id: 'B',
    name: 'Route B',
    etaMinutes: baseMinutes,
    costValue: baseCost + 45,
    delayProbability: 0.43,
  };

  const routeC = {
    id: 'C',
    name: 'Route C',
    etaMinutes: baseMinutes + 26,
    costValue: baseCost - 50,
    delayProbability: 0.59,
  };

  const routes = [routeA, routeB, routeC].map((route) => ({
    ...route,
    eta: minutesToEta(route.etaMinutes),
    cost: formatRupees(route.costValue),
    risk: toRiskLabel(route.delayProbability),
  }));

  return {
    tripId: `TRIP-${seed}`,
    source: input.source,
    destination: input.destination,
    cargoWeightKg: input.cargoWeightKg,
    createdAt: new Date().toISOString(),
    selectedRouteId: 'A',
    routes,
    prediction: {
      delayProbability: routeA.delayProbability,
      risk: toRiskLabel(routeA.delayProbability),
      eta: routeA.eta,
      cost: routeA.cost,
      selectedRoute: routeA.name,
      modelTag: 'DelayPredictor-v2.4',
    },
  };
}

export function simulateReroute(tripData) {
  const current = tripData.routes.find((r) => r.id === tripData.selectedRouteId) || tripData.routes[0];
  const rerouteTo = tripData.routes.find((r) => r.id === 'B') || tripData.routes[1];
  const improvement = Math.max(current.etaMinutes - rerouteTo.etaMinutes, 8);

  return {
    alertTitle: 'Route changed due to predicted delay',
    messages: [
      'Delay detected by AI risk model',
      'Traffic congestion identified ahead',
      `Switching to ${rerouteTo.name}`,
      `ETA improved by ${improvement} mins`,
    ],
    nextRouteId: rerouteTo.id,
    prediction: {
      delayProbability: rerouteTo.delayProbability,
      risk: rerouteTo.risk,
      cost: rerouteTo.cost,
      eta: rerouteTo.eta,
      selectedRoute: rerouteTo.name,
      improvement: `${improvement} mins faster`,
    },
  };
}
