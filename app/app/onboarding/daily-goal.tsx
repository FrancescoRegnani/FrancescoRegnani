import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { Screen, Title, Body, Heading, Button } from '../../components/ui';
import { useAuth } from '../../lib/auth-context';
import { updateUserProfile } from '../../lib/queries';
import { colors, spacing, radius } from '../../constants/theme';

const OPTIONS = [5, 10, 20, 30, 45, 60];

export default function DailyGoal() {
  const { session, refreshProfile } = useAuth();
  const [selected, setSelected] = useState<number>(20);
  const [saving, setSaving] = useState(false);

  async function handleContinue() {
    if (!session) return;
    setSaving(true);
    try {
      await updateUserProfile(session.user.id, { daily_minutes: selected });
      await refreshProfile();
      router.replace('/');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Screen>
      <Title>Quanto vuoi dedicare ogni giorno?</Title>
      <Body style={{ color: colors.textSecondary, marginTop: spacing.xs }}>
        Puoi cambiarlo in ogni momento dal tuo profilo.
      </Body>
      <View style={styles.grid}>
        {OPTIONS.map((minutes) => (
          <Pressable
            key={minutes}
            onPress={() => setSelected(minutes)}
            style={[styles.option, selected === minutes && styles.optionSelected]}
          >
            <Heading>{minutes}</Heading>
            <Body style={{ color: colors.textSecondary }}>min</Body>
          </Pressable>
        ))}
      </View>
      <Button title="Inizia a studiare" onPress={handleContinue} loading={saving} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  grid: {
    flex: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginTop: spacing.xl,
    alignContent: 'flex-start',
  },
  option: {
    width: '30%',
    aspectRatio: 1,
    borderRadius: radius.lg,
    borderWidth: 2,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  optionSelected: {
    borderColor: colors.success,
    backgroundColor: '#EAF7EF',
  },
});
