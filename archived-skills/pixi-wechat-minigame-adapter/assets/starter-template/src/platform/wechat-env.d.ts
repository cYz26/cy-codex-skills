interface WechatMinigameSafeArea {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

interface WechatMinigameSystemInfo {
  pixelRatio: number;
  windowWidth: number;
  windowHeight: number;
  safeArea?: WechatMinigameSafeArea;
  platform?: string;
  model?: string;
  brand?: string;
}

interface WechatMinigameDeviceInfo {
  platform?: string;
  system?: string;
  model?: string;
  brand?: string;
}

interface WechatMinigameReferrerInfo {
  appId?: string;
  extraData?: Record<string, unknown>;
}

interface WechatMinigameLaunchOptions {
  path?: string;
  query?: Record<string, string | undefined>;
  scene?: number;
  shareTicket?: string;
  referrerInfo?: WechatMinigameReferrerInfo;
}

interface WechatMinigameWindowResizeResult {
  windowWidth: number;
  windowHeight: number;
}

interface WechatMinigameSharePayload {
  title: string;
  imageUrl?: string;
}

interface WechatMinigameModalOptions {
  title: string;
  content: string;
  showCancel?: boolean;
  cancelText?: string;
  confirmText?: string;
}

interface WechatMinigameToastOptions {
  title: string;
  icon?: 'success' | 'error' | 'loading' | 'none';
  duration?: number;
}

interface WechatMinigameBackgroundColorOptions {
  backgroundColor?: string;
  backgroundColorTop?: string;
  backgroundColorBottom?: string;
}

interface WechatMinigameUnhandledRejectionResult {
  reason?: unknown;
  promise?: Promise<unknown>;
}

interface WechatMinigameMemoryWarningResult {
  level?: number;
}

interface WechatMinigameAPI {
  createCanvas(): object;
  createImage?(): object;
  getSystemInfoSync(): WechatMinigameSystemInfo;
  getDeviceInfo?(): WechatMinigameDeviceInfo;
  getEnterOptionsSync?(): WechatMinigameLaunchOptions;
  getLaunchOptionsSync?(): WechatMinigameLaunchOptions;
  getFileSystemManager?(): {
    readFileSync(filePath: string, encoding?: string): string | ArrayBuffer;
  };
  getStorageSync(key: string): unknown;
  setStorageSync(key: string, value: string): void;
  onWindowResize(listener: (result: WechatMinigameWindowResizeResult) => void): void;
  offWindowResize?(listener: (result: WechatMinigameWindowResizeResult) => void): void;
  onHide(listener: () => void): void;
  offHide?(listener: () => void): void;
  onShow(listener: (options?: WechatMinigameLaunchOptions) => void): void;
  offShow?(listener: (options?: WechatMinigameLaunchOptions) => void): void;
  onMemoryWarning?(
    listener: (result?: WechatMinigameMemoryWarningResult) => void
  ): void;
  offMemoryWarning?(
    listener: (result?: WechatMinigameMemoryWarningResult) => void
  ): void;
  shareAppMessage(payload: WechatMinigameSharePayload): void;
  setBackgroundColor?(options: WechatMinigameBackgroundColorOptions): void;
  showModal?(options: WechatMinigameModalOptions): void;
  showToast?(options: WechatMinigameToastOptions): void;
  onError?(listener: (error: string) => void): void;
  offError?(listener: (error: string) => void): void;
  onUnhandledRejection?(
    listener: (result: WechatMinigameUnhandledRejectionResult) => void
  ): void;
  offUnhandledRejection?(
    listener: (result: WechatMinigameUnhandledRejectionResult) => void
  ): void;
  vibrateShort?(): void;
  vibrateLong?(): void;
}

declare const wx: WechatMinigameAPI;
