import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { LoginScreen } from '../screens/LoginScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { CreateTripScreen } from '../screens/CreateTripScreen';
import { TripDetailsScreen } from '../screens/TripDetailsScreen';
import { colors, fonts } from '../theme/designSystem';
import { useAuth } from '../store/AuthContext';

const Stack = createNativeStackNavigator();

export function AppNavigator() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return null;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName={isAuthenticated ? 'Home' : 'Login'}
        screenOptions={{
          headerStyle: { backgroundColor: colors.panelSoft },
          headerTintColor: colors.text,
          headerTitleStyle: { fontFamily: fonts.heading, letterSpacing: 0.7 },
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        <Stack.Screen
          name="Login"
          component={LoginScreen}
          options={{ title: 'Operations Sign In', headerShown: false }}
        />
        <Stack.Screen
          name="Home"
          component={HomeScreen}
          options={{ title: 'Operations Console' }}
        />
        <Stack.Screen name="CreateTrip" component={CreateTripScreen} options={{ title: 'Plan Shipment' }} />
        <Stack.Screen name="TripDetails" component={TripDetailsScreen} options={{ title: 'Shipment Control' }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
