import { apiRequest } from './apiClient';

export async function registerUser({ email, password, fullName, phone, role = 'customer' }) {
  return apiRequest('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
      phone,
      role,
    }),
  });
}

export async function loginUser({ email, password }) {
  return apiRequest('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe(accessToken) {
  return apiRequest('/api/auth/me', {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}
