import { useCallback, useState } from 'react';
import { ActivityIndicator, ScrollView, View } from 'react-native';
import { Link, router, useFocusEffect } from 'expo-router';
import { Screen, Title, Body, Heading, Caption, Eyebrow, Card, ProgressBar, Button, IconChip } from '../../components/ui';
import { useAuth } from '../../lib/auth-context';
import { useAccent } from '../../lib/accent-context';
import {
  computeUnitReadiness,
  fetchDueLessonIds,
  fetchErrorSummary,
  fetchExams,
  fetchMinutesStudiedToday,
  fetchNextLesson,
  type NextLessonInfo,
} from '../../lib/queries';
import { colors, spacing } from '../../constants/theme';
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
  const { accent } = useAccent();
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
        <ActivityIndicator size="large" color={accent.primary} />
      </Screen>
    );
  }

  const dailyGoal = profile.daily_minutes || 1;
  const goalRatio = data.minutesToday / dailyGoal;
  const daysToExam = daysUntil(profile.exam_date, toDateOnlyISO(new Date()));

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ gap: spacing.md }} showsVerticalScrollIndicator={false}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.xs }}>
            <IconChip name="flame" size={28} color="#E0781F" background="#FDECD8" />
            <Caption>{profile.current_streak} giorni</Caption>
          </View>
          <Caption>{data.examName}</Caption>
        </View>
        <Title>Ciao {profile.name || ''}</Title>

        <Card>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <View>
              <Eyebrow>Obiettivo di oggi</Eyebrow>
              <Heading style={{ marginTop: spacing.xs }}>
                {data.minutesToday} / {dailyGoal} minuti
              </Heading>
            </View>
            <IconChip name="time" />
          </View>
          <View style={{ marginTop: spacing.md }}>
            <ProgressBar ratio={goalRatio} />
          </View>
        </Card>

        {data.next ? (
          <Card tinted>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md }}>
              <IconChip name="play" background={colors.surface} />
              <View style={{ flex: 1 }}>
                <Eyebrow>Continua il percorso</Eyebrow>
                <Heading style={{ marginTop: spacing.xs }}>{data.next.unit.title}</Heading>
                <Body style={{ color: colors.textSecondary }}>{data.next.lesson.title}</Body>
              </View>
            </View>
            <View style={{ marginTop: spacing.md }}>
              <Button
                title="Continua"
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
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md }}>
              <IconChip name="refresh" />
              <Heading style={{ flex: 1 }}>{data.dueCount} concetti da ripassare</Heading>
            </View>
            <View style={{ marginTop: spacing.md }}>
              <Link href="/review" asChild>
                <Button title="Ripassa" variant="secondary" />
              </Link>
            </View>
          </Card>
        )}

        {data.errorCount > 0 && (
          <Card>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md }}>
              <IconChip name="alert-circle" color={colors.danger} background="#FBE6E2" />
              <View style={{ flex: 1 }}>
                <Heading>I tuoi errori</Heading>
                <Body style={{ color: colors.textSecondary }}>{data.errorCount} domande da rivedere</Body>
              </View>
            </View>
            <View style={{ marginTop: spacing.md }}>
              <Link href="/errors" asChild>
                <Button title="Ripara errori" variant="secondary" />
              </Link>
            </View>
          </Card>
        )}

        <View style={{ flexDirection: 'row', gap: spacing.md }}>
          <Card style={{ flex: 1 }}>
            <IconChip name="flash" />
            <Eyebrow style={{ marginTop: spacing.sm }}>XP</Eyebrow>
            <Heading>{profile.xp}</Heading>
          </Card>
          <Card style={{ flex: 1 }}>
            <IconChip name="speedometer" />
            <Eyebrow style={{ marginTop: spacing.sm }}>Readiness</Eyebrow>
            <Heading>{data.readiness}%</Heading>
          </Card>
        </View>

        {daysToExam !== null && (
          <Card>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md }}>
              <IconChip name="calendar" />
              <View>
                <Eyebrow>Esame tra</Eyebrow>
                <Heading style={{ marginTop: spacing.xs }}>
                  {daysToExam >= 0 ? `${daysToExam} giorni` : 'Data superata'}
                </Heading>
              </View>
            </View>
          </Card>
        )}
      </ScrollView>
    </Screen>
  );
}
