import {
  getWeChatWebGLCompatInfo,
  installWeChatCanvasGetContextCompat,
  installWeChatCreateCanvasCompat,
} from './wechatWebGLCompat';
import { logWeChatDebug } from './wechatDebug';

type Listener = (event?: { type: string }) => void;

interface LocalFetchResponse {
  ok: boolean;
  status: number;
  statusText: string;
  url: string;
  text(): Promise<string>;
  json(): Promise<unknown>;
  arrayBuffer(): Promise<ArrayBuffer>;
  blob?(): Promise<Blob>;
}

interface ListenerMap {
  [eventType: string]: Set<Listener> | undefined;
}

interface EventCapable {
  addEventListener(type: string, listener: Listener): void;
  removeEventListener(type: string, listener: Listener): void;
  dispatchEvent(event: { type: string }): boolean;
}

interface DomNodeLike {
  children?: ArrayLike<unknown>;
  isConnected?: boolean;
  __pixiWeChatDomChildren__?: unknown[];
  ownerDocument?: unknown;
  parentNode?: unknown;
  remove?(): void;
}

interface TouchLike {
  identifier: number;
  clientX: number;
  clientY: number;
  pageX: number;
  pageY: number;
  screenX: number;
  screenY: number;
  force?: number;
  radiusX?: number;
  radiusY?: number;
}

interface TouchCoordinateAliases {
  x?: number;
  y?: number;
  offsetX?: number;
  offsetY?: number;
}

interface TouchEventInitLike {
  type: string;
  touches: TouchLike[];
  changedTouches: TouchLike[];
  targetTouches?: TouchLike[];
  target?: unknown;
}

interface WeChatTouchPayload {
  touches?: Array<Partial<TouchLike> & TouchCoordinateAliases>;
  changedTouches?: Array<Partial<TouchLike> & TouchCoordinateAliases>;
}

interface IntlSegmentDataLike {
  segment: string;
}

interface IntlSegmenterLike {
  segment(input: string): Iterable<IntlSegmentDataLike>;
}

interface IntlSegmenterConstructorLike {
  new (locales?: unknown, options?: unknown): IntlSegmenterLike;
}

interface IntlLike {
  Segmenter?: IntlSegmenterConstructorLike;
}

interface WeChatTouchAPI {
  onTouchStart?(listener: (event: WeChatTouchPayload) => void): void;
  onTouchMove?(listener: (event: WeChatTouchPayload) => void): void;
  onTouchEnd?(listener: (event: WeChatTouchPayload) => void): void;
  onTouchCancel?(listener: (event: WeChatTouchPayload) => void): void;
}

interface FileSystemManagerLike {
  readFileSync(filePath: string, encoding?: string): string | ArrayBuffer;
}

interface CanvasLike {
  width?: number;
  height?: number;
  id?: string;
  isConnected?: boolean;
  nodeName?: string;
  style?: Record<string, string>;
  tagName?: string;
  type?: string;
  getContext?(contextId: string, options?: unknown): unknown;
  getBoundingClientRect?(): {
    x?: number;
    y?: number;
    top: number;
    left: number;
    right: number;
    bottom: number;
    width: number;
    height: number;
  };
  addEventListener?(type: string, listener: Listener): void;
  removeEventListener?(type: string, listener: Listener): void;
}

interface RectLike {
  x?: number;
  y?: number;
  top?: number;
  left?: number;
  right?: number;
  bottom?: number;
  width?: number;
  height?: number;
}

interface PrimaryCanvasCandidate {
  canvas: CanvasLike;
  source: string;
}

interface WebGLContextMatcherLike {
  ARRAY_BUFFER?: number;
  ELEMENT_ARRAY_BUFFER?: number;
  bindBuffer?: unknown;
  bindVertexArray?: unknown;
  createVertexArray?: unknown;
  deleteVertexArray?: unknown;
  getExtension?: unknown;
  vertexAttribPointer?: unknown;
}

interface CanvasRenderingContext2DMatcherLike {
  clearRect?: unknown;
  fillRect?: unknown;
  getImageData?: unknown;
  measureText?: unknown;
  putImageData?: unknown;
}

interface ImageLike {
  src?: string;
  width?: number;
  height?: number;
  complete?: boolean;
  onload?: (() => void) | null;
  onerror?: ((error?: unknown) => void) | null;
  decode?(): Promise<void>;
  addEventListener?(type: string, listener: Listener): void;
  removeEventListener?(type: string, listener: Listener): void;
}

interface VideoLike {
  autoplay?: boolean;
  controls?: boolean;
  crossOrigin?: string | null;
  currentTime?: number;
  duration?: number;
  ended?: boolean;
  height?: number;
  loop?: boolean;
  muted?: boolean;
  paused?: boolean;
  playsInline?: boolean;
  preload?: string;
  readyState?: number;
  src?: string;
  videoHeight?: number;
  videoWidth?: number;
  width?: number;
  canPlayType?(mimeType: string): string;
  load?(): void;
  pause?(): void;
  play?(): Promise<void>;
  addEventListener?(type: string, listener: Listener): void;
  removeEventListener?(type: string, listener: Listener): void;
}

type WeChatRuntimeGlobal = typeof globalThis & {
  self?: typeof globalThis;
  window?: typeof globalThis;
  canvas?: CanvasLike;
  screencanvas?: CanvasLike;
  sharedCanvas?: CanvasLike;
  GameGlobal?: {
    canvas?: CanvasLike;
    screencanvas?: CanvasLike;
    sharedCanvas?: CanvasLike;
  };
  document?: {
    body: {
      style: Record<string, string>;
      children?: unknown[];
      appendChild(node: unknown): unknown;
      contains(node: unknown): boolean;
      removeChild(node: unknown): unknown;
    };
    head?: {
      style?: Record<string, string>;
      children?: unknown[];
      appendChild?(node: unknown): unknown;
      removeChild?(node: unknown): unknown;
    };
    fonts?: {
      ready: Promise<void>;
      addEventListener(type: string, listener: Listener): void;
      removeEventListener(type: string, listener: Listener): void;
    };
    baseURI?: string;
    createElement(tagName: string): unknown;
    getElementById?(id: string): unknown;
    getElementsByTagName?(tagName: string): ArrayLike<unknown>;
    querySelector?(selector: string): unknown;
    querySelectorAll?(selector: string): ArrayLike<unknown>;
    documentElement?: unknown;
    hidden?: boolean;
    location?: unknown;
    readyState?: string;
    visibilityState?: string;
  } & EventCapable;
  navigator?: {
    userAgent: string;
    platform: string;
    hardwareConcurrency?: number;
    language: string;
    maxTouchPoints?: number;
  };
  location?: {
    href: string;
    origin: string;
    pathname: string;
    search?: string;
    hash?: string;
  };
  Image?: new () => object;
  HTMLImageElement?: new () => object;
  HTMLVideoElement?: new () => object;
  HTMLCanvasElement?: new () => object;
  CanvasRenderingContext2D?: new () => object;
  WebGLRenderingContext?: new () => object;
  WebGL2RenderingContext?: new () => object;
  TouchEvent?: new (type: string, init?: TouchEventInitLike) => object;
  Intl?: IntlLike;
  ontouchstart?: ((event: unknown) => void) | null;
  fetch?: (...args: unknown[]) => Promise<unknown>;
  URL?: new (input: string, base?: string | { href?: string }) => {
    hash: string;
    host: string;
    hostname: string;
    href: string;
    origin: string;
    pathname: string;
    protocol: string;
    search: string;
    toJSON(): string;
    toString(): string;
  };
  createImageBitmap?: unknown;
  performance?: {
    now(): number;
  };
  structuredClone?: <T>(value: T) => T;
  addEventListener?: (type: string, listener: Listener) => void;
  removeEventListener?: (type: string, listener: Listener) => void;
  dispatchEvent?: (event: { type: string }) => boolean;
  requestAnimationFrame?: (callback: (timestamp: number) => void) => number;
  cancelAnimationFrame?: (handle: number) => void;
  __pixiWeChatRendererDebug__?: {
    resolution?: number;
  };
  __pixiWeChatCreateOffscreenCanvas?: () => CanvasLike;
  __pixiWeChatRuntimePrepared?: boolean;
  __pixiWeChatScreenCanvas?: CanvasLike;
};

