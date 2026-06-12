# Pixi Game Architecture

Use this reference when the task touches project structure, scene boundaries, startup flow, or reusable contracts.

## Recommended Layout

```text
src/
  boot/
  scenes/
  systems/
  ui/
  assets/
  platform/
  shared/
```

Directory intent:
1. `boot/`: create the Pixi application, resolve config, register scenes, and start preload.
2. `scenes/`: own display trees, transitions, and scene-local orchestration.
3. `systems/`: own domain state, save logic, economy rules, timers, and non-visual services.
4. `ui/`: own HUD widgets, menus, popups, and UI composition helpers.
5. `assets/`: own manifests, aliases, bundle grouping, and asset metadata.
6. `platform/`: own environment-specific wrappers and launch context.
7. `shared/`: own pure types, constants, math helpers, and serialization-safe utilities.

## Boot Flow

Keep startup explicit:
1. Resolve `GameBootConfig`.
2. Create the Pixi application and root container.
3. Initialize platform services.
4. Load critical asset bundles.
5. Mount the first scene.
6. Expose pause, resume, resize, and destroy hooks in one place.

Do not mix boot and gameplay initialization inside arbitrary scene constructors.

## Recommended Contracts

Use contracts like these even if implementations stay lightweight:

```ts
export type RuntimeTarget = 'web' | 'wechat-minigame' | 'douyin-minigame';

export interface GameBootConfig {
  target: RuntimeTarget;
  designWidth: number;
  designHeight: number;
  resolutionMode: 'contain' | 'cover' | 'fixed';
  assetProfile: 'dev' | 'prod';
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

## Responsibility Boundaries

Keep these separations:
1. Scene code coordinates display and flow.
2. System code owns rules and state.
3. Platform code wraps storage, telemetry, lifecycle, and vendor APIs.
4. Shared code stays pure and testable.

If a gameplay module cannot run without `window`, `document`, or DOM queries, the boundary is wrong.

## Anti-Patterns

Avoid:
1. one giant `Game.ts` that owns boot, input, scenes, storage, and UI
2. scene classes that fetch assets with raw URLs inline
3. systems importing Pixi display classes for no reason
4. gameplay logic reading from HTML elements
5. platform checks spread through scene code with `if (isMobile)` style branches
