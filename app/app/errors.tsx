import { useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Screen, Title, Body, Heading } from '../components/ui';
import { useAuth } from '../lib/auth-context';
import { fetchErrorSummary, type ErrorSummaryItem } from '../lib/queries';
import { colors, spacing, radius } from '../constants/theme';

export default function ErrorsScreen() {
  const { session } = useAuth();
  const [items, setItems] = useState<ErrorSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!session) {
      setLoading(false);
      return;
    }
    fetchErrorSummary(session.user.id)
      .then(setItems)
      .finally(() => setLoading(false));
  }, [session]);

  return (
    <Screen>
      <Pressable onPress={() => router.back()} style={{ marginBottom: spacing.md }}>
        <Ionicons name="chevron-back" size={24} color={colors.textPrimary} />
      </Pressable>
      <Title>I tuoi errori</Title>
      {loading ? (
        <ActivityIndicator style={{ marginTop: spacing.xl }} color={colors.success} />
      ) : items.length === 0 ? (
        <Body style={{ marginTop: spacing.lg, color: colors.textSecondary }}>
          Nessun errore da ripassare. Ottimo lavoro!
        </Body>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.lessonId}
          contentContainerStyle={{ gap: spacing.md, marginTop: spacing.lg }}
          renderItem={({ item }) => (
            <Pressable
              style={styles.card}
              onPress={() => router.push({ pathname: '/lesson/[id]', params: { id: item.lessonId } })}
            >
              <View style={{ flex: 1 }}>
                <Heading>{item.lessonTitle}</Heading>
                <Body style={{ color: colors.textSecondary }}>{item.count} errori</Body>
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
