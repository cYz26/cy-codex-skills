import { Application, Container } from 'pixi.js';

import { BOOT_CONFIG, SAFE_AREA_PADDING } from '../shared/config/gameConfig';
import type {
  GameBootConfig,
  RuntimePlatform,
  SceneContract,
  ViewportMetrics,
} from '../shared/contracts';
import { StarterScene } from '../scenes/StarterScene';

interface DebugWindow extends Window {
  render_game_to_text?: () => string;
}

export class GameCoordinator {
  private readonly app = new Application();
  private readonly root = new Container();
  private readonly scene: SceneContract = new StarterScene();

  private viewport: ViewportMetrics | null = null;

  constructor(
    private readonly platform: RuntimePlatform,
    private readonly bootConfig: GameBootConfig = BOOT_CONFIG,
  ) {}

  async init(): Promise<void> {
    const initialSize = this.platform.getViewportSize();
    const providedCanvas = this.platform.getCanvas();
    const isWeChatTarget = this.bootConfig.target === 'wechat-minigame';

    await this.app.init({
      width: initialSize.width,
      height: initialSize.height,
      antialias: true,
      autoDensity: true,
      resolution: this.platform.getRendererResolution(),
      background: '#07111d',
      preference: this.platform.getRendererPreference(),
      ...(isWeChatTarget
        ? {
            webgl: {
              preferWebGLVersion: 1 as const,
            },
          }
        : {}),
      ...(providedCanvas ? { canvas: providedCanvas as HTMLCanvasElement } : {}),
    });

    this.platform.attachCanvas(this.app.canvas as object);
    this.app.stage.addChild(this.root);
    this.root.addChild(this.scene.container);
    this.scene.mount();

    this.platform.onResize(() => this.resize());
    this.platform.onKeyDown((event) => this.handleKeyDown(event));

    this.app.ticker.add((ticker) => {
      this.scene.update(ticker.deltaMS);
    });

    this.resize();
    this.installDebugHooks();
    this.logWeChatDebug('app-init', {
      initialSize,
      rendererResolution: this.platform.getRendererResolution(),
      rendererPreference: this.platform.getRendererPreference(),
      rendererType: this.app.renderer.constructor.name,
    });
  }

  destroy(): void {
    this.scene.destroy();
    this.platform.destroy();
    this.app.destroy(true, { children: true });
  }

  private resize(): void {
    const viewportSize = this.platform.getViewportSize();
    const safeAreaInsets = this.platform.getSafeAreaInsets();
    const scale = Math.min(
      viewportSize.width / this.bootConfig.designWidth,
      viewportSize.height / this.bootConfig.designHeight,
    );
    const offsetX = (viewportSize.width - this.bootConfig.designWidth * scale) / 2;
    const offsetY = (viewportSize.height - this.bootConfig.designHeight * scale) / 2;

    this.app.renderer.resize(viewportSize.width, viewportSize.height);
    this.root.scale.set(scale);
    this.root.position.set(offsetX, offsetY);

    this.viewport = {
      width: this.bootConfig.designWidth,
      height: this.bootConfig.designHeight,
      scale,
      offsetX,
      offsetY,
      safeTop: safeAreaInsets.top + SAFE_AREA_PADDING,
      safeBottom: safeAreaInsets.bottom + SAFE_AREA_PADDING,
      safeLeft: safeAreaInsets.left + SAFE_AREA_PADDING,
      safeRight: safeAreaInsets.right + SAFE_AREA_PADDING,
    };

    this.scene.resize(this.viewport);
  }

  private handleKeyDown(event: KeyboardEvent): void {
    if (event.code === 'KeyF') {
      void this.platform.toggleFullscreen();
      return;
    }

    if (event.code === 'Escape' && this.platform.isFullscreenActive()) {
      void this.platform.exitFullscreen();
    }
  }

  private installDebugHooks(): void {
    const debugWindow = window as DebugWindow;
    debugWindow.render_game_to_text = () => this.scene.getTextSnapshot();
  }

  private logWeChatDebug(label: string, payload: unknown): void {
    if (this.bootConfig.target !== 'wechat-minigame') {
      return;
    }

    console.info(`[pixi-wechat] ${label}`, payload);
  }
}