const isRenderableCanvas = (
  candidate: CanvasLike | undefined,
): candidate is CanvasLike & Required<Pick<CanvasLike, 'getContext'>> => {
  if (!candidate) {
    return false;
  }

  return typeof candidate.getContext === 'function';
};

const canvasRectCompatInstalled = new WeakSet<object>();

const getCanvasRect = (candidate: CanvasLike): RectLike | null => {
  try {
    return typeof candidate.getBoundingClientRect === 'function'
      ? candidate.getBoundingClientRect()
      : null;
  } catch {
    return null;
  }
};

const summarizePrimaryCanvasCandidate = (
  candidate: PrimaryCanvasCandidate,
): Record<string, number | string | boolean | undefined | null> => {
  const rect = getCanvasRect(candidate.canvas);
  return {
    source: candidate.source,
    isConnected: (candidate.canvas as { isConnected?: boolean }).isConnected ?? null,
    width: readFiniteNumber(candidate.canvas.width),
    height: readFiniteNumber(candidate.canvas.height),
    styleWidth: candidate.canvas.style?.width ?? null,
    styleHeight: candidate.canvas.style?.height ?? null,
    rectWidth: readFiniteNumber(rect?.width),
    rectHeight: readFiniteNumber(rect?.height),
  };
};

const resolvePreboundScreenCanvas = (
  runtime: WeChatRuntimeGlobal,
): PrimaryCanvasCandidate | null => {
  const candidates: Array<[string, CanvasLike | undefined]> = [
    ['globalThis.__pixiWeChatScreenCanvas', runtime.__pixiWeChatScreenCanvas],
    ['globalThis.canvas', runtime.canvas],
    ['globalThis.screencanvas', runtime.screencanvas],
    ['GameGlobal.canvas', runtime.GameGlobal?.canvas],
    ['GameGlobal.screencanvas', runtime.GameGlobal?.screencanvas],
  ];

  for (const [source, candidate] of candidates) {
    if (!isRenderableCanvas(candidate)) {
      continue;
    }

    return {
      canvas: candidate,
      source,
    };
  }

  return null;
};

const summarizePrimaryCanvasIdentity = (
  runtime: WeChatRuntimeGlobal,
  canvas: CanvasLike,
): Record<string, boolean | number | string | null> => {
  const readStringProperty = (
    target: unknown,
    key: string,
  ): string | null => {
    if (!target || (typeof target !== 'object' && typeof target !== 'function')) {
      return null;
    }

    try {
      const value = Reflect.get(target as object, key);
      return typeof value === 'string' ? value : null;
    } catch {
      return null;
    }
  };
  const readBooleanComparison = (
    callback: () => boolean,
  ): boolean => {
    try {
      return callback();
    } catch {
      return false;
    }
  };
  const prototype = Object.getPrototypeOf(canvas as object) as
    | { constructor?: { name?: string } }
    | null;
  const prototypeOfPrototype = prototype
    ? (Object.getPrototypeOf(prototype as object) as
        | { constructor?: { name?: string }; tagName?: string; nodeName?: string }
        | null)
    : null;
  const documentCanvas =
    typeof runtime.document?.querySelector === 'function'
      ? (runtime.document.querySelector('canvas') as unknown)
      : null;

  return {
    traceId:
      typeof (canvas as { __pixiWeChatTraceId?: unknown }).__pixiWeChatTraceId === 'number'
        ? ((canvas as { __pixiWeChatTraceId?: number }).__pixiWeChatTraceId ?? null)
        : null,
    id: canvas.id ?? null,
    constructorName: (canvas as { constructor?: { name?: string } }).constructor?.name ?? null,
    prototypeConstructorName: prototype?.constructor?.name ?? null,
    prototypeOfPrototypeConstructorName: prototypeOfPrototype?.constructor?.name ?? null,
    prototypeOfPrototypeTagName: readStringProperty(prototypeOfPrototype, 'tagName'),
    prototypeOfPrototypeNodeName: readStringProperty(prototypeOfPrototype, 'nodeName'),
    tagName: canvas.tagName ?? null,
    nodeName: canvas.nodeName ?? null,
    querySelectorCanvasMatches: documentCanvas === canvas,
    bodyContainsCanvas: readBooleanComparison(() =>
      typeof runtime.document?.body?.contains === 'function'
        ? runtime.document.body.contains(canvas)
        : false,
    ),
    ownerDocumentMatches: getDomNodeOwnerDocument(canvas) === runtime.document,
  };
};

const isObjectLike = (value: unknown): value is Record<PropertyKey, unknown> =>
  (typeof value === 'object' && value !== null) || typeof value === 'function';

const setDomNodeLink = (
  node: unknown,
  key: keyof DomNodeLike,
  value: unknown,
): void => {
  if (!isObjectLike(node)) {
    return;
  }

  Object.defineProperty(node, key, {
    value,
    configurable: true,
    writable: true,
  });
};

const getDomNodeParent = (node: unknown): unknown =>
  isObjectLike(node)
    ? (node as DomNodeLike).parentNode
    : undefined;

const getDomNodeOwnerDocument = (node: unknown): unknown =>
  isObjectLike(node)
    ? (node as DomNodeLike).ownerDocument
    : undefined;

const createManagedDomChildrenStore = (node: DomNodeLike): unknown[] => {
  const nativeChildren = node.children;
  if (Array.isArray(nativeChildren)) {
    Object.defineProperty(node, '__pixiWeChatDomChildren__', {
      value: nativeChildren,
      configurable: true,
      writable: true,
    });
    return nativeChildren;
  }

  const initialChildren =
    nativeChildren &&
    typeof nativeChildren === 'object' &&
    typeof nativeChildren.length === 'number'
      ? Array.from(nativeChildren)
      : [];

  Object.defineProperty(node, '__pixiWeChatDomChildren__', {
    value: initialChildren,
    configurable: true,
    writable: true,
  });

  return initialChildren;
};

const getManagedDomChildren = (node: DomNodeLike): unknown[] =>
  Array.isArray(node.__pixiWeChatDomChildren__)
    ? node.__pixiWeChatDomChildren__
    : createManagedDomChildrenStore(node);

const setDomTreeConnection = (
  node: unknown,
  connected: boolean,
): void => {
  if (!isObjectLike(node)) {
    return;
  }

  setDomNodeLink(node, 'isConnected', connected);
  for (const child of getManagedDomChildren(node as DomNodeLike)) {
    setDomTreeConnection(child, connected);
  }
};

const parsePixelSize = (value: string | undefined): number | null => {
  if (!value) {
    return null;
  }

  const parsed = Number.parseFloat(value);

  return Number.isFinite(parsed) ? parsed : null;
};

const normalizeRectMetric = (
  value: number | undefined,
  fallback: number,
): number => (typeof value === 'number' && Number.isFinite(value) ? value : fallback);

const readFiniteNumber = (value: unknown): number | null =>
  typeof value === 'number' && Number.isFinite(value)
    ? value
    : null;

