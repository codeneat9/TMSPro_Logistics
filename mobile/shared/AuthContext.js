/**
 * Auth Context for managing authentication state
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  authAPI,
  setAuthTokens,
  getAuthTokens,
  hasValidToken,
  clearAuth,
  getUser,
} from './api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [state, setState] = useState({
    isLoading: true,
    isSignout: false,
    user: null,
    error: null,
  });

  const dispatch = (action) => {
    setState((prev) => authReducer(prev, action));
  };

  // Check if user is already logged in
  useEffect(() => {
    const bootstrapAsync = async () => {
      try {
        const valid = await hasValidToken();
        if (valid) {
          const user = await getUser();
          dispatch({ type: 'RESTORE_TOKEN', payload: { user } });
        } else {
          dispatch({ type: 'REST' });
        }
      } catch (e) {
        dispatch({ type: 'REST' });
      }
    };

    bootstrapAsync();
  }, []);

  const authContext = {
    state,
    signIn: async (email, password) => {
      try {
        const response = await authAPI.login(email, password);
        await setAuthTokens(response.data.access_token, response.data.refresh_token);
        const user = await getUser();
        dispatch({ type: 'SIGN_IN', payload: { user } });
        return { success: true };
      } catch (error) {
        const message = error.response?.data?.detail || 'Login failed';
        dispatch({ type: 'SIGN_IN_FAILURE', payload: { error: message } });
        return { success: false, error: message };
      }
    },

    signUp: async (email, password, fullName, phone) => {
      try {
        const response = await authAPI.register(email, password, fullName, phone);
        await setAuthTokens(response.data.access_token, response.data.refresh_token);
        const user = await getUser();
        dispatch({ type: 'SIGN_IN', payload: { user } });
        return { success: true };
      } catch (error) {
        const message = error.response?.data?.detail || 'Registration failed';
        dispatch({ type: 'SIGN_UP_FAILURE', payload: { error: message } });
        return { success: false, error: message };
      }
    },

    signOut: async () => {
      try {
        await clearAuth();
        dispatch({ type: 'SIGN_OUT' });
      } catch (error) {
        dispatch({ type: 'ERROR', payload: { error: 'Logout failed' } });
      }
    },
  };

  return (
    <AuthContext.Provider value={authContext}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Reducer for auth state
export const authReducer = (state, action) => {
  switch (action.type) {
    case 'RESTORE_TOKEN':
      return {
        isLoading: false,
        isSignout: false,
        user: action.payload.user,
        error: null,
      };
    case 'SIGN_IN':
      return {
        isLoading: false,
        isSignout: false,
        user: action.payload.user,
        error: null,
      };
    case 'SIGN_IN_FAILURE':
    case 'SIGN_UP_FAILURE':
    case 'ERROR':
      return {
        isLoading: false,
        isSignout: false,
        user: null,
        error: action.payload.error,
      };
    case 'SIGN_OUT':
      return {
        isLoading: false,
        isSignout: true,
        user: null,
        error: null,
      };
    case 'REST':
      return {
        isLoading: false,
        isSignout: false,
        user: null,
        error: null,
      };
    default:
      return state;
  }
};
