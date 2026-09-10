// Design tokens for ProExam. Fase 3 of the guide: modern, simple,
// trustworthy, young, professional — not academic, not childish.
// Commercialista uses green/blue; other exams get their own accent once
// their content ships (Fase 32-33).

export const colors = {
  background: '#F7F9F8',
  surface: '#FFFFFF',
  border: '#E4E9E7',
  textPrimary: '#12201B',
  textSecondary: '#5B6C65',
  textInverse: '#FFFFFF',
  success: '#1E9E5A',
  danger: '#D64545',
  warning: '#E0A62B',
  locked: '#C7D0CC',
} as const;

export const examColors: Record<string, { primary: string; secondary: string }> = {
  Commercialista: { primary: '#0B5D3B', secondary: '#1E88E5' },
  Avvocato: { primary: '#7A1F2B', secondary: '#B23A48' },
  'Consulente finanziario': { primary: '#1B3A6B', secondary: '#D4AF37' },
};

export const defaultExamColor = { primary: colors.success, secondary: colors.textSecondary };

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
} as const;

export const radius = {
  sm: 8,
  md: 14,
  lg: 20,
  pill: 999,
} as const;

export const typography = {
  title: { fontSize: 28, fontWeight: '700' as const },
  heading: { fontSize: 20, fontWeight: '700' as const },
  body: { fontSize: 16, fontWeight: '400' as const },
  caption: { fontSize: 13, fontWeight: '500' as const },
};
