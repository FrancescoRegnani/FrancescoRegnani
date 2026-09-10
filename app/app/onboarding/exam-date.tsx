import { useState } from 'react';
import { Platform, View } from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { router } from 'expo-router';
import { Screen, Title, Body, Button } from '../../components/ui';
import { useAuth } from '../../lib/auth-context';
import { updateUserProfile } from '../../lib/queries';
import { colors, spacing } from '../../constants/theme';
import { toDateOnlyISO } from '../../lib/learning';

const MIN_DATE = new Date();
const MAX_DATE = new Date();
MAX_DATE.setFullYear(MAX_DATE.getFullYear() + 5);

export default function ExamDate() {
  const { session } = useAuth();
  const [date, setDate] = useState<Date>(() => {
    const d = new Date();
    d.setMonth(d.getMonth() + 6);
    return d;
  });
  const [saving, setSaving] = useState(false);

  async function handleContinue() {
    if (!session) return;
    setSaving(true);
    try {
      await updateUserProfile(session.user.id, { exam_date: toDateOnlyISO(date) });
      router.push('/onboarding/daily-goal');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Screen>
      <Title>Quando vuoi sostenere l’esame?</Title>
      <Body style={{ color: colors.textSecondary, marginTop: spacing.xs }}>
        Useremo questa data per calibrare il tuo piano di studio.
      </Body>
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <DateTimePicker
          value={date}
          mode="date"
          minimumDate={MIN_DATE}
          maximumDate={MAX_DATE}
          display={Platform.OS === 'ios' ? 'inline' : 'default'}
          onChange={(_, selected) => selected && setDate(selected)}
        />
      </View>
      <Button title="Continua" onPress={handleContinue} loading={saving} />
    </Screen>
  );
}
