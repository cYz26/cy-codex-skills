import type { RuntimePlatform, SafeAreaInsets, ViewportSize } from '../shared/contracts';
import { UI_COLORS } from '../shared/config/gameConfig';
import {
  type WeChatViewportNormalizationSource,
  logWeChatDebug,
  setWeChatSystemInfoDebugSnapshot,
} from './wechatDebug';

interface WeChatRuntimeCanvasScope {
  __pixiWeChatScreenCanvas?: object;
  canvas?: object;
  screencanvas?: object;
  GameGlobal?: {
    canvas?: object;
    screencanvas?: object;
  };
}

interface RenderableCanvasCandidate {
  getContext?: unknown;
}

interface StyledCanvasCandidate extends RenderableCanvasCandidate {
  getBoundingClientRect?: () => {
    height?: number;
    width?: number;
  };
  height?: number;
  isConnected?: boolean;
  style?: Record<string, string>;
  width?: number;
}

interface ResolvedCanvasCandidate {
  canvas: object & StyledCanvasCandidate;
  source: string;
}

interface NormalizedSystemInfoResult {
  rawSystemInfo: WechatMinigameSystemInfo;
  systemInfo: WechatMinigameSystemInfo;
  normalizationFactor: number | null;
  normalizationSource: WeChatViewportNormalizationSource;
  viewportWasNormalized: boolean;
}

const isRenderableCanvas = (
  candidate: object | undefined,
): candidate is object & RenderableCanvasCandidate =>
  Boolean(candidate) &&
  typeof (candidate as RenderableCanvasCandidate).getContext === 'function';

const syncCanvasDisplaySize = (canvas: object, width: number, height: number): void => {
  const styledCanvas = canvas as StyledCanvasCandidate;
  styledCanvas.style ??= {};
  styledCanvas.style.width = `${width}px`;
  styledCanvas.style.height = `${height}px`;
};

const summarizeCanvasCandidate = (
  candidate: ResolvedCanvasCandidate,
): Record<string, boolean | number | string | null> => {
  const rect = candidate.canvas.getBoundingClientRect?.();

  return {
    source: candidate.source,
    isConnected: candidate.canvas.isConnected ?? null,
    width: candidate.canvas.width ?? null,
    height: candidate.canvas.height ?? null,
    styleWidth: candidate.canvas.style?.width ?? null,
    styleHeight: candidate.canvas.style?.height ?? null,
    rectWidth: rect?.width ?? null,
    rectHeight: rect?.height ?? null,
  };
};

const resolveScreenCanvas = (
  runtime: WeChatRuntimeCanvasScope,
): ResolvedCanvasCandidate | null => {
  for (const [candidate, source] of [
    [runtime.__pixiWeChatScreenCanvas, 'globalThis.__pixiWeChatScreenCanvas'],
    [runtime.canvas, 'globalThis.canvas'],
    [runtime.screencanvas, 'globalThis.screencanvas'],
    [runtime.GameGlobal?.canvas, 'GameGlobal.canvas'],
    [runtime.GameGlobal?.screencanvas, 'GameGlobal.screencanvas'],
  ] as const) {
    if (!isRenderableCanvas(candidate)) {
      continue;
    }

    return {
      canvas: candidate as object & StyledCanvasCandidate,
      source,
    };
  }

  return null;
};

const roundMetric = (value: number): number => Math.round(value * 1000) / 1000;

const cloneDefinedSafeArea = (
  safeArea: WechatMinigameSafeArea,
): WechatMinigameSafeArea => ({
  top: safeArea.top,
  right: safeArea.right,
  bottom: safeArea.bottom,
  left: safeArea.left,
});

const resolveViewportNormalization = (
  rawWidth: number,
  pixelRatio: number,
  aspectRatio: number,
): { factor: number | null; source: WeChatViewportNormalizationSource } => {
  if (pixelRatio <= 1 || rawWidth < 720 || aspectRatio < 1.7) {
    if (rawWidth < 720 || aspectRatio < 1.7) {
      return {
        factor: null,
        source: 'none',
      };
    }

    const inferredDensity = Math.max(2, Math.min(4, Math.round(rawWidth / 390)));
    const logicalWidth = rawWidth / inferredDensity;
    return logicalWidth >= 240 && logicalWidth <= 540
      ? {
          factor: inferredDensity,
          source: 'inferred-density',
        }
      : {
          factor: null,
          source: 'none',
        };
  }

  const logicalWidth = rawWidth / pixelRatio;
  return logicalWidth >= 240 && logicalWidth <= 540
    ? {
        factor: pixelRatio,
        source: 'pixel-ratio',
      }
    : {
        factor: null,
        source: 'none',
      };
};

const normalizeViewportDimension = (
  value: number,
  normalizationFactor: number | null,
): number => {
  if (!normalizationFactor || normalizationFactor <= 1) {
    return value;
  }

  return roundMetric(value / normalizationFactor);
};

