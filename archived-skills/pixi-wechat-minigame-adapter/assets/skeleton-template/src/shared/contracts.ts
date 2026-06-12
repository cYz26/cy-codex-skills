import type { Container } from 'pixi.js';

export type RuntimeTarget = 'web' | 'wechat-minigame';

export interface GameBootConfig {
  target: RuntimeTarget;
  designWidth: number;
  designHeight: number;
  resolutionMode: 'contain' | 'cover' | 'fixed';
  assetProfile: 'dev' | 'prod';
  runDurationMs: number;
}

export interface ViewportMetrics {
  width: number;
  height: number;
  scale: number;
  offsetX: number;
  offsetY: number;
  safeTop: number;
  safeBottom: number;
  safeLeft: number;
  safeRight: number;
}

export interface ViewportSize {
  width: number;
  height: number;
}

export interface SafeAreaInsets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export interface RuntimePlatform {
  readonly target: RuntimeTarget;
  getViewportSize(): ViewportSize;
  getSafeAreaInsets(): SafeAreaInsets;
  getRendererPreference(): 'canvas' | 'webgl' | 'webgpu';
  getRendererResolution(): number;
  getCanvas(): object | undefined;
  attachCanvas(canvas: object): void;
  onResize(listener: () => void): () => void;
  onKeyDown(listener: (event: KeyboardEvent) => void): () => void;
  toggleFullscreen(): Promise<void>;
  exitFullscreen(): Promise<void>;
  isFullscreenActive(): boolean;
  destroy(): void;
}

export interface SceneContract {
  key: string;
  container: Container;
  mount(): void;
  update(dtMs: number): void;
  resize(viewport: ViewportMetrics): void;
  getTextSnapshot(): string;
  destroy(): void;
}
