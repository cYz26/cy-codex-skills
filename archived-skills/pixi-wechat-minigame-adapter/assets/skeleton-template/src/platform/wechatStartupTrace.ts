export type WeChatStartupTraceStatus = 'running' | 'failed' | 'ready';
export type WeChatStartupTraceCheckpointKind = 'mark' | 'error';

export interface WeChatStartupTraceCheckpoint {
  phase: string;
  timestamp: number;
  kind: WeChatStartupTraceCheckpointKind;
  details?: string;
}

export interface WeChatStartupTraceSession {
  id: string;
  startedAt: number;
  updatedAt: number;
  status: WeChatStartupTraceStatus;
  lastPhase: string;
  errorSummary?: string;
  checkpoints: WeChatStartupTraceCheckpoint[];
}

export interface WeChatStartupTraceSnapshot {
  currentSession: WeChatStartupTraceSession | null;
  previousSession: WeChatStartupTraceSession | null;
  acknowledgedPreviousSessionId: string | null;
}

interface WeChatStorageLike {
  getStorageSync?: (key: string) => unknown;
  setStorageSync?: (key: string, value: string) => void;
}

interface StorageAdapter {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

type WeChatStartupTraceRuntime = typeof globalThis & {
  __pixiWeChatStartupTraceOverride__?: boolean;
  __pixiWeChatStartupTraceSnapshot__?: WeChatStartupTraceSnapshot;
  __pixiWeChatStartupTraceActiveSessionId__?: string;
  __pixiWeChatStartupTraceSessionCounter__?: number;
  process?: {
    env?: Record<string, string | undefined>;
  };
  wx?: WeChatStorageLike;
  localStorage?: Storage;
};

const WECHAT_STARTUP_TRACE_STORAGE_KEY =
  'pixi-wechat-minigame:startup-trace:v1';
const MAX_TRACE_CHECKPOINTS = 8;
const MAX_TRACE_PHASE_LENGTH = 48;
const MAX_TRACE_DETAIL_LENGTH = 160;

const getRuntime = (): WeChatStartupTraceRuntime =>
  globalThis as WeChatStartupTraceRuntime;

const createEmptyWeChatStartupTraceSnapshot =
  (): WeChatStartupTraceSnapshot => ({
    currentSession: null,
    previousSession: null,
    acknowledgedPreviousSessionId: null,
  });

const isTemplateDebugBuild = (): boolean =>
  typeof __WECHAT_DEBUG__ === 'boolean'
    ? __WECHAT_DEBUG__
    : getRuntime().process?.env?.VITE_WECHAT_DEBUG === '1';

const truncateString = (value: string, maxLength: number): string =>
  value.length <= maxLength ? value : `${value.slice(0, maxLength - 1)}…`;

const summarizeTraceDetails = (details: unknown): string | undefined => {
  if (details === undefined) {
    return undefined;
  }

  if (details instanceof Error) {
    return truncateString(
      `${details.name}: ${details.message}`.trim(),
      MAX_TRACE_DETAIL_LENGTH,
    );
  }

  if (typeof details === 'string') {
    return truncateString(details.trim(), MAX_TRACE_DETAIL_LENGTH);
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
      MAX_TRACE_DETAIL_LENGTH,
    );
  } catch {
    return truncateString(String(details), MAX_TRACE_DETAIL_LENGTH);
  }
};

const cloneTraceCheckpoint = (
  checkpoint: WeChatStartupTraceCheckpoint,
): WeChatStartupTraceCheckpoint => ({
  phase: checkpoint.phase,
  timestamp: checkpoint.timestamp,
  kind: checkpoint.kind,
  ...(checkpoint.details ? { details: checkpoint.details } : {}),
});

const cloneTraceSession = (
  session: WeChatStartupTraceSession,
): WeChatStartupTraceSession => ({
  id: session.id,
  startedAt: session.startedAt,
  updatedAt: session.updatedAt,
  status: session.status,
  lastPhase: session.lastPhase,
  ...(session.errorSummary ? { errorSummary: session.errorSummary } : {}),
  checkpoints: session.checkpoints.map(cloneTraceCheckpoint),
});

