# mini-game-readiness-checklist.md

Use this checklist before claiming a PixiJS project is ready for future WeChat or Douyin mini-game adaptation.

## 1) Runtime Boundary

- [ ] Gameplay code does not directly read `window` or `document`
- [ ] Browser storage is wrapped behind a platform service
- [ ] Networking is wrapped behind a service boundary
- [ ] Lifecycle hooks are centralized

## 2) Assets and Rendering

- [ ] Assets are manifest-driven
- [ ] Core gameplay does not depend on HTML overlays
- [ ] Resolution and resize policy is centralized
- [ ] Scene code does not hardcode CDN or file path policy

## 3) Input and Scene Flow

- [ ] Input is normalized before gameplay consumes it
- [ ] Mouse and touch are not split into unrelated game logic paths
- [ ] Scene lifecycle includes preload, mount, pause/resume, and destroy
- [ ] Listener cleanup is explicit

## 4) Future Platform Contracts

- [ ] `RuntimeTarget` exists
- [ ] `PlatformBridge` exists or is planned
- [ ] `AssetResolver` exists or is planned
- [ ] Launch context handling is isolated
- [ ] Share and vibration hooks are isolated if needed

## 5) Migration Gaps

- [ ] Blockers are listed
- [ ] High-risk couplings are listed
- [ ] Safe temporary Web-only code is listed
- [ ] Official vendor docs to re-check are listed