const normalizeSafeAreaEdge = (
  value: number,
  normalizationFactor: number | null,
  wasViewportNormalized: boolean,
): number => {
  if (!wasViewportNormalized || !normalizationFactor || normalizationFactor <= 1) {
    return value;
  }

  return roundMetric(value / normalizationFactor);
};

const normalizeSystemInfo = (
  systemInfo: WechatMinigameSystemInfo,
): NormalizedSystemInfoResult => {
  const rawSystemInfo: WechatMinigameSystemInfo = {
    ...systemInfo,
    ...(systemInfo.safeArea ? { safeArea: cloneDefinedSafeArea(systemInfo.safeArea) } : {}),
  };
  const pixelRatio = systemInfo.pixelRatio || 1;
  const rawWidth = systemInfo.windowWidth;
  const rawHeight = systemInfo.windowHeight;
  const aspectRatio = rawWidth > 0 && rawHeight > 0 ? rawHeight / rawWidth : 0;
  const normalization = resolveViewportNormalization(rawWidth, pixelRatio, aspectRatio);
  const normalizationFactor = normalization.factor;
  const normalizedWidth = normalizeViewportDimension(rawWidth, normalizationFactor);
  const normalizedHeight = normalizeViewportDimension(rawHeight, normalizationFactor);
  const viewportWasNormalized =
    normalizedWidth !== rawWidth || normalizedHeight !== rawHeight;

  if (!viewportWasNormalized && !systemInfo.safeArea) {
    return {
      rawSystemInfo,
      systemInfo: rawSystemInfo,
      normalizationFactor,
      normalizationSource: normalization.source,
      viewportWasNormalized,
    };
  }

  return {
    rawSystemInfo,
    systemInfo: {
      ...systemInfo,
      windowWidth: normalizedWidth,
      windowHeight: normalizedHeight,
      ...(systemInfo.safeArea
        ? {
            safeArea: {
              top: normalizeSafeAreaEdge(
                systemInfo.safeArea.top,
                normalizationFactor,
                viewportWasNormalized,
              ),
              right: normalizeSafeAreaEdge(
                systemInfo.safeArea.right,
                normalizationFactor,
                viewportWasNormalized,
              ),
              bottom: normalizeSafeAreaEdge(
                systemInfo.safeArea.bottom,
                normalizationFactor,
                viewportWasNormalized,
              ),
              left: normalizeSafeAreaEdge(
                systemInfo.safeArea.left,
                normalizationFactor,
                viewportWasNormalized,
              ),
            },
          }
        : {}),
    },
    normalizationFactor,
    normalizationSource: normalization.source,
    viewportWasNormalized,
  };
};

const clampInset = (value: number, size: number): number =>
  Math.min(Math.max(0, value), Math.max(0, size));

const normalizeAxisInsets = (
  start: number,
  end: number,
  size: number,
): { startInset: number; endInset: number } => {
  const normalizedStart = clampInset(start, size);
  const normalizedEnd = clampInset(end, size);

  if (normalizedEnd > size / 2) {
    return {
      startInset: normalizedStart,
      endInset: clampInset(size - normalizedEnd, size),
    };
  }

  if (normalizedStart + normalizedEnd < size) {
    return {
      startInset: normalizedStart,
      endInset: normalizedEnd,
    };
  }

  return {
    startInset: normalizedStart,
    endInset: clampInset(size - normalizedEnd, size),
  };
};

const createSafeAreaInsets = (
  safeArea: WechatMinigameSafeArea | undefined,
  width: number,
  height: number,
): SafeAreaInsets => {
  if (!safeArea) {
    return {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0,
    };
  }

  const horizontalInsets = normalizeAxisInsets(safeArea.left, safeArea.right, width);
  const verticalInsets = normalizeAxisInsets(safeArea.top, safeArea.bottom, height);

  return {
    top: verticalInsets.startInset,
    right: horizontalInsets.endInset,
    bottom: verticalInsets.endInset,
    left: horizontalInsets.startInset,
  };
};

const syncSystemInfoDebugSnapshot = (result: NormalizedSystemInfoResult): void => {
  setWeChatSystemInfoDebugSnapshot({
    rawWindowWidth: result.rawSystemInfo.windowWidth,
    rawWindowHeight: result.rawSystemInfo.windowHeight,
    rawPixelRatio: result.rawSystemInfo.pixelRatio || 1,
    normalizedWindowWidth: result.systemInfo.windowWidth,
    normalizedWindowHeight: result.systemInfo.windowHeight,
    normalizedPixelRatio: result.systemInfo.pixelRatio || 1,
    normalizationFactor: result.normalizationFactor,
    normalizationSource: result.normalizationSource,
    viewportWasNormalized: result.viewportWasNormalized,
    ...(result.rawSystemInfo.platform ? { platform: result.rawSystemInfo.platform } : {}),
    ...(result.rawSystemInfo.brand ? { brand: result.rawSystemInfo.brand } : {}),
    ...(result.rawSystemInfo.model ? { model: result.rawSystemInfo.model } : {}),
    ...(result.rawSystemInfo.safeArea
      ? { rawSafeArea: cloneDefinedSafeArea(result.rawSystemInfo.safeArea) }
      : {}),
    ...(result.systemInfo.safeArea
      ? { normalizedSafeArea: cloneDefinedSafeArea(result.systemInfo.safeArea) }
      : {}),
  });
};

