import { mkdtemp, mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

import { afterEach, describe, expect, test } from 'vitest';

import { auditWeChatBuild } from '../tools/audit-wechat-build.mjs';
import { buildWeChatProject } from '../tools/build-wechat.mjs';

const temporaryRoots: string[] = [];

afterEach(async () => {
  const { rm } = await import('node:fs/promises');
  await Promise.all(
    temporaryRoots.splice(0).map((root) => rm(root, { recursive: true, force: true }))
  );
});

const createFixture = async () => {
  const root = await mkdtemp(join(tmpdir(), 'pixi-wechat-audit-'));
  temporaryRoots.push(root);

  const runtimeDir = join(root, 'build', 'wechat-runtime');
  const debugRuntimeDir = join(root, 'build', 'wechat-runtime-debug');
  const publicDir = join(root, 'public');
  const assetsDir = join(publicDir, 'assets', 'sprites');

  await mkdir(runtimeDir, { recursive: true });
  await mkdir(debugRuntimeDir, { recursive: true });
  await mkdir(assetsDir, { recursive: true });
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

  return {
    debugOutputDir: join(root, 'build', 'wechatgame-debug'),
    debugRuntimeDir,
    outputDir: join(root, 'build', 'wechatgame'),
    publicDir,
    root,
    runtimeDir
  };
};

describe('auditWeChatBuild', () => {
  test('passes for a healthy release package and reports packaged size', async () => {
    const fixture = await createFixture();

    await buildWeChatProject({
      outputDir: fixture.outputDir,
      publicDir: fixture.publicDir,
      repoRoot: fixture.root,
      runtimeDir: fixture.runtimeDir
    });

    const audit = await auditWeChatBuild({
      buildProfile: 'release',
      outputDir: fixture.outputDir
    });

    expect(audit.ok).toBe(true);
    expect(audit.miniprogramSizeBytes).toBeGreaterThan(0);
    expect(audit.topFiles[0]?.path).toContain('miniprogram/');
    expect(
      audit.checks.find((check) => check.name === 'release build stays minified')?.passed
    ).toBe(true);
  });

  test('fails when sourcemaps, source art, or dotfiles leak into the release package', async () => {
    const fixture = await createFixture();

    await buildWeChatProject({
      outputDir: fixture.outputDir,
      publicDir: fixture.publicDir,
      repoRoot: fixture.root,
      runtimeDir: fixture.runtimeDir
    });

    await mkdir(join(fixture.outputDir, 'miniprogram', 'assets', 'ui', 'source'), {
      recursive: true
    });
    await writeFile(join(fixture.outputDir, 'miniprogram', 'assets', 'ui', 'source', 'raw.png'), 'raw', 'utf8');
    await writeFile(join(fixture.outputDir, 'miniprogram', '.DS_Store'), 'junk', 'utf8');
    await writeFile(join(fixture.outputDir, 'miniprogram', 'js', 'wechat-main.js.map'), '{}', 'utf8');

    const audit = await auditWeChatBuild({
      buildProfile: 'release',
      outputDir: fixture.outputDir
    });

    expect(audit.ok).toBe(false);
    expect(
      audit.checks.find((check) => check.name === 'release package excludes sourcemaps')?.passed
    ).toBe(false);
    expect(
      audit.checks.find((check) => check.name === 'packaged assets exclude source art')?.passed
    ).toBe(false);
    expect(
      audit.checks.find((check) => check.name === 'packaged output excludes dotfiles')?.passed
    ).toBe(false);
  });

  test('treats the debug profile as intentionally unminified', async () => {
    const fixture = await createFixture();

    await buildWeChatProject({
      buildProfile: 'debug',
      outputDir: fixture.debugOutputDir,
      publicDir: fixture.publicDir,
      repoRoot: fixture.root,
      runtimeDir: fixture.debugRuntimeDir
    });

    const audit = await auditWeChatBuild({
      buildProfile: 'debug',
      outputDir: fixture.debugOutputDir
    });

    expect(audit.ok).toBe(true);
    expect(
      audit.checks.find((check) => check.name === 'debug build keeps minification disabled')
        ?.passed
    ).toBe(true);
    expect(
      audit.checks.find(
        (check) => check.name === 'debug package includes packaged runtime sourcemaps'
      )?.passed
    ).toBe(true);
  });
});
