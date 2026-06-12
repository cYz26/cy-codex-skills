# Platform Abstraction Contract

Use this reference when designing a future-proof boundary between Pixi gameplay code and runtime-specific services.

## Core Types

```ts
export type RuntimeTarget = 'web' | 'wechat-minigame' | 'douyin-minigame';

export interface GameBootConfig {
  target: RuntimeTarget;
  designWidth: number;
  designHeight: number;
  resolutionMode: 'contain' | 'cover' | 'fixed';
  launchSource?: string;
}

export interface PlatformBridge {
  getLaunchContext(): Record<string, unknown>;
  onPause(handler: () => void): () => void;
  onResume(handler: () => void): () => void;
  getStorageItem(key: string): Promise<string | null>;
  setStorageItem(key: string, value: string): Promise<void>;
  share?(payload: { title: string; imageUrl?: string }): Promise<void>;
  vibrate?(kind: 'light' | 'medium' | 'heavy'): Promise<void>;
}

export interface AssetResolver {
  resolve(alias: string): string;
}

export interface InputAdapter {
  bind(): void;
  destroy(): void;
}

export interface SceneContract {
  key: string;
  preload?(): Promise<void>;
  mount(): void;
  pause?(): void;
  resume?(): void;
  destroy(): void;
}
```

## Boundary Rules

1. Gameplay modules may depend on contracts, not vendor globals.
2. Platform implementations may depend on browser or mini-game APIs.
3. Asset URL policy belongs in `AssetResolver`, not scenes.
4. Lifecycle subscriptions belong in `PlatformBridge` or boot modules.
5. Vendor-specific share, login, storage, and launch payload shapes must not leak into gameplay code.

## Incremental Adoption

If the project is already Web-only:
1. keep a `web` implementation first
2. update call sites to depend on contracts
3. add vendor implementations later without rewriting scene logic
