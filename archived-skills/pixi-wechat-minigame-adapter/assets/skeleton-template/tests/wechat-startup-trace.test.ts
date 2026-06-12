import { afterEach, describe, expect, test } from 'vitest';

import {
  beginWeChatStartupTrace,
  completeWeChatStartupTrace,
  consumePendingWeChatStartupReport,
  failWeChatStartupTrace,
  getWeChatStartupTraceSnapshot,
  markWeChatStartupPhase,
  resetWeChatStartupTraceStateForTests,
  setWeChatStartupTraceEnabledForTests,
} from '../src/platform/wechatStartupTrace';

type StartupTraceTestRuntime = typeof globalThis & {
  wx?: {
    getStorageSync?: (key: string) => unknown;
    setStorageSync?: (key: string, value: string) => void;
  };
  __pixiWeChatStartupTraceSnapshot__?: unknown;
  __pixiWeChatStartupTraceActiveSessionId__?: string;
  __pixiWeChatStartupTraceSessionCounter__?: number;
};

afterEach(() => {
  resetWeChatStartupTraceStateForTests();
});

describe('wechatStartupTrace', () => {
  test('rotates an unfinished run into the pending previous-session report', () => {
    const runtime = globalThis as StartupTraceTestRuntime;
    const storage = new Map<string, string>();
    const previousWx = runtime.wx;

    runtime.wx = {
      getStorageSync: (key) => storage.get(key) ?? null,
      setStorageSync: (key, value) => {
        storage.set(key, value);
      },
    };
    setWeChatStartupTraceEnabledForTests(true);

    try {
      beginWeChatStartupTrace();
      markWeChatStartupPhase('runtime-prep-start');

      delete runtime.__pixiWeChatStartupTraceSnapshot__;
      delete runtime.__pixiWeChatStartupTraceActiveSessionId__;

      beginWeChatStartupTrace();
      const snapshot = getWeChatStartupTraceSnapshot();

      expect(snapshot.previousSession?.status).toBe('running');
      expect(snapshot.previousSession?.lastPhase).toBe('runtime-prep-start');

      const report = consumePendingWeChatStartupReport();
      expect(report?.status).toBe('running');
      expect(report?.lastPhase).toBe('runtime-prep-start');
      expect(consumePendingWeChatStartupReport()).toBeNull();
    } finally {
      runtime.wx = previousWx;
    }
  });

  test('bounds checkpoints and marks failures with a summarized error', () => {
    const runtime = globalThis as StartupTraceTestRuntime;
    const storage = new Map<string, string>();
    const previousWx = runtime.wx;

    runtime.wx = {
      getStorageSync: (key) => storage.get(key) ?? null,
      setStorageSync: (key, value) => {
        storage.set(key, value);
      },
    };
    setWeChatStartupTraceEnabledForTests(true);

    try {
      beginWeChatStartupTrace();
      for (let index = 0; index < 10; index += 1) {
        markWeChatStartupPhase(`phase-${index}`);
      }
      failWeChatStartupTrace('bootstrap failed', new Error('missing canvas'));

      const snapshot = getWeChatStartupTraceSnapshot();
      expect(snapshot.currentSession?.status).toBe('failed');
      expect(snapshot.currentSession?.lastPhase).toBe('bootstrap failed');
      expect(snapshot.currentSession?.errorSummary).toBe('Error: missing canvas');
      expect(snapshot.currentSession?.checkpoints).toHaveLength(8);
      expect(snapshot.currentSession?.checkpoints.at(-1)).toMatchObject({
        phase: 'bootstrap failed',
        kind: 'error',
      });
    } finally {
      runtime.wx = previousWx;
    }
  });

  test('does not surface a pending report after a ready session', () => {
    const runtime = globalThis as StartupTraceTestRuntime;
    const storage = new Map<string, string>();
    const previousWx = runtime.wx;

    runtime.wx = {
      getStorageSync: (key) => storage.get(key) ?? null,
      setStorageSync: (key, value) => {
        storage.set(key, value);
      },
    };
    setWeChatStartupTraceEnabledForTests(true);

    try {
      beginWeChatStartupTrace();
      markWeChatStartupPhase('first-render');
      completeWeChatStartupTrace('first-tick');

      delete runtime.__pixiWeChatStartupTraceSnapshot__;
      delete runtime.__pixiWeChatStartupTraceActiveSessionId__;

      beginWeChatStartupTrace();
      const snapshot = getWeChatStartupTraceSnapshot();

      expect(snapshot.previousSession?.status).toBe('ready');
      expect(consumePendingWeChatStartupReport()).toBeNull();
    } finally {
      runtime.wx = previousWx;
    }
  });
});
