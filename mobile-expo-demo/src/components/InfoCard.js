import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, fonts } from '../theme/designSystem';

export function InfoCard({ title, value, subtitle, tone = 'blue' }) {
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
    borderRadius: 14,
    padding: 12,
    borderWidth: 1,
    minHeight: 88,
  },
  blue: {
    backgroundColor: '#111C30',
    borderColor: '#2A4066',
  },
  red: {
    backgroundColor: '#291522',
    borderColor: '#61324A',
  },
  green: {
    backgroundColor: '#112322',
    borderColor: '#2D5A4F',
  },
  title: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
    letterSpacing: 0.4,
  },
  value: {
    color: colors.text,
    fontFamily: fonts.bodyStrong,
    fontSize: 20,
    marginTop: 6,
  },
  subtitle: {
    color: colors.textDim,
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    marginTop: 4,
  },
});
