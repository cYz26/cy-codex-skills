import { afterEach, describe, expect, test } from 'vitest';

import {
  getWeChatDebugLogSnapshot,
  logWeChatDebug,
  recordWeChatDebugError,
  resetWeChatDebugStateForTests,
  setWeChatDebugLoggingOverrideForTests,
} from '../src/platform/wechatDebug';

type DebugTestRuntime = typeof globalThis & {
  wx?: {
    getStorageSync?: (key: string) => unknown;
    setStorageSync?: (key: string, value: string) => void;
  };
  __pixiWeChatDebugLogs__?: unknown;
  __pixiWeChatDebugActiveSessionId__?: string;
  __pixiWeChatDebugSessionCounter__?: number;
};

afterEach(() => {
  resetWeChatDebugStateForTests();
});

describe('wechatDebug', () => {
  test('persists breadcrumbs across runs and exposes the previous session', () => {
    const runtime = globalThis as DebugTestRuntime;
    const storage = new Map<string, string>();
    const previousWx = runtime.wx;

    runtime.wx = {
      getStorageSync: (key) => storage.get(key) ?? null,
      setStorageSync: (key, value) => {
        storage.set(key, value);
      },
    };
    setWeChatDebugLoggingOverrideForTests(true);

    try {
      logWeChatDebug('runtime prepared');
      logWeChatDebug('unsafe-eval ready');
      recordWeChatDebugError('bootstrap failed', new Error('missing canvas'));

      const firstSnapshot = getWeChatDebugLogSnapshot();
      expect(firstSnapshot.currentSession?.entries.map((entry) => entry.message)).toEqual([
        'runtime prepared',
        'unsafe-eval ready',
        'bootstrap failed',
      ]);
      expect(firstSnapshot.currentSession?.entries.at(-1)).toMatchObject({
        level: 'error',
        details: 'Error: missing canvas',
      });

      delete runtime.__pixiWeChatDebugLogs__;
      delete runtime.__pixiWeChatDebugActiveSessionId__;

      logWeChatDebug('runtime prepared');
      const secondSnapshot = getWeChatDebugLogSnapshot();

      expect(secondSnapshot.currentSession?.entries.map((entry) => entry.message)).toEqual([
        'runtime prepared',
      ]);
      expect(secondSnapshot.previousSession?.entries.map((entry) => entry.message)).toEqual([
        'runtime prepared',
        'unsafe-eval ready',
        'bootstrap failed',
      ]);
    } finally {
      runtime.wx = previousWx;
    }
  });

  test('does not persist breadcrumbs when debug logging is disabled', () => {
    const runtime = globalThis as DebugTestRuntime;
    const storage = new Map<string, string>();
    const previousWx = runtime.wx;

    runtime.wx = {
      getStorageSync: (key) => storage.get(key) ?? null,
      setStorageSync: (key, value) => {
        storage.set(key, value);
      },
    };
    setWeChatDebugLoggingOverrideForTests(false);

    try {
      logWeChatDebug('runtime prepared');
      recordWeChatDebugError('bootstrap failed', new Error('blocked'));

      expect(getWeChatDebugLogSnapshot()).toEqual({
        currentSession: null,
        previousSession: null,
      });
      expect(storage.values().next().value).toBeUndefined();
    } finally {
      runtime.wx = previousWx;
    }
  });
});
