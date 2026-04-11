import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, fonts, shadows } from '../theme/designSystem';
import { useAuth } from '../store/AuthContext';

export function LoginScreen({ navigation }) {
  const { signIn, signUp } = useAuth();

  const [mode, setMode] = useState('signin');
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const onSubmit = async () => {
    if (!email.trim() || !password.trim()) return;
    if (mode === 'signup' && (!fullName.trim() || !phone.trim())) return;

    setError('');
    setLoading(true);
    try {
      if (mode === 'signup') {
        await signUp({
          fullName: fullName.trim(),
          phone: phone.trim(),
          email: email.trim(),
          password,
        });
      } else {
        await signIn({ email: email.trim(), password });
      }
      navigation.replace('Home');
    } catch (submitError) {
      setError(submitError.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <LinearGradient colors={['#05070D', '#0B1426', '#091C36']} style={styles.background}>
      <View style={styles.container}>
        <Text style={styles.title}>NEXUS FREIGHT GRID</Text>
        <Text style={styles.subtitle}>AI Logistics Intelligence Layer</Text>

        <View style={styles.formCard}>
          <Text style={styles.formTitle}>{mode === 'signup' ? 'Create Operator Account' : 'Secure Operator Sign In'}</Text>
          {mode === 'signup' ? (
            <>
              <TextInput
                style={styles.input}
                value={fullName}
                onChangeText={setFullName}
                placeholder="Full Name"
                placeholderTextColor={colors.textDim}
                selectionColor={colors.accent}
              />
              <TextInput
                style={styles.input}
                value={phone}
                onChangeText={setPhone}
                placeholder="Phone Number (India, e.g. 9XXXXXXXXX)"
                placeholderTextColor={colors.textDim}
                selectionColor={colors.accent}
                keyboardType="phone-pad"
              />
            </>
          ) : null}
          <TextInput
            style={styles.input}
            value={email}
            onChangeText={setEmail}
            placeholder="Email"
            placeholderTextColor={colors.textDim}
            selectionColor={colors.accent}
            autoCapitalize="none"
            keyboardType="email-address"
          />
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            placeholder="Password"
            placeholderTextColor={colors.textDim}
            selectionColor={colors.accent}
            secureTextEntry
          />

          {error ? <Text style={styles.errorText}>{error}</Text> : null}

          <TouchableOpacity style={styles.button} onPress={onSubmit} disabled={loading}>
            {loading ? (
              <ActivityIndicator color={colors.text} />
            ) : (
              <Text style={styles.buttonText}>{mode === 'signup' ? 'Create Account' : 'Access Console'}</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={() => {
              setMode(mode === 'signup' ? 'signin' : 'signup');
              setError('');
            }}
          >
            <Text style={styles.secondaryText}>
              {mode === 'signup' ? 'Already have an account? Sign in' : 'No account yet? Create one'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  background: {
    flex: 1,
  },
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
  },
  title: {
    color: colors.text,
    fontFamily: fonts.heading,
    fontSize: 30,
    letterSpacing: 1.2,
    marginBottom: 6,
  },
  subtitle: {
    color: colors.textMuted,
    marginBottom: 26,
    fontSize: 16,
    fontFamily: fonts.body,
  },
  formCard: {
    backgroundColor: 'rgba(16, 24, 42, 0.92)',
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    ...shadows.card,
  },
  formTitle: {
    fontSize: 18,
    fontFamily: fonts.bodyStrong,
    color: colors.text,
    marginBottom: 12,
  },
  input: {
    backgroundColor: '#0A1324',
    borderWidth: 1,
    borderColor: '#2A3C5E',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 12,
    fontFamily: fonts.body,
    fontSize: 17,
    color: colors.text,
  },
  button: {
    backgroundColor: '#1170FF',
    borderRadius: 10,
    alignItems: 'center',
    paddingVertical: 14,
    marginTop: 8,
  },
  buttonText: {
    color: colors.text,
    fontFamily: fonts.bodyStrong,
    fontSize: 18,
    letterSpacing: 0.5,
  },
  secondaryButton: {
    marginTop: 12,
    alignItems: 'center',
  },
  secondaryText: {
    color: '#8FD9FF',
    fontFamily: fonts.body,
    fontSize: 14,
  },
  errorText: {
    color: '#FF90AE',
    marginBottom: 8,
    fontFamily: fonts.body,
    fontSize: 14,
  },
});
