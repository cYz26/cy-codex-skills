import { readdir, readFile, stat, writeFile } from 'node:fs/promises';
import { dirname, join, relative, resolve, sep } from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const defaultRepoRoot = resolve(__dirname, '..');
const defaultBuildProfile =
  process.env.WECHAT_BUILD_PROFILE === 'debug' ? 'debug' : 'release';
const releaseSubpackagePlanningThresholdBytes = Math.round(3.5 * 1024 * 1024);

const resolveOutputDir = (repoRoot, buildProfile) =>
  join(repoRoot, 'build', buildProfile === 'debug' ? 'wechatgame-debug' : 'wechatgame');

const normalizePath = (value) => value.split(sep).join('/');

const formatBytes = (bytes) => {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(2)} MiB`;
  }

  if (bytes >= 1024) {
    return `${(bytes / 1024).toFixed(2)} KiB`;
  }

  return `${bytes} B`;
};

const collectFiles = async (rootDir, currentDir = rootDir) => {
  const entries = await readdir(currentDir, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const fullPath = join(currentDir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await collectFiles(rootDir, fullPath)));
      continue;
    }

    if (!entry.isFile()) {
      continue;
    }

    const fileStat = await stat(fullPath);
    files.push({
      path: fullPath,
      relativePath: normalizePath(relative(rootDir, fullPath)),
      sizeBytes: fileStat.size
    });
  }

  return files;
};

const buildCheck = (name, passed, details = '') => ({
  name,
  passed,
  details
});

export const auditWeChatBuild = async ({
  repoRoot = defaultRepoRoot,
  buildProfile = defaultBuildProfile,
  outputDir = resolveOutputDir(repoRoot, buildProfile),
  reportPath = process.env.WX_AUDIT_REPORT || null,
  topFileCount = 10
} = {}) => {
  const projectConfigPath = join(outputDir, 'project.config.json');
  const minigameDir = join(outputDir, 'miniprogram');
  const projectConfig = JSON.parse(await readFile(projectConfigPath, 'utf8'));
  const files = await collectFiles(outputDir);
  const miniprogramFiles = files.filter((file) => file.relativePath.startsWith('miniprogram/'));
  const miniprogramSizeBytes = miniprogramFiles.reduce(
    (total, file) => total + file.sizeBytes,
    0
  );
  const topFiles = [...miniprogramFiles]
    .sort((left, right) => right.sizeBytes - left.sizeBytes)
    .slice(0, topFileCount)
    .map((file) => ({
      path: file.relativePath,
      sizeBytes: file.sizeBytes,
      sizeLabel: formatBytes(file.sizeBytes)
    }));

  const sourcemaps = files.filter((file) => file.relativePath.endsWith('.map'));
  const packagedRuntimeSourcemaps = sourcemaps.filter((file) =>
    file.relativePath.startsWith('miniprogram/js/')
  );
  const dotfiles = files.filter((file) =>
    file.relativePath.split('/').some((segment) => segment.startsWith('.'))
  );
  const sourceArtFiles = files.filter(
    (file) =>
      file.relativePath === 'miniprogram/assets/ui/source' ||
      file.relativePath.startsWith('miniprogram/assets/ui/source/') ||
      file.relativePath === 'miniprogram/gameContext/assets/ui/source' ||
      file.relativePath.startsWith('miniprogram/gameContext/assets/ui/source/')
  );
  const minified = Boolean(projectConfig.setting?.minified);

  const checks = [
    buildCheck(
      buildProfile === 'debug'
        ? 'debug build keeps minification disabled'
        : 'release build stays minified',
      buildProfile === 'debug' ? !minified : minified,
      `project.config.json.setting.minified=${String(minified)}`
    ),
    buildCheck(
      'package keeps official mini-game runtime root',
      projectConfig.compileType === 'game' &&
        projectConfig.miniprogramRoot === 'miniprogram/' &&
        projectConfig.srcMiniprogramRoot === 'miniprogram/',
      `compileType=${projectConfig.compileType}, miniprogramRoot=${projectConfig.miniprogramRoot}, srcMiniprogramRoot=${projectConfig.srcMiniprogramRoot}`
    ),
    buildCheck(
      'package keeps a non-empty libVersion',
      typeof projectConfig.libVersion === 'string' && projectConfig.libVersion.length > 0,
      `libVersion=${projectConfig.libVersion ?? ''}`
    ),
    buildCheck(
      'release package excludes sourcemaps',
      buildProfile === 'debug' ? true : sourcemaps.length === 0,
      buildProfile === 'debug'
        ? 'debug build; release-only check skipped'
        : sourcemaps.length === 0
          ? 'none found'
          : sourcemaps.map((file) => file.relativePath).join(', ')
    ),
    buildCheck(
      'debug package includes packaged runtime sourcemaps',
      buildProfile === 'debug' ? packagedRuntimeSourcemaps.length > 0 : true,
      buildProfile !== 'debug'
        ? 'release build; debug-only check skipped'
        : packagedRuntimeSourcemaps.length === 0
          ? 'none found'
          : packagedRuntimeSourcemaps.map((file) => file.relativePath).join(', ')
    ),
    buildCheck(
      'packaged assets exclude source art',
      sourceArtFiles.length === 0,
      sourceArtFiles.length === 0
        ? 'none found'
        : sourceArtFiles.map((file) => file.relativePath).join(', ')
    ),
    buildCheck(
      'packaged output excludes dotfiles',
      dotfiles.length === 0,
      dotfiles.length === 0
        ? 'none found'
        : dotfiles.map((file) => file.relativePath).join(', ')
    ),
    buildCheck(
      'release package stays below the 3.5 MiB subpackage planning threshold',
      buildProfile === 'debug' || miniprogramSizeBytes < releaseSubpackagePlanningThresholdBytes,
      buildProfile === 'debug'
        ? 'debug build; release-only threshold skipped'
        : `${formatBytes(miniprogramSizeBytes)} / ${formatBytes(releaseSubpackagePlanningThresholdBytes)}`
    )
  ];

  const result = {
    ok: checks.every((check) => check.passed),
    buildProfile,
    outputDir,
    minigameDir,
    miniprogramSizeBytes,
    miniprogramSizeLabel: formatBytes(miniprogramSizeBytes),
    topFiles,
    checks
  };

  if (reportPath) {
    await writeFile(reportPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
  }

  return result;
};

export const renderAuditSummary = (audit) => {
  const lines = [
    `WeChat build audit (${audit.buildProfile})`,
    `Output dir: ${audit.outputDir}`,
    `Packaged miniprogram size: ${audit.miniprogramSizeLabel} (${audit.miniprogramSizeBytes} bytes)`,
    '',
    'Largest packaged files:',
    ...audit.topFiles.map(
      (file, index) => `${index + 1}. ${file.path} - ${file.sizeLabel} (${file.sizeBytes} bytes)`
    ),
    '',
    'Checks:',
    ...audit.checks.map(
      (check) => `- ${check.passed ? 'PASS' : 'FAIL'} ${check.name}: ${check.details}`
    )
  ];

  return `${lines.join('\n')}\n`;
};

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const audit = await auditWeChatBuild();
    process.stdout.write(renderAuditSummary(audit));

    if (!audit.ok) {
      process.exitCode = 1;
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    process.stderr.write(`${message}\n`);
    process.exitCode = 1;
  }
}
