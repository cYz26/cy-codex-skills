import { prepareWeChatRuntime as bundledPrepareWeChatRuntime } from './platform/prepareWeChatRuntime';
import { isWeChatDevtoolsRuntime, recordWeChatDebugError } from './platform/wechatDebug';
import {
  beginWeChatStartupTrace,
  consumePendingWeChatStartupReport,
  failWeChatStartupTrace,
  markWeChatStartupPhase,
  type WeChatStartupTraceSession,
} from './platform/wechatStartupTrace';

type WeChatMainRuntime = typeof globalThis & {
  __pixiSkipWeChatMainAutoRun__?: boolean;
};

export interface WeChatMainDependencies {
  importPrepareRuntime: () => Promise<() => void>;
  importUnsafeEval: () => Promise<unknown>;
  importBootstrap: () => Promise<() => Promise<void>>;
}

let nativeStartupErrorShown = false;
let nativeStartupReportShown = false;

const formatStartupError = (error: unknown): string => {
  if (error instanceof Error) {
    return error.stack || error.message || error.name || 'error';
  }

  if (typeof error === 'string') {
    return error;
  }

  try {
    return JSON.stringify(error);
  } catch {
    return String(error);
  }
};

const showNativeModal = (title: string, content: string): void => {
  if (typeof wx === 'undefined' || isWeChatDevtoolsRuntime()) {
    return;
  }

  if (typeof wx.showModal === 'function') {
    wx.showModal({
      title,
      content,
      showCancel: false,
      confirmText: 'OK',
    });
    return;
  }

  wx.showToast?.({
    title,
    icon: 'none',
    duration: 4000,
  });
};

const showNativeStartupError = (phase: string, error: unknown): void => {
  if (nativeStartupErrorShown) {
    return;
  }

  nativeStartupErrorShown = true;
  showNativeModal(
    'WX startup error',
    `phase:${phase}\nerr:${formatStartupError(error).slice(0, 220)}`,
  );
};

const formatStartupTraceCheckpoint = (
  checkpoint: WeChatStartupTraceSession['checkpoints'][number],
): string => {
  const prefix = checkpoint.kind === 'error' ? '!' : '>';
  const detail = checkpoint.details ? `:${checkpoint.details}` : '';
  return `${prefix}${checkpoint.phase}${detail}`;
};

const showPendingStartupReport = (
  session: WeChatStartupTraceSession,
): void => {
  if (nativeStartupReportShown || session.status !== 'running') {
    return;
  }

  nativeStartupReportShown = true;
  const lines = [
    `status:${session.status}`,
    `last_phase:${session.lastPhase}`,
    `error:${session.errorSummary ?? '-'}`,
    ...session.checkpoints
      .slice(-5)
      .map((checkpoint) =>
        formatStartupTraceCheckpoint(checkpoint).slice(0, 80),
      ),
  ];
  showNativeModal('Last startup trace', lines.join('\n'));
};

const handleWeChatStartupFailure = (phase: string, error: unknown): void => {
  recordWeChatDebugError(phase, error);
  failWeChatStartupTrace(phase, error);
  showNativeStartupError(phase, error);
};

const scheduleWeChatMainAutoRun = (): void => {
  const start = (): void => {
    void runWeChatMain();
  };

  if (typeof globalThis.setTimeout === 'function') {
    globalThis.setTimeout(start, 0);
    return;
  }

  void Promise.resolve().then(start);
};

const installWeChatGlobalErrorHooks = (): void => {
  if (typeof wx === 'undefined') {
    return;
  }

  wx.onError?.((error) => {
    handleWeChatStartupFailure('wx.onError', error);
  });

  wx.onUnhandledRejection?.((result) => {
    handleWeChatStartupFailure(
      'wx.onUnhandledRejection',
      result.reason ?? result,
    );
  });
};

export const runWeChatMain = async (
  dependencies: Partial<WeChatMainDependencies> = {},
): Promise<void> => {
  beginWeChatStartupTrace();
  const pendingReport = isWeChatDevtoolsRuntime()
    ? null
    : consumePendingWeChatStartupReport();
  if (pendingReport) {
    showPendingStartupReport(pendingReport);
  }

  installWeChatGlobalErrorHooks();
  let activePhase = 'error-hooks-ready';
  const advancePhase = (phase: string): void => {
    activePhase = phase;
    markWeChatStartupPhase(phase);
  };
  advancePhase('error-hooks-ready');

  const resolvedDependencies: WeChatMainDependencies = {
    importPrepareRuntime: async () => bundledPrepareWeChatRuntime,
    importUnsafeEval: async () => import('pixi.js/unsafe-eval'),
    importBootstrap: async () =>
      (await import('./boot/bootstrap')).bootstrapWeChatGame,
    ...dependencies,
  };

  try {
    advancePhase('runtime-prep-start');
    const prepareWeChatRuntime = await resolvedDependencies.importPrepareRuntime();
    prepareWeChatRuntime();
    advancePhase('runtime-prep-end');

    advancePhase('unsafe-eval-start');
    await resolvedDependencies.importUnsafeEval();
    advancePhase('unsafe-eval-end');

    advancePhase('bootstrap-import-start');
    const bootstrapWeChatGame = await resolvedDependencies.importBootstrap();
    advancePhase('bootstrap-import-end');

    advancePhase('bootstrap-run-start');
    await bootstrapWeChatGame();
    advancePhase('bootstrap-run-end');
  } catch (error) {
    handleWeChatStartupFailure(activePhase, error);
    console.error(`[pixi-wx] startup failed during ${activePhase}`, error);
    throw error;
  }
};

const runtime = globalThis as WeChatMainRuntime;
if (!runtime.__pixiSkipWeChatMainAutoRun__) {
  scheduleWeChatMainAutoRun();
}
