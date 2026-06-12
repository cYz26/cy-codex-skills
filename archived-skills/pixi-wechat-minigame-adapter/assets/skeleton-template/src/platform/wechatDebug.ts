export type WeChatViewportNormalizationSource =
  | 'none'
  | 'pixel-ratio'
  | 'inferred-density';

interface WeChatDebugSafeAreaSnapshot {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export interface WeChatSystemInfoDebugSnapshot {
  platform?: string;
  brand?: string;
  model?: string;
  rawWindowWidth: number;
  rawWindowHeight: number;
  rawPixelRatio: number;
  normalizedWindowWidth: number;
  normalizedWindowHeight: number;
  normalizedPixelRatio: number;
  normalizationFactor: number | null;
  normalizationSource: WeChatViewportNormalizationSource;
  viewportWasNormalized: boolean;
  rawSafeArea?: WeChatDebugSafeAreaSnapshot;
  normalizedSafeArea?: WeChatDebugSafeAreaSnapshot;
}

export interface WeChatDebugBreadcrumbEntry {
  index: number;
  level: 'info' | 'error';
  message: string;
  details?: string;
  timestamp: number;
}

export interface WeChatDebugBreadcrumbSession {
  id: string;
  startedAt: number;
  lastUpdatedAt: number;
  entries: WeChatDebugBreadcrumbEntry[];
}

export interface WeChatDebugLogSnapshot {
  currentSession: WeChatDebugBreadcrumbSession | null;
  previousSession: WeChatDebugBreadcrumbSession | null;
}

interface WeChatStorageLike {
  getStorageSync?: (key: string) => unknown;
  setStorageSync?: (key: string, value: string) => void;
}

interface StorageAdapter {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

type WeChatDebugRuntime = typeof globalThis & {
  __pixiWeChatDebugOverride__?: boolean;
  __pixiWeChatSystemInfoDebug__?: WeChatSystemInfoDebugSnapshot;
  __pixiWeChatDebugLogs__?: WeChatDebugLogSnapshot;
  __pixiWeChatDebugActiveSessionId__?: string;
  __pixiWeChatDebugSessionCounter__?: number;
  process?: {
    env?: Record<string, string | undefined>;
  };
  wx?: WeChatStorageLike;
  localStorage?: Storage;
};

const WECHAT_DEBUG_STORAGE_KEY = 'pixi-wechat-minigame:debug-breadcrumbs:v1';
const MAX_DEBUG_SESSIONS = 2;
const MAX_DEBUG_ENTRIES_PER_SESSION = 12;
const MAX_DEBUG_MESSAGE_LENGTH = 48;
const MAX_DEBUG_DETAIL_LENGTH = 120;

const getRuntime = (): WeChatDebugRuntime => globalThis as WeChatDebugRuntime;

const createEmptyWeChatDebugLogSnapshot = (): WeChatDebugLogSnapshot => ({
  currentSession: null,
  previousSession: null,
});

const isTemplateDebugBuild = (): boolean =>
  typeof __WECHAT_DEBUG__ === 'boolean'
    ? __WECHAT_DEBUG__
    : getRuntime().process?.env?.VITE_WECHAT_DEBUG === '1';

const truncateString = (value: string, maxLength: number): string =>
  value.length <= maxLength ? value : `${value.slice(0, maxLength - 1)}…`;

const normalizeWeChatPlatformValue = (platform: string | undefined): string =>
  platform?.trim().toLowerCase() ?? '';

const getWeChatDeviceInfoSnapshot = (): WechatMinigameDeviceInfo | null => {
  if (typeof wx === 'undefined' || typeof wx.getDeviceInfo !== 'function') {
    return null;
  }

  try {
    return wx.getDeviceInfo();
  } catch {
    return null;
  }
};

const summarizeDebugDetails = (details: unknown): string | undefined => {
  if (details === undefined) {
    return undefined;
  }

  if (details instanceof Error) {
    return truncateString(
      `${details.name}: ${details.message}`.trim(),
      MAX_DEBUG_DETAIL_LENGTH,
    );
  }

  if (typeof details === 'string') {
    return truncateString(details.trim(), MAX_DEBUG_DETAIL_LENGTH);
  }

  try {
    return truncateString(
      JSON.stringify(details, (_key, value) => {
        if (value instanceof Error) {
          return {
            name: value.name,
            message: value.message,
          };
        }

        if (typeof value === 'function') {
          return `[function ${value.name || 'anonymous'}]`;
        }

        return value;
      }),
      MAX_DEBUG_DETAIL_LENGTH,
    );
  } catch {
    return truncateString(String(details), MAX_DEBUG_DETAIL_LENGTH);
  }
};

const cloneBreadcrumbEntry = (
  entry: WeChatDebugBreadcrumbEntry,
): WeChatDebugBreadcrumbEntry => ({
  index: entry.index,
  level: entry.level,
  message: entry.message,
  timestamp: entry.timestamp,
  ...(entry.details ? { details: entry.details } : {}),
});

const cloneBreadcrumbSession = (
  session: WeChatDebugBreadcrumbSession,
): WeChatDebugBreadcrumbSession => ({
  id: session.id,
  startedAt: session.startedAt,
  lastUpdatedAt: session.lastUpdatedAt,
  entries: session.entries.map(cloneBreadcrumbEntry),
});

const cloneWeChatDebugLogSnapshot = (
  snapshot: WeChatDebugLogSnapshot,
): WeChatDebugLogSnapshot => ({
  currentSession: snapshot.currentSession
    ? cloneBreadcrumbSession(snapshot.currentSession)
    : null,
  previousSession: snapshot.previousSession
    ? cloneBreadcrumbSession(snapshot.previousSession)
    : null,
});

const normalizeSafeAreaSnapshot = (
  candidate: unknown,
): WeChatDebugSafeAreaSnapshot | undefined => {
  if (!candidate || typeof candidate !== 'object') {
    return undefined;
  }

  const value = candidate as Partial<WeChatDebugSafeAreaSnapshot>;
  if (
    typeof value.top !== 'number' ||
    typeof value.right !== 'number' ||
    typeof value.bottom !== 'number' ||
    typeof value.left !== 'number'
  ) {
    return undefined;
  }

  return {
    top: value.top,
    right: value.right,
    bottom: value.bottom,
    left: value.left,
  };
};

const normalizeWeChatSystemInfoDebugSnapshot = (
  candidate: unknown,
): WeChatSystemInfoDebugSnapshot | undefined => {
  if (!candidate || typeof candidate !== 'object') {
    return undefined;
  }

  const value = candidate as Partial<WeChatSystemInfoDebugSnapshot>;
  if (
    typeof value.rawWindowWidth !== 'number' ||
    typeof value.rawWindowHeight !== 'number' ||
    typeof value.rawPixelRatio !== 'number' ||
    typeof value.normalizedWindowWidth !== 'number' ||
    typeof value.normalizedWindowHeight !== 'number' ||
    typeof value.normalizedPixelRatio !== 'number' ||
    typeof value.viewportWasNormalized !== 'boolean'
  ) {
    return undefined;
  }

  const rawSafeArea = normalizeSafeAreaSnapshot(value.rawSafeArea);
  const normalizedSafeArea = normalizeSafeAreaSnapshot(value.normalizedSafeArea);

  return {
    rawWindowWidth: value.rawWindowWidth,
    rawWindowHeight: value.rawWindowHeight,
    rawPixelRatio: value.rawPixelRatio,
    normalizedWindowWidth: value.normalizedWindowWidth,
    normalizedWindowHeight: value.normalizedWindowHeight,
    normalizedPixelRatio: value.normalizedPixelRatio,
    normalizationFactor:
      value.normalizationFactor === null ||
      typeof value.normalizationFactor === 'number'
        ? value.normalizationFactor
        : null,
    normalizationSource:
      value.normalizationSource === 'pixel-ratio' ||
      value.normalizationSource === 'inferred-density'
        ? value.normalizationSource
        : 'none',
    viewportWasNormalized: value.viewportWasNormalized,
    ...(typeof value.platform === 'string' ? { platform: value.platform } : {}),
    ...(typeof value.brand === 'string' ? { brand: value.brand } : {}),
    ...(typeof value.model === 'string' ? { model: value.model } : {}),
    ...(rawSafeArea ? { rawSafeArea } : {}),
    ...(normalizedSafeArea ? { normalizedSafeArea } : {}),
  };
};

const normalizeBreadcrumbEntry = (
  candidate: unknown,
): WeChatDebugBreadcrumbEntry | null => {
  if (!candidate || typeof candidate !== 'object') {
    return null;
  }

  const value = candidate as Partial<WeChatDebugBreadcrumbEntry>;
  if (
    typeof value.index !== 'number' ||
    typeof value.timestamp !== 'number' ||
    (value.level !== 'info' && value.level !== 'error') ||
    typeof value.message !== 'string'
  ) {
    return null;
  }

  return {
    index: value.index,
    timestamp: value.timestamp,
    level: value.level,
    message: truncateString(value.message, MAX_DEBUG_MESSAGE_LENGTH),
    ...(typeof value.details === 'string'
      ? { details: truncateString(value.details, MAX_DEBUG_DETAIL_LENGTH) }
      : {}),
  };
};

const normalizeBreadcrumbSession = (
  candidate: unknown,
): WeChatDebugBreadcrumbSession | null => {
  if (!candidate || typeof candidate !== 'object') {
    return null;
  }

  const value = candidate as Partial<WeChatDebugBreadcrumbSession> & {
    entries?: unknown[];
  };
  if (
    typeof value.id !== 'string' ||
    typeof value.startedAt !== 'number' ||
    typeof value.lastUpdatedAt !== 'number' ||
    !Array.isArray(value.entries)
  ) {
    return null;
  }

  return {
    id: value.id,
    startedAt: value.startedAt,
    lastUpdatedAt: value.lastUpdatedAt,
    entries: value.entries
      .map(normalizeBreadcrumbEntry)
      .filter((entry): entry is WeChatDebugBreadcrumbEntry => entry !== null)
      .slice(-MAX_DEBUG_ENTRIES_PER_SESSION),
  };
};

const normalizeWeChatDebugLogSnapshot = (
  candidate: unknown,
): WeChatDebugLogSnapshot => {
  if (!candidate || typeof candidate !== 'object') {
    return createEmptyWeChatDebugLogSnapshot();
  }

  const value = candidate as Partial<WeChatDebugLogSnapshot>;
  const currentSession = normalizeBreadcrumbSession(value.currentSession);
  const previousSession = normalizeBreadcrumbSession(value.previousSession);

  return {
    currentSession,
    previousSession:
      previousSession && previousSession.id !== currentSession?.id
        ? previousSession
        : null,
  };
};

const resolveDebugStorage = (): StorageAdapter | null => {
  const runtime = getRuntime();
  const weChatStorage = runtime.wx;
  if (
    weChatStorage &&
    typeof weChatStorage.getStorageSync === 'function' &&
    typeof weChatStorage.setStorageSync === 'function'
  ) {
    return {
      getItem(key: string): string | null {
        const value = weChatStorage.getStorageSync?.(key);
        return typeof value === 'string' ? value : null;
      },
      setItem(key: string, value: string): void {
        weChatStorage.setStorageSync?.(key, value);
      },
    };
  }

  const storage = runtime.localStorage;
  if (
    storage &&
    typeof storage.getItem === 'function' &&
    typeof storage.setItem === 'function'
  ) {
    return storage;
  }

  return null;
};

const persistWeChatDebugLogSnapshot = (snapshot: WeChatDebugLogSnapshot): void => {
  const runtime = getRuntime();
  runtime.__pixiWeChatDebugLogs__ = cloneWeChatDebugLogSnapshot(snapshot);

  const storage = resolveDebugStorage();
  if (!storage) {
    return;
  }

  try {
    storage.setItem(WECHAT_DEBUG_STORAGE_KEY, JSON.stringify(snapshot));
  } catch {
    // Ignore storage failures in debug diagnostics.
  }
};

const loadWeChatDebugLogSnapshot = (): WeChatDebugLogSnapshot => {
  const runtime = getRuntime();
  if (runtime.__pixiWeChatDebugLogs__) {
    return cloneWeChatDebugLogSnapshot(runtime.__pixiWeChatDebugLogs__);
  }

  const storage = resolveDebugStorage();
  if (!storage) {
    const empty = createEmptyWeChatDebugLogSnapshot();
    runtime.__pixiWeChatDebugLogs__ = empty;
    return cloneWeChatDebugLogSnapshot(empty);
  }

  try {
    const rawValue = storage.getItem(WECHAT_DEBUG_STORAGE_KEY);
    const snapshot = rawValue
      ? normalizeWeChatDebugLogSnapshot(JSON.parse(rawValue))
      : createEmptyWeChatDebugLogSnapshot();
    runtime.__pixiWeChatDebugLogs__ = snapshot;
    return cloneWeChatDebugLogSnapshot(snapshot);
  } catch {
    const empty = createEmptyWeChatDebugLogSnapshot();
    runtime.__pixiWeChatDebugLogs__ = empty;
    return cloneWeChatDebugLogSnapshot(empty);
  }
};

const createSessionId = (): string => {
  const runtime = getRuntime();
  runtime.__pixiWeChatDebugSessionCounter__ =
    (runtime.__pixiWeChatDebugSessionCounter__ ?? 0) + 1;
  return `wx-${Date.now().toString(36)}-${runtime.__pixiWeChatDebugSessionCounter__}`;
};

const startWeChatDebugSession = (): WeChatDebugLogSnapshot => {
  const runtime = getRuntime();
  const snapshot = loadWeChatDebugLogSnapshot();
  const previousSession =
    snapshot.currentSession ?? snapshot.previousSession ?? null;
  const sessionStartedAt = Date.now();
  const currentSession: WeChatDebugBreadcrumbSession = {
    id: createSessionId(),
    startedAt: sessionStartedAt,
    lastUpdatedAt: sessionStartedAt,
    entries: [],
  };

  const nextSnapshot: WeChatDebugLogSnapshot = {
    currentSession,
    previousSession:
      previousSession && MAX_DEBUG_SESSIONS > 1
        ? cloneBreadcrumbSession(previousSession)
        : null,
  };

  runtime.__pixiWeChatDebugActiveSessionId__ = currentSession.id;
  persistWeChatDebugLogSnapshot(nextSnapshot);
  return nextSnapshot;
};

const ensureWeChatDebugLogSnapshot = (): WeChatDebugLogSnapshot => {
  const runtime = getRuntime();
  const cachedSnapshot = loadWeChatDebugLogSnapshot();
  if (
    runtime.__pixiWeChatDebugActiveSessionId__ &&
    cachedSnapshot.currentSession?.id === runtime.__pixiWeChatDebugActiveSessionId__
  ) {
    return cachedSnapshot;
  }

  return startWeChatDebugSession();
};

const appendWeChatDebugBreadcrumb = (
  level: WeChatDebugBreadcrumbEntry['level'],
  message: string,
  details?: unknown,
): void => {
  const snapshot = ensureWeChatDebugLogSnapshot();
  const session = snapshot.currentSession;
  if (!session) {
    return;
  }

  const summarizedDetails = summarizeDebugDetails(details);
  const nextEntry: WeChatDebugBreadcrumbEntry = {
    index: (session.entries.at(-1)?.index ?? 0) + 1,
    level,
    message: truncateString(message, MAX_DEBUG_MESSAGE_LENGTH),
    timestamp: Date.now(),
    ...(summarizedDetails ? { details: summarizedDetails } : {}),
  };

  const nextSession: WeChatDebugBreadcrumbSession = {
    ...session,
    lastUpdatedAt: nextEntry.timestamp,
    entries: [...session.entries, nextEntry].slice(-MAX_DEBUG_ENTRIES_PER_SESSION),
  };

  persistWeChatDebugLogSnapshot({
    currentSession: nextSession,
    previousSession: snapshot.previousSession,
  });
};

export const isWeChatDebugLoggingEnabled = (): boolean => {
  const override = getRuntime().__pixiWeChatDebugOverride__;
  if (override !== undefined) {
    return override;
  }

  return isTemplateDebugBuild();
};

export const logWeChatDebug = (message: string, details?: unknown): void => {
  if (!isWeChatDebugLoggingEnabled()) {
    return;
  }

  appendWeChatDebugBreadcrumb('info', message, details);

  if (details === undefined) {
    console.info(`[pixi-wx] ${message}`);
    return;
  }

  console.info(`[pixi-wx] ${message}`, details);
};

export const recordWeChatDebugError = (
  message: string,
  details?: unknown,
): void => {
  if (!isWeChatDebugLoggingEnabled()) {
    return;
  }

  appendWeChatDebugBreadcrumb('error', message, details);
};

export const setWeChatDebugLoggingOverrideForTests = (
  enabled: boolean | undefined,
): void => {
  const runtime = getRuntime();
  if (enabled === undefined) {
    delete runtime.__pixiWeChatDebugOverride__;
    return;
  }

  runtime.__pixiWeChatDebugOverride__ = enabled;
};

export const getWeChatSystemInfoDebugSnapshot = ():
  | WeChatSystemInfoDebugSnapshot
  | undefined =>
  normalizeWeChatSystemInfoDebugSnapshot(getRuntime().__pixiWeChatSystemInfoDebug__);

export const isWeChatDevtoolsRuntime = (): boolean => {
  const snapshotPlatform = normalizeWeChatPlatformValue(
    getWeChatSystemInfoDebugSnapshot()?.platform,
  );
  if (snapshotPlatform) {
    return snapshotPlatform === 'devtools';
  }

  if (typeof wx === 'undefined' || typeof wx.getSystemInfoSync !== 'function') {
    return false;
  }

  try {
    return normalizeWeChatPlatformValue(wx.getSystemInfoSync().platform) === 'devtools';
  } catch {
    return false;
  }
};

export const isWeChatOhosRuntime = (): boolean => {
  const deviceInfo = getWeChatDeviceInfoSnapshot();
  return normalizeWeChatPlatformValue(deviceInfo?.platform) === 'ohos';
};

export const setWeChatSystemInfoDebugSnapshot = (
  snapshot: WeChatSystemInfoDebugSnapshot | undefined,
): void => {
  const runtime = getRuntime();
  if (snapshot === undefined) {
    delete runtime.__pixiWeChatSystemInfoDebug__;
    return;
  }

  runtime.__pixiWeChatSystemInfoDebug__ = snapshot;
};

export const getWeChatDebugLogSnapshot = (): WeChatDebugLogSnapshot =>
  cloneWeChatDebugLogSnapshot(loadWeChatDebugLogSnapshot());

export const resetWeChatDebugStateForTests = (): void => {
  const runtime = getRuntime();
  delete runtime.__pixiWeChatDebugOverride__;
  delete runtime.__pixiWeChatSystemInfoDebug__;
  delete runtime.__pixiWeChatDebugLogs__;
  delete runtime.__pixiWeChatDebugActiveSessionId__;
  delete runtime.__pixiWeChatDebugSessionCounter__;

  const storage = resolveDebugStorage();
  if (!storage) {
    return;
  }

  try {
    storage.setItem(
      WECHAT_DEBUG_STORAGE_KEY,
      JSON.stringify(createEmptyWeChatDebugLogSnapshot()),
    );
  } catch {
    // Ignore storage reset failures in tests.
  }
};
