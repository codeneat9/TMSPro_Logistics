import React, { useMemo } from 'react';
import { View, StyleSheet } from 'react-native';
import { WebView } from 'react-native-webview';

function escapeForTemplate(str) {
  return String(str || '')
    .replace(/\\/g, '\\\\')
    .replace(/`/g, '\\`')
    .replace(/\$/g, '\\$');
}

export function OsmMapView({ center, markers = [], polylines = [], height = 220 }) {
  const html = useMemo(() => {
    const safeCenter = JSON.stringify(center || { latitude: 20.5937, longitude: 78.9629, zoom: 5 });
    const safeMarkers = JSON.stringify(markers || []);
    const safePolylines = JSON.stringify(polylines || []);

    return `<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map { margin: 0; padding: 0; width: 100%; height: 100%; background: #0b1220; }
    .leaflet-container { font-family: Arial, sans-serif; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const center = ${escapeForTemplate(safeCenter)};
    const markers = ${escapeForTemplate(safeMarkers)};
    const polylines = ${escapeForTemplate(safePolylines)};

    function toNumber(value) {
      const n = Number(value);
      return Number.isFinite(n) ? n : null;
    }

    function normalizePoint(point) {
      if (!point) return null;
      const lat = toNumber(point.latitude ?? point.lat);
      const lng = toNumber(point.longitude ?? point.lng ?? point.lon);
      if (lat === null || lng === null) return null;
      if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
      return { lat, lng };
    }

    const map = L.map('map', { zoomControl: false }).setView([center.latitude, center.longitude], center.zoom || 6);

    // OpenStreetMap tile providers with runtime fallback.
    // Use mirrors first because tile.openstreetmap.org may return policy-block images on heavy/demo traffic.
    const tileProviders = [
      'https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
      'https://tile.openstreetmap.de/{z}/{x}/{y}.png',
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    ];

    let activeTileLayer = null;
    let activeProviderIndex = 0;
    function mountTileLayer(providerIndex) {
      if (activeTileLayer) {
        map.removeLayer(activeTileLayer);
      }
      activeProviderIndex = providerIndex;
      let tileErrors = 0;
      activeTileLayer = L.tileLayer(tileProviders[providerIndex], {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
      });
      activeTileLayer.on('tileerror', () => {
        tileErrors += 1;
        if (tileErrors >= 6 && activeProviderIndex < tileProviders.length - 1) {
          mountTileLayer(activeProviderIndex + 1);
        }
      });
      activeTileLayer.addTo(map);
    }

    mountTileLayer(0);

    markers.forEach((m) => {
      const point = normalizePoint(m);
      if (!point) return;
      const marker = L.marker([point.lat, point.lng]).addTo(map);
      if (m.title || m.description) {
        marker.bindPopup((m.title || '') + (m.description ? '<br/>' + m.description : ''));
      }
    });

    let hasPolyline = false;
    polylines.forEach((line) => {
      if (!line.coordinates || !line.coordinates.length) return;
      const latLngs = line.coordinates
        .map((c) => normalizePoint(c))
        .filter(Boolean)
        .map((c) => [c.lat, c.lng]);
      if (latLngs.length < 2) return;
      hasPolyline = true;
      L.polyline(latLngs, {
        color: line.color || '#44ccff',
        weight: line.weight || 4,
        opacity: line.opacity || 0.9
      }).addTo(map);
    });

    if (!hasPolyline && markers.length >= 2) {
      const a = normalizePoint(markers[0]);
      const b = normalizePoint(markers[1]);
      if (a && b) {
        L.polyline([
          [a.lat, a.lng],
          [b.lat, b.lng],
        ], {
          color: '#4CC9FF',
          weight: 3,
          opacity: 0.85,
          dashArray: '6,8',
        }).addTo(map);
      }
    }

    const fitPoints = [];
    markers.forEach((m) => {
      const p = normalizePoint(m);
      if (p) fitPoints.push([p.lat, p.lng]);
    });
    polylines.forEach((line) => {
      (line.coordinates || []).forEach((c) => {
        const p = normalizePoint(c);
        if (p) fitPoints.push([p.lat, p.lng]);
      });
    });

    if (fitPoints.length > 1) {
      map.fitBounds(fitPoints, { padding: [20, 20] });
    }
  </script>
</body>
</html>`;
  }, [center, markers, polylines]);

  return (
    <View style={[styles.wrap, { height }]}> 
      <WebView
        originWhitelist={['*']}
        source={{ html }}
        style={styles.webview}
        javaScriptEnabled
        domStorageEnabled
        scrollEnabled={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: '100%',
    overflow: 'hidden',
    borderRadius: 12,
  },
  webview: {
    backgroundColor: '#0b1220',
  },
});
