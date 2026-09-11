import { useCallback, useState } from 'react';
import { ActivityIndicator, ScrollView, View } from 'react-native';
import { Link, router, useFocusEffect } from 'expo-router';
import { Screen, Title, Body, Heading, Caption, Card, ProgressBar, Button } from '../../components/ui';
import { useAuth } from '../../lib/auth-context';
import {
  computeUnitReadiness,
  fetchDueLessonIds,
  fetchErrorSummary,
  fetchExams,
  fetchMinutesStudiedToday,
  fetchNextLesson,
  type NextLessonInfo,
} from '../../lib/queries';
import { colors, examColors, defaultExamColor, spacing } from '../../constants/theme';
import { daysUntil, toDateOnlyISO } from '../../lib/learning';

interface HomeData {
  examName: string;
  minutesToday: number;
  next: NextLessonInfo | null;
  readiness: number;
  dueCount: number;
  errorCount: number;
}

export default function Home() {
  const { session, profile } = useAuth();
  const [data, setData] = useState<HomeData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!session || !profile?.selected_exam) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [exams, minutesToday, next, dueIds, errors] = await Promise.all([
        fetchExams(),
        fetchMinutesStudiedToday(session.user.id),
        fetchNextLesson(session.user.id, profile.selected_exam),
        fetchDueLessonIds(session.user.id),
        fetchErrorSummary(session.user.id),
      ]);
      const exam = exams.find((e) => e.id === profile.selected_exam);
      const readiness = next ? await computeUnitReadiness(session.user.id, next.unit.id) : 0;
      setData({
        examName: exam?.name ?? '',
        minutesToday,
        next,
        readiness,
        dueCount: dueIds.length,
        errorCount: errors.reduce((sum, e) => sum + e.count, 0),
      });
    } finally {
      setLoading(false);
    }
  }, [session, profile?.selected_exam]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  if (loading || !data || !profile) {
    return (
      <Screen style={{ alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator size="large" color={colors.success} />
      </Screen>
    );
  }

  const palette = examColors[data.examName] ?? defaultExamColor;
  const dailyGoal = profile.daily_minutes || 1;
  const goalRatio = data.minutesToday / dailyGoal;
  const daysToExam = daysUntil(profile.exam_date, toDateOnlyISO(new Date()));

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ gap: spacing.md }} showsVerticalScrollIndicator={false}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <Caption>🔥 {profile.current_streak} giorni</Caption>
          <Caption>{data.examName}</Caption>
        </View>
        <Title>Ciao {profile.name || ''}</Title>

        <Card>
          <Body>Obiettivo di oggi</Body>
          <Heading>
            {data.minutesToday} / {dailyGoal} minuti
          </Heading>
          <View style={{ marginTop: spacing.sm }}>
            <ProgressBar ratio={goalRatio} color={palette.primary} />
          </View>
        </Card>

        {data.next ? (
          <Card>
            <Caption>Continua il percorso</Caption>
            <Heading style={{ marginTop: spacing.xs }}>{data.next.unit.title}</Heading>
            <Body style={{ color: colors.textSecondary }}>{data.next.lesson.title}</Body>
            <View style={{ marginTop: spacing.md }}>
              <Button
                title="Continua"
                color={palette.primary}
                onPress={() => router.push({ pathname: '/lesson/[id]', params: { id: data.next!.lesson.id } })}
              />
            </View>
          </Card>
        ) : (
          <Card>
            <Heading>Percorso completato 🎉</Heading>
            <Body style={{ color: colors.textSecondary }}>Hai finito tutte le lezioni disponibili per ora.</Body>
          </Card>
        )}

        {data.dueCount > 0 && (
          <Card>
            <Heading>{data.dueCount} concetti da ripassare</Heading>
            <View style={{ marginTop: spacing.md }}>
              <Link href="/review" asChild>
                <Button title="Ripassa" variant="secondary" color={palette.primary} />
              </Link>
            </View>
          </Card>
        )}

        {data.errorCount > 0 && (
          <Card>
            <Heading>I tuoi errori</Heading>
            <Body style={{ color: colors.textSecondary }}>{data.errorCount} domande da rivedere</Body>
            <View style={{ marginTop: spacing.md }}>
              <Link href="/errors" asChild>
                <Button title="Ripara errori" variant="secondary" color={palette.primary} />
              </Link>
            </View>
          </Card>
        )}

        <View style={{ flexDirection: 'row', gap: spacing.md }}>
          <Card style={{ flex: 1 }}>
            <Caption>XP</Caption>
            <Heading>{profile.xp}</Heading>
          </Card>
          <Card style={{ flex: 1 }}>
            <Caption>Readiness</Caption>
            <Heading>{data.readiness}%</Heading>
          </Card>
        </View>

        {daysToExam !== null && (
          <Card>
            <Caption>Esame tra</Caption>
            <Heading>{daysToExam >= 0 ? `${daysToExam} giorni` : 'Data superata'}</Heading>
          </Card>
        )}
      </ScrollView>
    </Screen>
  );
}
