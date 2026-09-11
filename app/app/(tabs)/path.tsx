import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Screen, Title, Heading, Body, Caption } from '../../components/ui';
import { useAuth } from '../../lib/auth-context';
import {
  fetchExams,
  fetchLessonsForUnit,
  fetchProgressForUser,
  fetchSubjectsForExam,
  fetchUnitsForSubject,
} from '../../lib/queries';
import { colors, examColors, defaultExamColor, spacing, radius } from '../../constants/theme';
import type { Lesson, Subject, Unit, UserProgress } from '../../lib/types';

interface UnitBlock {
  unit: Unit;
  lessons: Lesson[];
}

interface SubjectBlock {
  subject: Subject;
  units: UnitBlock[];
}

export default function Path() {
  const { session, profile } = useAuth();
  const [blocks, setBlocks] = useState<SubjectBlock[]>([]);
  const [progress, setProgress] = useState<Record<string, UserProgress>>({});
  const [loading, setLoading] = useState(true);
  const [examName, setExamName] = useState('');

  const load = useCallback(async () => {
    if (!session || !profile?.selected_exam) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const exams = await fetchExams();
      const exam = exams.find((e) => e.id === profile.selected_exam);
      setExamName(exam?.name ?? '');
      const subjects = await fetchSubjectsForExam(profile.selected_exam);
      const subjectBlocks: SubjectBlock[] = [];
      for (const subject of subjects) {
        const units = await fetchUnitsForSubject(subject.id);
        const unitBlocks: UnitBlock[] = [];
        for (const unit of units) {
          const lessons = await fetchLessonsForUnit(unit.id);
          unitBlocks.push({ unit, lessons });
        }
        subjectBlocks.push({ subject, units: unitBlocks });
      }
      setBlocks(subjectBlocks);
      setProgress(await fetchProgressForUser(session.user.id));
    } finally {
      setLoading(false);
    }
  }, [session, profile?.selected_exam]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  if (loading) {
    return (
      <Screen style={{ alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator size="large" color={colors.success} />
      </Screen>
    );
  }

  const palette = examColors[examName] ?? defaultExamColor;

  return (
    <Screen>
      <Title>Il tuo percorso</Title>
      <ScrollView contentContainerStyle={{ gap: spacing.lg, paddingTop: spacing.md }} showsVerticalScrollIndicator={false}>
        {blocks.map(({ subject, units }) => (
          <View key={subject.id} style={{ gap: spacing.md }}>
            <Heading>{subject.name}</Heading>
            {units.map(({ unit, lessons }) => {
              let unlocked = true;
              return (
                <View key={unit.id} style={{ gap: spacing.sm }}>
                  <Caption>{unit.title}</Caption>
                  {lessons.map((lesson, index) => {
                    const lessonProgress = progress[lesson.id];
                    const isCompleted = !!lessonProgress?.completed;
                    const isUnlocked = unlocked;
                    if (!isCompleted) unlocked = false;

                    return (
                      <Pressable
                        key={lesson.id}
                        disabled={!isUnlocked}
                        onPress={() => router.push({ pathname: '/lesson/[id]', params: { id: lesson.id } })}
                        style={[
                          styles.node,
                          { borderColor: isUnlocked ? palette.primary : colors.locked },
                          isCompleted && { backgroundColor: '#EAF7EF' },
                        ]}
                      >
                        <Ionicons
                          name={lesson.is_checkpoint ? 'trophy' : isCompleted ? 'checkmark-circle' : 'ellipse-outline'}
                          size={22}
                          color={isUnlocked ? palette.primary : colors.locked}
                        />
                        <View style={{ flex: 1 }}>
                          <Body style={!isUnlocked ? { color: colors.locked } : undefined}>
                            {index + 1}. {lesson.title}
                          </Body>
                        </View>
                        {!isUnlocked && <Ionicons name="lock-closed" size={16} color={colors.locked} />}
                      </Pressable>
                    );
                  })}
                </View>
              );
            })}
          </View>
        ))}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  node: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    backgroundColor: colors.surface,
    borderWidth: 2,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
});
