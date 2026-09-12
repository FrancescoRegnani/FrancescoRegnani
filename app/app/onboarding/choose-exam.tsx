import { useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { Screen, Title, Body, Heading, Caption } from '../../components/ui';
import { useAuth } from '../../lib/auth-context';
import { useAccent } from '../../lib/accent-context';
import { fetchExams, updateUserProfile } from '../../lib/queries';
import { examColors, defaultExamColor, colors, spacing, radius } from '../../constants/theme';
import { SUPPORTED_EXAM_NAME } from '../../lib/types';
import type { Exam } from '../../lib/types';

export default function ChooseExam() {
  const { session, refreshProfile } = useAuth();
  const { accent } = useAccent();
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);

  useEffect(() => {
    fetchExams()
      .then(setExams)
      .finally(() => setLoading(false));
  }, []);

  async function selectExam(exam: Exam) {
    if (!session || exam.name !== SUPPORTED_EXAM_NAME) return;
    setSavingId(exam.id);
    try {
      await updateUserProfile(session.user.id, { selected_exam: exam.id });
      await refreshProfile();
      router.push('/onboarding/exam-date');
    } finally {
      setSavingId(null);
    }
  }

  return (
    <Screen>
      <Title>Quale esame devi sostenere?</Title>
      <Body style={{ color: colors.textSecondary, marginTop: spacing.xs }}>
        Scegli il tuo percorso. Potrai aggiungerne altri più avanti.
      </Body>
      {loading ? (
        <ActivityIndicator style={{ marginTop: spacing.xl }} color={accent.primary} />
      ) : (
        <FlatList
          data={exams}
          keyExtractor={(item) => item.id}
          contentContainerStyle={{ gap: spacing.md, marginTop: spacing.lg }}
          renderItem={({ item }) => {
            const isSupported = item.name === SUPPORTED_EXAM_NAME;
            const palette = examColors[item.name] ?? defaultExamColor;
            return (
              <Pressable
                onPress={() => selectExam(item)}
                disabled={!isSupported || savingId !== null}
                style={[styles.card, !isSupported && styles.cardDisabled, { borderColor: palette.primary }]}
              >
                <View style={{ flex: 1 }}>
                  <Heading>{item.name}</Heading>
                  {item.description && <Caption style={{ marginTop: spacing.xs }}>{item.description}</Caption>}
                </View>
                {!isSupported && <Caption style={{ color: colors.locked }}>Prossimamente</Caption>}
                {savingId === item.id && <ActivityIndicator color={palette.primary} />}
              </Pressable>
            );
          }}
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.surface,
    borderWidth: 2,
    borderRadius: radius.lg,
    padding: spacing.lg,
  },
  cardDisabled: {
    opacity: 0.5,
  },
});
