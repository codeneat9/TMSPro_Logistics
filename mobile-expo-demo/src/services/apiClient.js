import Constants from 'expo-constants';

function inferBaseUrl() {
  const configured = process.env.EXPO_PUBLIC_API_BASE_URL;
  if (configured && configured.trim()) return configured.trim();

  const hostUri =
    Constants.expoConfig?.hostUri ||
    Constants.manifest2?.extra?.expoClient?.hostUri ||
    '';
  const host = hostUri.split(':')[0];
  return host ? `http://${host}:8000` : 'http://localhost:8000';
}

export const API_BASE_URL = inferBaseUrl();

export async function apiRequest(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });

  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { detail: text };
    }
  }

  if (!response.ok) {
    const detail = payload?.detail || `Request failed (${response.status})`;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }

  return payload;
}
