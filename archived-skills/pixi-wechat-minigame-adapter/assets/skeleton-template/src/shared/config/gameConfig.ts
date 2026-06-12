import type { GameBootConfig } from '../contracts';

export const SAFE_AREA_PADDING = 20;

export const UI_COLORS = {
  backgroundTop: 0x07111d,
  backgroundBottom: 0x091a2b,
  panel: 0x0b2034,
  panelBorder: 0x15344f,
  accent: 0xe8c95a,
  textPrimary: 0xf5f7ff,
  textMuted: 0x9db3c7,
  buttonFill: 0x0f2843,
  buttonStroke: 0xe8c95a,
};

export const BOOT_CONFIG: GameBootConfig = {
  target: 'web',
  designWidth: 720,
  designHeight: 1280,
  resolutionMode: 'contain',
  assetProfile: 'dev',
  runDurationMs: 20 * 60 * 1000,
};
