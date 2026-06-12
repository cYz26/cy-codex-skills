import { afterEach, beforeEach, describe, expect, test } from 'vitest';

import { prepareWeChatRuntime } from '../src/platform/prepareWeChatRuntime';
import { setWeChatDebugLoggingOverrideForTests } from '../src/platform/wechatDebug';

type GlobalWithWeChatPrep = typeof globalThis & {
  wx?: unknown;
  canvas?: unknown;
  screencanvas?: unknown;
  GameGlobal?: unknown;
  self?: typeof globalThis;
  window?: typeof globalThis;
  ontouchstart?: unknown;
  document?: unknown;
  navigator?: unknown;
  location?: unknown;
  URL?: unknown;
  fetch?: unknown;
  createImageBitmap?: unknown;
  addEventListener?: (type: string, listener: (event?: { type: string }) => void) => void;
  removeEventListener?: (type: string, listener: (event?: { type: string }) => void) => void;
  dispatchEvent?: (event: { type: string }) => boolean;
  Image?: unknown;
  HTMLImageElement?: unknown;
  HTMLVideoElement?: unknown;
  HTMLCanvasElement?: unknown;
  CanvasRenderingContext2D?: unknown;
  WebGLRenderingContext?: unknown;
  WebGL2RenderingContext?: unknown;
  TouchEvent?: new (type: string, init?: unknown) => object;
  Intl?: {
    Segmenter?: new (locales?: unknown, options?: unknown) => {
      segment(input: string): Iterable<{ segment: string }>;
    };
  };
  structuredClone?: <T>(value: T) => T;
  __pixiWeChatCreateOffscreenCanvas?: () => unknown;
  __pixiWeChatRendererDebug__?: {
    resolution?: number;
  };
  __pixiWeChatRuntimePrepared?: boolean;
  __pixiWeChatScreenCanvas?: unknown;
};

const globalRuntime = globalThis as GlobalWithWeChatPrep;

