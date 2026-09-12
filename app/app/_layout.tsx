import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AuthProvider } from '../lib/auth-context';
import { AccentProvider } from '../lib/accent-context';

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AccentProvider>
        <AuthProvider>
          <StatusBar style="dark" />
          <Stack screenOptions={{ headerShown: false }}>
            <Stack.Screen name="lesson-result" options={{ presentation: 'modal', gestureEnabled: false }} />
          </Stack>
        </AuthProvider>
      </AccentProvider>
    </SafeAreaProvider>
  );
}
