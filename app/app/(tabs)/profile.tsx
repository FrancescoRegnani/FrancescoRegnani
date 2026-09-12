import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Screen, Title, Body, Heading, Caption, Eyebrow, Card, Button } from '../../components/ui';
import { useAuth } from '../../lib/auth-context';
import { useAccent } from '../../lib/accent-context';
import { colors, spacing, ACCENT_PALETTE } from '../../constants/theme';
import { daysUntil, toDateOnlyISO } from '../../lib/learning';

export default function Profile() {
  const { profile, signOut } = useAuth();
  const { accent, setAccentKey } = useAccent();
  const [signingOut, setSigningOut] = useState(false);

  if (!profile) return null;

  const daysToExam = daysUntil(profile.exam_date, toDateOnlyISO(new Date()));

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await signOut();
      router.replace('/welcome');
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <Screen>
      <Title>Profilo</Title>
      <ScrollView contentContainerStyle={{ marginTop: spacing.lg, gap: spacing.md }} showsVerticalScrollIndicator={false}>
        <Card>
          <Heading>{profile.name}</Heading>
          <Caption>{profile.email}</Caption>
        </Card>
        <Card>
          <Row label="Data esame" value={profile.exam_date ?? '—'} />
          <Row label="Giorni rimanenti" value={daysToExam !== null ? `${daysToExam}` : '—'} />
          <Row label="Obiettivo giornaliero" value={`${profile.daily_minutes} min`} last />
        </Card>
        <Card>
          <Row label="XP totali" value={`${profile.xp}`} />
          <Row label="Streak" value={`${profile.current_streak} giorni`} last />
        </Card>

        <Card>
          <Eyebrow>Aspetto</Eyebrow>
          <Body style={{ color: colors.textSecondary, marginTop: spacing.xs }}>
            Scegli il colore dell'app.
          </Body>
          <View style={styles.swatchRow}>
            {ACCENT_PALETTE.map((option) => {
              const isSelected = option.key === accent.key;
              return (
                <Pressable
                  key={option.key}
                  accessibilityLabel={option.name}
                  onPress={() => setAccentKey(option.key)}
                  style={styles.swatchTouchTarget}
                >
                  <View style={[styles.swatch, { backgroundColor: option.primary }, isSelected && styles.swatchSelected]}>
                    {isSelected && <Ionicons name="checkmark" size={20} color={colors.textInverse} />}
                  </View>
                </Pressable>
              );
            })}
          </View>
          <Caption style={{ marginTop: spacing.sm, textAlign: 'center' }}>{accent.name}</Caption>
        </Card>

        <Button title="Esci" variant="secondary" color={colors.danger} onPress={handleSignOut} loading={signingOut} />
      </ScrollView>
    </Screen>
  );
}

function Row({ label, value, last }: { label: string; value: string; last?: boolean }) {
  return (
    <View
      style={{
        flexDirection: 'row',
        justifyContent: 'space-between',
        paddingVertical: spacing.sm,
        borderBottomWidth: last ? 0 : 1,
        borderBottomColor: colors.border,
      }}
    >
      <Body>{label}</Body>
      <Heading>{value}</Heading>
    </View>
  );
}

const styles = StyleSheet.create({
  swatchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.md,
  },
  swatchTouchTarget: {
    padding: spacing.xs,
  },
  swatch: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  swatchSelected: {
    borderWidth: 2,
    borderColor: colors.textPrimary,
  },
});
