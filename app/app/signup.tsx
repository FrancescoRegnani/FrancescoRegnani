import { useState } from 'react';
import { TextInput, View, StyleSheet } from 'react-native';
import { router, Link } from 'expo-router';
import { Screen, Title, Body, Caption, Button } from '../components/ui';
import { useAuth } from '../lib/auth-context';
import { colors, spacing, radius } from '../constants/theme';

export default function Signup() {
  const { signUp } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmMessage, setConfirmMessage] = useState<string | null>(null);

  async function handleSignup() {
    setError(null);
    if (!name.trim() || !email.trim() || password.length < 6) {
      setError('Inserisci nome, email e una password di almeno 6 caratteri.');
      return;
    }
    setLoading(true);
    try {
      const { needsEmailConfirmation } = await signUp(email.trim(), password, name.trim());
      if (needsEmailConfirmation) {
        setConfirmMessage('Controlla la tua email per confermare l’account, poi accedi.');
      } else {
        router.replace('/');
      }
    } catch (e: any) {
      setError(e?.message ?? 'Registrazione non riuscita.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen>
      <Title>Crea il tuo account</Title>
      <View style={{ marginTop: spacing.lg, gap: spacing.md }}>
        <TextInput
          style={styles.input}
          placeholder="Nome"
          placeholderTextColor={colors.textSecondary}
          value={name}
          onChangeText={setName}
          autoCapitalize="words"
        />
        <TextInput
          style={styles.input}
          placeholder="Email"
          placeholderTextColor={colors.textSecondary}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
        />
        <TextInput
          style={styles.input}
          placeholder="Password"
          placeholderTextColor={colors.textSecondary}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />
        {error && <Caption style={{ color: colors.danger }}>{error}</Caption>}
        {confirmMessage && <Caption style={{ color: colors.success }}>{confirmMessage}</Caption>}
        <Button title="Registrati" onPress={handleSignup} loading={loading} />
        <Link href="/login" asChild>
          <Button title="Hai già un account? Accedi" variant="ghost" />
        </Link>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    fontSize: 16,
    color: colors.textPrimary,
  },
});
