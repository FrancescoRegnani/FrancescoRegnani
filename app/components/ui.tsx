import { ReactNode } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
  type PressableProps,
  type ViewStyle,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, radius, spacing, typography } from '../constants/theme';
import { useAccent } from '../lib/accent-context';

export function Screen({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  return <View style={[styles.screen, style]}>{children}</View>;
}

export function Card({
  children,
  style,
  tinted,
}: {
  children: ReactNode;
  style?: ViewStyle;
  /** Wash the card with the current accent's soft tone, for a featured card. */
  tinted?: boolean;
}) {
  const { accent } = useAccent();
  return (
    <View style={[styles.card, tinted && { backgroundColor: accent.soft, borderColor: 'transparent' }, style]}>
      {children}
    </View>
  );
}

interface ButtonProps extends PressableProps {
  title: string;
  variant?: 'primary' | 'secondary' | 'ghost';
  loading?: boolean;
  color?: string;
}

export function Button({ title, variant = 'primary', loading, color, style, disabled, ...rest }: ButtonProps) {
  const { accent } = useAccent();
  const tone = color ?? accent.primary;
  const isPrimary = variant === 'primary';
  const isSecondary = variant === 'secondary';
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.button,
        isPrimary && { backgroundColor: tone },
        isSecondary && [styles.buttonSecondary, { borderColor: tone }],
        variant === 'ghost' && styles.buttonGhost,
        (disabled || loading) && styles.buttonDisabled,
        pressed && !disabled && !loading && styles.buttonPressed,
        style as ViewStyle,
      ]}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator color={isPrimary ? colors.textInverse : tone} />
      ) : (
        <Text style={[styles.buttonText, isPrimary && { color: colors.textInverse }, !isPrimary && { color: tone }]}>
          {title}
        </Text>
      )}
    </Pressable>
  );
}

export function Title({ children, style }: { children: ReactNode; style?: object }) {
  return <Text style={[styles.title, style]}>{children}</Text>;
}

export function Heading({ children, style }: { children: ReactNode; style?: object }) {
  return <Text style={[styles.heading, style]}>{children}</Text>;
}

export function Body({ children, style }: { children: ReactNode; style?: object }) {
  return <Text style={[styles.body, style]}>{children}</Text>;
}

export function Caption({ children, style }: { children: ReactNode; style?: object }) {
  return <Text style={[styles.caption, style]}>{children}</Text>;
}

/** Small uppercase label for stat tiles and section eyebrows (e.g. "XP", "STREAK"). */
export function Eyebrow({ children, style }: { children: ReactNode; style?: object }) {
  return <Text style={[styles.eyebrow, style]}>{children}</Text>;
}

export function ProgressBar({ ratio, color }: { ratio: number; color?: string }) {
  const { accent } = useAccent();
  const clamped = Math.max(0, Math.min(1, ratio));
  return (
    <View style={styles.progressTrack}>
      <View style={[styles.progressFill, { width: `${clamped * 100}%`, backgroundColor: color ?? accent.primary }]} />
    </View>
  );
}

/** A small circular tinted badge behind an icon — used on stat tiles and list rows to add color without shouting. */
export function IconChip({
  name,
  color,
  background,
  size = 40,
}: {
  name: keyof typeof Ionicons.glyphMap;
  color?: string;
  background?: string;
  size?: number;
}) {
  const { accent } = useAccent();
  return (
    <View
      style={[
        styles.iconChip,
        { width: size, height: size, borderRadius: size / 2, backgroundColor: background ?? accent.soft },
      ]}
    >
      <Ionicons name={name} size={size * 0.52} color={color ?? accent.primary} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.background,
    padding: spacing.lg,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
    ...Platform.select({
      web: { boxShadow: `0 1px 3px ${colors.shadow}14, 0 1px 2px ${colors.shadow}0d` },
      default: {
        shadowColor: colors.shadow,
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.06,
        shadowRadius: 4,
        elevation: 1,
      },
    }),
  },
  button: {
    borderRadius: radius.pill,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonSecondary: {
    backgroundColor: 'transparent',
    borderWidth: 2,
  },
  buttonGhost: {
    backgroundColor: 'transparent',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonPressed: {
    opacity: 0.85,
  },
  buttonText: {
    fontSize: 16,
    fontWeight: '700',
  },
  title: { ...typography.title, color: colors.textPrimary },
  heading: { ...typography.heading, color: colors.textPrimary },
  body: { ...typography.body, color: colors.textPrimary },
  caption: { ...typography.caption, color: colors.textSecondary },
  eyebrow: {
    ...typography.caption,
    color: colors.textSecondary,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  progressTrack: {
    height: 10,
    borderRadius: radius.pill,
    backgroundColor: colors.border,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: radius.pill,
  },
  iconChip: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
