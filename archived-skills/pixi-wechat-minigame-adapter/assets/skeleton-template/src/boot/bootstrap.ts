import { GameCoordinator } from './GameCoordinator';
import { BrowserPlatform } from '../platform/browserPlatform';
import { WeChatPlatform } from '../platform/WeChatPlatform';
import { webGameBootConfig, wechatGameBootConfig } from './config';

const requireAppRoot = (): HTMLDivElement => {
  const appRoot = document.querySelector<HTMLDivElement>('#app');
  if (!appRoot) {
    throw new Error('Missing #app mount node.');
  }

  return appRoot;
};

export const bootstrapWebGame = async (): Promise<void> => {
  const appRoot = requireAppRoot();
  const game = new GameCoordinator(new BrowserPlatform(appRoot), webGameBootConfig);

  try {
    await game.init();
  } catch (error) {
    console.error(error);
    appRoot.textContent = 'Starter boot failed. Check the console for details.';
    throw error;
  }
};

export const bootstrapWeChatGame = async (): Promise<void> => {
  const game = new GameCoordinator(
    new WeChatPlatform(wechatGameBootConfig.designWidth, wechatGameBootConfig.designHeight),
    wechatGameBootConfig,
  );

  await game.init();
};
