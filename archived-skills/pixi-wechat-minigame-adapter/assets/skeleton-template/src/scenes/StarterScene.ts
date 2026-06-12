import { Container, Graphics, Text } from 'pixi.js';

import { UI_COLORS } from '../shared/config/gameConfig';
import type { SceneContract, ViewportMetrics } from '../shared/contracts';

export class StarterScene implements SceneContract {
  readonly key = 'starter';
  readonly container = new Container();

  private readonly panel = new Graphics();
  private readonly button = new Graphics();
  private readonly halo = new Graphics();
  private readonly title = new Text({
    text: 'PixiJS WeChat Starter',
    style: {
      fill: UI_COLORS.textPrimary,
      fontFamily: 'sans-serif',
      fontSize: 56,
      fontWeight: '700',
    },
  });
  private readonly subtitle = new Text({
    text: 'Single screen canvas. Dual target. Canonical adapter boundary.',
    style: {
      fill: UI_COLORS.accent,
      fontFamily: 'sans-serif',
      fontSize: 24,
      fontWeight: '600',
    },
  });
  private readonly status = new Text({
    text: 'Tap the button or press F on Web.',
    style: {
      fill: UI_COLORS.textMuted,
      fontFamily: 'sans-serif',
      fontSize: 26,
      fontWeight: '500',
      align: 'center',
    },
  });
  private readonly buttonLabel = new Text({
    text: 'Confirm Boot',
    style: {
      fill: UI_COLORS.textPrimary,
      fontFamily: 'sans-serif',
      fontSize: 34,
      fontWeight: '700',
    },
  });

  private confirmed = false;

  constructor() {
    this.container.addChild(this.panel, this.halo, this.title, this.subtitle, this.status, this.button, this.buttonLabel);
    this.button.eventMode = 'static';
    this.button.cursor = 'pointer';
    this.button.on('pointertap', () => this.confirmBoot());
  }

  mount(): void {
    this.redraw();
  }

  update(dtMs: number): void {
    this.halo.rotation += dtMs * 0.00015;
  }

  resize(viewport: ViewportMetrics): void {
    this.container.position.set(0, 0);
    this.redraw();

    const centerX = viewport.width / 2;
    this.title.anchor.set(0.5, 0);
    this.title.position.set(centerX, viewport.safeTop + 120);

    this.subtitle.anchor.set(0.5, 0);
    this.subtitle.position.set(centerX, this.title.y + 96);

    this.status.anchor.set(0.5, 0);
    this.status.position.set(centerX, this.subtitle.y + 140);

    this.halo.position.set(centerX, viewport.height - 280);

    this.button.position.set(centerX - 180, viewport.height - 360);
    this.buttonLabel.anchor.set(0.5);
    this.buttonLabel.position.set(centerX, viewport.height - 300);
  }

  getTextSnapshot(): string {
    return JSON.stringify({
      scene: this.key,
      confirmed: this.confirmed,
      status: this.status.text,
    });
  }

  destroy(): void {
    this.button.removeAllListeners();
    this.container.destroy({ children: true });
  }

  private confirmBoot(): void {
    this.confirmed = true;
    this.status.text = 'Boot confirmed. Continue from this skeleton.';
    this.redraw();
  }

  private redraw(): void {
    this.panel.clear();
    this.panel.roundRect(48, 72, 624, 1136, 32).fill({
      color: UI_COLORS.panel,
      alpha: 0.98,
    });
    this.panel.roundRect(48, 72, 624, 1136, 32).stroke({
      color: UI_COLORS.panelBorder,
      alpha: 1,
      width: 4,
    });

    this.halo.clear();
    this.halo.circle(0, 0, 180).stroke({
      color: UI_COLORS.panelBorder,
      alpha: 0.7,
      width: 6,
    });

    this.button.clear();
    this.button.roundRect(0, 0, 360, 108, 26).fill({
      color: this.confirmed ? UI_COLORS.accent : UI_COLORS.buttonFill,
      alpha: 1,
    });
    this.button.roundRect(0, 0, 360, 108, 26).stroke({
      color: UI_COLORS.buttonStroke,
      alpha: 1,
      width: 4,
    });
  }
}
