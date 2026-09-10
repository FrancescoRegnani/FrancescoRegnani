import { ActivityIndicator, View } from 'react-native';
import { Redirect } from 'expo-router';
import { useAuth } from '../lib/auth-context';
import { colors } from '../constants/theme';

export default function Index() {
  const { session, profile, loading } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.background }}>
        <ActivityIndicator size="large" color={colors.success} />
      </View>
    );
  }

  if (!session) return <Redirect href="/welcome" />;
  if (!profile?.selected_exam) return <Redirect href="/onboarding/choose-exam" />;
  return <Redirect href="/(tabs)/home" />;
}