const cloneTraceSnapshot = (
  snapshot: WeChatStartupTraceSnapshot,
): WeChatStartupTraceSnapshot => ({
  currentSession: snapshot.currentSession
    ? cloneTraceSession(snapshot.currentSession)
    : null,
  previousSession: snapshot.previousSession
    ? cloneTraceSession(snapshot.previousSession)
    : null,
  acknowledgedPreviousSessionId: snapshot.acknowledgedPreviousSessionId,
});

const normalizeTraceCheckpoint = (
  candidate: unknown,
): WeChatStartupTraceCheckpoint | null => {
  if (!candidate || typeof candidate !== 'object') {
    return null;
  }

  const value = candidate as Partial<WeChatStartupTraceCheckpoint>;
  if (
    typeof value.phase !== 'string' ||
    typeof value.timestamp !== 'number' ||
    (value.kind !== 'mark' && value.kind !== 'error')
  ) {
    return null;
  }

  return {
    phase: truncateString(value.phase, MAX_TRACE_PHASE_LENGTH),
    timestamp: value.timestamp,
    kind: value.kind,
    ...(typeof value.details === 'string'
      ? { details: truncateString(value.details, MAX_TRACE_DETAIL_LENGTH) }
      : {}),
  };
};

const normalizeTraceSession = (
  candidate: unknown,
): WeChatStartupTraceSession | null => {
  if (!candidate || typeof candidate !== 'object') {
    return null;
  }

  const value = candidate as Partial<WeChatStartupTraceSession> & {
    checkpoints?: unknown[];
  };
  if (
    typeof value.id !== 'string' ||
    typeof value.startedAt !== 'number' ||
    typeof value.updatedAt !== 'number' ||
    (value.status !== 'running' &&
      value.status !== 'failed' &&
      value.status !== 'ready') ||
    typeof value.lastPhase !== 'string' ||
    !Array.isArray(value.checkpoints)
  ) {
    return null;
  }

  return {
    id: value.id,
    startedAt: value.startedAt,
    updatedAt: value.updatedAt,
    status: value.status,
    lastPhase: truncateString(value.lastPhase, MAX_TRACE_PHASE_LENGTH),
    ...(typeof value.errorSummary === 'string'
      ? {
          errorSummary: truncateString(
            value.errorSummary,
            MAX_TRACE_DETAIL_LENGTH,
          ),
        }
      : {}),
    checkpoints: value.checkpoints
      .map(normalizeTraceCheckpoint)
      .filter(
        (
          checkpoint,
        ): checkpoint is WeChatStartupTraceCheckpoint => checkpoint !== null,
      )
      .slice(-MAX_TRACE_CHECKPOINTS),
  };
};

const normalizeTraceSnapshot = (
  candidate: unknown,
): WeChatStartupTraceSnapshot => {
  if (!candidate || typeof candidate !== 'object') {
    return createEmptyWeChatStartupTraceSnapshot();
  }

  const value = candidate as Partial<WeChatStartupTraceSnapshot>;
  const currentSession = normalizeTraceSession(value.currentSession);
  const previousSession = normalizeTraceSession(value.previousSession);

  return {
    currentSession,
    previousSession:
      previousSession && previousSession.id !== currentSession?.id
        ? previousSession
        : null,
    acknowledgedPreviousSessionId:
      typeof value.acknowledgedPreviousSessionId === 'string'
        ? value.acknowledgedPreviousSessionId
        : null,
  };
};

