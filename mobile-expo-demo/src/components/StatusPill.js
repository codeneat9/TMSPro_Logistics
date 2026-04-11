import React from 'react';
import { Text, StyleSheet } from 'react-native';
import { fonts } from '../theme/designSystem';

export function StatusPill({ status }) {
  const style =
    status === 'PREPARING'
      ? styles.preparing
      : status === 'DELAYED'
      ? styles.delayed
      : status === 'IN_TRANSIT'
        ? styles.transit
        : status === 'ON_HOLD'
          ? styles.hold
          : status === 'COMPLETED'
            ? styles.complete
            : styles.created;

  return <Text style={[styles.base, style]}>{status.replace('_', ' ')}</Text>;
}

const styles = StyleSheet.create({
  base: {
    overflow: 'hidden',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
    fontFamily: fonts.bodyStrong,
    fontSize: 11,
    letterSpacing: 0.4,
  },
  preparing: {
    color: '#BFDBFE',
    backgroundColor: '#1D3557',
  },
  created: {
    color: '#A2D8FF',
    backgroundColor: '#1A2F4D',
  },
  transit: {
    color: '#9BF7E8',
    backgroundColor: '#153A37',
  },
  delayed: {
    color: '#FFC3D0',
    backgroundColor: '#4A1A2B',
  },
  hold: {
    color: '#FFE0A4',
    backgroundColor: '#453110',
  },
  complete: {
    color: '#A9F4C9',
    backgroundColor: '#143927',
  },
});
