# constraints.md (Pixi Game Constraint Template)

Record non-negotiable constraints before major implementation or refactor.

## 1) Runtime and Target

- Runtime today: Web
- Future runtime target: none / WeChat mini-game / Douyin mini-game / both
- Orientation: portrait / landscape / adaptive
- Safe-area strategy:

## 2) Display and Performance Budget

- Design resolution:
- Resolution mode: contain / cover / fixed
- Target FPS:
- Minimum acceptable FPS:
- First interactive time budget:
- Peak texture memory budget:

## 3) Asset Budget

- Initial critical asset budget:
- Lazy-loaded asset budget:
- Audio budget:
- Compression and versioning strategy:

## 4) Input Model

- Primary input: pointer / tap / drag / swipe
- One-hand interaction requirement:
- Accessibility or vibration needs:

## 5) Architecture Boundaries

- Required scene boundary:
- Required system boundary:
- Required platform abstraction:
- Forbidden browser APIs in gameplay:

## 6) Validation

- Required commands:
- Required manual smoke flow:
- Mini-game readiness required: yes / no
