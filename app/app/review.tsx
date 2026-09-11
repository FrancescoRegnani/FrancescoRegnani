import { useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Screen, Title, Body, Heading } from '../components/ui';
import { useAuth } from '../lib/auth-context';
import { fetchDueLessonIds, fetchLesson } from '../lib/queries';
import { colors, spacing, radius } from '../constants/theme';
import type { Lesson } from '../lib/types';

export default function ReviewScreen() {
  const { session } = useAuth();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!session) {
      setLoading(false);
      return;
    }
    (async () => {
      const ids = await fetchDueLessonIds(session.user.id);
      const fetched = await Promise.all(ids.map((lessonId) => fetchLesson(lessonId)));
      setLessons(fetched.filter((l): l is Lesson => l !== null));
      setLoading(false);
    })();
  }, [session]);

  return (
    <Screen>
      <Pressable onPress={() => router.back()} style={{ marginBottom: spacing.md }}>
        <Ionicons name="chevron-back" size={24} color={colors.textPrimary} />
      </Pressable>
      <Title>Da ripassare</Title>
      {loading ? (
        <ActivityIndicator style={{ marginTop: spacing.xl }} color={colors.success} />
      ) : lessons.length === 0 ? (
        <Body style={{ marginTop: spacing.lg, color: colors.textSecondary }}>
          Nessun ripasso in scadenza oggi.
        </Body>
      ) : (
        <FlatList
          data={lessons}
          keyExtractor={(item) => item.id}
          contentContainerStyle={{ gap: spacing.md, marginTop: spacing.lg }}
          renderItem={({ item }) => (
            <Pressable
              style={styles.card}
              onPress={() => router.push({ pathname: '/lesson/[id]', params: { id: item.id } })}
            >
              <View style={{ flex: 1 }}>
                <Heading>{item.title}</Heading>
              </View>
              <Ionicons name="chevron-forward" size={20} color={colors.textSecondary} />
            </Pressable>
          )}
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.lg,
  },
});
