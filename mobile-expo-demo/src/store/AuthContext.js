import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { getMe, loginUser, registerUser } from '../services/authApi';

const TOKEN_KEY = 'tms_access_token';
const REFRESH_KEY = 'tms_refresh_token';

function normalizeIndiaPhone(phone) {
  const digits = String(phone || '').replace(/\D/g, '');
  let local = '';

  if (digits.length === 12 && digits.startsWith('91')) {
    local = digits.slice(2);
  } else if (digits.length === 10) {
    local = digits;
  } else {
    throw new Error('Enter a valid India mobile number (10 digits).');
  }

  if (!/^[6-9]\d{9}$/.test(local)) {
    throw new Error('India mobile number must start with 6/7/8/9.');
  }

  return `+91${local}`;
}

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [loading, setLoading] = useState(true);
  const [accessToken, setAccessToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        // Force fresh authentication on every app launch.
        await AsyncStorage.multiRemove([TOKEN_KEY, REFRESH_KEY]);
        setAccessToken(null);
        setRefreshToken(null);
        setUser(null);
      } catch {
        await AsyncStorage.multiRemove([TOKEN_KEY, REFRESH_KEY]);
      } finally {
        setLoading(false);
      }
    };

    bootstrap();
  }, []);

  const signIn = async ({ email, password }) => {
    const tokens = await loginUser({ email, password });
    const profile = await getMe(tokens.access_token);
    setAccessToken(tokens.access_token);
    setRefreshToken(tokens.refresh_token);
    setUser(profile);
    return profile;
  };

  const signUp = async ({ fullName, email, phone, password }) => {
    const normalizedPhone = normalizeIndiaPhone(phone);
    const tokens = await registerUser({
      fullName,
      email,
      phone: normalizedPhone,
      password,
      role: 'customer',
    });
    const profile = await getMe(tokens.access_token);
    setAccessToken(tokens.access_token);
    setRefreshToken(tokens.refresh_token);
    setUser(profile);
    return profile;
  };

  const signOut = async () => {
    await AsyncStorage.multiRemove([TOKEN_KEY, REFRESH_KEY]);
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({
      loading,
      isAuthenticated: !!accessToken,
      accessToken,
      refreshToken,
      user,
      signIn,
      signUp,
      signOut,
    }),
    [loading, accessToken, refreshToken, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
