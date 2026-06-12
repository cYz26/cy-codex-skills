import { access, cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { basename, dirname, join, relative, resolve, sep } from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const defaultRepoRoot = resolve(__dirname, '..');
const defaultWeChatAppId = process.env.WX_MINIGAME_APPID || 'touristappid';
const defaultWeChatLibVersion = process.env.WX_MINIGAME_LIB_VERSION || '3.15.0';
const defaultBuildProfile =
  process.env.WECHAT_BUILD_PROFILE === 'debug' ? 'debug' : 'release';
const defaultSurfaceBackgroundColor = '#07111d';

const resolveRuntimeDir = (repoRoot, buildProfile) =>
  join(
    repoRoot,
    'build',
    buildProfile === 'debug' ? 'wechat-runtime-debug' : 'wechat-runtime'
  );

const resolveOutputDir = (repoRoot, buildProfile) =>
  join(repoRoot, 'build', buildProfile === 'debug' ? 'wechatgame-debug' : 'wechatgame');

const pathExists = async (targetPath) => {
  try {
    await access(targetPath);
    return true;
  } catch {
    return false;
  }
};

const ensureRuntimeExists = async (runtimeEntry) => {
  try {
    await readFile(runtimeEntry, 'utf8');
  } catch {
    throw new Error(
      `WeChat runtime bundle not found at ${runtimeEntry}. Run vite.wechat.config.ts first.`
    );
  }
};

const copyRuntimeSourcemapIfNeeded = async ({ buildProfile, minigameDir, runtimeDir }) => {
  if (buildProfile !== 'debug') {
    return false;
  }

  const runtimeSourcemapEntry = join(runtimeDir, 'wechat-main.js.map');
  try {
    await readFile(runtimeSourcemapEntry, 'utf8');
  } catch {
    throw new Error(
      `WeChat debug runtime sourcemap not found at ${runtimeSourcemapEntry}. Run vite.wechat.config.ts with debug sourcemaps enabled first.`
    );
  }

  await cp(runtimeSourcemapEntry, join(minigameDir, 'js', 'wechat-main.js.map'));
  return true;
};

const writeJson = async (targetPath, value) => {
  await writeFile(targetPath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
};

const shouldCopyPublicEntry = (publicDir, sourcePath) => {
  const entryName = basename(sourcePath);
  if (entryName.startsWith('.')) {
    return false;
  }

  const relativePath = relative(publicDir, sourcePath);
  if (!relativePath || relativePath === '') {
    return true;
  }

  const normalizedPath = relativePath.split(sep).join('/');
  if (
    normalizedPath === 'assets/ui/source' ||
    normalizedPath.startsWith('assets/ui/source/')
  ) {
    return false;
  }

  return !normalizedPath.split('/').some((segment) => segment.startsWith('.'));
};

const copyPackagedPublicDir = async (publicDir, targetDir) => {
  if (!(await pathExists(publicDir))) {
    return false;
  }

  await cp(publicDir, targetDir, {
    recursive: true,
    filter: (sourcePath) => shouldCopyPublicEntry(publicDir, sourcePath)
  });
  return true;
};

const mirrorDevtoolsGameContextAssets = async (publicDir, minigameDir) => {
  const publicAssetsDir = join(publicDir, 'assets');
  if (!(await pathExists(publicAssetsDir))) {
    return false;
  }

  const gameContextDir = join(minigameDir, 'gameContext');
  await mkdir(gameContextDir, { recursive: true });
  await cp(publicAssetsDir, join(gameContextDir, 'assets'), {
    recursive: true,
    filter: (sourcePath) => shouldCopyPublicEntry(publicDir, sourcePath)
  });
  return true;
};

const createWeChatGameEntrySource = (buildProfile) => {
  const debugEnabled = buildProfile === 'debug' ? 'true' : 'false';

  return `const __pixiWeChatGlobal = typeof globalThis !== 'undefined' ? globalThis : GameGlobal;
const __pixiWeChatDebugEnabled = ${debugEnabled};
const __pixiWeChatCanvasRoleKey = '__pixiWeChatCanvasRole';
const __pixiWeChatScreenCanvasKey = '__pixiWeChatScreenCanvas';
const __pixiWeChatOffscreenCanvasFactoryKey = '__pixiWeChatCreateOffscreenCanvas';
const __pixiWeChatScreenCanvasId = 'myCanvas';

const __pixiWeChatSafeDefine = (target, key, value) => {
  if (!target || (typeof target !== 'object' && typeof target !== 'function')) {
    return value;
  }
  try {
    Object.defineProperty(target, key, {
      value,
      configurable: true,
      writable: true,
    });
  } catch {
    try {
      target[key] = value;
    } catch {}
  }
  return value;
};

const __pixiWeChatReadMetric = (value) =>
  typeof value === 'number' && Number.isFinite(value) ? value : 0;

const __pixiWeChatParsePixelSize = (value) => {
  if (typeof value !== 'string' || value.length === 0) {
    return null;
  }
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const __pixiWeChatLog = (label, details) => {
  if (!__pixiWeChatDebugEnabled) {
    return;
  }
  if (typeof console !== 'undefined' && typeof console.info === 'function') {
    console.info(label, details);
  }
};

const __pixiWeChatInstallEventTarget = (target) => {
  if (!target || (typeof target !== 'object' && typeof target !== 'function')) {
    return target;
  }
  if (
    typeof target.addEventListener === 'function' &&
    typeof target.removeEventListener === 'function' &&
    typeof target.dispatchEvent === 'function'
  ) {
    return target;
  }

  const listeners = Object.create(null);
  __pixiWeChatSafeDefine(target, 'addEventListener', (type, listener) => {
    if (typeof listener !== 'function') {
      return;
    }
    (listeners[type] ||= new Set()).add(listener);
  });
  __pixiWeChatSafeDefine(target, 'removeEventListener', (type, listener) => {
    listeners[type]?.delete(listener);
  });
  __pixiWeChatSafeDefine(target, 'dispatchEvent', (event) => {
    const type = event && typeof event.type === 'string' ? event.type : '';
    for (const listener of listeners[type] || []) {
      listener(event);
    }
    return true;
  });

  return target;
};

const __pixiWeChatSetDomLink = (node, key, value) => {
  if (!node || (typeof node !== 'object' && typeof node !== 'function')) {
    return;
  }
  __pixiWeChatSafeDefine(node, key, value);
};

const __pixiWeChatNodeContains = (root, node) => {
  let current = node;
  while (current) {
    if (current === root) {
      return true;
    }
    current =
      current && (typeof current === 'object' || typeof current === 'function')
        ? current.parentNode
        : null;
  }
  return false;
};

const __pixiWeChatSetConnection = (node, connected) => {
  if (!node || (typeof node !== 'object' && typeof node !== 'function')) {
    return;
  }
  __pixiWeChatSetDomLink(node, 'isConnected', connected);
  const children = Array.isArray(node.children) ? node.children : [];
  for (const child of children) {
    __pixiWeChatSetConnection(child, connected);
  }
};

const __pixiWeChatAppendChild = (parent, child) => {
  if (!Array.isArray(parent.children)) {
    parent.children = [];
  }
  if (!parent.children.includes(child)) {
    parent.children.push(child);
  }
  __pixiWeChatSetDomLink(child, 'parentNode', parent);
  if (parent.ownerDocument !== undefined) {
    __pixiWeChatSetDomLink(child, 'ownerDocument', parent.ownerDocument);
  }
  __pixiWeChatSetConnection(child, parent.isConnected === true);
  return child;
};

const __pixiWeChatRemoveChild = (parent, child) => {
  if (!Array.isArray(parent.children)) {
    parent.children = [];
  }
  const index = parent.children.indexOf(child);
  if (index >= 0) {
    parent.children.splice(index, 1);
  }
  if (child && (typeof child === 'object' || typeof child === 'function')) {
    if (child.parentNode === parent) {
      __pixiWeChatSetDomLink(child, 'parentNode', null);
    }
    __pixiWeChatSetConnection(child, false);
  }
  return child;
};

const __pixiWeChatCreateElementStub = (tagName) => {
  const normalizedTagName = String(tagName || '').toUpperCase();
  const node = {
    tagName: normalizedTagName,
    nodeName: normalizedTagName,
    style: {},
    children: [],
    appendChild(child) {
      return __pixiWeChatAppendChild(node, child);
    },
    removeChild(child) {
      return __pixiWeChatRemoveChild(node, child);
    },
    contains(child) {
      return __pixiWeChatNodeContains(node, child);
    },
    getContext() {
      return null;
    },
    getBoundingClientRect() {
      const width =
        __pixiWeChatParsePixelSize(node.style.width) ?? __pixiWeChatReadMetric(node.width);
      const height =
        __pixiWeChatParsePixelSize(node.style.height) ?? __pixiWeChatReadMetric(node.height);
      return {
        top: 0,
        left: 0,
        right: width,
        bottom: height,
        width,
        height,
        x: 0,
        y: 0,
      };
    },
    setAttribute(name, value) {
      node[name] = value;
    },
  };

  __pixiWeChatSafeDefine(node, 'clientWidth', 0);
  __pixiWeChatSafeDefine(node, 'clientHeight', 0);
  return node;
};

const __pixiWeChatInstallCanvasIdentity = (canvas, role) => {
  if (!canvas || (typeof canvas !== 'object' && typeof canvas !== 'function')) {
    return canvas;
  }

  canvas.style ||= {};
  __pixiWeChatSafeDefine(canvas, 'type', 'canvas');
  __pixiWeChatSafeDefine(canvas, 'tagName', 'CANVAS');
  __pixiWeChatSafeDefine(canvas, 'nodeName', 'CANVAS');
  if (role === 'screen') {
    __pixiWeChatSafeDefine(canvas, 'id', canvas.id || __pixiWeChatScreenCanvasId);
  }

  if (typeof canvas.getBoundingClientRect !== 'function') {
    __pixiWeChatSafeDefine(canvas, 'getBoundingClientRect', () => {
      const width =
        __pixiWeChatParsePixelSize(canvas.style.width) ?? __pixiWeChatReadMetric(canvas.width);
      const height =
        __pixiWeChatParsePixelSize(canvas.style.height) ?? __pixiWeChatReadMetric(canvas.height);
      return {
        top: 0,
        left: 0,
        right: width,
        bottom: height,
        width,
        height,
        x: 0,
        y: 0,
      };
    });
  }

  __pixiWeChatInstallEventTarget(canvas);
  __pixiWeChatSafeDefine(canvas, __pixiWeChatCanvasRoleKey, role);
  return canvas;
};

const __pixiWeChatDescribeCanvas = (canvas, index, role, stack) => ({
  index,
  role,
  width: canvas && typeof canvas.width === 'number' ? canvas.width : null,
  height: canvas && typeof canvas.height === 'number' ? canvas.height : null,
  hasGetContext: !!(canvas && typeof canvas.getContext === 'function'),
  constructorName:
    canvas && canvas.constructor && typeof canvas.constructor.name === 'string'
      ? canvas.constructor.name
      : null,
  stack,
});

if (typeof __pixiWeChatGlobal.self === 'undefined') {
  __pixiWeChatGlobal.self = __pixiWeChatGlobal;
}
if (typeof __pixiWeChatGlobal.window === 'undefined') {
  __pixiWeChatGlobal.window = __pixiWeChatGlobal;
}
if (typeof __pixiWeChatGlobal.top === 'undefined') {
  __pixiWeChatGlobal.top = __pixiWeChatGlobal;
}
if (typeof __pixiWeChatGlobal.parent === 'undefined') {
  __pixiWeChatGlobal.parent = __pixiWeChatGlobal;
}
if (typeof __pixiWeChatGlobal.Intl === 'undefined') {
  __pixiWeChatGlobal.Intl = {};
}
if (typeof __pixiWeChatGlobal.navigator === 'undefined') {
  __pixiWeChatGlobal.navigator = {
    userAgent: 'Mozilla/5.0 WeChatMiniGame',
    platform: 'wechat-minigame',
    language: 'zh-CN',
    maxTouchPoints: 5,
    hardwareConcurrency: 4,
  };
}
if (typeof __pixiWeChatGlobal.location === 'undefined') {
  __pixiWeChatGlobal.location = {
    href: 'https://minigame.weixin.qq.com/',
    origin: 'https://minigame.weixin.qq.com',
    pathname: '/',
    search: '',
    hash: '',
  };
}

__pixiWeChatInstallEventTarget(__pixiWeChatGlobal);

if (__pixiWeChatDebugEnabled) {
  __pixiWeChatLog('[pixi-wechat] game.js prelude', {
    hasGlobalCanvas: typeof __pixiWeChatGlobal.canvas !== 'undefined',
    hasGlobalScreenCanvas: typeof __pixiWeChatGlobal.screencanvas !== 'undefined',
    hasGameGlobalCanvas:
      typeof GameGlobal !== 'undefined' && typeof GameGlobal.canvas !== 'undefined',
    globalCanvasConstructor:
      __pixiWeChatGlobal.canvas &&
      __pixiWeChatGlobal.canvas.constructor &&
      typeof __pixiWeChatGlobal.canvas.constructor.name === 'string'
        ? __pixiWeChatGlobal.canvas.constructor.name
        : null,
  });
}

if (typeof wx !== 'undefined' && typeof wx.createCanvas === 'function') {
  const __pixiWeChatOriginalCreateCanvas =
    __pixiWeChatGlobal.__pixiWeChatOriginalCreateCanvas || wx.createCanvas.bind(wx);
  __pixiWeChatGlobal.__pixiWeChatOriginalCreateCanvas = __pixiWeChatOriginalCreateCanvas;
  __pixiWeChatGlobal.__pixiWeChatCanvasTrace ||= [];
  __pixiWeChatGlobal.__pixiWeChatCanvasCreateCount ||= 0;

  let __pixiWeChatScreenCanvas = __pixiWeChatGlobal[__pixiWeChatScreenCanvasKey];
  if (!__pixiWeChatScreenCanvas) {
    __pixiWeChatScreenCanvas = __pixiWeChatInstallCanvasIdentity(
      __pixiWeChatOriginalCreateCanvas(),
      'screen',
    );
    const __pixiWeChatTraceId = ++__pixiWeChatGlobal.__pixiWeChatCanvasCreateCount;
    __pixiWeChatSafeDefine(__pixiWeChatScreenCanvas, '__pixiWeChatTraceId', __pixiWeChatTraceId);
    const __pixiWeChatStack = (() => {
      try {
        return String(new Error().stack || '')
          .split('\\n')
          .slice(2, 5)
          .join(' | ') || null;
      } catch {
        return null;
      }
    })();
    const __pixiWeChatSummary = __pixiWeChatDescribeCanvas(
      __pixiWeChatScreenCanvas,
      __pixiWeChatTraceId,
      'screen',
      __pixiWeChatStack,
    );
    __pixiWeChatGlobal.__pixiWeChatCanvasTrace.push(__pixiWeChatSummary);
    __pixiWeChatLog('[pixi-wechat] wx.createCanvas', __pixiWeChatSummary);
  }

  const __pixiWeChatCreateOffscreenCanvas = () => {
    const __pixiWeChatCanvas = __pixiWeChatInstallCanvasIdentity(
      __pixiWeChatOriginalCreateCanvas(),
      'offscreen',
    );
    const __pixiWeChatTraceId = ++__pixiWeChatGlobal.__pixiWeChatCanvasCreateCount;
    __pixiWeChatSafeDefine(__pixiWeChatCanvas, '__pixiWeChatTraceId', __pixiWeChatTraceId);
    const __pixiWeChatStack = (() => {
      try {
        return String(new Error().stack || '')
          .split('\\n')
          .slice(2, 5)
          .join(' | ') || null;
      } catch {
        return null;
      }
    })();
    const __pixiWeChatSummary = __pixiWeChatDescribeCanvas(
      __pixiWeChatCanvas,
      __pixiWeChatTraceId,
      'offscreen',
      __pixiWeChatStack,
    );
    __pixiWeChatGlobal.__pixiWeChatCanvasTrace.push(__pixiWeChatSummary);
    __pixiWeChatLog('[pixi-wechat] wx.createCanvas', __pixiWeChatSummary);
    return __pixiWeChatCanvas;
  };

  __pixiWeChatSafeDefine(__pixiWeChatGlobal, __pixiWeChatScreenCanvasKey, __pixiWeChatScreenCanvas);
  __pixiWeChatSafeDefine(
    __pixiWeChatGlobal,
    __pixiWeChatOffscreenCanvasFactoryKey,
    __pixiWeChatCreateOffscreenCanvas,
  );
  __pixiWeChatSafeDefine(__pixiWeChatGlobal, 'canvas', __pixiWeChatScreenCanvas);
  __pixiWeChatSafeDefine(__pixiWeChatGlobal, 'screencanvas', __pixiWeChatScreenCanvas);

  if (typeof GameGlobal !== 'undefined') {
    __pixiWeChatSafeDefine(GameGlobal, 'canvas', __pixiWeChatScreenCanvas);
    __pixiWeChatSafeDefine(GameGlobal, 'screencanvas', __pixiWeChatScreenCanvas);
  }

  if (!__pixiWeChatGlobal.__pixiWeChatWrappedCreateCanvas) {
    __pixiWeChatGlobal.__pixiWeChatWrappedCreateCanvas = true;
    wx.createCanvas = function() {
      return __pixiWeChatCreateOffscreenCanvas();
    };
  }

  const __pixiWeChatExistingDocument = (() => {
    try {
      if (
        __pixiWeChatGlobal.document &&
        (typeof __pixiWeChatGlobal.document === 'object' ||
          typeof __pixiWeChatGlobal.document === 'function')
      ) {
        return __pixiWeChatGlobal.document;
      }
    } catch {}
    try {
      if (
        typeof GameGlobal !== 'undefined' &&
        GameGlobal.document &&
        (typeof GameGlobal.document === 'object' || typeof GameGlobal.document === 'function')
      ) {
        return GameGlobal.document;
      }
    } catch {}
    return null;
  })();

  if (__pixiWeChatExistingDocument) {
    if (typeof GameGlobal !== 'undefined' && !GameGlobal.document) {
      __pixiWeChatSafeDefine(GameGlobal, 'document', __pixiWeChatExistingDocument);
    }
  } else {
    const __pixiWeChatDocument = __pixiWeChatInstallEventTarget({});
    const __pixiWeChatHead = __pixiWeChatInstallEventTarget({});
    __pixiWeChatSafeDefine(__pixiWeChatHead, 'tagName', 'HEAD');
    __pixiWeChatSafeDefine(__pixiWeChatHead, 'nodeName', 'HEAD');
    __pixiWeChatSafeDefine(__pixiWeChatHead, 'style', {});
    __pixiWeChatSafeDefine(__pixiWeChatHead, 'children', []);
    __pixiWeChatSafeDefine(__pixiWeChatHead, 'appendChild', (node) =>
      __pixiWeChatAppendChild(__pixiWeChatHead, node),
    );
    __pixiWeChatSafeDefine(__pixiWeChatHead, 'removeChild', (node) =>
      __pixiWeChatRemoveChild(__pixiWeChatHead, node),
    );
    __pixiWeChatSetDomLink(__pixiWeChatHead, 'isConnected', true);

    const __pixiWeChatBody = __pixiWeChatInstallEventTarget({});
    __pixiWeChatSafeDefine(__pixiWeChatBody, 'tagName', 'BODY');
    __pixiWeChatSafeDefine(__pixiWeChatBody, 'nodeName', 'BODY');
    __pixiWeChatSafeDefine(__pixiWeChatBody, 'style', {});
    __pixiWeChatSafeDefine(__pixiWeChatBody, 'children', []);
    __pixiWeChatSafeDefine(__pixiWeChatBody, 'appendChild', (node) =>
      __pixiWeChatAppendChild(__pixiWeChatBody, node),
    );
    __pixiWeChatSafeDefine(__pixiWeChatBody, 'removeChild', (node) =>
      __pixiWeChatRemoveChild(__pixiWeChatBody, node),
    );
    __pixiWeChatSafeDefine(__pixiWeChatBody, 'contains', (node) =>
      __pixiWeChatNodeContains(__pixiWeChatBody, node),
    );
    __pixiWeChatSetDomLink(__pixiWeChatBody, 'isConnected', true);

    __pixiWeChatSafeDefine(__pixiWeChatDocument, 'readyState', 'complete');
    __pixiWeChatSafeDefine(__pixiWeChatDocument, 'visibilityState', 'visible');
    __pixiWeChatSafeDefine(__pixiWeChatDocument, 'hidden', false);
    __pixiWeChatSafeDefine(__pixiWeChatDocument, 'location', __pixiWeChatGlobal.location);
    __pixiWeChatSafeDefine(__pixiWeChatDocument, 'baseURI', __pixiWeChatGlobal.location.href);
    __pixiWeChatSafeDefine(__pixiWeChatDocument, 'head', __pixiWeChatHead);
    __pixiWeChatSafeDefine(__pixiWeChatDocument, 'body', __pixiWeChatBody);
    __pixiWeChatSafeDefine(__pixiWeChatDocument, 'documentElement', __pixiWeChatGlobal);
    __pixiWeChatSafeDefine(__pixiWeChatDocument, 'createElement', (tagName) => {
      const normalizedTagName = String(tagName || '').toLowerCase();
      if (normalizedTagName === 'canvas') {
        return __pixiWeChatCreateOffscreenCanvas();
      }
      if (
        (normalizedTagName === 'img' || normalizedTagName === 'image') &&
        typeof wx.createImage === 'function'
      ) {
        return wx.createImage();
      }
      return __pixiWeChatCreateElementStub(normalizedTagName);
    });
    __pixiWeChatSafeDefine(__pixiWeChatDocument, 'querySelectorAll', (selector) => {
      if (selector === 'canvas') {
        return [__pixiWeChatScreenCanvas];
      }
      if (selector === 'body') {
        return [__pixiWeChatBody];
      }
      if (selector === 'head') {
        return [__pixiWeChatHead];
      }
      if (selector === '#' + __pixiWeChatScreenCanvas.id) {
        return [__pixiWeChatScreenCanvas];
      }
      return [];
    });
    __pixiWeChatSafeDefine(__pixiWeChatDocument, 'querySelector', (selector) =>
      __pixiWeChatDocument.querySelectorAll(selector)[0] || null,
    );
    __pixiWeChatSafeDefine(__pixiWeChatDocument, 'getElementsByTagName', (tagName) =>
      __pixiWeChatDocument.querySelectorAll(String(tagName || '').toLowerCase()),
    );
    __pixiWeChatSafeDefine(__pixiWeChatDocument, 'getElementById', (id) =>
      id === __pixiWeChatScreenCanvas.id ? __pixiWeChatScreenCanvas : null,
    );

    __pixiWeChatSetDomLink(__pixiWeChatHead, 'ownerDocument', __pixiWeChatDocument);
    __pixiWeChatSetDomLink(__pixiWeChatHead, 'parentNode', __pixiWeChatDocument);
    __pixiWeChatSetDomLink(__pixiWeChatBody, 'ownerDocument', __pixiWeChatDocument);
    __pixiWeChatSetDomLink(__pixiWeChatBody, 'parentNode', __pixiWeChatDocument);
    __pixiWeChatAppendChild(__pixiWeChatBody, __pixiWeChatScreenCanvas);
    __pixiWeChatSetDomLink(__pixiWeChatScreenCanvas, 'ownerDocument', __pixiWeChatDocument);

    __pixiWeChatSafeDefine(__pixiWeChatGlobal, 'document', __pixiWeChatDocument);
    if (typeof GameGlobal !== 'undefined') {
      __pixiWeChatSafeDefine(GameGlobal, 'document', __pixiWeChatDocument);
    }
  }
}

try {
  require('./js/wechat-main.js');
} catch (error) {
  const __pixiWeChatEntryError = error && typeof error === 'object' && typeof error.stack === 'string'
    ? error.stack
    : String(error);
  __pixiWeChatGlobal.__pixiWeChatWeChatEntryError__ = __pixiWeChatEntryError;
  if (typeof console !== 'undefined' && typeof console.error === 'function') {
    console.error('[pixi-wechat] game.js require failed', error);
  }
  if (typeof wx !== 'undefined') {
    try {
      wx.setStorageSync?.('pixi-wechat-minigame:entry-error:v1', __pixiWeChatEntryError);
      wx.showModal?.({
        title: 'WX entry error',
        content: __pixiWeChatEntryError.slice(0, 220),
        showCancel: false,
        confirmText: 'OK'
      });
    } catch {
      wx.showToast?.({
        title: 'WX entry error',
        icon: 'none',
        duration: 4000
      });
    }
  }
  throw error;
}
`;
};

export const buildWeChatProject = async ({
  repoRoot = defaultRepoRoot,
  buildProfile = defaultBuildProfile,
  runtimeDir = resolveRuntimeDir(repoRoot, buildProfile),
  outputDir = resolveOutputDir(repoRoot, buildProfile),
  publicDir = join(repoRoot, 'public'),
  wechatAppId = defaultWeChatAppId,
  wechatLibVersion = defaultWeChatLibVersion
} = {}) => {
  const minigameDir = join(outputDir, 'miniprogram');
  const runtimeEntry = join(runtimeDir, 'wechat-main.js');

  await ensureRuntimeExists(runtimeEntry);
  await rm(outputDir, { recursive: true, force: true });
  await mkdir(join(minigameDir, 'js'), { recursive: true });

  await cp(runtimeEntry, join(minigameDir, 'js', 'wechat-main.js'));
  const packagedDebugSourcemap = await copyRuntimeSourcemapIfNeeded({
    buildProfile,
    minigameDir,
    runtimeDir
  });
  const copiedPublicDir = await copyPackagedPublicDir(publicDir, minigameDir);
  const mirroredGameContextAssets = await mirrorDevtoolsGameContextAssets(publicDir, minigameDir);

  await writeFile(
    join(minigameDir, 'game.js'),
    createWeChatGameEntrySource(buildProfile),
    'utf8'
  );

  await writeJson(join(minigameDir, 'game.json'), {
    deviceOrientation: 'portrait',
    backgroundColor: defaultSurfaceBackgroundColor,
    backgroundColorTop: defaultSurfaceBackgroundColor,
    backgroundColorBottom: defaultSurfaceBackgroundColor,
    showStatusBar: false
  });

  await writeJson(join(outputDir, 'project.config.json'), {
    appid: wechatAppId,
    compileType: 'game',
    projectname: process.env.WX_MINIGAME_PROJECT_NAME || 'pixi-wechat-minigame',
    miniprogramRoot: 'miniprogram/',
    srcMiniprogramRoot: 'miniprogram/',
    simulatorType: 'wechat',
    libVersion: wechatLibVersion,
    setting: {
      urlCheck: false,
      postcss: false,
      minified: buildProfile === 'debug' ? false : true,
      es6: true,
      enhance: false,
      newFeature: true,
      useMultiFrameRuntime: true,
      useApiHook: true,
      useApiHostProcess: true,
      useIsolateContext: true
    }
  });

  await writeFile(
    join(outputDir, 'README.md'),
    [
      '# WeChat Mini Game Build',
      '',
      '- Import this folder into WeChat DevTools as a mini game project.',
      `- Build profile: \`${buildProfile}\`.`,
      '- Runtime files are generated under `miniprogram/` to match the official mini-game project layout.',
      copiedPublicDir
        ? '- Packaged web-safe public assets were copied into `miniprogram/`.'
        : '- No `public/` directory was present, so only runtime files were packaged.',
      mirroredGameContextAssets
        ? '- DevTools compatibility assets were also mirrored into `miniprogram/gameContext/assets/`.'
        : '- No `public/assets/` directory was present, so no `gameContext/assets/` mirror was required.',
      '- For release-style package health checks, run `make audit` from the repo root after building.',
      `- Default appid: \`${wechatAppId}\`. Override it with \`WX_MINIGAME_APPID=<appid>\` before running \`make wechat\` if needed.`,
      '- Override the DevTools project name with `WX_MINIGAME_PROJECT_NAME=<name>` if your team needs a custom project label.',
      `- Default libVersion: \`${wechatLibVersion}\`. Override it with \`WX_MINIGAME_LIB_VERSION=<version>\` before running \`make wechat\` if needed.`,
      buildProfile === 'debug'
        ? packagedDebugSourcemap
          ? '- Debug build keeps WeChat diagnostics enabled and packages `miniprogram/js/wechat-main.js.map` for DevTools debugging.'
          : '- Debug build keeps WeChat diagnostics enabled.'
        : '- Release build keeps production-style bundling and disables debug-only info logs by default.'
    ].join('\n'),
    'utf8'
  );
};

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await buildWeChatProject();
}
