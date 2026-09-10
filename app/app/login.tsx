import { useState } from 'react';
import { TextInput, View, StyleSheet } from 'react-native';
import { router, Link } from 'expo-router';
import { Screen, Title, Caption, Button } from '../components/ui';
import { useAuth } from '../lib/auth-context';
import { colors, spacing, radius } from '../constants/theme';

export default function Login() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin() {
    setError(null);
    setLoading(true);
    try {
      await signIn(email.trim(), password);
      router.replace('/');
    } catch (e: any) {
      setError(e?.message ?? 'Accesso non riuscito.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen>
      <Title>Bentornato</Title>
      <View style={{ marginTop: spacing.lg, gap: spacing.md }}>
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
        <Button title="Accedi" onPress={handleLogin} loading={loading} />
        <Link href="/signup" asChild>
          <Button title="Non hai un account? Registrati" variant="ghost" />
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
