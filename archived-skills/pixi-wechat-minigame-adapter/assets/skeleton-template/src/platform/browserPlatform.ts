import type { RuntimePlatform, SafeAreaInsets, ViewportSize } from '../shared/contracts';

const EMPTY_SAFE_AREA: SafeAreaInsets = {
  top: 0,
  right: 0,
  bottom: 0,
  left: 0
};

export class BrowserPlatform implements RuntimePlatform {
  readonly target = 'web' as const;
  private readonly resizeListeners = new Set<() => void>();
  private readonly keyListeners = new Set<(event: KeyboardEvent) => void>();

  private readonly handleResize = (): void => {
    for (const listener of this.resizeListeners) {
      listener();
    }
  };

  private readonly handleKeyDown = (event: KeyboardEvent): void => {
    for (const listener of this.keyListeners) {
      listener(event);
    }
  };

  constructor(private readonly fullscreenTarget: HTMLElement) {
    window.addEventListener('resize', this.handleResize);
    window.addEventListener('keydown', this.handleKeyDown);
  }

  getSafeAreaInsets(): SafeAreaInsets {
    return EMPTY_SAFE_AREA;
  }

  getRendererResolution(): number {
    return Math.min(window.devicePixelRatio || 1, 2);
  }

  getRendererPreference(): 'webgl' {
    return 'webgl';
  }

  getCanvas(): object | undefined {
    return undefined;
  }

  attachCanvas(canvas: object): void {
    this.fullscreenTarget.replaceChildren(canvas as Node);
  }

  getViewportSize(): ViewportSize {
    return {
      width: Math.max(window.innerWidth, 320),
      height: Math.max(window.innerHeight, 480)
    };
  }

  onResize(listener: () => void): () => void {
    this.resizeListeners.add(listener);
    return () => this.resizeListeners.delete(listener);
  }

  onKeyDown(listener: (event: KeyboardEvent) => void): () => void {
    this.keyListeners.add(listener);
    return () => this.keyListeners.delete(listener);
  }

  async toggleFullscreen(): Promise<void> {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
      return;
    }

    await this.fullscreenTarget.requestFullscreen();
  }

  async exitFullscreen(): Promise<void> {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    }
  }

  isFullscreenActive(): boolean {
    return Boolean(document.fullscreenElement);
  }

  destroy(): void {
    window.removeEventListener('resize', this.handleResize);
    window.removeEventListener('keydown', this.handleKeyDown);
    this.resizeListeners.clear();
    this.keyListeners.clear();
  }
}