const installCanvasBoundingClientRectCompat = (canvas: CanvasLike): void => {
  if (canvasRectCompatInstalled.has(canvas as object)) {
    return;
  }
  canvasRectCompatInstalled.add(canvas as object);

  const nativeGetBoundingClientRect =
    typeof canvas.getBoundingClientRect === 'function'
      ? canvas.getBoundingClientRect.bind(canvas)
      : null;

  Object.defineProperty(canvas, 'getBoundingClientRect', {
    configurable: true,
    writable: true,
    value: (): Required<RectLike> => {
      const nativeRect = nativeGetBoundingClientRect?.() as RectLike | undefined;
      const styleWidth = parsePixelSize(canvas.style?.width);
      const styleHeight = parsePixelSize(canvas.style?.height);

      if (styleWidth !== null || styleHeight !== null) {
        const width = styleWidth ?? normalizeRectMetric(nativeRect?.width, Number(canvas.width ?? 0));
        const height =
          styleHeight ?? normalizeRectMetric(nativeRect?.height, Number(canvas.height ?? 0));

        return {
          top: 0,
          left: 0,
          right: width,
          bottom: height,
          width,
          height,
          x: 0,
          y: 0,
        };
      }

      const width = normalizeRectMetric(nativeRect?.width, Number(canvas.width ?? 0));
      const height = normalizeRectMetric(nativeRect?.height, Number(canvas.height ?? 0));
      const left = normalizeRectMetric(nativeRect?.left ?? nativeRect?.x, 0);
      const top = normalizeRectMetric(nativeRect?.top ?? nativeRect?.y, 0);

      return {
        top,
        left,
        right: normalizeRectMetric(nativeRect?.right, left + width),
        bottom: normalizeRectMetric(nativeRect?.bottom, top + height),
        width,
        height,
        x: normalizeRectMetric(nativeRect?.x, left),
        y: normalizeRectMetric(nativeRect?.y, top),
      };
    },
  });
};

const isWeChatDevtoolsRuntime = (): boolean => {
  try {
    const platform = wx.getSystemInfoSync?.().platform?.toLowerCase();
    return platform === 'devtools';
  } catch {
    return false;
  }
};

const scaleTouchCoordinates = (touch: TouchLike, scale: number): TouchLike => ({
  ...touch,
  clientX: touch.clientX * scale,
  clientY: touch.clientY * scale,
  pageX: touch.pageX * scale,
  pageY: touch.pageY * scale,
  screenX: touch.screenX * scale,
  screenY: touch.screenY * scale,
});

const nodeContainsDescendant = (root: unknown, node: unknown): boolean => {
  let current: unknown = node;

  while (current) {
    if (current === root) {
      return true;
    }

    current = getDomNodeParent(current);
  }

  return false;
};

const appendDomChild = (
  parent: DomNodeLike & { ownerDocument?: unknown },
  child: unknown,
): unknown => {
  const children = getManagedDomChildren(parent);
  if (!children.includes(child)) {
    children.push(child);
  }

  setDomNodeLink(child, 'parentNode', parent);
  if (parent.ownerDocument !== undefined) {
    setDomNodeLink(child, 'ownerDocument', parent.ownerDocument);
  }
  setDomTreeConnection(child, parent.isConnected === true);

  return child;
};

const removeDomChild = (
  parent: DomNodeLike,
  child: unknown,
): unknown => {
  const children = getManagedDomChildren(parent);
  const index = children.indexOf(child);
  if (index >= 0) {
    children.splice(index, 1);
  }

  if (getDomNodeParent(child) === parent) {
    setDomNodeLink(child, 'parentNode', null);
  }
  setDomTreeConnection(child, false);

  return child;
};

const installDomNodeRemoveCompat = <T extends object>(node: T): T => {
  const domNode = node as T & DomNodeLike;

  if (typeof domNode.remove !== 'function') {
    Object.defineProperty(domNode, 'remove', {
      configurable: true,
      writable: true,
      value: (): void => {
        const parent = getDomNodeParent(domNode) as
          | (DomNodeLike & { removeChild?(child: unknown): unknown })
          | undefined;

        if (typeof parent?.removeChild === 'function') {
          parent.removeChild(domNode);
          return;
        }

        setDomNodeLink(domNode, 'parentNode', null);
        setDomTreeConnection(domNode, false);
      },
    });
  }

  return node;
};

const installPrimaryCanvas = (
  runtime: WeChatRuntimeGlobal,
  canvas: CanvasLike,
): void => {
  installCanvasPrototypeBridge(canvas);
  installWeChatCanvasGetContextCompat(canvas);
  installCanvasBoundingClientRectCompat(canvas);
  const interactiveCanvas = installEventTarget(canvas);
  installDomNodeRemoveCompat(interactiveCanvas as object);
  if (typeof interactiveCanvas.id !== 'string' || interactiveCanvas.id.length === 0) {
    Object.defineProperty(interactiveCanvas, 'id', {
      value: WECHAT_PRIMARY_CANVAS_ID,
      configurable: true,
      writable: true,
    });
  }
  defineGlobalValue(runtime, '__pixiWeChatScreenCanvas', interactiveCanvas);
  runtime.canvas = interactiveCanvas;
  runtime.screencanvas = interactiveCanvas;
  runtime.GameGlobal ??= {};
  runtime.GameGlobal.canvas = interactiveCanvas;
  runtime.GameGlobal.screencanvas = interactiveCanvas;
};

const createEventTarget = (): EventCapable => {
  const listeners: ListenerMap = {};

  return {
    addEventListener(type: string, listener: Listener): void {
      (listeners[type] ??= new Set()).add(listener);
    },
    removeEventListener(type: string, listener: Listener): void {
      listeners[type]?.delete(listener);
    },
    dispatchEvent(event: { type: string }): boolean {
      for (const listener of listeners[event.type] ?? []) {
        listener(event);
      }
      return true;
    },
  };
};

const installEventTarget = <T extends object>(target: T): T & EventCapable => {
  const eventTarget = createEventTarget();

  Object.defineProperties(target, {
    addEventListener: {
      value: eventTarget.addEventListener,
      configurable: true,
      writable: true,
    },
    removeEventListener: {
      value: eventTarget.removeEventListener,
      configurable: true,
      writable: true,
    },
    dispatchEvent: {
      value: eventTarget.dispatchEvent,
      configurable: true,
      writable: true,
    },
  });

  return target as T & EventCapable;
};

const installEventTargetIfMissing = <T extends object>(target: T): T & EventCapable => {
  const existingEventTarget = target as Partial<EventCapable>;

  if (
    typeof existingEventTarget.addEventListener === 'function' &&
    typeof existingEventTarget.removeEventListener === 'function' &&
    typeof existingEventTarget.dispatchEvent === 'function'
  ) {
    return target as T & EventCapable;
  }

  const eventTarget = createEventTarget();

  if (typeof existingEventTarget.addEventListener !== 'function') {
    Object.defineProperty(target, 'addEventListener', {
      value: eventTarget.addEventListener,
      configurable: true,
      writable: true,
    });
  }

  if (typeof existingEventTarget.removeEventListener !== 'function') {
    Object.defineProperty(target, 'removeEventListener', {
      value: eventTarget.removeEventListener,
      configurable: true,
      writable: true,
    });
  }

  if (typeof existingEventTarget.dispatchEvent !== 'function') {
    Object.defineProperty(target, 'dispatchEvent', {
      value: eventTarget.dispatchEvent,
      configurable: true,
      writable: true,
    });
  }

  return target as T & EventCapable;
};

const installGlobalEventTargetPolyfills = (runtime: WeChatRuntimeGlobal): void => {
  const candidates = new Set<object>();

  for (const candidate of [runtime, runtime.window, runtime.self]) {
    if (!candidate || (typeof candidate !== 'object' && typeof candidate !== 'function')) {
      continue;
    }

    const eventTargetCandidate = candidate as object;
    if (candidates.has(eventTargetCandidate)) {
      continue;
    }

    installEventTargetIfMissing(eventTargetCandidate);
    candidates.add(eventTargetCandidate);
  }
};

