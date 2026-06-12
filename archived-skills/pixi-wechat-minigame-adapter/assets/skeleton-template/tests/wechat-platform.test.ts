import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import { WeChatPlatform } from '../src/platform/WeChatPlatform';
import { setWeChatDebugLoggingOverrideForTests } from '../src/platform/wechatDebug';

type WeChatPlatformTestRuntime = typeof globalThis & {
  __pixiWeChatScreenCanvas?: unknown;
  wx?: unknown;
  canvas?: unknown;
  screencanvas?: unknown;
  GameGlobal?: unknown;
  document?: unknown;
};

const globalRuntime = globalThis as WeChatPlatformTestRuntime;
const restoreKeys = [
  '__pixiWeChatScreenCanvas',
  'wx',
  'canvas',
  'screencanvas',
  'GameGlobal',
  'document',
] as const;
const snapshot = new Map<string, unknown>();

for (const key of restoreKeys) {
  snapshot.set(key, globalRuntime[key]);
}

const restoreGlobalValue = (key: (typeof restoreKeys)[number], value: unknown): void => {
  if (value === undefined) {
    delete globalRuntime[key];
    return;
  }

  Object.defineProperty(globalRuntime, key, {
    value,
    configurable: true,
    writable: true,
  });
};

const prebindScreenCanvas = (canvas: unknown): void => {
  Object.defineProperty(globalRuntime, '__pixiWeChatScreenCanvas', {
    value: canvas,
    configurable: true,
    writable: true,
  });
  Object.defineProperty(globalRuntime, 'canvas', {
    value: canvas,
    configurable: true,
    writable: true,
  });
  Object.defineProperty(globalRuntime, 'screencanvas', {
    value: canvas,
    configurable: true,
    writable: true,
  });
  Object.defineProperty(globalRuntime, 'GameGlobal', {
    value: {
      canvas,
      screencanvas: canvas,
    },
    configurable: true,
    writable: true,
  });
};

beforeEach(() => {
  setWeChatDebugLoggingOverrideForTests(false);
});

afterEach(() => {
  setWeChatDebugLoggingOverrideForTests(undefined);
  vi.restoreAllMocks();
  for (const key of restoreKeys) {
    restoreGlobalValue(key, snapshot.get(key));
  }
});

describe('WeChatPlatform', () => {
  test('reuses the prebound screen canvas without creating a new one', () => {
    const runtimeCanvas = {
      width: 390,
      height: 844,
      style: {},
      getBoundingClientRect() {
        return {
          top: 0,
          left: 0,
          right: 390,
          bottom: 844,
          width: 390,
          height: 844,
          x: 0,
          y: 0,
        };
      },
      getContext(): object {
        return {};
      },
    };

    prebindScreenCanvas(runtimeCanvas);
    globalRuntime.wx = {
      createCanvas: vi.fn(() => ({
        style: {},
        getContext(): object {
          return {};
        },
      })),
      getStorageSync(): null {
        return null;
      },
      setStorageSync(): void {},
      getSystemInfoSync() {
        return {
          pixelRatio: 2,
          platform: 'devtools',
          windowHeight: 844,
          windowWidth: 390,
        };
      },
      onHide(): void {},
      onShow(): void {},
      onWindowResize(): void {},
      shareAppMessage(): void {},
      setBackgroundColor(): void {},
    };

    const platform = new WeChatPlatform(720, 1280);

    expect(platform.getCanvas()).toBe(runtimeCanvas);
    expect(globalRuntime.canvas).toBe(runtimeCanvas);
    expect(globalRuntime.screencanvas).toBe(runtimeCanvas);
    expect(globalRuntime.__pixiWeChatScreenCanvas).toBe(runtimeCanvas);
    expect(
      (globalRuntime.GameGlobal as { canvas?: unknown; screencanvas?: unknown } | undefined)?.canvas,
    ).toBe(runtimeCanvas);
    expect(runtimeCanvas.style).toMatchObject({
      width: '390px',
      height: '844px',
    });
    expect((globalRuntime.wx as { createCanvas: ReturnType<typeof vi.fn> }).createCanvas).not.toHaveBeenCalled();
  });

  test('ignores document canvases and keeps the prebound screen canvas', () => {
    const screenCanvas = {
      width: 390,
      height: 844,
      style: {},
      getBoundingClientRect() {
        return {
          top: 0,
          left: 0,
          right: 390,
          bottom: 844,
          width: 390,
          height: 844,
          x: 0,
          y: 0,
        };
      },
      getContext(): object {
        return {};
      },
    };

    prebindScreenCanvas(screenCanvas);
    globalRuntime.document = {
      querySelectorAll(selector: string): unknown[] {
        if (selector !== 'canvas') {
          return [];
        }

        return [
          {
            width: 16,
            height: 16,
            style: {},
            getContext(): object {
              return {};
            },
          },
        ];
      },
    };
    globalRuntime.wx = {
      createCanvas: vi.fn(),
      getStorageSync(): null {
        return null;
      },
      setStorageSync(): void {},
      getSystemInfoSync() {
        return {
          pixelRatio: 2,
          platform: 'devtools',
          windowHeight: 844,
          windowWidth: 390,
        };
      },
      onHide(): void {},
      onShow(): void {},
      onWindowResize(): void {},
      shareAppMessage(): void {},
      setBackgroundColor(): void {},
    };

    const platform = new WeChatPlatform(720, 1280);

    expect(platform.getCanvas()).toBe(screenCanvas);
    expect((globalRuntime.wx as { createCanvas: ReturnType<typeof vi.fn> }).createCanvas).not.toHaveBeenCalled();
  });

  test('throws when no prebound screen canvas is available', () => {
    globalRuntime.wx = {
      createCanvas: vi.fn(),
      getStorageSync(): null {
        return null;
      },
      setStorageSync(): void {},
      getSystemInfoSync() {
        return {
          pixelRatio: 2,
          platform: 'devtools',
          windowHeight: 844,
          windowWidth: 390,
        };
      },
      onHide(): void {},
      onShow(): void {},
      onWindowResize(): void {},
      shareAppMessage(): void {},
      setBackgroundColor(): void {},
    };

    expect(() => new WeChatPlatform(720, 1280)).toThrow(
      /prebound screen canvas/i,
    );
  });
});
