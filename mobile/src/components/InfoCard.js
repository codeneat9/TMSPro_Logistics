import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export function InfoCard({ title, value, tone = 'blue', subtitle }) {
  const toneStyle =
    tone === 'red' ? styles.red : tone === 'green' ? styles.green : styles.blue;

  return (
    <View style={[styles.card, toneStyle]}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.value}>{value}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    minHeight: 86,
  },
  blue: {
    backgroundColor: '#E9F2FF',
    borderColor: '#B6D3FF',
  },
  red: {
    backgroundColor: '#FFEAEA',
    borderColor: '#FFB3B3',
  },
  green: {
    backgroundColor: '#EAFBF0',
    borderColor: '#B5ECCA',
  },
  title: {
    fontSize: 12,
    color: '#486581',
    fontWeight: '600',
  },
  value: {
    marginTop: 6,
    fontSize: 20,
    color: '#102A43',
    fontWeight: '800',
  },
  subtitle: {
    marginTop: 4,
    fontSize: 12,
    color: '#486581',
  },
});
