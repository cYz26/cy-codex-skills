import { mkdtemp, mkdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import vm from 'node:vm';

import { afterEach, describe, expect, test } from 'vitest';

import { buildWeChatProject } from '../tools/build-wechat.mjs';

const temporaryRoots: string[] = [];

afterEach(async () => {
  const { rm } = await import('node:fs/promises');
  await Promise.all(
    temporaryRoots.splice(0).map((root) => rm(root, { recursive: true, force: true }))
  );
});

const createFixture = async () => {
  const root = await mkdtemp(join(tmpdir(), 'pixi-wechat-build-'));
  temporaryRoots.push(root);

  const runtimeDir = join(root, 'build', 'wechat-runtime');
  const debugRuntimeDir = join(root, 'build', 'wechat-runtime-debug');
  const publicDir = join(root, 'public');
  const outputDir = join(root, 'build', 'wechatgame');
  const debugOutputDir = join(root, 'build', 'wechatgame-debug');
  const assetsDir = join(publicDir, 'assets', 'sprites');
  const sourceDir = join(publicDir, 'assets', 'ui', 'source');
  const hiddenDir = join(publicDir, '.hidden');

  await mkdir(runtimeDir, { recursive: true });
  await mkdir(debugRuntimeDir, { recursive: true });
  await mkdir(assetsDir, { recursive: true });
  await mkdir(sourceDir, { recursive: true });
  await mkdir(hiddenDir, { recursive: true });
  await writeFile(join(runtimeDir, 'wechat-main.js'), "console.log('wx runtime');\n", 'utf8');
  await writeFile(
    join(debugRuntimeDir, 'wechat-main.js'),
    "console.log('wx runtime debug');\n//# sourceMappingURL=wechat-main.js.map\n",
    'utf8'
  );
  await writeFile(
    join(debugRuntimeDir, 'wechat-main.js.map'),
    '{"version":3,"file":"wechat-main.js"}\n',
    'utf8'
  );
  await writeFile(join(assetsDir, 'player.png'), 'player', 'utf8');
  await writeFile(join(sourceDir, 'raw.png'), 'raw', 'utf8');
  await writeFile(join(publicDir, '.DS_Store'), 'junk', 'utf8');
  await writeFile(join(hiddenDir, 'ignored.txt'), 'hidden', 'utf8');

  return {
    debugOutputDir,
    debugRuntimeDir,
    outputDir,
    publicDir,
    root,
    runtimeDir
  };
};

describe('buildWeChatProject', () => {
  test('packages runtime and public assets while excluding source art and dotfiles', async () => {
    const fixture = await createFixture();

    await buildWeChatProject({
      outputDir: fixture.outputDir,
      publicDir: fixture.publicDir,
      repoRoot: fixture.root,
      runtimeDir: fixture.runtimeDir,
      wechatAppId: 'wx-test-appid'
    });

    await expect(
      readFile(
        join(fixture.outputDir, 'miniprogram', 'gameContext', 'assets', 'sprites', 'player.png'),
        'utf8'
      )
    ).resolves.toBe('player');
    await expect(
      readFile(join(fixture.outputDir, 'miniprogram', 'assets', 'ui', 'source', 'raw.png'), 'utf8')
    ).rejects.toThrow();
    await expect(readFile(join(fixture.outputDir, 'miniprogram', '.DS_Store'), 'utf8')).rejects.toThrow();
    await expect(readFile(join(fixture.outputDir, 'project.config.json'), 'utf8')).resolves.toContain(
      '"appid": "wx-test-appid"'
    );
    await expect(readFile(join(fixture.outputDir, 'project.config.json'), 'utf8')).resolves.toContain(
      '"libVersion": "3.15.0"'
    );
    await expect(readFile(join(fixture.outputDir, 'project.config.json'), 'utf8')).resolves.toContain(
      '"enhance": false'
    );
    await expect(readFile(join(fixture.outputDir, 'project.config.json'), 'utf8')).resolves.toContain(
      '"useMultiFrameRuntime": true'
    );
    await expect(readFile(join(fixture.outputDir, 'miniprogram', 'game.json'), 'utf8')).resolves.toContain(
      '"backgroundColor": "#07111d"'
    );
    await expect(readFile(join(fixture.outputDir, 'miniprogram', 'game.json'), 'utf8')).resolves.not.toContain(
      '"iOSHighPerformance"'
    );
    await expect(readFile(join(fixture.outputDir, 'miniprogram', 'game.js'), 'utf8')).resolves.toContain(
      "const __pixiWeChatScreenCanvasKey = '__pixiWeChatScreenCanvas';"
    );
    await expect(readFile(join(fixture.outputDir, 'miniprogram', 'game.js'), 'utf8')).resolves.toContain(
      '__pixiWeChatCreateOffscreenCanvas'
    );
    await expect(readFile(join(fixture.outputDir, 'miniprogram', 'game.js'), 'utf8')).resolves.toContain(
      "__pixiWeChatSafeDefine(__pixiWeChatDocument, 'querySelectorAll'"
    );
    await expect(readFile(join(fixture.outputDir, 'README.md'), 'utf8')).resolves.toContain(
      'run `make audit`'
    );
  });

  test('allows overriding the default libVersion', async () => {
    const fixture = await createFixture();

    await buildWeChatProject({
      outputDir: fixture.outputDir,
      publicDir: fixture.publicDir,
      repoRoot: fixture.root,
      runtimeDir: fixture.runtimeDir,
      wechatLibVersion: '2.33.1'
    });

    await expect(readFile(join(fixture.outputDir, 'project.config.json'), 'utf8')).resolves.toContain(
      '"libVersion": "2.33.1"'
    );
  });

  test('writes debug-profile metadata and packages the debug sourcemap', async () => {
    const fixture = await createFixture();

    await buildWeChatProject({
      buildProfile: 'debug',
      outputDir: fixture.debugOutputDir,
      publicDir: fixture.publicDir,
      repoRoot: fixture.root,
      runtimeDir: fixture.debugRuntimeDir
    });

    await expect(readFile(join(fixture.debugOutputDir, 'project.config.json'), 'utf8')).resolves.toContain(
      '"minified": false'
    );
    await expect(readFile(join(fixture.debugOutputDir, 'README.md'), 'utf8')).resolves.toContain(
      'Build profile: `debug`'
    );
    await expect(
      readFile(join(fixture.debugOutputDir, 'miniprogram', 'js', 'wechat-main.js.map'), 'utf8')
    ).resolves.toContain('"version":3');
  });

  test('bootstraps against a getter-only global document without throwing', async () => {
    const fixture = await createFixture();

    await buildWeChatProject({
      outputDir: fixture.outputDir,
      publicDir: fixture.publicDir,
      repoRoot: fixture.root,
      runtimeDir: fixture.runtimeDir
    });

    const entrySource = await readFile(join(fixture.outputDir, 'miniprogram', 'game.js'), 'utf8');
    const existingDocument: Record<string, unknown> = {};
    const context = {
      GameGlobal: {},
      console: {
        error() {},
        info() {}
      },
      require() {
        return {};
      },
      wx: {
        createCanvas() {
          return {
            width: 390,
            height: 844,
            style: {},
            getContext() {
              return {};
            }
          };
        },
        createImage() {
          return {
            complete: true
          };
        }
      }
    };

    Object.defineProperty(context, 'document', {
      get() {
        return existingDocument;
      }
    });

    vm.createContext(context);

    expect(() => vm.runInContext(entrySource, context)).not.toThrow();
    expect((context.GameGlobal as { canvas?: unknown }).canvas).toBeDefined();
    expect((context.GameGlobal as { document?: unknown }).document).toBe(existingDocument);
  });

  test('creates a synthetic document when no global document exists', async () => {
    const fixture = await createFixture();

    await buildWeChatProject({
      outputDir: fixture.outputDir,
      publicDir: fixture.publicDir,
      repoRoot: fixture.root,
      runtimeDir: fixture.runtimeDir
    });

    const entrySource = await readFile(join(fixture.outputDir, 'miniprogram', 'game.js'), 'utf8');
    const context = {
      GameGlobal: {},
      console: {
        error() {},
        info() {}
      },
      require() {
        return {};
      },
      wx: {
        createCanvas() {
          return {
            width: 390,
            height: 844,
            style: {},
            getContext() {
              return {};
            }
          };
        },
        createImage() {
          return {
            complete: true
          };
        }
      }
    };

    vm.createContext(context);

    expect(() => vm.runInContext(entrySource, context)).not.toThrow();
    expect((context.document as { querySelector(selector: string): unknown }).querySelector('canvas')).toBe(
      (context.GameGlobal as { canvas?: unknown }).canvas
    );
    expect(
      ((context.document as { body?: { contains(node: unknown): boolean } }).body)?.contains(
        (context.GameGlobal as { canvas?: unknown }).canvas
      )
    ).toBe(true);
  });
});
