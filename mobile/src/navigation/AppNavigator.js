import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';

import { LoginScreen } from '../screens/LoginScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { CreateTripScreen } from '../screens/CreateTripScreen';
import { TripDetailsScreen } from '../screens/TripDetailsScreen';

const Stack = createStackNavigator();

export function AppNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Login"
        screenOptions={{
          headerStyle: { backgroundColor: '#0B3D91' },
          headerTintColor: '#FFFFFF',
          headerTitleStyle: { fontWeight: '700' },
          cardStyle: { backgroundColor: '#F5F7FA' },
        }}
      >
        <Stack.Screen
          name="Login"
          component={LoginScreen}
          options={{ title: 'Embedded AI TMS' }}
        />
        <Stack.Screen
          name="Home"
          component={HomeScreen}
          options={{ title: 'Home Dashboard' }}
        />
        <Stack.Screen
          name="CreateTrip"
          component={CreateTripScreen}
          options={{ title: 'Create Trip' }}
        />
        <Stack.Screen
          name="TripDetails"
          component={TripDetailsScreen}
          options={{ title: 'Trip Details' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
