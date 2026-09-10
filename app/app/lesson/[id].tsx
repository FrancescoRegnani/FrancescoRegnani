import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Screen, Title, Body, Heading, Caption, Button, ProgressBar } from '../../components/ui';
import { useAuth } from '../../lib/auth-context';
import {
  completeLessonSession,
  fetchLesson,
  fetchProgressForLesson,
  fetchQuestionsForLesson,
  type QuizAnswerResult,
} from '../../lib/queries';
import { colors, spacing, radius } from '../../constants/theme';
import type { Lesson, Question } from '../../lib/types';

type Stage = 'loading' | 'intro' | 'quiz' | 'submitting';

export default function LessonScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { session, profile, refreshProfile } = useAuth();
  const [stage, setStage] = useState<Stage>('loading');
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [answers, setAnswers] = useState<QuizAnswerResult[]>([]);
  const questionStartedAt = useRef<number>(Date.now());

  useEffect(() => {
    if (!id) return;
    (async () => {
      const [l, q] = await Promise.all([fetchLesson(id), fetchQuestionsForLesson(id)]);
      setLesson(l);
      setQuestions(q);
      setStage('intro');
    })();
  }, [id]);

  useEffect(() => {
    questionStartedAt.current = Date.now();
  }, [index]);

  if (stage === 'loading' || !lesson) {
    return (
      <Screen style={{ alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator size="large" color={colors.success} />
      </Screen>
    );
  }

  if (stage === 'intro') {
    return (
      <Screen>
        <Title>{lesson.title}</Title>
        <View style={{ marginTop: spacing.lg }}>
          <Body>{lesson.explanation}</Body>
        </View>
        <View style={{ flex: 1 }} />
        <Button
          title="Continua"
          onPress={() => (questions.length > 0 ? setStage('quiz') : finishLesson([]))}
        />
      </Screen>
    );
  }

  const question = questions[index];
  const options: { key: string; text: string }[] = [
    { key: 'A', text: question.answer_a ?? '' },
    { key: 'B', text: question.answer_b ?? '' },
    { key: 'C', text: question.answer_c ?? '' },
    { key: 'D', text: question.answer_d ?? '' },
  ].filter((o) => o.text.length > 0);

  const isCorrect = selected === question.correct_answer;

  function selectAnswer(key: string) {
    if (selected) return;
    setSelected(key);
    const responseTimeSeconds = (Date.now() - questionStartedAt.current) / 1000;
    setAnswers((prev) => [...prev, { questionId: question.id, correct: key === question.correct_answer, responseTimeSeconds }]);
  }

  function next() {
    if (index + 1 < questions.length) {
      setSelected(null);
      setIndex(index + 1);
    } else {
      finishLesson(answers);
    }
  }

  async function finishLesson(finalAnswers: QuizAnswerResult[]) {
    if (!session || !profile || !lesson) return;
    setStage('submitting');
    const previousProgress = await fetchProgressForLesson(session.user.id, lesson.id);
    const summary = await completeLessonSession({
      userId: session.user.id,
      lessonId: lesson.id,
      answers: finalAnswers,
      previousProgress,
      profile,
    });
    await refreshProfile();
    router.replace({
      pathname: '/lesson-result',
      params: {
        xp: String(summary.xpEarned),
        accuracy: String(summary.accuracy),
        mastery: String(summary.mastery),
        time: String(Math.round(summary.totalTimeSeconds)),
      },
    });
  }

  if (stage === 'submitting') {
    return (
      <Screen style={{ alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator size="large" color={colors.success} />
      </Screen>
    );
  }

  return (
    <Screen>
      <ProgressBar ratio={(index + (selected ? 1 : 0)) / questions.length} />
      <View style={{ marginTop: spacing.lg }}>
        <Heading>{question.question}</Heading>
      </View>
      <View style={{ marginTop: spacing.lg, gap: spacing.md }}>
        {options.map((option) => {
          const isSelected = selected === option.key;
          const showCorrect = selected !== null && option.key === question.correct_answer;
          const showWrong = isSelected && !isCorrect;
          return (
            <Pressable
              key={option.key}
              onPress={() => selectAnswer(option.key)}
              disabled={selected !== null}
              style={[
                styles.option,
                showCorrect && styles.optionCorrect,
                showWrong && styles.optionWrong,
              ]}
            >
              <Body>{option.text}</Body>
            </Pressable>
          );
        })}
      </View>

      {selected && (
        <View style={{ marginTop: spacing.lg }}>
          <Caption style={{ color: isCorrect ? colors.success : colors.danger }}>
            {isCorrect ? '✅ Corretto!' : `❌ Non proprio. Risposta corretta: ${question.correct_answer}.`}
          </Caption>
          {question.explanation && <Body style={{ marginTop: spacing.xs }}>{question.explanation}</Body>}
        </View>
      )}

      <View style={{ flex: 1 }} />
      {selected && <Button title="Continua" onPress={next} />}
    </Screen>
  );
}

const styles = StyleSheet.create({
  option: {
    borderWidth: 2,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    backgroundColor: colors.surface,
  },
  optionCorrect: {
    borderColor: colors.success,
    backgroundColor: '#EAF7EF',
  },
  optionWrong: {
    borderColor: colors.danger,
    backgroundColor: '#FBEAEA',
  },
});
