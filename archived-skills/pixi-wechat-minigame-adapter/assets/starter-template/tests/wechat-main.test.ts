import { afterEach, describe, expect, test, vi } from 'vitest';

type WeChatMainTestRuntime = typeof globalThis & {
  wx?: {
    getStorageSync?: (key: string) => unknown;
    setStorageSync?: (key: string, value: string) => void;
    onError?: (listener: (error: string) => void) => void;
    onUnhandledRejection?: (
      listener: (result: { reason?: unknown }) => void,
    ) => void;
    getSystemInfoSync?: () => {
      platform?: string;
    };
    showModal?: (options: {
      title: string;
      content: string;
      showCancel?: boolean;
      confirmText?: string;
    }) => void;
    showToast?: (options: { title: string }) => void;
  };
  __pixiSkipWeChatMainAutoRun__?: boolean;
};

const loadWeChatMainModules = async () => {
  vi.resetModules();
  const runtime = globalThis as WeChatMainTestRuntime;
  runtime.__pixiSkipWeChatMainAutoRun__ = true;

  const startupTrace = await import('../src/platform/wechatStartupTrace');
  const wechatMain = await import('../src/wechat-main');
  return {
    ...startupTrace,
    ...wechatMain,
  };
};

afterEach(async () => {
  const runtime = globalThis as WeChatMainTestRuntime;
  runtime.wx = undefined;
  delete runtime.__pixiSkipWeChatMainAutoRun__;

  const startupTrace = await import('../src/platform/wechatStartupTrace');
  startupTrace.resetWeChatStartupTraceStateForTests();
});

