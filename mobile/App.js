import React, { useEffect } from 'react';
import { StatusBar, SafeAreaView, Text } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

import { AuthProvider, useAuth } from './shared/AuthContext';
import { LoginScreen } from './customer/LoginScreen';
import { RegisterScreen } from './customer/RegisterScreen';
import { HomeScreen } from './customer/HomeScreen';
import { TripDetailsScreen } from './customer/TripDetailsScreen';
import { CreateTripScreen } from './customer/CreateTripScreen';
import { TrackingScreen } from './customer/TrackingScreen';
import { ProfileScreen } from './customer/ProfileScreen';
import { initializePushNotifications } from './shared/pushNotifications';


const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

/**
 * Auth Stack - Login/Register screens
 */
const AuthStack = () => (
  <Stack.Navigator
    screenOptions={{
      headerShown: false,
      cardStyle: { backgroundColor: '#f5f5f5' },
    }}
  >
    <Stack.Screen
      name="Login"
      component={LoginScreen}
      options={{ animationEnabled: false }}
    />
    <Stack.Screen
      name="Register"
      component={RegisterScreen}
      options={{
        animationEnabled: true,
        animationTypeForReplace: 'pop',
      }}
    />
  </Stack.Navigator>
);

/**
 * Home Stack - Nested stack for home flow (Home → TripDetails, CreateTrip)
 */
const HomeStack = () => (
  <Stack.Navigator
    screenOptions={{
      headerStyle: { backgroundColor: '#2196F3' },
      headerTintColor: '#fff',
      headerTitleStyle: { fontWeight: '700' },
    }}
  >
    <Stack.Screen
      name="HomeScreen"
      component={HomeScreen}
      options={{ title: 'TMSPro Dashboard' }}
    />
    <Stack.Screen
      name="TripDetails"
      component={TripDetailsScreen}
      options={({ route }) => ({
        title: `Trip #${route.params?.tripId || 'Loading'}`,
      })}
    />
    <Stack.Screen
      name="CreateTrip"
      component={CreateTripScreen}
      options={{ title: 'Create New Trip' }}
    />
  </Stack.Navigator>
);

/**
 * App Stack - Main app screens with bottom tab navigation
 */
const AppStack = () => (
  <Tab.Navigator
    screenOptions={{
      headerShown: true,
      tabBarActiveTintColor: '#2196F3',
      tabBarInactiveTintColor: '#999',
      headerStyle: {
        backgroundColor: '#2196F3',
      },
      headerTintColor: '#fff',
      headerTitleStyle: {
        fontWeight: '700',
      },
    }}
  >
    <Tab.Screen
      name="HomeTab"
      component={HomeStack}
      options={{
        tabBarLabel: 'Dashboard',
        tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>🏠</Text>,
        headerShown: false,
      }}
    />
    <Tab.Screen
      name="Tracking"
      component={TrackingScreen}
      options={{
        tabBarLabel: 'Tracking',
        tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>📍</Text>,
        title: 'Live Tracking',
      }}
    />
    <Tab.Screen
      name="Profile"
      component={ProfileScreen}
      options={{
        tabBarLabel: 'Profile',
        tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>👤</Text>,
        title: 'My Profile',
      }}
    />
  </Tab.Navigator>
);

/**
 * Navigation root - shows auth or app stack based on user state
 */
const RootNavigator = () => {
  const { state } = useAuth();

  // Show loading splash while checking session
  if (state.isLoading) {
    return (
      <SafeAreaView style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#2196F3' }}>
        <Text style={{ fontSize: 18, color: '#fff', fontWeight: '600' }}>TMSPro</Text>
        <Text style={{ fontSize: 12, color: '#ccc', marginTop: 8 }}>Loading...</Text>
      </SafeAreaView>
    );
  }

  return (
    <NavigationContainer>
      <StatusBar barStyle="light-content" backgroundColor="#2196F3" />
      {state.user ? <AppStack /> : <AuthStack />}
    </NavigationContainer>
  );
};

/**
 * Main App Component - Entry point with auth provider
 */
export default function App() {
  useEffect(() => {
    let cleanup = null;

    const bootstrapPush = async () => {
      cleanup = await initializePushNotifications();
    };

    bootstrapPush();

    return () => {
      if (cleanup) {
        cleanup();
      }
    };
  }, []);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <AuthProvider>
        <RootNavigator />
      </AuthProvider>
    </GestureHandlerRootView>
  );
}