const restoreKeys = [
  'wx',
  'canvas',
  'screencanvas',
  'GameGlobal',
  'self',
  'window',
  'ontouchstart',
  'document',
  'navigator',
  'location',
  'URL',
  'fetch',
  'createImageBitmap',
  'addEventListener',
  'removeEventListener',
  'dispatchEvent',
  'Image',
  'HTMLImageElement',
  'HTMLVideoElement',
  'HTMLCanvasElement',
  'CanvasRenderingContext2D',
  'WebGLRenderingContext',
  'WebGL2RenderingContext',
  'TouchEvent',
  'Intl',
  'structuredClone',
  '__pixiWeChatCreateOffscreenCanvas',
  '__pixiWeChatRendererDebug__',
  '__pixiWeChatRuntimePrepared',
  '__pixiWeChatScreenCanvas',
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

afterEach(() => {
  setWeChatDebugLoggingOverrideForTests(undefined);
  for (const key of restoreKeys) {
    restoreGlobalValue(key, snapshot.get(key));
  }
});

beforeEach(() => {
  setWeChatDebugLoggingOverrideForTests(false);
});

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

describe('prepareWeChatRuntime', () => {
  test('installs global event-target shims when the WeChat runtime lacks window listeners', () => {
    class MockCanvasRenderingContext2D {
      letterSpacing = '0px';
    }
    class MockWebGLRenderingContext {
      readonly ARRAY_BUFFER = 34962;

      readonly ELEMENT_ARRAY_BUFFER = 34963;

      bindBuffer(): void {}

      disableVertexAttribArray(): void {}

      enableVertexAttribArray(): void {}

      getExtension(): unknown {
        return null;
      }

      vertexAttribPointer(): void {}
    }

    delete globalRuntime.self;
    delete globalRuntime.window;
    delete globalRuntime.addEventListener;
    delete globalRuntime.removeEventListener;
    delete globalRuntime.dispatchEvent;
    Object.defineProperty(globalRuntime, 'navigator', {
      value: {
        userAgent: 'prelude-agent',
      } satisfies Partial<NonNullable<GlobalWithWeChatPrep['navigator']>>,
      configurable: true,
      writable: true,
    });
    Object.defineProperty(globalRuntime, 'location', {
      value: {
        href: 'https://minigame.weixin.qq.com/prelude',
      } satisfies Partial<NonNullable<GlobalWithWeChatPrep['location']>>,
      configurable: true,
      writable: true,
    });

    globalRuntime.wx = {
      createCanvas(): object {
        return {
          style: {},
          getContext(contextId: string): unknown {
            if (contextId === '2d') {
              return new MockCanvasRenderingContext2D();
            }
            if (contextId === 'webgl' || contextId === 'experimental-webgl') {
              return new MockWebGLRenderingContext();
            }

            return null;
          },
        };
      },
      onTouchStart() {},
      onTouchMove() {},
      onTouchEnd() {},
      onTouchCancel() {},
    };
    prebindScreenCanvas(
      (globalRuntime.wx as {
        createCanvas(): object;
      }).createCanvas(),
    );

    prepareWeChatRuntime();

    expect(globalRuntime.self).toBe(globalRuntime);
    expect(globalRuntime.window).toBe(globalRuntime);
    expect(globalRuntime.addEventListener).toBeTypeOf('function');
    expect(globalRuntime.removeEventListener).toBeTypeOf('function');
    expect(globalRuntime.dispatchEvent).toBeTypeOf('function');
    expect(globalRuntime.navigator).toMatchObject({
      userAgent: 'prelude-agent',
      platform: 'wechat-minigame',
      language: 'zh-CN',
      maxTouchPoints: 5,
      hardwareConcurrency: 4,
    });
    expect(globalRuntime.location).toMatchObject({
      href: 'https://minigame.weixin.qq.com/prelude',
      origin: 'https://minigame.weixin.qq.com',
      pathname: '/',
      search: '',
      hash: '',
    });

    const receivedEvents: string[] = [];
    globalRuntime.addEventListener?.('pointerup', (event) => {
      receivedEvents.push(event?.type ?? 'unknown');
    });

    expect(globalRuntime.dispatchEvent?.({ type: 'pointerup' })).toBe(true);
    expect(receivedEvents).toEqual(['pointerup']);
  });

  test('installs document and fetch shims for the WeChat entrypoint', async () => {
    const createdCanvases: object[] = [];
    const createdImages: object[] = [];
    let touchStartListener:
      | ((event: {
          touches?: Array<Partial<{ clientX: number; clientY: number }>>;
          changedTouches?: Array<Partial<{ clientX: number; clientY: number }>>;
        }) => void)
      | null = null;
    class MockCanvasRenderingContext2D {
      letterSpacing = '0px';
    }
    class MockWebGLRenderingContext {
      readonly ARRAY_BUFFER = 34962;

      readonly ELEMENT_ARRAY_BUFFER = 34963;

      bindBuffer(): void {}

      disableVertexAttribArray(): void {}

      enableVertexAttribArray(): void {}

      getExtension(): unknown {
        return null;
      }

      vertexAttribPointer(): void {}
    }
    class MockWebGL2RenderingContext extends MockWebGLRenderingContext {
      bindVertexArray(): void {}

      createVertexArray(): object {
        return {};
      }

      deleteVertexArray(): void {}
    }
    class MockCanvas {}

    globalRuntime.wx = {
      createCanvas(): object {
        const canvas = {
          kind: 'canvas',
          style: {},
          getContext(contextId: string): unknown {
            if (contextId === '2d') {
              return new MockCanvasRenderingContext2D();
            }
            if (contextId === 'webgl2') {
              return new MockWebGL2RenderingContext();
            }
            if (contextId === 'webgl' || contextId === 'experimental-webgl') {
              return new MockWebGLRenderingContext();
            }

            return null;
          },
        };
        Object.setPrototypeOf(canvas, MockCanvas.prototype);
        createdCanvases.push(canvas);
        return canvas;
      },
      createImage(): object {
        const image = {
          kind: 'image',
          complete: true,
          _src: '',
          get src(): string {
            return this._src;
          },
          set src(value: string) {
            this._src = value;
          },
        };
        createdImages.push(image);
        return image;
      },
      getFileSystemManager() {
        return {
          readFileSync(filePath: string, encoding?: string): string | ArrayBuffer {
            if (encoding === 'utf8') {
              return `<svg data-path="${filePath}"></svg>`;
            }

            return new Uint8Array([1, 2, 3]).buffer;
          },
        };
      },
      onTouchStart(listener: typeof touchStartListener) {
        touchStartListener = listener;
      },
      onTouchMove() {},
      onTouchEnd() {},
      onTouchCancel() {},
    };
    prebindScreenCanvas(
      (globalRuntime.wx as {
        createCanvas(): object;
      }).createCanvas(),
    );

    prepareWeChatRuntime();

    expect(globalRuntime.document).toBeTruthy();
    expect(globalRuntime.URL).toBeTypeOf('function');
    expect(globalRuntime.fetch).toBeTypeOf('function');
    expect(globalRuntime.createImageBitmap).toBeUndefined();
    expect(globalRuntime.Image).toBeTruthy();
    expect(globalRuntime.structuredClone).toBeTypeOf('function');
    expect(globalRuntime.ontouchstart).toBeNull();
    expect(globalRuntime.TouchEvent).toBeTypeOf('function');
    expect(globalRuntime.Intl?.Segmenter).toBeTypeOf('function');
    expect(globalRuntime.HTMLCanvasElement).toBe(MockCanvas);
    expect(globalRuntime.CanvasRenderingContext2D).toBeTypeOf('function');
    expect(globalRuntime.WebGLRenderingContext).toBeTypeOf('function');
    expect(globalRuntime.WebGL2RenderingContext).toBeTypeOf('function');
    expect(globalRuntime.canvas).toBe(createdCanvases[0]);
    expect(globalRuntime.screencanvas).toBe(createdCanvases[0]);
    expect(
      (globalRuntime.document as { querySelector(selector: string): unknown }).querySelector('canvas'),
    ).toBe(globalRuntime.canvas);
    expect(
      (
        globalRuntime.document as { querySelectorAll(selector: string): unknown[] }
      ).querySelectorAll('canvas'),
    ).toEqual([globalRuntime.canvas]);
    expect(
      (
        globalRuntime.document as { getElementsByTagName(tagName: string): unknown[] }
      ).getElementsByTagName('canvas'),
    ).toEqual([globalRuntime.canvas]);
    expect(
      (
        globalRuntime.document as { getElementById(id: string): unknown }
      ).getElementById('__pixi-wechat-screen-canvas'),
    ).toBe(globalRuntime.canvas);
    expect(
      (globalRuntime.GameGlobal as { canvas?: unknown; screencanvas?: unknown } | undefined)
        ?.canvas,
    ).toBe(createdCanvases[0]);
    expect(
      (globalRuntime.document as { createElement(tagName: string): unknown }).createElement('canvas'),
    ).toMatchObject({ kind: 'canvas' });
    expect(
      (globalRuntime.document as { createElement(tagName: string): unknown }).createElement('img'),
    ).toMatchObject({ kind: 'image' });
    const detachedDiv = (
      globalRuntime.document as { createElement(tagName: string): unknown }
    ).createElement('div') as {
      parentNode?: unknown;
      remove(): void;
    };
    const documentBody = (
      globalRuntime.document as {
        body: {
          appendChild(node: unknown): unknown;
          contains(node: unknown): boolean;
          removeChild(node: unknown): unknown;
        };
      }
    ).body;
    expect(documentBody.contains(globalRuntime.canvas)).toBe(true);
    expect(
      (globalRuntime.canvas as { isConnected?: boolean }).isConnected,
    ).toBe(true);
    (
      globalRuntime.canvas as {
        width?: number;
        height?: number;
        style?: Record<string, string>;
        getBoundingClientRect(): { width: number; height: number };
      }
    ).width = 780;
    (
      globalRuntime.canvas as {
        width?: number;
        height?: number;
        style?: Record<string, string>;
        getBoundingClientRect(): { width: number; height: number };
      }
    ).height = 1688;
    (
      globalRuntime.canvas as {
        style?: Record<string, string>;
      }
    ).style = {
      width: '390px',
      height: '844px',
    };
    expect(
      (
        globalRuntime.canvas as {
          getBoundingClientRect(): { width: number; height: number };
        }
      ).getBoundingClientRect(),
    ).toMatchObject({
      left: 0,
      top: 0,
      x: 0,
      y: 0,
      width: 390,
      height: 844,
    });
    const detachedCanvas = (
      globalRuntime.document as { createElement(tagName: string): unknown }
    ).createElement('canvas');
    expect((detachedCanvas as { isConnected?: boolean }).isConnected).toBe(false);
    expect(documentBody.contains(detachedCanvas)).toBe(false);
    documentBody.appendChild(detachedCanvas);
    expect((detachedCanvas as { isConnected?: boolean }).isConnected).toBe(true);
    expect(documentBody.contains(detachedCanvas)).toBe(true);
    documentBody.appendChild(detachedDiv);
    expect(detachedDiv.parentNode).toBe(documentBody);
    expect(documentBody.contains(detachedDiv)).toBe(true);
    detachedDiv.remove();
    expect(detachedDiv.parentNode).toBeNull();
    expect(documentBody.contains(detachedDiv)).toBe(false);
    (globalRuntime.canvas as { remove(): void }).remove();
    expect(documentBody.contains(globalRuntime.canvas)).toBe(false);
    documentBody.appendChild(globalRuntime.canvas);
    expect(documentBody.contains(globalRuntime.canvas)).toBe(true);
    documentBody.removeChild(detachedCanvas);
    expect((detachedCanvas as { isConnected?: boolean }).isConnected).toBe(false);
    expect(documentBody.contains(detachedCanvas)).toBe(false);
    const videoElement = (
      globalRuntime.document as {
        createElement(tagName: string): {
          canPlayType?(mimeType: string): string;
        };
      }
    ).createElement('video');
    expect(globalRuntime.HTMLVideoElement).toBeTypeOf('function');
    expect(videoElement).toBeInstanceOf(
      globalRuntime.HTMLVideoElement as new (...args: never[]) => object,
    );
    expect(videoElement.canPlayType?.('video/mp4')).toBe('');
    const parsedUrl = new (
      globalRuntime.URL as new (
        input: string,
        base?: string,
      ) => { href: string; hostname: string; pathname: string; origin: string }
    )('./assets/ui/text/fixed-copy-glyphs.png', 'https://minigame.weixin.qq.com/game/index.html');
    expect(parsedUrl.href).toBe('https://minigame.weixin.qq.com/game/assets/ui/text/fixed-copy-glyphs.png');
    expect(parsedUrl.hostname).toBe('minigame.weixin.qq.com');
    expect(parsedUrl.pathname).toBe('/game/assets/ui/text/fixed-copy-glyphs.png');
    expect(parsedUrl.origin).toBe('https://minigame.weixin.qq.com');

    const primaryWebGLContext = (
      globalRuntime.canvas as {
        getContext(contextId: string): unknown;
      }
    ).getContext('webgl');
    const freshWebGL2Context = (
      (globalRuntime.document as {
        createElement(tagName: string): {
          getContext(contextId: string): unknown;
        };
      }).createElement('canvas')
    ).getContext('webgl2');
    expect(primaryWebGLContext).toBeInstanceOf(
      globalRuntime.WebGLRenderingContext as new (...args: never[]) => object,
    );
    expect(primaryWebGLContext).not.toBeInstanceOf(
      globalRuntime.WebGL2RenderingContext as new (...args: never[]) => object,
    );
    expect(freshWebGL2Context).toBeInstanceOf(
      globalRuntime.WebGL2RenderingContext as new (...args: never[]) => object,
    );

    const response = await (globalRuntime.fetch as (input: string) => Promise<{ text(): Promise<string> }>)('assets/ui/stamp-ring.svg');
    await expect(response.text()).resolves.toContain('assets/ui/stamp-ring.svg');
    const scriptRelativeResponse = await (
      globalRuntime.fetch as (input: string) => Promise<{ text(): Promise<string> }>
    )('game.js/assets/ui/stamp-ring.svg');
    await expect(scriptRelativeResponse.text()).resolves.toContain('assets/ui/stamp-ring.svg');
    const devtoolsResponse = await (
      globalRuntime.fetch as (input: string) => Promise<{ text(): Promise<string> }>
    )('http://127.0.0.1:12816/game/gameContext/assets/ui/stamp-ring.svg');
    await expect(devtoolsResponse.text()).resolves.toContain('assets/ui/stamp-ring.svg');
    const minigameResponse = await (
      globalRuntime.fetch as (input: string) => Promise<{ text(): Promise<string> }>
    )('https://minigame.weixin.qq.com/assets/ui/stamp-ring.svg');
    await expect(minigameResponse.text()).resolves.toContain('assets/ui/stamp-ring.svg');
    const mirroredMinigameResponse = await (
      globalRuntime.fetch as (input: string) => Promise<{ text(): Promise<string> }>
    )('https://minigame.weixin.qq.com/game/gameContext/assets/ui/stamp-ring.svg');
    await expect(mirroredMinigameResponse.text()).resolves.toContain('assets/ui/stamp-ring.svg');
    const imageElement = new (
      globalRuntime.Image as new () => { src: string }
    )();
    imageElement.src = 'https://minigame.weixin.qq.com/assets/ui/text/fixed-copy-glyphs.png';
    expect(imageElement.src).toBe('assets/ui/text/fixed-copy-glyphs.png');
    imageElement.src = 'game.js/assets/ui/text/fixed-copy-glyphs.png';
    expect(imageElement.src).toBe('assets/ui/text/fixed-copy-glyphs.png');
    imageElement.src =
      'https://developers.weixin.qq.com/minigame/en/introduction/assets/ui/text/fixed-copy-glyphs.png';
    expect(imageElement.src).toBe('assets/ui/text/fixed-copy-glyphs.png');
    expect(
      (
        globalRuntime.canvas as {
          getContext(contextId: string): { getExtension(name: string): unknown };
        }
      )
        .getContext('webgl')
        .getExtension('OES_vertex_array_object'),
    ).toBeTruthy();
    expect(createdCanvases.length).toBeGreaterThanOrEqual(4);
    expect(createdImages.length).toBeGreaterThanOrEqual(2);

    const touchEvents: Array<{ type: string; changedTouches: Array<{ clientX: number }> }> = [];
    (
      globalRuntime.canvas as {
        addEventListener(
          type: string,
          listener: (event: { type: string; changedTouches: Array<{ clientX: number }> }) => void,
        ): void;
      }
    ).addEventListener('touchstart', (event) => {
      touchEvents.push(event);
    });
    touchStartListener?.({
      touches: [{ clientX: 12, clientY: 34 }],
      changedTouches: [{ clientX: 12, clientY: 34 }],
    });
    expect(touchEvents).toHaveLength(1);
    expect(touchEvents[0]?.type).toBe('touchstart');
    expect(touchEvents[0]?.changedTouches[0]?.clientX).toBe(12);
    expect(touchEvents[0]).toBeInstanceOf(
      globalRuntime.TouchEvent as new (...args: never[]) => object,
    );

    const original = {
      nested: { stage: 3, flags: ['tutorial', 'wx'] },
    };
    const cloned = globalRuntime.structuredClone?.(original);
    expect(cloned).toEqual(original);
    expect(cloned).not.toBe(original);
    expect(cloned?.nested).not.toBe(original.nested);

    const Segmenter = globalRuntime.Intl?.Segmenter as new () => {
      segment(input: string): Iterable<{ segment: string }>;
    };
    const segmenter = new Segmenter();
    expect(Array.from(segmenter.segment('印灵排布')).map((entry) => entry.segment)).toEqual([
      '印',
      '灵',
      '排',
      '布',
    ]);
  });

  test('augments an existing runtime document with event-target methods', async () => {
    const existingBody = {
      style: {},
    };
    Object.defineProperty(existingBody, 'isConnected', {
      configurable: true,
      get() {
        return false;
      },
    });
    Object.defineProperty(existingBody, 'ownerDocument', {
      configurable: true,
      get() {
        return null;
      },
    });
    Object.defineProperty(existingBody, 'parentNode', {
      configurable: true,
      get() {
        return null;
      },
    });
    const existingDocument = {
      body: existingBody,
    };

    globalRuntime.document = existingDocument as typeof globalRuntime.document;
    globalRuntime.wx = {
      createCanvas(): object {
        return {
          style: {},
          getContext(): object {
            return {};
          },
        };
      },
      createImage(): object {
        return {
          complete: true,
        };
      },
      getFileSystemManager() {
        return {
          readFileSync(): ArrayBuffer {
            return new Uint8Array([1, 2, 3]).buffer;
          },
        };
      },
      onTouchStart() {},
      onTouchMove() {},
      onTouchEnd() {},
      onTouchCancel() {},
    };
    prebindScreenCanvas(
      (globalRuntime.wx as {
        createCanvas(): object;
      }).createCanvas(),
    );

    prepareWeChatRuntime();

    expect(globalRuntime.document).toBe(existingDocument);
    expect(globalRuntime.document?.addEventListener).toBeTypeOf('function');
    expect(globalRuntime.document?.removeEventListener).toBeTypeOf('function');
    expect(globalRuntime.document?.dispatchEvent).toBeTypeOf('function');
    expect(globalRuntime.document?.body.isConnected).toBe(true);
    expect(globalRuntime.document?.body.ownerDocument).toBe(existingDocument);
    expect(globalRuntime.document?.body.parentNode).toBe(existingDocument);
    expect(globalRuntime.document?.body.contains?.(globalRuntime.canvas)).toBe(true);
  });

  test('forces existing devtools document canvas queries to the primary canvas', async () => {
    const misleadingCanvas = {
      id: 'wrong-canvas',
      style: {},
      getContext(): object {
        return {};
      },
    };
    const existingDocument = {
      querySelector(selector: string): unknown {
        return selector === 'canvas' ? misleadingCanvas : null;
      },
      querySelectorAll(selector: string): unknown[] {
        return selector === 'canvas' ? [misleadingCanvas] : [];
      },
      getElementsByTagName(tagName: string): unknown[] {
        return tagName === 'canvas' ? [misleadingCanvas] : [];
      },
      getElementById(id: string): unknown {
        return id === 'wrong-canvas' ? misleadingCanvas : null;
      },
      body: {
        style: {},
        children: [],
        appendChild(node: unknown): unknown {
          return node;
        },
        contains(): boolean {
          return false;
        },
        removeChild(node: unknown): unknown {
          return node;
        },
      },
    };

    globalRuntime.document = existingDocument as typeof globalRuntime.document;
    globalRuntime.wx = {
      createCanvas(): object {
        return {
          id: 'myCanvas',
          style: {},
          getContext(contextId: string): object | null {
            if (contextId === 'webgl' || contextId === '2d' || contextId === 'webgl2') {
              return {};
            }
            return null;
          },
        };
      },
      createImage(): object {
        return {
          complete: true,
        };
      },
      getSystemInfoSync() {
        return {
          platform: 'devtools',
        };
      },
      getFileSystemManager() {
        return {
          readFileSync(): ArrayBuffer {
            return new Uint8Array([1, 2, 3]).buffer;
          },
        };
      },
      onTouchStart() {},
      onTouchMove() {},
      onTouchEnd() {},
      onTouchCancel() {},
    };
    prebindScreenCanvas(
      (globalRuntime.wx as {
        createCanvas(): object;
      }).createCanvas(),
    );

    prepareWeChatRuntime();

    expect(globalRuntime.document?.querySelector?.('canvas')).toBe(globalRuntime.canvas);
    expect(globalRuntime.document?.querySelectorAll?.('canvas')).toEqual([globalRuntime.canvas]);
    expect(globalRuntime.document?.getElementsByTagName?.('canvas')).toEqual([globalRuntime.canvas]);
    expect(
      globalRuntime.document?.getElementById?.(
        (globalRuntime.canvas as { id?: string } | undefined)?.id ?? '',
      ),
    ).toBe(globalRuntime.canvas);
    expect(globalRuntime.document?.body.contains?.(globalRuntime.canvas)).toBe(true);
  });

  test('requires a prebound screen canvas before runtime prep', () => {
    globalRuntime.wx = {
      createCanvas(): object {
        return {
          style: {},
          getContext(): object {
            return {};
          },
        };
      },
      createImage(): object {
        return {
          complete: true,
        };
      },
      getFileSystemManager() {
        return {
          readFileSync(): ArrayBuffer {
            return new Uint8Array([1, 2, 3]).buffer;
          },
        };
      },
      onTouchStart() {},
      onTouchMove() {},
      onTouchEnd() {},
      onTouchCancel() {},
    };

    expect(() => prepareWeChatRuntime()).toThrow(
      /prebound screen canvas/i,
    );
  });

  test('keeps a prebound screen canvas even when document contains other canvases', async () => {
    const screenCanvas = {
      id: 'screen-canvas',
      style: {},
      getContext(): object {
        return {};
      },
    };
    const misleadingCanvas = {
      style: {},
      getContext(): object {
        return {};
      },
    };
    globalRuntime.document = {
      querySelectorAll(selector: string): unknown[] {
        return selector === 'canvas' ? [misleadingCanvas] : [];
      },
      body: {
        style: {},
        children: {
          0: misleadingCanvas,
          length: 1,
        },
        appendChild(node: unknown): unknown {
          return node;
        },
        contains(node: unknown): boolean {
          return node === misleadingCanvas;
        },
        removeChild(node: unknown): unknown {
          return node;
        },
      },
    } as typeof globalRuntime.document;
    globalRuntime.wx = {
      createCanvas(): object {
        return {
          style: {},
          getContext(contextId: string): object | null {
            if (contextId === 'webgl' || contextId === '2d' || contextId === 'webgl2') {
              return {};
            }
            return null;
          },
        };
      },
      createImage(): object {
        return {
          complete: true,
        };
      },
      getFileSystemManager() {
        return {
          readFileSync(): ArrayBuffer {
            return new Uint8Array([1, 2, 3]).buffer;
          },
        };
      },
      onTouchStart() {},
      onTouchMove() {},
      onTouchEnd() {},
      onTouchCancel() {},
    };
    prebindScreenCanvas(screenCanvas);

    prepareWeChatRuntime();

    expect(globalRuntime.canvas).toBe(screenCanvas);
    expect(globalRuntime.screencanvas).toBe(screenCanvas);
    expect(globalRuntime.document?.querySelectorAll?.('canvas')).toEqual([screenCanvas]);
  });

  test('creates offscreen canvases through document.createElement without replacing screen globals', async () => {
    const createdCanvases: object[] = [];
    globalRuntime.wx = {
      createCanvas(): object {
        const canvas = {
          style: {},
          getContext(contextId: string): object | null {
            if (contextId === 'webgl' || contextId === '2d' || contextId === 'webgl2') {
              return {};
            }
            return null;
          },
        };
        createdCanvases.push(canvas);
        return canvas;
      },
      createImage(): object {
        return {
          complete: true,
        };
      },
      getFileSystemManager() {
        return {
          readFileSync(): ArrayBuffer {
            return new Uint8Array([1, 2, 3]).buffer;
          },
        };
      },
      onTouchStart() {},
      onTouchMove() {},
      onTouchEnd() {},
      onTouchCancel() {},
    };
    const screenCanvas = (
      globalRuntime.wx as {
        createCanvas(): object;
      }
    ).createCanvas();
    prebindScreenCanvas(screenCanvas);

    prepareWeChatRuntime();

    const offscreenCanvas = (
      globalRuntime.document as { createElement(tagName: string): unknown }
    ).createElement('canvas');
    expect(offscreenCanvas).not.toBe(screenCanvas);
    expect(globalRuntime.canvas).toBe(screenCanvas);
    expect(globalRuntime.screencanvas).toBe(screenCanvas);
    expect(createdCanvases).toHaveLength(2);
  });

  test('normalizes an existing DevTools canvas rect to logical mini-game coordinates', () => {
    class MockCanvasRenderingContext2D {
      letterSpacing = '0px';
    }
    class MockWebGLRenderingContext {
      readonly ARRAY_BUFFER = 34962;

      readonly ELEMENT_ARRAY_BUFFER = 34963;

      bindBuffer(): void {}

      disableVertexAttribArray(): void {}

      enableVertexAttribArray(): void {}

      getExtension(): unknown {
        return null;
      }

      vertexAttribPointer(): void {}
    }

    const existingCanvas = {
      width: 1170,
      height: 2532,
      style: {
        width: '390px',
        height: '844px',
      },
      getContext(contextId: string): unknown {
        if (contextId === '2d') {
          return new MockCanvasRenderingContext2D();
        }
        if (contextId === 'webgl' || contextId === 'experimental-webgl') {
          return new MockWebGLRenderingContext();
        }

        return null;
      },
      getBoundingClientRect() {
        return {
          left: 28,
          top: 44,
          right: 340,
          bottom: 720,
          width: 312,
          height: 676,
          x: 28,
          y: 44,
        };
      },
    };

    globalRuntime.canvas = existingCanvas;
    globalRuntime.screencanvas = existingCanvas;
    globalRuntime.GameGlobal = {
      canvas: existingCanvas,
      screencanvas: existingCanvas,
    };
    globalRuntime.wx = {
      createCanvas(): object {
        return {
          style: {},
          getContext(contextId: string): unknown {
            if (contextId === '2d') {
              return new MockCanvasRenderingContext2D();
            }
            if (contextId === 'webgl' || contextId === 'experimental-webgl') {
              return new MockWebGLRenderingContext();
            }

            return null;
          },
        };
      },
      onTouchStart() {},
      onTouchMove() {},
      onTouchEnd() {},
      onTouchCancel() {},
    };

    prepareWeChatRuntime();

    expect(globalRuntime.canvas).toBe(existingCanvas);
    expect(
      (
        globalRuntime.canvas as {
          getBoundingClientRect(): {
            left: number;
            top: number;
            right: number;
            bottom: number;
            width: number;
            height: number;
            x: number;
            y: number;
          };
        }
      ).getBoundingClientRect(),
    ).toEqual({
      left: 0,
      top: 0,
      right: 390,
      bottom: 844,
      width: 390,
      height: 844,
      x: 0,
      y: 0,
    });

    existingCanvas.style.width = '412px';
    existingCanvas.style.height = '915px';

    expect(
      (
        globalRuntime.canvas as {
          getBoundingClientRect(): {
            left: number;
            top: number;
            right: number;
            bottom: number;
            width: number;
            height: number;
            x: number;
            y: number;
          };
        }
      ).getBoundingClientRect(),
    ).toEqual({
      left: 0,
      top: 0,
      right: 412,
      bottom: 915,
      width: 412,
      height: 915,
      x: 0,
      y: 0,
    });
  });

  test('prefers explicit x and y touch aliases when DevTools provides them', () => {
    let touchStartListener:
      | ((event: {
          touches?: Array<Partial<{ x: number; y: number; clientX: number; clientY: number }>>;
          changedTouches?: Array<
            Partial<{ x: number; y: number; clientX: number; clientY: number }>
          >;
        }) => void)
      | null = null;
    class MockCanvasRenderingContext2D {
      letterSpacing = '0px';
    }
    class MockWebGLRenderingContext {
      readonly ARRAY_BUFFER = 34962;

      readonly ELEMENT_ARRAY_BUFFER = 34963;

      bindBuffer(): void {}

      disableVertexAttribArray(): void {}

      enableVertexAttribArray(): void {}

      getExtension(): unknown {
        return null;
      }

      vertexAttribPointer(): void {}
    }

    const screenCanvas = {
      style: {},
      getContext(contextId: string): unknown {
        if (contextId === '2d') {
          return new MockCanvasRenderingContext2D();
        }
        if (contextId === 'webgl' || contextId === 'experimental-webgl') {
          return new MockWebGLRenderingContext();
        }

        return null;
      },
    };

    globalRuntime.wx = {
      createCanvas(): object {
        return {
          style: {},
          getContext(contextId: string): unknown {
            if (contextId === '2d') {
              return new MockCanvasRenderingContext2D();
            }
            if (contextId === 'webgl' || contextId === 'experimental-webgl') {
              return new MockWebGLRenderingContext();
            }

            return null;
          },
        };
      },
      onTouchStart(listener: typeof touchStartListener) {
        touchStartListener = listener;
      },
      onTouchMove() {},
      onTouchEnd() {},
      onTouchCancel() {},
    };
    prebindScreenCanvas(screenCanvas);

    prepareWeChatRuntime();

    const touchEvents: Array<{ changedTouches: Array<{ clientX: number; clientY: number }> }> =
      [];
    (
      globalRuntime.canvas as {
        addEventListener(
          type: string,
          listener: (event: {
            changedTouches: Array<{ clientX: number; clientY: number }>;
          }) => void,
        ): void;
      }
    ).addEventListener('touchstart', (event) => {
      touchEvents.push(event);
    });

    touchStartListener?.({
      touches: [{ x: 48, y: 96, clientX: 248, clientY: 396 }],
      changedTouches: [{ x: 48, y: 96, clientX: 248, clientY: 396 }],
    });

    expect(touchEvents).toHaveLength(1);
    expect(touchEvents[0]?.changedTouches[0]).toMatchObject({
      clientX: 48,
      clientY: 96,
    });
  });

  test('scales DevTools touch coordinates by renderer resolution before dispatch', () => {
    let touchStartListener:
      | ((event: {
          touches?: Array<Partial<{ clientX: number; clientY: number }>>;
          changedTouches?: Array<Partial<{ clientX: number; clientY: number }>>;
        }) => void)
      | null = null;
    class MockCanvasRenderingContext2D {
      letterSpacing = '0px';
    }
    class MockWebGLRenderingContext {
      readonly ARRAY_BUFFER = 34962;

      readonly ELEMENT_ARRAY_BUFFER = 34963;

      bindBuffer(): void {}

      disableVertexAttribArray(): void {}

      enableVertexAttribArray(): void {}

      getExtension(): unknown {
        return null;
      }

      vertexAttribPointer(): void {}
    }

    const screenCanvas = {
      style: {},
      getContext(contextId: string): unknown {
        if (contextId === '2d') {
          return new MockCanvasRenderingContext2D();
        }
        if (contextId === 'webgl' || contextId === 'experimental-webgl') {
          return new MockWebGLRenderingContext();
        }

        return null;
      },
    };

    globalRuntime.__pixiWeChatRendererDebug__ = {
      resolution: 2,
    };
    globalRuntime.wx = {
      createCanvas(): object {
        return {
          style: {},
          getContext(contextId: string): unknown {
            if (contextId === '2d') {
              return new MockCanvasRenderingContext2D();
            }
            if (contextId === 'webgl' || contextId === 'experimental-webgl') {
              return new MockWebGLRenderingContext();
            }

            return null;
          },
        };
      },
      getSystemInfoSync() {
        return {
          windowWidth: 390,
          windowHeight: 844,
          pixelRatio: 3,
          platform: 'devtools',
        };
      },
      onTouchStart(listener: typeof touchStartListener) {
        touchStartListener = listener;
      },
      onTouchMove() {},
      onTouchEnd() {},
      onTouchCancel() {},
    };
    prebindScreenCanvas(screenCanvas);

    prepareWeChatRuntime();

    const touchEvents: Array<{ changedTouches: Array<{ clientX: number; clientY: number }> }> =
      [];
    (
      globalRuntime.canvas as {
        addEventListener(
          type: string,
          listener: (event: {
            changedTouches: Array<{ clientX: number; clientY: number }>;
          }) => void,
        ): void;
      }
    ).addEventListener('touchstart', (event) => {
      touchEvents.push(event);
    });

    touchStartListener?.({
      touches: [{ clientX: 48, clientY: 96 }],
      changedTouches: [{ clientX: 48, clientY: 96 }],
    });

    expect(touchEvents).toHaveLength(1);
    expect(touchEvents[0]?.changedTouches[0]).toMatchObject({
      clientX: 96,
      clientY: 192,
    });
  });

  test('classifies primary WebGL contexts by capability even when probe canvases use a different constructor', () => {
    class PrimaryWebGLRenderingContext {
      readonly ARRAY_BUFFER = 34962;

      readonly ELEMENT_ARRAY_BUFFER = 34963;

      bindBuffer(): void {}

      disableVertexAttribArray(): void {}

      enableVertexAttribArray(): void {}

      getExtension(): unknown {
        return null;
      }

      vertexAttribPointer(): void {}
    }

    class ProbeWebGLRenderingContext extends PrimaryWebGLRenderingContext {}

    class ProbeWebGL2RenderingContext extends ProbeWebGLRenderingContext {
      bindVertexArray(): void {}

      createVertexArray(): object {
        return {};
      }

      deleteVertexArray(): void {}
    }

    const primaryCanvas = {
      style: {},
      getContext(contextId: string): unknown {
        if (contextId === 'webgl' || contextId === 'experimental-webgl') {
          return new PrimaryWebGLRenderingContext();
        }

        return null;
      },
    };

    globalRuntime.canvas = primaryCanvas;
    globalRuntime.screencanvas = primaryCanvas;
    globalRuntime.GameGlobal = {
      canvas: primaryCanvas,
      screencanvas: primaryCanvas,
    };
    globalRuntime.wx = {
      createCanvas(): object {
        return {
          style: {},
          getContext(contextId: string): unknown {
            if (contextId === '2d') {
              return { constructor: class MockCanvasRenderingContext2D {} };
            }
            if (contextId === 'webgl2') {
              return new ProbeWebGL2RenderingContext();
            }
            if (contextId === 'webgl' || contextId === 'experimental-webgl') {
              return new ProbeWebGLRenderingContext();
            }

            return null;
          },
        };
      },
      createImage(): object {
        return { complete: true };
      },
      getFileSystemManager() {
        return {
          readFileSync(_filePath: string, encoding?: string): string | ArrayBuffer {
            if (encoding === 'utf8') {
              return '<svg></svg>';
            }

            return new Uint8Array([1, 2, 3]).buffer;
          },
        };
      },
      onTouchStart() {},
      onTouchMove() {},
      onTouchEnd() {},
      onTouchCancel() {},
    };

    prepareWeChatRuntime();

    const primaryWebGLContext = (
      globalRuntime.canvas as { getContext(contextId: string): unknown }
    ).getContext('webgl');
    const probeWebGL2Context = (
      globalRuntime.document as {
        createElement(tagName: string): {
          getContext(contextId: string): unknown;
        };
      }
    ).createElement('canvas').getContext('webgl2');

    expect(primaryWebGLContext).toBeInstanceOf(
      globalRuntime.WebGLRenderingContext as new (...args: never[]) => object,
    );
    expect(primaryWebGLContext).not.toBeInstanceOf(
      globalRuntime.WebGL2RenderingContext as new (...args: never[]) => object,
    );
    expect(probeWebGL2Context).toBeInstanceOf(
      globalRuntime.WebGL2RenderingContext as new (...args: never[]) => object,
    );
  });

  test('overrides pre-existing WebGL globals with matcher-based classifiers', () => {
    class WrongWebGLRenderingContext {}
    class WrongWebGL2RenderingContext {}

    class ActualWebGLRenderingContext {
      readonly ARRAY_BUFFER = 34962;

      readonly ELEMENT_ARRAY_BUFFER = 34963;

      bindBuffer(): void {}

      disableVertexAttribArray(): void {}

      enableVertexAttribArray(): void {}

      getExtension(): unknown {
        return null;
      }

      vertexAttribPointer(): void {}
    }

    const screenCanvas = {
      style: {},
      getContext(contextId: string): unknown {
        if (contextId === '2d') {
          return { constructor: class MockCanvasRenderingContext2D {} };
        }
        if (contextId === 'webgl' || contextId === 'experimental-webgl') {
          return new ActualWebGLRenderingContext();
        }

        return null;
      },
    };

    globalRuntime.WebGLRenderingContext = WrongWebGLRenderingContext;
    globalRuntime.WebGL2RenderingContext = WrongWebGL2RenderingContext;
    globalRuntime.wx = {
      createCanvas(): object {
        return {
          style: {},
          getContext(contextId: string): unknown {
            if (contextId === '2d') {
              return { constructor: class MockCanvasRenderingContext2D {} };
            }
            if (contextId === 'webgl' || contextId === 'experimental-webgl') {
              return new ActualWebGLRenderingContext();
            }

            return null;
          },
        };
      },
      createImage(): object {
        return { complete: true };
      },
      getFileSystemManager() {
        return {
          readFileSync(_filePath: string, encoding?: string): string | ArrayBuffer {
            if (encoding === 'utf8') {
              return '<svg></svg>';
            }

            return new Uint8Array([1, 2, 3]).buffer;
          },
        };
      },
      onTouchStart() {},
      onTouchMove() {},
      onTouchEnd() {},
      onTouchCancel() {},
    };
    prebindScreenCanvas(screenCanvas);

    prepareWeChatRuntime();

    const webglContext = (
      globalRuntime.canvas as { getContext(contextId: string): unknown }
    ).getContext('webgl');

    expect(globalRuntime.WebGLRenderingContext).not.toBe(WrongWebGLRenderingContext);
    expect(globalRuntime.WebGL2RenderingContext).not.toBe(WrongWebGL2RenderingContext);
    expect(globalRuntime.createImageBitmap).toBeUndefined();
    expect(webglContext).toBeInstanceOf(
      globalRuntime.WebGLRenderingContext as new (...args: never[]) => object,
    );
    expect(webglContext).not.toBeInstanceOf(
      globalRuntime.WebGL2RenderingContext as new (...args: never[]) => object,
    );
  });
});
