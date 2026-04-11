import React from 'react';
import { TouchableOpacity, View, Text, StyleSheet } from 'react-native';

export function RouteCard({ route, isSelected, onPress }) {
  return (
    <TouchableOpacity
      activeOpacity={0.9}
      style={[styles.card, isSelected ? styles.selectedCard : styles.defaultCard]}
      onPress={onPress}
    >
      <View style={styles.headerRow}>
        <Text style={styles.routeName}>{route.name}</Text>
        <Text style={[styles.riskBadge, route.risk === 'High' ? styles.riskHigh : route.risk === 'Medium' ? styles.riskMedium : styles.riskLow]}>
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
    backgroundColor: '#F2F7FF',
    borderColor: '#BFD7FF',
  },
  selectedCard: {
    backgroundColor: '#DBECFF',
    borderColor: '#3B82F6',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  routeName: {
    fontSize: 17,
    fontWeight: '800',
    color: '#102A43',
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
    color: '#9B1C1C',
    backgroundColor: '#FFE3E3',
  },
  riskMedium: {
    color: '#92400E',
    backgroundColor: '#FFF4D6',
  },
  riskLow: {
    color: '#166534',
    backgroundColor: '#DCFCE7',
  },
  detail: {
    fontSize: 14,
    color: '#334E68',
    marginBottom: 2,
  },
  selectedText: {
    marginTop: 6,
    color: '#1D4ED8',
    fontWeight: '700',
    fontSize: 13,
  },
});
