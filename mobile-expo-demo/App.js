import React from 'react';
import { ActivityIndicator, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useFonts } from 'expo-font';
import {
  Orbitron_600SemiBold,
} from '@expo-google-fonts/orbitron';
import {
  Rajdhani_400Regular,
  Rajdhani_500Medium,
  Rajdhani_700Bold,
} from '@expo-google-fonts/rajdhani';

import { AppNavigator } from './src/navigation/AppNavigator';
import { TripProvider } from './src/store/TripContext';
import { AuthProvider } from './src/store/AuthContext';
import { colors } from './src/theme/designSystem';
import { LiveAlertBanner } from './src/components/LiveAlertBanner';

export default function App() {
  const [fontsLoaded] = useFonts({
    Orbitron_600SemiBold,
    Rajdhani_400Regular,
    Rajdhani_500Medium,
    Rajdhani_700Bold,
  });

  if (!fontsLoaded) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <SafeAreaProvider>
      <AuthProvider>
        <TripProvider>
          <StatusBar style="light" />
          <AppNavigator />
          <LiveAlertBanner />
        </TripProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
