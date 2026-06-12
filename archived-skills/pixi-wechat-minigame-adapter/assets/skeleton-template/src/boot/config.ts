import { BOOT_CONFIG } from '../shared/config/gameConfig';
import type { GameBootConfig } from '../shared/contracts';

export const webGameBootConfig: GameBootConfig = {
  ...BOOT_CONFIG,
  target: 'web',
  assetProfile: 'dev',
};

export const wechatGameBootConfig: GameBootConfig = {
  ...BOOT_CONFIG,
  target: 'wechat-minigame',
  assetProfile: 'prod',
};
