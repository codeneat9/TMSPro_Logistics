import React from 'react';
import { TouchableOpacity, View, Text, StyleSheet } from 'react-native';
import { colors, fonts } from '../theme/designSystem';

export function RouteCard({ route, isSelected, onPress }) {
  return (
    <TouchableOpacity
      activeOpacity={0.9}
      style={[styles.card, isSelected ? styles.selectedCard : styles.defaultCard]}
      onPress={onPress}
    >
      <View style={styles.headerRow}>
        <Text style={styles.routeName}>{route.name}</Text>
        <Text
          style={[
            styles.riskBadge,
            route.risk === 'High'
              ? styles.riskHigh
              : route.risk === 'Medium'
                ? styles.riskMedium
                : styles.riskLow,
          ]}
        >
          {route.risk}
        </Text>
      </View>
      <Text style={styles.detail}>ETA: {route.eta}</Text>
      <Text style={styles.detail}>Cost: {route.cost}</Text>
      <Text style={styles.detail}>Delay Probability: {(route.delayProbability * 100).toFixed(0)}%</Text>
      {isSelected ? <Text style={styles.selectedText}>Selected Route</Text> : null}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 14,
    marginBottom: 12,
  },
  defaultCard: {
    backgroundColor: '#0F1628',
    borderColor: '#24324F',
  },
  selectedCard: {
    backgroundColor: '#13213B',
    borderColor: '#2EA6FF',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  routeName: {
    fontSize: 17,
    fontFamily: fonts.heading,
    color: colors.text,
    letterSpacing: 0.4,
  },
  riskBadge: {
    fontSize: 12,
    fontWeight: '700',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    overflow: 'hidden',
  },
  riskHigh: {
    color: '#FFC1CF',
    backgroundColor: '#4A1A2B',
  },
  riskMedium: {
    color: '#FFE2A0',
    backgroundColor: '#4A3513',
  },
  riskLow: {
    color: '#AEF5CD',
    backgroundColor: '#153628',
  },
  detail: {
    fontSize: 14,
    color: colors.textMuted,
    fontFamily: fonts.body,
    marginBottom: 2,
  },
  selectedText: {
    marginTop: 6,
    color: colors.accent,
    fontFamily: fonts.bodyStrong,
    fontSize: 13,
  },
});
