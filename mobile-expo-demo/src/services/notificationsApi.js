import { apiRequest } from './apiClient';

export async function sendSmsTripUpdate({ accessToken, phone, tripId, status, title, message }) {
  if (!accessToken && !phone) {
    return { sent: false, reason: 'missing_auth_and_phone' };
  }

  try {
    const result = await apiRequest('/api/notifications/sms-update', {
      method: 'POST',
      headers: {
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: JSON.stringify({
        ...(phone ? { phone } : {}),
        trip_id: tripId,
        status,
        title,
        message,
      }),
    });
    return result;
  } catch (error) {
    return { sent: false, reason: error.message, result: error.message };
  }
}