describe('template wechat-main', () => {
  test('registers global hooks before heavy imports', async () => {
    const runtime = globalThis as WeChatMainTestRuntime;
    const storage = new Map<string, string>();
    const order: string[] = [];

    runtime.wx = {
      getStorageSync: (key) => storage.get(key) ?? null,
      setStorageSync: (key, value) => {
        storage.set(key, value);
      },
      onError: () => {
        order.push('hook:onError');
      },
      onUnhandledRejection: () => {
        order.push('hook:onUnhandledRejection');
      },
      showModal: vi.fn(),
    };

    const {
      completeWeChatStartupTrace,
      runWeChatMain,
      setWeChatStartupTraceEnabledForTests,
    } = await loadWeChatMainModules();
    setWeChatStartupTraceEnabledForTests(true);

    await runWeChatMain({
      importPrepareRuntime: async () => {
        order.push('import:prepare');
        return () => {
          order.push('call:prepare');
        };
      },
      importUnsafeEval: async () => {
        order.push('import:unsafe-eval');
        return {};
      },
      importBootstrap: async () => {
        order.push('import:bootstrap');
        return async () => {
          order.push('call:bootstrap');
          completeWeChatStartupTrace('first-tick');
        };
      },
    });

    expect(order).toEqual([
      'hook:onError',
      'hook:onUnhandledRejection',
      'import:prepare',
      'call:prepare',
      'import:unsafe-eval',
      'import:bootstrap',
      'call:bootstrap',
    ]);
  });

  test('persists startup failures and shows a native startup error', async () => {
    const runtime = globalThis as WeChatMainTestRuntime;
    const storage = new Map<string, string>();
    const showModal = vi.fn();

    runtime.wx = {
      getStorageSync: (key) => storage.get(key) ?? null,
      setStorageSync: (key, value) => {
        storage.set(key, value);
      },
      onError: vi.fn(),
      onUnhandledRejection: vi.fn(),
      showModal,
    };

    const {
      getWeChatStartupTraceSnapshot,
      runWeChatMain,
      setWeChatStartupTraceEnabledForTests,
    } = await loadWeChatMainModules();
    setWeChatStartupTraceEnabledForTests(true);

    await expect(
      runWeChatMain({
        importPrepareRuntime: async () => () => {},
        importUnsafeEval: async () => {
          throw new Error('unsafe eval blocked');
        },
        importBootstrap: async () => async () => {},
      }),
    ).rejects.toThrow('unsafe eval blocked');

    const snapshot = getWeChatStartupTraceSnapshot();
    expect(snapshot.currentSession?.status).toBe('failed');
    expect(snapshot.currentSession?.lastPhase).toBe('unsafe-eval-start');
    expect(showModal).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'WX startup error',
      }),
    );
  });

  test('suppresses native startup modals in devtools while still persisting failures', async () => {
    const runtime = globalThis as WeChatMainTestRuntime;
    const storage = new Map<string, string>();
    const showModal = vi.fn();

    runtime.wx = {
      getStorageSync: (key) => storage.get(key) ?? null,
      setStorageSync: (key, value) => {
        storage.set(key, value);
      },
      getSystemInfoSync: () => ({
        platform: 'devtools',
      }),
      onError: vi.fn(),
      onUnhandledRejection: vi.fn(),
      showModal,
    };

    const {
      getWeChatStartupTraceSnapshot,
      runWeChatMain,
      setWeChatStartupTraceEnabledForTests,
    } = await loadWeChatMainModules();
    setWeChatStartupTraceEnabledForTests(true);

    await expect(
      runWeChatMain({
        importPrepareRuntime: async () => () => {},
        importUnsafeEval: async () => {
          throw new Error('unsafe eval blocked');
        },
        importBootstrap: async () => async () => {},
      }),
    ).rejects.toThrow('unsafe eval blocked');

    const snapshot = getWeChatStartupTraceSnapshot();
    expect(snapshot.currentSession?.status).toBe('failed');
    expect(snapshot.currentSession?.lastPhase).toBe('unsafe-eval-start');
    expect(showModal).not.toHaveBeenCalled();
  });

  test('does not surface a stale failed startup report after a later successful run', async () => {
    const runtime = globalThis as WeChatMainTestRuntime & {
      __pixiWeChatStartupTraceSnapshot__?: unknown;
      __pixiWeChatStartupTraceActiveSessionId__?: string;
    };
    const storage = new Map<string, string>();
    const showModal = vi.fn();

    runtime.wx = {
      getStorageSync: (key) => storage.get(key) ?? null,
      setStorageSync: (key, value) => {
        storage.set(key, value);
      },
      onError: vi.fn(),
      onUnhandledRejection: vi.fn(),
      showModal,
    };

    const initial = await loadWeChatMainModules();
    initial.setWeChatStartupTraceEnabledForTests(true);

    await expect(
      initial.runWeChatMain({
        importPrepareRuntime: async () => () => {},
        importUnsafeEval: async () => {
          throw new Error('unsafe eval blocked');
        },
        importBootstrap: async () => async () => {},
      }),
    ).rejects.toThrow('unsafe eval blocked');

    delete runtime.__pixiWeChatStartupTraceSnapshot__;
    delete runtime.__pixiWeChatStartupTraceActiveSessionId__;
    showModal.mockClear();

    const refreshed = await loadWeChatMainModules();
    refreshed.setWeChatStartupTraceEnabledForTests(true);
    await refreshed.runWeChatMain({
      importPrepareRuntime: async () => () => {},
      importUnsafeEval: async () => ({}),
      importBootstrap: async () => async () => {
        refreshed.completeWeChatStartupTrace('first-tick');
      },
    });

    expect(
      showModal.mock.calls.some(
        ([options]) => options.title === 'Last startup trace',
      ),
    ).toBe(false);
  });

  test('still surfaces a pending startup report for unfinished previous runs', async () => {
    const runtime = globalThis as WeChatMainTestRuntime & {
      __pixiWeChatStartupTraceSnapshot__?: unknown;
      __pixiWeChatStartupTraceActiveSessionId__?: string;
    };
    const storage = new Map<string, string>();
    const showModal = vi.fn();

    runtime.wx = {
      getStorageSync: (key) => storage.get(key) ?? null,
      setStorageSync: (key, value) => {
        storage.set(key, value);
      },
      onError: vi.fn(),
      onUnhandledRejection: vi.fn(),
      showModal,
    };

    const initial = await loadWeChatMainModules();
    initial.setWeChatStartupTraceEnabledForTests(true);
    initial.beginWeChatStartupTrace();
    initial.markWeChatStartupPhase('runtime-prep-start');

    delete runtime.__pixiWeChatStartupTraceSnapshot__;
    delete runtime.__pixiWeChatStartupTraceActiveSessionId__;
    showModal.mockClear();

    const refreshed = await loadWeChatMainModules();
    refreshed.setWeChatStartupTraceEnabledForTests(true);
    await refreshed.runWeChatMain({
      importPrepareRuntime: async () => () => {},
      importUnsafeEval: async () => ({}),
      importBootstrap: async () => async () => {
        refreshed.completeWeChatStartupTrace('first-tick');
      },
    });

    expect(
      showModal.mock.calls.some(
        ([options]) => options.title === 'Last startup trace',
      ),
    ).toBe(true);
  });

  test('suppresses pending startup trace modals in devtools relaunches without consuming the report', async () => {
    const runtime = globalThis as WeChatMainTestRuntime & {
      __pixiWeChatStartupTraceSnapshot__?: unknown;
      __pixiWeChatStartupTraceActiveSessionId__?: string;
    };
    const storage = new Map<string, string>();
    const showModal = vi.fn();

    runtime.wx = {
      getStorageSync: (key) => storage.get(key) ?? null,
      setStorageSync: (key, value) => {
        storage.set(key, value);
      },
      onError: vi.fn(),
      onUnhandledRejection: vi.fn(),
      showModal,
    };

    const initial = await loadWeChatMainModules();
    initial.setWeChatStartupTraceEnabledForTests(true);

    await expect(
      initial.runWeChatMain({
        importPrepareRuntime: async () => () => {},
        importUnsafeEval: async () => {
          throw new Error('unsafe eval blocked');
        },
        importBootstrap: async () => async () => {},
      }),
    ).rejects.toThrow('unsafe eval blocked');

    delete runtime.__pixiWeChatStartupTraceSnapshot__;
    delete runtime.__pixiWeChatStartupTraceActiveSessionId__;
    showModal.mockClear();
    runtime.wx = {
      getStorageSync: (key) => storage.get(key) ?? null,
      setStorageSync: (key, value) => {
        storage.set(key, value);
      },
      getSystemInfoSync: () => ({
        platform: 'devtools',
      }),
      onError: vi.fn(),
      onUnhandledRejection: vi.fn(),
      showModal,
    };

    const refreshed = await loadWeChatMainModules();
    refreshed.setWeChatStartupTraceEnabledForTests(true);
    await refreshed.runWeChatMain({
      importPrepareRuntime: async () => () => {},
      importUnsafeEval: async () => ({}),
      importBootstrap: async () => async () => {
        refreshed.completeWeChatStartupTrace('first-tick');
      },
    });

    expect(showModal).not.toHaveBeenCalled();
    const pendingReport = refreshed.consumePendingWeChatStartupReport();
    expect(pendingReport?.status).toBe('failed');
    expect(pendingReport?.lastPhase).toBe('unsafe-eval-start');
  });
});
