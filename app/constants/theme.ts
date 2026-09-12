// Design tokens for ProExam. Fase 3 of the guide: modern, simple,
// trustworthy, young, professional — not academic, not childish.

export const colors = {
  background: '#F7F9F8',
  surface: '#FFFFFF',
  border: '#E7EBE9',
  textPrimary: '#182422',
  textSecondary: '#5B6C68',
  textInverse: '#FFFFFF',
  // Semantic feedback colors are fixed and never follow the user's chosen
  // accent: "correct" reads green and "wrong" reads red everywhere, so the
  // meaning stays instantly recognizable no matter which accent is active.
  success: '#2F9E63',
  danger: '#E4573D',
  warning: '#E0A62B',
  locked: '#C7D0CC',
  shadow: '#0F2A26',
} as const;

export interface AccentColor {
  key: string;
  name: string;
  /** Saturated tone used for buttons, active icons, progress fills. */
  primary: string;
  /** Light wash of the same hue, used for selected/highlighted surfaces. */
  soft: string;
}

/**
 * The 5 accent colors a learner can pick from (Profile → Aspetto). Chosen at
 * a "Material 600"-like lightness/saturation band so white text always sits
 * on top cleanly, whichever one is active.
 */
export const ACCENT_PALETTE: AccentColor[] = [
  { key: 'sugarcane', name: 'Azzurro canna da zucchero', primary: '#1D8FA3', soft: '#E1F3F6' },
  { key: 'coral', name: 'Corallo', primary: '#F1573A', soft: '#FCE7E3' },
  { key: 'plum', name: 'Prugna', primary: '#6E42B8', soft: '#EEE6F9' },
  { key: 'sage', name: 'Salvia', primary: '#2F8F63', soft: '#E2F2E9' },
  { key: 'indigo', name: 'Blu notte', primary: '#3B4FA0', soft: '#E6E9F6' },
];

export const DEFAULT_ACCENT_KEY = ACCENT_PALETTE[0].key;

// Exam-selection cards (Fase 3): each exam keeps its own brand identity on
// the "choose your exam" screen only. Once inside the app, the learner's
// personal accent color (above) drives the rest of the UI.
export const examColors: Record<string, { primary: string; secondary: string }> = {
  Commercialista: { primary: '#2F8F63', secondary: '#1D8FA3' },
  Avvocato: { primary: '#B23A48', secondary: '#7A1F2B' },
  'Consulente finanziario': { primary: '#3B4FA0', secondary: '#C79A2E' },
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
  sm: 10,
  md: 16,
  lg: 22,
  pill: 999,
} as const;

export const typography = {
  title: { fontSize: 28, fontWeight: '800' as const, letterSpacing: -0.3 },
  heading: { fontSize: 19, fontWeight: '700' as const },
  body: { fontSize: 16, fontWeight: '400' as const },
  caption: { fontSize: 13, fontWeight: '600' as const },
};