const cloneStructuredValue = <T>(
  value: T,
  seen = new WeakMap<object, unknown>(),
): T => {
  if (value === null || typeof value !== 'object') {
    return value;
  }

  if (seen.has(value as object)) {
    return seen.get(value as object) as T;
  }

  if (value instanceof Date) {
    return new Date(value.getTime()) as T;
  }

  if (value instanceof Map) {
    const result = new Map();
    seen.set(value, result);
    for (const [key, nestedValue] of value.entries()) {
      result.set(
        cloneStructuredValue(key, seen),
        cloneStructuredValue(nestedValue, seen),
      );
    }
    return result as T;
  }

  if (value instanceof Set) {
    const result = new Set();
    seen.set(value, result);
    for (const nestedValue of value.values()) {
      result.add(cloneStructuredValue(nestedValue, seen));
    }
    return result as T;
  }

  if (Array.isArray(value)) {
    const result: unknown[] = [];
    seen.set(value, result);
    for (const nestedValue of value) {
      result.push(cloneStructuredValue(nestedValue, seen));
    }
    return result as T;
  }

  if (value instanceof ArrayBuffer) {
    return value.slice(0) as T;
  }

  if (ArrayBuffer.isView(value)) {
    if (value instanceof DataView) {
      return new DataView(value.buffer.slice(0), value.byteOffset, value.byteLength) as T;
    }

    const typedArray = value as unknown as {
      constructor: new (buffer: ArrayBuffer) => unknown;
      buffer: ArrayBuffer;
    };

    return new typedArray.constructor(typedArray.buffer.slice(0)) as T;
  }

  const prototype = Object.getPrototypeOf(value);
  const result = Object.create(prototype) as Record<PropertyKey, unknown>;
  seen.set(value as object, result);

  for (const key of Reflect.ownKeys(value as object)) {
    const descriptor = Object.getOwnPropertyDescriptor(value as object, key);
    if (!descriptor) {
      continue;
    }

    if ('value' in descriptor) {
      descriptor.value = cloneStructuredValue(
        descriptor.value as unknown,
        seen,
      );
    }

    Object.defineProperty(result, key, descriptor);
  }

  return result as T;
};

const DEVTOOLS_GAME_CONTEXT_PREFIX = '/game/gameContext/';
const WECHAT_PRIMARY_CANVAS_ID = '__pixi-wechat-screen-canvas';
const PACKAGED_ASSET_PATH_MARKERS = [
  '/game/gameContext/assets/',
  '/miniprogram/gameContext/assets/',
  '/gameContext/assets/',
  '/game/assets/',
  '/miniprogram/assets/',
  '/assets/',
] as const;

const extractPackagedAssetLocalPath = (input: string): string | null => {
  try {
    const url = new URL(input);
    const pathname = url.pathname;
    if (pathname.includes(DEVTOOLS_GAME_CONTEXT_PREFIX)) {
      return pathname.slice(
        pathname.indexOf(DEVTOOLS_GAME_CONTEXT_PREFIX) + DEVTOOLS_GAME_CONTEXT_PREFIX.length,
      );
    }

    for (const marker of PACKAGED_ASSET_PATH_MARKERS) {
      if (!pathname.includes(marker)) {
        continue;
      }

      const relativePath = pathname.slice(pathname.indexOf(marker) + marker.length);
      return `assets/${relativePath.replace(/^\/+/, '')}`;
    }

    if (['127.0.0.1', 'localhost'].includes(url.hostname)) {
      if (pathname.startsWith('/miniprogram/')) {
        return pathname.slice('/miniprogram/'.length);
      }

      return pathname.replace(/^\/+/, '');
    }

    return null;
  } catch {
    return null;
  }
};

const normalizeWeChatLocalAssetPath = (input: string): string => {
  const embeddedAssetPathMatch = input
    .replace(/\\/g, '/')
    .match(/(?:^|\/)(assets\/.+)$/);
  const embeddedAssetPath = embeddedAssetPathMatch?.[1];
  if (embeddedAssetPath) {
    return embeddedAssetPath;
  }

  if (!/^[a-z]+:\/\//i.test(input)) {
    return input.replace(/^[./]+/, '').replace(/^\/+/, '');
  }

  const packagedAssetLocalPath = extractPackagedAssetLocalPath(input);
  if (packagedAssetLocalPath) {
    return packagedAssetLocalPath;
  }

  return input;
};

const normalizeLocalPath = (input: string): string => {
  if (/^[a-z]+:\/\//i.test(input)) {
    const packagedAssetLocalPath = extractPackagedAssetLocalPath(input);
    if (packagedAssetLocalPath) {
      return packagedAssetLocalPath;
    }

    throw new Error(`Remote fetch is not supported in WeChat runtime prep: ${input}`);
  }

  return normalizeWeChatLocalAssetPath(input);
};

const guessMimeType = (filePath: string): string => {
  if (filePath.endsWith('.svg')) {
    return 'image/svg+xml';
  }
  if (filePath.endsWith('.png')) {
    return 'image/png';
  }
  if (filePath.endsWith('.jpg') || filePath.endsWith('.jpeg')) {
    return 'image/jpeg';
  }
  if (filePath.endsWith('.webp')) {
    return 'image/webp';
  }

  return 'application/octet-stream';
};

const createFetchPolyfill = (
  fileSystemManager: FileSystemManagerLike | undefined,
  existingFetch: WeChatRuntimeGlobal['fetch'],
): ((input: string) => Promise<LocalFetchResponse | unknown>) => {
  return async (input: string) => {
    const devtoolsLocalPath = /^[a-z]+:\/\//i.test(input)
      ? extractPackagedAssetLocalPath(input)
      : null;
    if (/^[a-z]+:\/\//i.test(input) && !devtoolsLocalPath) {
      if (!existingFetch) {
        throw new Error(`Remote fetch is not available in WeChat runtime prep: ${input}`);
      }

      return existingFetch(input);
    }

    if (!fileSystemManager) {
      throw new Error(`No file-system manager available for fetch(${input})`);
    }

    const filePath = devtoolsLocalPath ?? normalizeLocalPath(input);
    const readText = async (): Promise<string> => {
      const value = fileSystemManager.readFileSync(filePath, 'utf8');
      return typeof value === 'string'
        ? value
        : new TextDecoder().decode(value as ArrayBuffer);
    };
    const readArrayBuffer = async (): Promise<ArrayBuffer> => {
      const value = fileSystemManager.readFileSync(filePath);
      if (value instanceof ArrayBuffer) {
        return value;
      }

      return new TextEncoder().encode(value).buffer;
    };

    return {
      ok: true,
      status: 200,
      statusText: 'OK',
      url: filePath,
      text: readText,
      async json(): Promise<unknown> {
        return JSON.parse(await readText());
      },
      arrayBuffer: readArrayBuffer,
      async blob(): Promise<Blob> {
        return new Blob([await readArrayBuffer()], {
          type: guessMimeType(filePath),
        });
      },
    };
  };
};

const findPropertyDescriptor = (
  value: object,
  key: PropertyKey,
): PropertyDescriptor | null => {
  let current: object | null = value;
  while (current) {
    const descriptor = Object.getOwnPropertyDescriptor(current, key);
    if (descriptor) {
      return descriptor;
    }
    current = Object.getPrototypeOf(current);
  }

  return null;
};

const createElementStub = (tagName: string): Record<string, unknown> => {
  const node: DomNodeLike & Record<string, unknown> = {
    tagName: tagName.toUpperCase(),
    nodeName: tagName.toUpperCase(),
    isConnected: false,
    style: {},
    children: [],
    appendChild(child: unknown): unknown {
      return appendDomChild(node, child);
    },
    removeChild(child: unknown): unknown {
      return removeDomChild(node, child);
    },
    contains(child: unknown): boolean {
      return nodeContainsDescendant(node, child);
    },
    setAttribute(): void {},
    getContext(): null {
      return null;
    },
    getBoundingClientRect() {
      return {
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: 0,
        height: 0,
        x: 0,
        y: 0,
      };
    },
  };

  Object.defineProperty(node, 'clientWidth', {
    configurable: true,
    get(): number {
      const styledNode = node as { style?: Record<string, string> };
      return parsePixelSize(
        typeof styledNode.style?.width === 'string' ? styledNode.style.width : undefined,
      ) ?? 0;
    },
  });
  Object.defineProperty(node, 'clientHeight', {
    configurable: true,
    get(): number {
      const styledNode = node as { style?: Record<string, string> };
      return parsePixelSize(
        typeof styledNode.style?.height === 'string' ? styledNode.style.height : undefined,
      ) ?? 0;
    },
  });

  return installDomNodeRemoveCompat(node);
};

