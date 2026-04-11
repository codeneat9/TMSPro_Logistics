import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useTrips } from '../store/TripContext';
import { colors, fonts, shadows } from '../theme/designSystem';

export function LiveAlertBanner() {
  const { activeBanner } = useTrips();
  const insets = useSafeAreaInsets();

  if (!activeBanner) {
    return null;
  }

  return (
    <View style={[styles.wrap, { top: insets.top + 8 }]} pointerEvents="none">
      <View style={styles.card}>
        <Text style={styles.title}>{activeBanner.title}</Text>
        <Text style={styles.message}>{activeBanner.message}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: 'absolute',
    left: 12,
    right: 12,
    zIndex: 999,
  },
  card: {
    borderWidth: 1,
    borderColor: '#4E2E57',
    backgroundColor: '#1E1328',
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 12,
    ...shadows.card,
  },
  title: {
    color: '#FFADC2',
    fontFamily: fonts.bodyStrong,
    fontSize: 15,
    marginBottom: 2,
  },
  message: {
    color: colors.text,
    fontFamily: fonts.body,
    fontSize: 14,
  },
});
