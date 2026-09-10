import { View } from 'react-native';
import { Link } from 'expo-router';
import { Screen, Title, Body, Button } from '../components/ui';
import { colors, spacing } from '../constants/theme';

export default function Welcome() {
  return (
    <Screen style={{ justifyContent: 'flex-end' }}>
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: spacing.md }}>
        <Title>ProExam</Title>
        <Body style={{ textAlign: 'center', color: colors.textSecondary }}>
          Preparati. Un giorno alla volta.
        </Body>
      </View>
      <View style={{ gap: spacing.md, paddingBottom: spacing.lg }}>
        <Link href="/signup" asChild>
          <Button title="Registrati" />
        </Link>
        <Link href="/login" asChild>
          <Button title="Accedi" variant="secondary" />
        </Link>
      </View>
    </Screen>
  );
}