const installCanvasPrototypeBridge = (canvas: CanvasLike): void => {
  if (!isWeChatDevtoolsRuntime()) {
    return;
  }

  try {
    const nativePrototype = Object.getPrototypeOf(canvas);
    if (!nativePrototype) {
      return;
    }

    const existingBridge = Object.getPrototypeOf(nativePrototype);
    if (
      existingBridge &&
      typeof existingBridge === 'object' &&
      (existingBridge as { tagName?: unknown }).tagName === 'CANVAS'
    ) {
      return;
    }

    const canvasElementBridge = createElementStub('canvas');
    (canvasElementBridge as { style?: Record<string, string> }).style = canvas.style ?? {};
    Object.setPrototypeOf(nativePrototype, canvasElementBridge);
  } catch {
    // DevTools-only best effort bridge. Leave the native canvas untouched if the prototype is sealed.
  }
};

const URL_ABSOLUTE_PATTERN = /^([a-z][a-z0-9+.-]*:)?\/\/([^/?#]+)([^?#]*)(\?[^#]*)?(#.*)?$/i;

const parseUrlParts = (
  input: string,
): {
  hash: string;
  host: string;
  hostname: string;
  href: string;
  origin: string;
  pathname: string;
  protocol: string;
  search: string;
} => {
  const match = input.match(URL_ABSOLUTE_PATTERN);

  if (!match) {
    throw new TypeError(`Invalid URL: ${input}`);
  }

  const protocol = match[1] ?? 'https:';
  const host = match[2] ?? '';
  const pathname = match[3] && match[3].length > 0 ? match[3] : '/';
  const search = match[4] ?? '';
  const hash = match[5] ?? '';

  return {
    hash,
    host,
    hostname: host.replace(/:\d+$/, ''),
    href: `${protocol}//${host}${pathname}${search}${hash}`,
    origin: `${protocol}//${host}`,
    pathname,
    protocol,
    search,
  };
};

const resolveUrlString = (
  input: string,
  base: string,
): string => {
  if (URL_ABSOLUTE_PATTERN.test(input)) {
    return input;
  }

  const resolvedBase = parseUrlParts(base);

  if (input.startsWith('/')) {
    return `${resolvedBase.origin}${input}`;
  }

  const normalizedBasePath = resolvedBase.pathname.endsWith('/')
    ? resolvedBase.pathname
    : resolvedBase.pathname.replace(/[^/]*$/, '');
  const combinedPath = `${normalizedBasePath}${input}`;
  const segments = combinedPath.split('/');
  const resolvedSegments: string[] = [];

  for (const segment of segments) {
    if (!segment || segment === '.') {
      continue;
    }
    if (segment === '..') {
      resolvedSegments.pop();
      continue;
    }
    resolvedSegments.push(segment);
  }

  return `${resolvedBase.origin}/${resolvedSegments.join('/')}`;
};

const installUrlPolyfill = (runtime: WeChatRuntimeGlobal): void => {
  if (typeof runtime.URL === 'function') {
    return;
  }

  const fallbackBase = runtime.location?.href ?? 'https://minigame.weixin.qq.com/';

  class WeChatURL {
    readonly hash: string;

    readonly host: string;

    readonly hostname: string;

    readonly href: string;

    readonly origin: string;

    readonly pathname: string;

    readonly protocol: string;

    readonly search: string;

    constructor(input: string, base?: string | { href?: string }) {
      const baseHref =
        typeof base === 'string'
          ? base
          : typeof base?.href === 'string'
            ? base.href
            : fallbackBase;
      const resolved = parseUrlParts(resolveUrlString(String(input), baseHref));

      this.hash = resolved.hash;
      this.host = resolved.host;
      this.hostname = resolved.hostname;
      this.href = resolved.href;
      this.origin = resolved.origin;
      this.pathname = resolved.pathname;
      this.protocol = resolved.protocol;
      this.search = resolved.search;
    }

    toJSON(): string {
      return this.href;
    }

    toString(): string {
      return this.href;
    }
  }

  defineGlobalValue(runtime, 'URL', WeChatURL as unknown as WeChatRuntimeGlobal['URL']);
};

const ensureHtmlVideoElementConstructor = (
  runtime: WeChatRuntimeGlobal,
): (new () => object) => {
  const existingConstructor = runtime.HTMLVideoElement;

  if (typeof existingConstructor === 'function') {
    return existingConstructor;
  }

  const constructor = class WeChatHTMLVideoElement {} as unknown as new () => object;
  defineGlobalValue(runtime, 'HTMLVideoElement', constructor);

  return constructor;
};

const createVideoElementStub = (
  runtime: WeChatRuntimeGlobal,
): VideoLike & EventCapable => {
  const eventTarget = createEventTarget();
  const video = {
    ...createElementStub('video'),
    autoplay: false,
    controls: false,
    crossOrigin: null,
    currentTime: 0,
    duration: 0,
    ended: false,
    loop: false,
    muted: false,
    paused: true,
    playsInline: true,
    preload: 'auto',
    readyState: 0,
    src: '',
    videoHeight: 0,
    videoWidth: 0,
    canPlayType(): string {
      return '';
    },
    load(): void {},
    pause(): void {
      this.paused = true;
    },
    async play(): Promise<void> {
      this.paused = false;
    },
    addEventListener: eventTarget.addEventListener,
    removeEventListener: eventTarget.removeEventListener,
    dispatchEvent: eventTarget.dispatchEvent,
  };

  Object.setPrototypeOf(video, ensureHtmlVideoElementConstructor(runtime).prototype);

  return video as VideoLike & EventCapable;
};

const createCanvasInstance = (): CanvasLike => {
  const runtime = globalThis as WeChatRuntimeGlobal;
  const canvasFactory =
    runtime.__pixiWeChatCreateOffscreenCanvas ??
    (wx.createCanvas?.bind(wx) as (() => CanvasLike) | undefined);

  if (typeof canvasFactory !== 'function') {
    throw new Error('No offscreen canvas factory available in WeChat runtime prep.');
  }

  const canvas = canvasFactory() as CanvasLike;
  canvas.style ??= {};
  Object.defineProperty(canvas, 'type', {
    value: 'canvas',
    configurable: true,
    writable: true,
  });
  Object.defineProperty(canvas, 'tagName', {
    value: 'CANVAS',
    configurable: true,
    writable: true,
  });
  Object.defineProperty(canvas, 'nodeName', {
    value: 'CANVAS',
    configurable: true,
    writable: true,
  });
  installCanvasPrototypeBridge(canvas);
  installWeChatCanvasGetContextCompat(canvas);
  installCanvasBoundingClientRectCompat(canvas);
  installEventTarget(canvas);
  setDomNodeLink(canvas, 'isConnected', false);
  installDomNodeRemoveCompat(canvas as object);

  return canvas;
};

class WeChatTouchEvent {
  readonly type: string;

  readonly touches: TouchLike[];

  readonly changedTouches: TouchLike[];

  readonly targetTouches: TouchLike[];

  readonly target: unknown;

  defaultPrevented = false;

  constructor(type: string, init?: TouchEventInitLike) {
    this.type = type;
    this.touches = init?.touches ?? [];
    this.changedTouches = init?.changedTouches ?? [];
    this.targetTouches = init?.targetTouches ?? init?.touches ?? [];
    this.target = init?.target ?? null;
  }

  preventDefault(): void {
    this.defaultPrevented = true;
  }

  stopPropagation(): void {}
}

class WeChatSegmenter implements IntlSegmenterLike {
  segment(input: string): IntlSegmentDataLike[] {
    return Array.from(input).map((segment) => ({ segment }));
  }
}

const normalizeWeChatTouch = (touch: Partial<TouchLike>, identifier = 0): TouchLike => {
  const touchWithAliases = touch as Partial<TouchLike> & TouchCoordinateAliases;
  const x =
    readFiniteNumber(touchWithAliases.x) ??
    readFiniteNumber(touchWithAliases.clientX) ??
    readFiniteNumber(touchWithAliases.pageX) ??
    readFiniteNumber(touchWithAliases.offsetX) ??
    readFiniteNumber(touchWithAliases.screenX) ??
    0;
  const y =
    readFiniteNumber(touchWithAliases.y) ??
    readFiniteNumber(touchWithAliases.clientY) ??
    readFiniteNumber(touchWithAliases.pageY) ??
    readFiniteNumber(touchWithAliases.offsetY) ??
    readFiniteNumber(touchWithAliases.screenY) ??
    0;
  const normalizedTouch: TouchLike = {
    identifier: touch.identifier ?? identifier,
    clientX: x,
    clientY: y,
    pageX:
      readFiniteNumber(touchWithAliases.pageX) ??
      readFiniteNumber(touchWithAliases.x) ??
      x,
    pageY:
      readFiniteNumber(touchWithAliases.pageY) ??
      readFiniteNumber(touchWithAliases.y) ??
      y,
    screenX:
      readFiniteNumber(touchWithAliases.screenX) ??
      readFiniteNumber(touchWithAliases.clientX) ??
      x,
    screenY:
      readFiniteNumber(touchWithAliases.screenY) ??
      readFiniteNumber(touchWithAliases.clientY) ??
      y,
  };

  if (touch.force !== undefined) {
    normalizedTouch.force = touch.force;
  }
  if (touch.radiusX !== undefined) {
    normalizedTouch.radiusX = touch.radiusX;
  }
  if (touch.radiusY !== undefined) {
    normalizedTouch.radiusY = touch.radiusY;
  }

  return normalizedTouch;
};

const installTouchForwarders = (runtime: WeChatRuntimeGlobal): void => {
  const touchApi = wx as WechatMinigameAPI & WeChatTouchAPI;
  const resolveDevtoolsTouchScale = (): number => {
    if (!isWeChatDevtoolsRuntime()) {
      return 1;
    }

    const rendererResolution = readFiniteNumber(
      runtime.__pixiWeChatRendererDebug__?.resolution,
    );

    if (rendererResolution === null || rendererResolution <= 1) {
      return 1;
    }

    return rendererResolution;
  };
  const dispatchTouch = (
    type: string,
    event: WeChatTouchPayload | undefined,
  ): void => {
    const target = runtime.canvas as (CanvasLike & EventCapable) | undefined;
    if (!target?.dispatchEvent || !runtime.TouchEvent) {
      return;
    }

    const touches = (event?.touches ?? []).map((touch, index) =>
      normalizeWeChatTouch(touch, index),
    );
    const changedTouches = (event?.changedTouches ?? []).map((touch, index) =>
      normalizeWeChatTouch(touch, index),
    );
    const devtoolsTouchScale = resolveDevtoolsTouchScale();
    const scaledTouches =
      devtoolsTouchScale === 1
        ? touches
        : touches.map((touch) => scaleTouchCoordinates(touch, devtoolsTouchScale));
    const scaledChangedTouches =
      devtoolsTouchScale === 1
        ? changedTouches
        : changedTouches.map((touch) => scaleTouchCoordinates(touch, devtoolsTouchScale));

    target.dispatchEvent(
      new runtime.TouchEvent(type, {
        type,
        touches: scaledTouches,
        changedTouches: scaledChangedTouches,
        targetTouches: scaledTouches,
        target,
      }) as { type: string },
    );
  };

  touchApi.onTouchStart?.((event: WeChatTouchPayload) => {
    dispatchTouch('touchstart', event);
  });
  touchApi.onTouchMove?.((event: WeChatTouchPayload) => {
    dispatchTouch('touchmove', event);
  });
  touchApi.onTouchEnd?.((event: WeChatTouchPayload) => {
    dispatchTouch('touchend', event);
  });
  touchApi.onTouchCancel?.((event: WeChatTouchPayload) => {
    dispatchTouch('touchcancel', event);
  });
};

const installImageInstancePolyfills = (image: object): ImageLike => {
  const imageLike = image as ImageLike;
  installDomNodeRemoveCompat(imageLike as object);
  const sourceDescriptor = findPropertyDescriptor(imageLike, 'src');
  const readNativeSrc = (): string | undefined => {
    if (sourceDescriptor?.get) {
      return sourceDescriptor.get.call(imageLike) as string | undefined;
    }

    return imageLike.src;
  };
  let fallbackSrc = normalizeWeChatLocalAssetPath(readNativeSrc() ?? '');
  const writeNativeSrc = (nextValue: string): void => {
    if (sourceDescriptor?.set) {
      sourceDescriptor.set.call(imageLike, nextValue);
      return;
    }

    fallbackSrc = nextValue;
  };

  Object.defineProperty(imageLike, 'src', {
    configurable: true,
    enumerable: true,
    get(): string {
      if (sourceDescriptor?.get) {
        return normalizeWeChatLocalAssetPath(readNativeSrc() ?? '');
      }

      return fallbackSrc;
    },
    set(value: string) {
      const normalizedValue = normalizeWeChatLocalAssetPath(String(value));
      fallbackSrc = normalizedValue;
      writeNativeSrc(normalizedValue);
    },
  });
  imageLike.addEventListener ??= (type: string, listener: Listener) => {
    if (type === 'load') {
      imageLike.onload = () => listener({ type });
      return;
    }
    if (type === 'error') {
      imageLike.onerror = () => listener({ type });
    }
  };
  imageLike.removeEventListener ??= (type: string) => {
    if (type === 'load') {
      imageLike.onload = null;
      return;
    }
    if (type === 'error') {
      imageLike.onerror = null;
    }
  };
  imageLike.decode ??= () =>
    new Promise<void>((resolve, reject) => {
      if (imageLike.complete) {
        resolve();
        return;
      }

      const previousOnLoad = imageLike.onload;
      const previousOnError = imageLike.onerror;

      imageLike.onload = () => {
        previousOnLoad?.();
        resolve();
      };
      imageLike.onerror = (error?: unknown) => {
        previousOnError?.(error);
        reject(error ?? new Error('Failed to decode WeChat image resource.'));
      };
    });

  return imageLike;
};

const defineGlobalValue = (
  runtime: WeChatRuntimeGlobal,
  key: keyof WeChatRuntimeGlobal,
  value: unknown,
): void => {
  Object.defineProperty(runtime, key, {
    value,
    configurable: true,
    writable: true,
  });
};

const setGlobalIfMissing = (
  runtime: WeChatRuntimeGlobal,
  key: keyof WeChatRuntimeGlobal,
  value: unknown,
): void => {
  if (runtime[key] !== undefined) {
    return;
  }

  defineGlobalValue(runtime, key, value);
};

const isWebGLContextMatcherLike = (
  value: unknown,
): value is WebGLContextMatcherLike => {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const context = value as WebGLContextMatcherLike;

  return (
    typeof context.getExtension === 'function' &&
    typeof context.bindBuffer === 'function' &&
    typeof context.vertexAttribPointer === 'function' &&
    typeof context.ARRAY_BUFFER === 'number' &&
    typeof context.ELEMENT_ARRAY_BUFFER === 'number'
  );
};

const isCanvasRenderingContext2DLike = (
  value: unknown,
): value is CanvasRenderingContext2DMatcherLike => {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const context = value as CanvasRenderingContext2DMatcherLike;

  return (
    typeof context.clearRect === 'function' &&
    typeof context.fillRect === 'function' &&
    typeof context.getImageData === 'function' &&
    typeof context.putImageData === 'function' &&
    typeof context.measureText === 'function'
  );
};

const hasNativeWebGL2VertexArrayMethods = (value: unknown): boolean => {
  if (!isWebGLContextMatcherLike(value)) {
    return false;
  }

  return (
    typeof value.createVertexArray === 'function' &&
    typeof value.bindVertexArray === 'function' &&
    typeof value.deleteVertexArray === 'function'
  );
};

const classifyWeChatWebGLVersion = (value: unknown): 1 | 2 | null => {
  const compatInfo = getWeChatWebGLCompatInfo(value);

  if (compatInfo) {
    return compatInfo.webglVersion;
  }

  if (!isWebGLContextMatcherLike(value)) {
    return null;
  }

  return hasNativeWebGL2VertexArrayMethods(value) ? 2 : 1;
};

const createContextInstanceMatcher = (
  name: string,
  matcher: (value: unknown) => boolean,
): (new () => object) => {
  const constructor = function WeChatContextMatcher(): never {
    throw new TypeError(`${name} is not constructible in WeChat runtime prep`);
  };

  Object.defineProperty(constructor, 'name', {
    value: name,
    configurable: true,
  });
  Object.defineProperty(constructor, Symbol.hasInstance, {
    value: matcher,
    configurable: true,
  });

  return constructor as unknown as new () => object;
};

const installIntlPolyfills = (runtime: WeChatRuntimeGlobal): void => {
  const existingIntl = runtime.Intl;
  const intlObject =
    existingIntl && typeof existingIntl === 'object' ? existingIntl : ({} as IntlLike);

  if (runtime.Intl !== intlObject) {
    defineGlobalValue(runtime, 'Intl', intlObject);
  }

  if (intlObject.Segmenter === undefined) {
    Object.defineProperty(intlObject, 'Segmenter', {
      value: WeChatSegmenter,
      configurable: true,
      writable: true,
    });
  }
};

const installNavigatorPolyfills = (runtime: WeChatRuntimeGlobal): void => {
  const existingNavigator = runtime.navigator;
  const navigatorObject =
    existingNavigator && typeof existingNavigator === 'object'
      ? existingNavigator
      : ({} as NonNullable<WeChatRuntimeGlobal['navigator']>);

  if (runtime.navigator !== navigatorObject) {
    defineGlobalValue(runtime, 'navigator', navigatorObject);
  }

  navigatorObject.userAgent ??= 'Mozilla/5.0 WeChatMiniGame';
  navigatorObject.platform ??= 'wechat-minigame';
  navigatorObject.language ??= 'zh-CN';
  navigatorObject.maxTouchPoints ??= 5;
  navigatorObject.hardwareConcurrency ??= 4;
};

const installLocationPolyfills = (runtime: WeChatRuntimeGlobal): void => {
  const existingLocation = runtime.location;
  const locationObject =
    existingLocation && typeof existingLocation === 'object'
      ? existingLocation
      : ({} as NonNullable<WeChatRuntimeGlobal['location']>);

  if (runtime.location !== locationObject) {
    defineGlobalValue(runtime, 'location', locationObject);
  }

  locationObject.href ??= 'https://minigame.weixin.qq.com/';
  locationObject.origin ??= 'https://minigame.weixin.qq.com';
  locationObject.pathname ??= '/';
  locationObject.search ??= '';
  locationObject.hash ??= '';
};

export const prepareWeChatRuntime = (): void => {
  const runtime = globalThis as WeChatRuntimeGlobal;
  if (runtime.__pixiWeChatRuntimePrepared) {
    return;
  }

  defineGlobalValue(runtime, '__pixiWeChatRuntimePrepared', true);
  setGlobalIfMissing(runtime, 'self', globalThis);
  setGlobalIfMissing(runtime, 'window', globalThis);
  installGlobalEventTargetPolyfills(runtime);
  installNavigatorPolyfills(runtime);
  installLocationPolyfills(runtime);
  installUrlPolyfill(runtime);
  setGlobalIfMissing(runtime, 'ontouchstart', null);
  setGlobalIfMissing(runtime, 'performance', {
    now: () => Date.now(),
  });
  defineGlobalValue(runtime, 'createImageBitmap', undefined);
  setGlobalIfMissing(runtime, 'structuredClone', cloneStructuredValue);
  installIntlPolyfills(runtime);
  setGlobalIfMissing(runtime, 'TouchEvent', WeChatTouchEvent as new (
    type: string,
    init?: TouchEventInitLike,
  ) => object);
  setGlobalIfMissing(
    runtime,
    'requestAnimationFrame',
    (callback: (timestamp: number) => void) =>
      setTimeout(
        () => callback(runtime.performance?.now() ?? Date.now()),
        16,
      ) as unknown as number,
  );
  setGlobalIfMissing(runtime, 'cancelAnimationFrame', (handle: number) => {
    clearTimeout(handle);
  });

  installWeChatCreateCanvasCompat(wx as WechatMinigameAPI & {
    createCanvas?: () => unknown;
  });

  const resolvedPrimaryCanvas = resolvePreboundScreenCanvas(runtime);
  if (!resolvedPrimaryCanvas) {
    throw new Error(
      'WeChat runtime prep requires a prebound screen canvas before bootstrap.',
    );
  }

  const primaryCanvas = resolvedPrimaryCanvas.canvas;
  logWeChatDebug('selected primary canvas', summarizePrimaryCanvasCandidate(resolvedPrimaryCanvas));
  installPrimaryCanvas(runtime, primaryCanvas);
  logWeChatDebug(
    'primary canvas identity',
    summarizePrimaryCanvasIdentity(runtime, primaryCanvas),
  );
  setGlobalIfMissing(
    runtime,
    'HTMLCanvasElement',
    primaryCanvas.constructor as unknown as new () => object,
  );
  defineGlobalValue(
    runtime,
    'CanvasRenderingContext2D',
    createContextInstanceMatcher(
      'CanvasRenderingContext2D',
      (value: unknown) => isCanvasRenderingContext2DLike(value),
    ),
  );
  defineGlobalValue(
    runtime,
    'WebGLRenderingContext',
    createContextInstanceMatcher(
      'WebGLRenderingContext',
      (value: unknown) => classifyWeChatWebGLVersion(value) === 1,
    ),
  );

  defineGlobalValue(
    runtime,
    'WebGL2RenderingContext',
    createContextInstanceMatcher(
      'WebGL2RenderingContext',
      (value: unknown) => classifyWeChatWebGLVersion(value) === 2,
    ),
  );
  installTouchForwarders(runtime);

  const createImage = wx.createImage;
  const sampleImage = createImage ? installImageInstancePolyfills(createImage()) : null;
  if (sampleImage) {
    setGlobalIfMissing(
      runtime,
      'HTMLImageElement',
      sampleImage.constructor as unknown as new () => object,
    );
  }
  if (!runtime.Image && createImage) {
    const createImageFn = createImage;
    defineGlobalValue(
      runtime,
      'Image',
      class WeChatImage {
        constructor() {
          return installImageInstancePolyfills(createImageFn()) as object;
        }
      } as unknown as new () => object,
    );
  }
  setGlobalIfMissing(runtime, 'HTMLImageElement', runtime.Image);

  defineGlobalValue(
    runtime,
    'fetch',
    createFetchPolyfill(wx.getFileSystemManager?.(), runtime.fetch),
  );

  const createDocumentBody = () => {
    const body: DomNodeLike & {
      style: Record<string, string>;
      children: unknown[];
      appendChild(node: unknown): unknown;
      contains(node: unknown): boolean;
      removeChild(node: unknown): unknown;
    } = {
      isConnected: true,
      style: {},
      children: [],
      appendChild(node: unknown): unknown {
        return appendDomChild(body, node);
      },
      contains(node: unknown): boolean {
        return nodeContainsDescendant(body, node);
      },
      removeChild(node: unknown): unknown {
        return removeDomChild(body, node);
      },
    };

    return installDomNodeRemoveCompat(body);
  };

  const createDocumentHead = () => {
    const head: DomNodeLike & {
      style: Record<string, string>;
      children: unknown[];
      appendChild(node: unknown): unknown;
      removeChild(node: unknown): unknown;
    } = {
      isConnected: true,
      style: {},
      children: [],
      appendChild(node: unknown): unknown {
        return appendDomChild(head, node);
      },
      removeChild(node: unknown): unknown {
        return removeDomChild(head, node);
      },
    };

    return installDomNodeRemoveCompat(head);
  };

  const createDocumentElement = (tagName: string): unknown => {
    const normalizedTag = tagName.toLowerCase();
    if (normalizedTag === 'canvas') {
      return createCanvasInstance();
    }
    if (normalizedTag === 'img' || normalizedTag === 'image') {
      return runtime.Image ? new runtime.Image() : createElementStub(tagName);
    }
    if (normalizedTag === 'video') {
      return createVideoElementStub(runtime);
    }

    return createElementStub(tagName);
  };

  const documentEvents = createEventTarget();
  const fontsEvents = createEventTarget();
  const document = (
    runtime.document
      ? installEventTargetIfMissing(runtime.document)
      : {
          ...documentEvents,
        }
  ) as EventCapable & {
    body?: DomNodeLike & {
      style?: Record<string, string>;
      children?: ArrayLike<unknown>;
      appendChild?(node: unknown): unknown;
      contains?(node: unknown): boolean;
      removeChild?(node: unknown): unknown;
    };
    head?: DomNodeLike & {
      style?: Record<string, string>;
      children?: ArrayLike<unknown>;
      appendChild?(node: unknown): unknown;
      removeChild?(node: unknown): unknown;
    };
    fonts?: EventCapable & {
      ready?: Promise<void>;
    };
    baseURI?: string;
    createElement?(tagName: string): unknown;
    getElementById?(id: string): unknown;
    getElementsByTagName?(tagName: string): ArrayLike<unknown>;
    querySelector?(selector: string): unknown;
    querySelectorAll?(selector: string): ArrayLike<unknown>;
    documentElement?: unknown;
    hidden?: boolean;
    location?: unknown;
    readyState?: string;
    visibilityState?: string;
  };
  const bodyCandidate =
    runtime.document?.body && isObjectLike(runtime.document.body)
      ? (runtime.document.body as DomNodeLike & {
          style?: Record<string, string>;
          children?: ArrayLike<unknown>;
          appendChild?(node: unknown): unknown;
          contains?(node: unknown): boolean;
          removeChild?(node: unknown): unknown;
        })
      : createDocumentBody();
  setDomNodeLink(bodyCandidate, 'isConnected', true);
  bodyCandidate.style ??= {};
  getManagedDomChildren(bodyCandidate);
  bodyCandidate.appendChild = (node: unknown): unknown =>
    appendDomChild(body, node);
  bodyCandidate.contains = (node: unknown): boolean =>
    nodeContainsDescendant(body, node);
  bodyCandidate.removeChild = (node: unknown): unknown =>
    removeDomChild(body, node);
  installDomNodeRemoveCompat(bodyCandidate as object);
  const body = bodyCandidate as DomNodeLike & {
    style: Record<string, string>;
    children?: ArrayLike<unknown>;
    appendChild(node: unknown): unknown;
    contains(node: unknown): boolean;
    removeChild(node: unknown): unknown;
  };
  const headCandidate =
    runtime.document?.head && isObjectLike(runtime.document.head)
      ? (runtime.document.head as DomNodeLike & {
          style?: Record<string, string>;
          children?: ArrayLike<unknown>;
          appendChild?(node: unknown): unknown;
          removeChild?(node: unknown): unknown;
        })
      : createDocumentHead();
  setDomNodeLink(headCandidate, 'isConnected', true);
  headCandidate.style ??= {};
  getManagedDomChildren(headCandidate);
  if (typeof headCandidate.appendChild !== 'function') {
    headCandidate.appendChild = (node: unknown): unknown =>
      appendDomChild(head, node);
  }
  if (typeof headCandidate.removeChild !== 'function') {
    headCandidate.removeChild = (node: unknown): unknown =>
      removeDomChild(head, node);
  }
  installDomNodeRemoveCompat(headCandidate as object);
  const head = headCandidate as DomNodeLike & {
    style: Record<string, string>;
    children?: ArrayLike<unknown>;
    appendChild(node: unknown): unknown;
    removeChild(node: unknown): unknown;
  };

  const fontsCandidate =
    runtime.document?.fonts && isObjectLike(runtime.document.fonts)
      ? installEventTargetIfMissing(runtime.document.fonts)
      : {
          ready: Promise.resolve(),
          addEventListener: fontsEvents.addEventListener,
          removeEventListener: fontsEvents.removeEventListener,
          dispatchEvent: fontsEvents.dispatchEvent,
        };

  if (
    !('ready' in fontsCandidate) ||
    !(fontsCandidate.ready instanceof Promise)
  ) {
    Object.defineProperty(fontsCandidate, 'ready', {
      value: Promise.resolve(),
      configurable: true,
      writable: true,
    });
  }
  const fonts = fontsCandidate as EventCapable & {
    ready: Promise<void>;
  };

  if (typeof document.createElement !== 'function') {
    Object.defineProperty(document, 'createElement', {
      value: createDocumentElement,
      configurable: true,
      writable: true,
    });
  }

  if (typeof document.baseURI !== 'string') {
    Object.defineProperty(document, 'baseURI', {
      value: runtime.location.href,
      configurable: true,
      writable: true,
    });
  }

  Object.defineProperty(document, 'body', {
    value: body,
    configurable: true,
    writable: true,
  });
  Object.defineProperty(document, 'head', {
    value: head,
    configurable: true,
    writable: true,
  });
  Object.defineProperty(document, 'fonts', {
    value: fonts,
    configurable: true,
    writable: true,
  });
  if (document.documentElement === undefined) {
    Object.defineProperty(document, 'documentElement', {
      value: runtime.window ?? runtime,
      configurable: true,
      writable: true,
    });
  }
  if (document.hidden === undefined) {
    Object.defineProperty(document, 'hidden', {
      value: false,
      configurable: true,
      writable: true,
    });
  }
  if (document.visibilityState === undefined) {
    Object.defineProperty(document, 'visibilityState', {
      value: 'visible',
      configurable: true,
      writable: true,
    });
  }
  if (document.readyState === undefined) {
    Object.defineProperty(document, 'readyState', {
      value: 'complete',
      configurable: true,
      writable: true,
    });
  }
  if (document.location === undefined) {
    Object.defineProperty(document, 'location', {
      value: runtime.location,
      configurable: true,
      writable: true,
    });
  }

  setDomNodeLink(body, 'ownerDocument', document);
  setDomNodeLink(body, 'parentNode', document);
  setDomNodeLink(head, 'ownerDocument', document);
  setDomNodeLink(head, 'parentNode', document);
  if (!body.contains(primaryCanvas)) {
    body.appendChild(primaryCanvas);
  }
  setDomNodeLink(primaryCanvas, 'ownerDocument', document);

  const selectDocumentNodes = (selector: string): unknown[] => {
    if (selector === 'canvas') {
      return [primaryCanvas];
    }
    if (selector === 'body') {
      return [body];
    }
    if (selector === 'head') {
      return [head];
    }
    if (
      selector.startsWith('#') &&
      typeof primaryCanvas.id === 'string' &&
      selector.slice(1) === primaryCanvas.id
    ) {
      return [primaryCanvas];
    }

    return [];
  };

  Object.defineProperty(document, 'querySelectorAll', {
    value: (selector: string): unknown[] => selectDocumentNodes(selector),
    configurable: true,
    writable: true,
  });
  Object.defineProperty(document, 'querySelector', {
    value: (selector: string): unknown | null =>
      selectDocumentNodes(selector)[0] ?? null,
    configurable: true,
    writable: true,
  });
  Object.defineProperty(document, 'getElementsByTagName', {
    value: (tagName: string): unknown[] =>
      selectDocumentNodes(tagName.toLowerCase()),
    configurable: true,
    writable: true,
  });
  Object.defineProperty(document, 'getElementById', {
    value: (id: string): unknown | null =>
      typeof primaryCanvas.id === 'string' && primaryCanvas.id === id
        ? primaryCanvas
        : null,
    configurable: true,
    writable: true,
  });

  if (!runtime.document) {
    defineGlobalValue(runtime, 'document', document);
  }
};
