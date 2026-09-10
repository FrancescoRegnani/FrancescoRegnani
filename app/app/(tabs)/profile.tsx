import { useState } from 'react';
import { View } from 'react-native';
import { router } from 'expo-router';
import { Screen, Title, Body, Heading, Caption, Card, Button } from '../../components/ui';
import { useAuth } from '../../lib/auth-context';
import { colors, spacing } from '../../constants/theme';
import { daysUntil, toDateOnlyISO } from '../../lib/learning';

export default function Profile() {
  const { profile, signOut } = useAuth();
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
      <View style={{ marginTop: spacing.lg, gap: spacing.md }}>
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
        <Button title="Esci" variant="secondary" color={colors.danger} onPress={handleSignOut} loading={signingOut} />
      </View>
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
