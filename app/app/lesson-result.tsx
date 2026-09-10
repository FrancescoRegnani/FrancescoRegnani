import { View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Screen, Title, Heading, Body, Card, Button } from '../components/ui';
import { colors, spacing } from '../constants/theme';

function formatTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

export default function LessonResult() {
  const { xp, accuracy, mastery, time } = useLocalSearchParams<{
    xp: string;
    accuracy: string;
    mastery: string;
    time: string;
  }>();

  const xpNumber = Number(xp ?? 0);
  const accuracyPercent = Math.round(Number(accuracy ?? 0) * 100);
  const masteryValue = Math.round(Number(mastery ?? 0));
  const timeSeconds = Number(time ?? 0);

  return (
    <Screen>
      <View style={{ flex: 1, justifyContent: 'center', gap: spacing.lg }}>
        <Title>Lezione completata</Title>
        <Card>
          <Row label="⚡ XP guadagnati" value={`+${xpNumber}`} />
          <Row label="🎯 Accuratezza" value={`${accuracyPercent}%`} />
          <Row label="⏱ Tempo" value={formatTime(timeSeconds)} />
          <Row label="🧠 Mastery" value={`${masteryValue}%`} last />
        </Card>
      </View>
      <Button title="Continua" onPress={() => router.replace('/(tabs)/home')} />
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