const syncWeChatBackgroundColor = (): void => {
  const backgroundColor = `#${UI_COLORS.backgroundTop.toString(16).padStart(6, '0')}`;
  wx.setBackgroundColor?.({
    backgroundColor,
    backgroundColorTop: backgroundColor,
    backgroundColorBottom: backgroundColor,
  });
};

export class WeChatPlatform implements RuntimePlatform {
  readonly target = 'wechat-minigame' as const;

  private readonly canvas: object;
  private systemInfoState = normalizeSystemInfo(wx.getSystemInfoSync());

  constructor(
    private readonly designWidth: number,
    private readonly designHeight: number,
  ) {
    syncSystemInfoDebugSnapshot(this.systemInfoState);
    syncWeChatBackgroundColor();

    const runtime = globalThis as unknown as WeChatRuntimeCanvasScope;
    const screenCanvas = resolveScreenCanvas(runtime);

    if (!screenCanvas) {
      throw new Error(
        'WeChatPlatform requires a prebound screen canvas before initialization.',
      );
    }

    runtime.__pixiWeChatScreenCanvas = screenCanvas.canvas;
    runtime.canvas = screenCanvas.canvas;
    runtime.screencanvas = screenCanvas.canvas;
    runtime.GameGlobal ??= {};
    runtime.GameGlobal.canvas = screenCanvas.canvas;
    runtime.GameGlobal.screencanvas = screenCanvas.canvas;
    this.canvas = screenCanvas.canvas;

    syncCanvasDisplaySize(
      this.canvas,
      this.systemInfo.windowWidth || this.designWidth,
      this.systemInfo.windowHeight || this.designHeight,
    );
    logWeChatDebug('selected runtime canvas', summarizeCanvasCandidate(screenCanvas));
  }

  getCanvas(): object {
    return this.canvas;
  }

  getViewportSize(): ViewportSize {
    return {
      width: this.systemInfo.windowWidth || this.designWidth,
      height: this.systemInfo.windowHeight || this.designHeight,
    };
  }

  getSafeAreaInsets(): SafeAreaInsets {
    return createSafeAreaInsets(
      this.systemInfo.safeArea,
      this.systemInfo.windowWidth || this.designWidth,
      this.systemInfo.windowHeight || this.designHeight,
    );
  }

  getRendererResolution(): number {
    if (this.systemInfo.platform?.toLowerCase() === 'devtools') {
      return 1;
    }

    return Math.min(this.systemInfo.pixelRatio || 1, 2);
  }

  getRendererPreference(): 'canvas' | 'webgl' {
    if (this.systemInfo.platform?.toLowerCase() === 'devtools') {
      return 'canvas';
    }

    return 'webgl';
  }

  attachCanvas(canvas: object): void {
    void canvas;
    syncCanvasDisplaySize(
      this.canvas,
      this.systemInfo.windowWidth || this.designWidth,
      this.systemInfo.windowHeight || this.designHeight,
    );
  }

  onResize(listener: () => void): () => void {
    const handler = (event: WechatMinigameWindowResizeResult): void => {
      this.refreshSystemInfo();
      syncWeChatBackgroundColor();
      syncCanvasDisplaySize(
        this.canvas,
        this.systemInfo.windowWidth || event.windowWidth,
        this.systemInfo.windowHeight || event.windowHeight,
      );
      listener();
    };

    wx.onWindowResize(handler);
    return () => {
      wx.offWindowResize?.(handler);
    };
  }

  onKeyDown(listener: (event: KeyboardEvent) => void): () => void {
    void listener;
    return () => {};
  }

  async toggleFullscreen(): Promise<void> {}

  async exitFullscreen(): Promise<void> {}

  isFullscreenActive(): boolean {
    return false;
  }

  destroy(): void {}

  private get systemInfo(): WechatMinigameSystemInfo {
    return this.systemInfoState.systemInfo;
  }

  private refreshSystemInfo(): void {
    try {
      this.systemInfoState = normalizeSystemInfo(wx.getSystemInfoSync());
      syncSystemInfoDebugSnapshot(this.systemInfoState);
    } catch {
      logWeChatDebug('failed to refresh system info');
    }
  }
}