const resolveStartupTraceStorage = (): StorageAdapter | null => {
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

const persistWeChatStartupTraceSnapshot = (
  snapshot: WeChatStartupTraceSnapshot,
): void => {
  const runtime = getRuntime();
  runtime.__pixiWeChatStartupTraceSnapshot__ = cloneTraceSnapshot(snapshot);

  const storage = resolveStartupTraceStorage();
  if (!storage) {
    return;
  }

  try {
    storage.setItem(
      WECHAT_STARTUP_TRACE_STORAGE_KEY,
      JSON.stringify(snapshot),
    );
  } catch {
    // Ignore startup trace persistence failures in diagnostics.
  }
};

const loadWeChatStartupTraceSnapshot = (): WeChatStartupTraceSnapshot => {
  const runtime = getRuntime();
  if (runtime.__pixiWeChatStartupTraceSnapshot__) {
    return cloneTraceSnapshot(runtime.__pixiWeChatStartupTraceSnapshot__);
  }

  const storage = resolveStartupTraceStorage();
  if (!storage) {
    const empty = createEmptyWeChatStartupTraceSnapshot();
    runtime.__pixiWeChatStartupTraceSnapshot__ = empty;
    return cloneTraceSnapshot(empty);
  }

  try {
    const rawValue = storage.getItem(WECHAT_STARTUP_TRACE_STORAGE_KEY);
    const snapshot = rawValue
      ? normalizeTraceSnapshot(JSON.parse(rawValue))
      : createEmptyWeChatStartupTraceSnapshot();
    runtime.__pixiWeChatStartupTraceSnapshot__ = snapshot;
    return cloneTraceSnapshot(snapshot);
  } catch {
    const empty = createEmptyWeChatStartupTraceSnapshot();
    runtime.__pixiWeChatStartupTraceSnapshot__ = empty;
    return cloneTraceSnapshot(empty);
  }
};

const createTraceSessionId = (): string => {
  const runtime = getRuntime();
  runtime.__pixiWeChatStartupTraceSessionCounter__ =
    (runtime.__pixiWeChatStartupTraceSessionCounter__ ?? 0) + 1;
  return `wx-startup-${Date.now().toString(36)}-${runtime.__pixiWeChatStartupTraceSessionCounter__}`;
};

const isWeChatStartupTraceEnabled = (): boolean => {
  const override = getRuntime().__pixiWeChatStartupTraceOverride__;
  if (override !== undefined) {
    return override;
  }

  return isTemplateDebugBuild();
};

const ensureCurrentStartupTraceSnapshot =
  (): WeChatStartupTraceSnapshot | null => {
    if (!isWeChatStartupTraceEnabled()) {
      return null;
    }

    const runtime = getRuntime();
    const snapshot = loadWeChatStartupTraceSnapshot();
    if (
      runtime.__pixiWeChatStartupTraceActiveSessionId__ &&
      snapshot.currentSession?.id ===
        runtime.__pixiWeChatStartupTraceActiveSessionId__
    ) {
      return snapshot;
    }

    if (snapshot.currentSession) {
      runtime.__pixiWeChatStartupTraceActiveSessionId__ =
        snapshot.currentSession.id;
      return snapshot;
    }

    return null;
  };

const appendStartupCheckpoint = (
  kind: WeChatStartupTraceCheckpointKind,
  phase: string,
  details?: unknown,
): void => {
  const snapshot = ensureCurrentStartupTraceSnapshot();
  const currentSession = snapshot?.currentSession;
  if (!currentSession || currentSession.status === 'failed') {
    return;
  }

  const timestamp = Date.now();
  const summarizedDetails = summarizeTraceDetails(details);
  const checkpoint: WeChatStartupTraceCheckpoint = {
    phase: truncateString(phase, MAX_TRACE_PHASE_LENGTH),
    timestamp,
    kind,
    ...(summarizedDetails ? { details: summarizedDetails } : {}),
  };

  const nextSession: WeChatStartupTraceSession = {
    ...currentSession,
    updatedAt: timestamp,
    lastPhase: checkpoint.phase,
    checkpoints: [...currentSession.checkpoints, checkpoint].slice(
      -MAX_TRACE_CHECKPOINTS,
    ),
  };

  if (kind === 'error') {
    nextSession.status = 'failed';
    if (checkpoint.details) {
      nextSession.errorSummary = checkpoint.details;
    }
  }

  persistWeChatStartupTraceSnapshot({
    currentSession: nextSession,
    previousSession: snapshot?.previousSession ?? null,
    acknowledgedPreviousSessionId:
      snapshot?.acknowledgedPreviousSessionId ?? null,
  });
};

export const beginWeChatStartupTrace = (): WeChatStartupTraceSession | null => {
  if (!isWeChatStartupTraceEnabled()) {
    return null;
  }

  const runtime = getRuntime();
  const snapshot = loadWeChatStartupTraceSnapshot();
  if (
    runtime.__pixiWeChatStartupTraceActiveSessionId__ &&
    snapshot.currentSession?.id ===
      runtime.__pixiWeChatStartupTraceActiveSessionId__
  ) {
    return snapshot.currentSession
      ? cloneTraceSession(snapshot.currentSession)
      : null;
  }

  const timestamp = Date.now();
  const previousSession = snapshot.currentSession
    ? cloneTraceSession(snapshot.currentSession)
    : snapshot.previousSession
      ? cloneTraceSession(snapshot.previousSession)
      : null;
  const currentSession: WeChatStartupTraceSession = {
    id: createTraceSessionId(),
    startedAt: timestamp,
    updatedAt: timestamp,
    status: 'running',
    lastPhase: 'entry',
    checkpoints: [
      {
        phase: 'entry',
        timestamp,
        kind: 'mark',
      },
    ],
  };

  runtime.__pixiWeChatStartupTraceActiveSessionId__ = currentSession.id;
  persistWeChatStartupTraceSnapshot({
    currentSession,
    previousSession,
    acknowledgedPreviousSessionId: snapshot.acknowledgedPreviousSessionId,
  });
  return cloneTraceSession(currentSession);
};

export const markWeChatStartupPhase = (
  phase: string,
  details?: unknown,
): void => {
  if (!isWeChatStartupTraceEnabled()) {
    return;
  }

  appendStartupCheckpoint('mark', phase, details);
};

export const failWeChatStartupTrace = (
  phase: string,
  error: unknown,
): void => {
  if (!isWeChatStartupTraceEnabled()) {
    return;
  }

  appendStartupCheckpoint('error', phase, error);
};

export const completeWeChatStartupTrace = (phase: string): void => {
  if (!isWeChatStartupTraceEnabled()) {
    return;
  }

  const snapshot = ensureCurrentStartupTraceSnapshot();
  const currentSession = snapshot?.currentSession;
  if (!currentSession || currentSession.status === 'failed') {
    return;
  }

  const normalizedPhase = truncateString(phase, MAX_TRACE_PHASE_LENGTH);
  const lastCheckpoint = currentSession.checkpoints.at(-1);
  if (
    lastCheckpoint?.kind !== 'mark' ||
    lastCheckpoint.phase !== normalizedPhase
  ) {
    appendStartupCheckpoint('mark', phase);
  }

  const refreshedSnapshot = ensureCurrentStartupTraceSnapshot();
  const refreshedSession = refreshedSnapshot?.currentSession;
  if (!refreshedSession || refreshedSession.status === 'failed') {
    return;
  }

  const timestamp = Date.now();
  persistWeChatStartupTraceSnapshot({
    currentSession: {
      ...refreshedSession,
      updatedAt: timestamp,
      status: 'ready',
      lastPhase: normalizedPhase,
    },
    previousSession: refreshedSnapshot?.previousSession ?? null,
    acknowledgedPreviousSessionId:
      refreshedSnapshot?.acknowledgedPreviousSessionId ?? null,
  });
};

export const consumePendingWeChatStartupReport =
  (): WeChatStartupTraceSession | null => {
    if (!isWeChatStartupTraceEnabled()) {
      return null;
    }

    const snapshot = loadWeChatStartupTraceSnapshot();
    const previousSession = snapshot.previousSession;
    if (
      !previousSession ||
      previousSession.status === 'ready' ||
      previousSession.id === snapshot.acknowledgedPreviousSessionId
    ) {
      return null;
    }

    persistWeChatStartupTraceSnapshot({
      ...snapshot,
      acknowledgedPreviousSessionId: previousSession.id,
    });
    return cloneTraceSession(previousSession);
  };

export const getWeChatStartupTraceSnapshot =
  (): WeChatStartupTraceSnapshot =>
    cloneTraceSnapshot(loadWeChatStartupTraceSnapshot());

export const setWeChatStartupTraceEnabledForTests = (
  enabled: boolean | undefined,
): void => {
  const runtime = getRuntime();
  if (enabled === undefined) {
    delete runtime.__pixiWeChatStartupTraceOverride__;
    return;
  }

  runtime.__pixiWeChatStartupTraceOverride__ = enabled;
};

export const resetWeChatStartupTraceStateForTests = (): void => {
  const runtime = getRuntime();
  delete runtime.__pixiWeChatStartupTraceOverride__;
  delete runtime.__pixiWeChatStartupTraceSnapshot__;
  delete runtime.__pixiWeChatStartupTraceActiveSessionId__;
  delete runtime.__pixiWeChatStartupTraceSessionCounter__;

  const storage = resolveStartupTraceStorage();
  if (!storage) {
    return;
  }

  try {
    storage.setItem(
      WECHAT_STARTUP_TRACE_STORAGE_KEY,
      JSON.stringify(createEmptyWeChatStartupTraceSnapshot()),
    );
  } catch {
    // Ignore startup trace reset failures in tests.
  }
};
