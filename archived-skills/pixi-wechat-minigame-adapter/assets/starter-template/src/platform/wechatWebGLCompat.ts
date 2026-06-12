import { logWeChatDebug } from './wechatDebug';

type CanvasGetContext = (contextId: string, options?: unknown) => unknown;

type WebGLContextRequestType = 'webgl' | 'experimental-webgl' | 'webgl2';

export type WeChatWebGLCompatMode = 'native' | 'oes-bridge' | 'js-shim';

export interface VertexAttribState {
  buffer: unknown | null;
  divisor: number;
  enabled: boolean;
  integer: boolean;
  normalized: boolean;
  offset: number;
  size: number;
  stride: number;
  type: number;
}

export interface VertexArrayState {
  attributes: Map<number, Partial<VertexAttribState>>;
  deleted: boolean;
  elementArrayBuffer: unknown | null;
  id: number;
}

export interface WeChatWebGLCompatInfo {
  hasAngleInstancedArrays: boolean;
  requestedContextType: WebGLContextRequestType;
  vaoMode: WeChatWebGLCompatMode;
  webglVersion: 1 | 2;
}

interface CanvasLike {
  getContext?: CanvasGetContext;
}

interface OESVertexArrayObjectLike {
  bindVertexArrayOES(vao: unknown | null): void;
  createVertexArrayOES(): unknown;
  deleteVertexArrayOES(vao: unknown | null): void;
  isVertexArrayOES?(vao: unknown): boolean;
}

interface WeChatWebGLContextLike {
  ARRAY_BUFFER: number;
  ELEMENT_ARRAY_BUFFER: number;
  bindBuffer(target: number, buffer: unknown): void;
  bindVertexArray?(vao: unknown | null): void;
  createVertexArray?(): unknown;
  deleteVertexArray?(vao: unknown | null): void;
  disableVertexAttribArray(index: number): void;
  enableVertexAttribArray(index: number): void;
  getExtension(name: string): unknown;
  isVertexArray?(vao: unknown): boolean;
  vertexAttribDivisor?(index: number, divisor: number): void;
  vertexAttribIPointer?(
    index: number,
    size: number,
    type: number,
    stride: number,
    offset: number,
  ): void;
  vertexAttribPointer(
    index: number,
    size: number,
    type: number,
    normalized: boolean,
    stride: number,
    offset: number,
  ): void;
}

interface WeChatCreateCanvasOwner {
  createCanvas?: () => unknown;
}

interface WeChatWebGLCompatState {
  currentArrayBuffer: unknown | null;
  currentElementArrayBuffer: unknown | null;
  currentVertexArray: VertexArrayState | null;
  info: WeChatWebGLCompatInfo;
  knownAttributeLocations: Set<number>;
  nextVertexArrayId: number;
  originalBindBuffer: WeChatWebGLContextLike['bindBuffer'];
  originalBindVertexArray: WeChatWebGLContextLike['bindVertexArray'] | null;
  originalCreateVertexArray: WeChatWebGLContextLike['createVertexArray'] | null;
  originalDeleteVertexArray: WeChatWebGLContextLike['deleteVertexArray'] | null;
  originalDisableVertexAttribArray: WeChatWebGLContextLike['disableVertexAttribArray'];
  originalEnableVertexAttribArray: WeChatWebGLContextLike['enableVertexAttribArray'];
  originalGetExtension: WeChatWebGLContextLike['getExtension'];
  originalIsVertexArray: WeChatWebGLContextLike['isVertexArray'] | null;
  originalVertexAttribDivisor: WeChatWebGLContextLike['vertexAttribDivisor'] | null;
  originalVertexAttribIPointer: WeChatWebGLContextLike['vertexAttribIPointer'] | null;
  originalVertexAttribPointer: WeChatWebGLContextLike['vertexAttribPointer'];
  replaying: boolean;
  vertexArrays: Set<VertexArrayState>;
}

const WEBGL_CONTEXT_REQUEST_TYPES = new Set<WebGLContextRequestType>([
  'webgl',
  'experimental-webgl',
  'webgl2',
]);

const OES_VERTEX_ARRAY_OBJECT_NAMES = [
  'OES_vertex_array_object',
  'MOZ_OES_vertex_array_object',
  'WEBKIT_OES_vertex_array_object',
] as const;

const wrappedCanvasSet = new WeakSet<object>();
const wrappedCreateCanvasOwners = new WeakSet<object>();
const compatStateByContext = new WeakMap<object, WeChatWebGLCompatState>();

const isCanvasLike = (value: unknown): value is CanvasLike & object =>
  Boolean(value) &&
  typeof value === 'object' &&
  typeof (value as CanvasLike).getContext === 'function';

const isWebGLContextRequestType = (
  contextId: string,
): contextId is WebGLContextRequestType =>
  WEBGL_CONTEXT_REQUEST_TYPES.has(contextId as WebGLContextRequestType);

const isWebGLContextLike = (value: unknown): value is WeChatWebGLContextLike & object => {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const gl = value as Partial<WeChatWebGLContextLike>;

  return (
    typeof gl.getExtension === 'function' &&
    typeof gl.bindBuffer === 'function' &&
    typeof gl.enableVertexAttribArray === 'function' &&
    typeof gl.disableVertexAttribArray === 'function' &&
    typeof gl.vertexAttribPointer === 'function' &&
    typeof gl.ARRAY_BUFFER === 'number' &&
    typeof gl.ELEMENT_ARRAY_BUFFER === 'number'
  );
};

const getAnyVertexArrayExtension = (
  getExtension: WeChatWebGLContextLike['getExtension'],
): OESVertexArrayObjectLike | null => {
  for (const name of OES_VERTEX_ARRAY_OBJECT_NAMES) {
    const extension = getExtension(name);
    if (extension) {
      return extension as OESVertexArrayObjectLike;
    }
  }

  return null;
};

const getVertexAttribState = (
  vao: VertexArrayState,
  index: number,
): Partial<VertexAttribState> => {
  let state = vao.attributes.get(index);

  if (!state) {
    state = {};
    vao.attributes.set(index, state);
  }

  return state;
};

const createVertexArrayState = (
  compatState: WeChatWebGLCompatState,
): VertexArrayState => {
  const vao: VertexArrayState = {
    attributes: new Map(),
    deleted: false,
    elementArrayBuffer: null,
    id: compatState.nextVertexArrayId,
  };

  compatState.nextVertexArrayId += 1;
  compatState.vertexArrays.add(vao);

  return vao;
};

const isKnownVertexArray = (
  compatState: WeChatWebGLCompatState,
  vao: unknown,
): vao is VertexArrayState =>
  Boolean(vao) &&
  typeof vao === 'object' &&
  compatState.vertexArrays.has(vao as VertexArrayState) &&
  !(vao as VertexArrayState).deleted;

const createNativeBackedVertexArrayExtension = (
  compatState: WeChatWebGLCompatState,
  nativeExtension: OESVertexArrayObjectLike | null,
): OESVertexArrayObjectLike => {
  if (nativeExtension) {
    return {
      bindVertexArrayOES: nativeExtension.bindVertexArrayOES.bind(nativeExtension),
      createVertexArrayOES: nativeExtension.createVertexArrayOES.bind(nativeExtension),
      deleteVertexArrayOES: nativeExtension.deleteVertexArrayOES.bind(nativeExtension),
      isVertexArrayOES:
        nativeExtension.isVertexArrayOES?.bind(nativeExtension) ??
        compatState.originalIsVertexArray ??
        (() => false),
    };
  }

  return {
    bindVertexArrayOES: (vao: unknown | null): void => {
      compatState.originalBindVertexArray?.(vao);
    },
    createVertexArrayOES: (): unknown => compatState.originalCreateVertexArray?.(),
    deleteVertexArrayOES: (vao: unknown | null): void => {
      compatState.originalDeleteVertexArray?.(vao);
    },
    isVertexArrayOES: (vao: unknown): boolean =>
      compatState.originalIsVertexArray?.(vao) ?? false,
  };
};

const replayVertexArrayState = (
  gl: WeChatWebGLContextLike,
  compatState: WeChatWebGLCompatState,
  vao: VertexArrayState | null,
): void => {
  const previousArrayBuffer = compatState.currentArrayBuffer;
  const sortedLocations = Array.from(compatState.knownAttributeLocations.values()).sort(
    (left, right) => left - right,
  );

  compatState.replaying = true;

  try {
    compatState.originalBindBuffer.call(
      gl,
      gl.ELEMENT_ARRAY_BUFFER,
      vao?.elementArrayBuffer ?? null,
    );
    compatState.currentElementArrayBuffer = vao?.elementArrayBuffer ?? null;

    for (const location of sortedLocations) {
      const attributeState = vao?.attributes.get(location);

      if (!attributeState) {
        compatState.originalDisableVertexAttribArray.call(gl, location);
        compatState.originalVertexAttribDivisor?.call(gl, location, 0);
        continue;
      }

      if (attributeState.buffer !== undefined) {
        compatState.originalBindBuffer.call(gl, gl.ARRAY_BUFFER, attributeState.buffer);
      }

      if (attributeState.integer) {
        if (compatState.originalVertexAttribIPointer) {
          compatState.originalVertexAttribIPointer.call(
            gl,
            location,
            attributeState.size ?? 0,
            attributeState.type ?? 0,
            attributeState.stride ?? 0,
            attributeState.offset ?? 0,
          );
        } else {
          compatState.originalVertexAttribPointer.call(
            gl,
            location,
            attributeState.size ?? 0,
            attributeState.type ?? 0,
            false,
            attributeState.stride ?? 0,
            attributeState.offset ?? 0,
          );
        }
      } else if (attributeState.size !== undefined && attributeState.type !== undefined) {
        compatState.originalVertexAttribPointer.call(
          gl,
          location,
          attributeState.size,
          attributeState.type,
          attributeState.normalized ?? false,
          attributeState.stride ?? 0,
          attributeState.offset ?? 0,
        );
      }

      if (attributeState.enabled === false) {
        compatState.originalDisableVertexAttribArray.call(gl, location);
      } else {
        compatState.originalEnableVertexAttribArray.call(gl, location);
      }

      if (compatState.originalVertexAttribDivisor) {
        compatState.originalVertexAttribDivisor.call(gl, location, attributeState.divisor ?? 0);
      }
    }
  } finally {
    compatState.replaying = false;
    compatState.originalBindBuffer.call(gl, gl.ARRAY_BUFFER, previousArrayBuffer);
    compatState.currentArrayBuffer = previousArrayBuffer;
  }
};

const createJsVertexArrayExtension = (
  gl: WeChatWebGLContextLike,
  compatState: WeChatWebGLCompatState,
): OESVertexArrayObjectLike => ({
  bindVertexArrayOES(vao: unknown | null): void {
    compatState.currentVertexArray = isKnownVertexArray(compatState, vao) ? vao : null;
    replayVertexArrayState(gl, compatState, compatState.currentVertexArray);
  },
  createVertexArrayOES(): VertexArrayState {
    return createVertexArrayState(compatState);
  },
  deleteVertexArrayOES(vao: unknown | null): void {
    if (!isKnownVertexArray(compatState, vao)) {
      return;
    }

    vao.deleted = true;
    vao.attributes.clear();
    compatState.vertexArrays.delete(vao);

    if (compatState.currentVertexArray === vao) {
      compatState.currentVertexArray = null;
      replayVertexArrayState(gl, compatState, null);
    }
  },
  isVertexArrayOES(vao: unknown): boolean {
    return isKnownVertexArray(compatState, vao);
  },
});

const patchVertexArrayMethods = (
  gl: WeChatWebGLContextLike,
  compatState: WeChatWebGLCompatState,
  extension: OESVertexArrayObjectLike,
): void => {
  if (!gl.createVertexArray) {
    gl.createVertexArray = () => extension.createVertexArrayOES();
  }
  if (!gl.bindVertexArray) {
    gl.bindVertexArray = (vao: unknown | null) => {
      extension.bindVertexArrayOES(vao);
    };
  }
  if (!gl.deleteVertexArray) {
    gl.deleteVertexArray = (vao: unknown | null) => {
      extension.deleteVertexArrayOES(vao);
    };
  }
  if (!gl.isVertexArray) {
    gl.isVertexArray = (vao: unknown) => extension.isVertexArrayOES?.(vao) ?? false;
  }

  gl.getExtension = ((name: string): unknown => {
    if (OES_VERTEX_ARRAY_OBJECT_NAMES.includes(name as (typeof OES_VERTEX_ARRAY_OBJECT_NAMES)[number])) {
      return extension;
    }

    return compatState.originalGetExtension.call(gl, name);
  }) as WeChatWebGLContextLike['getExtension'];
};

const installJsVertexArrayStateTracking = (
  gl: WeChatWebGLContextLike,
  compatState: WeChatWebGLCompatState,
): void => {
  gl.bindBuffer = ((target: number, buffer: unknown): void => {
    if (!compatState.replaying) {
      if (target === gl.ARRAY_BUFFER) {
        compatState.currentArrayBuffer = buffer;
      } else if (target === gl.ELEMENT_ARRAY_BUFFER) {
        compatState.currentElementArrayBuffer = buffer;
        if (compatState.currentVertexArray) {
          compatState.currentVertexArray.elementArrayBuffer = buffer;
        }
      }
    }

    compatState.originalBindBuffer.call(gl, target, buffer);
  }) as WeChatWebGLContextLike['bindBuffer'];

  gl.enableVertexAttribArray = ((index: number): void => {
    if (compatState.currentVertexArray && !compatState.replaying) {
      compatState.knownAttributeLocations.add(index);
      getVertexAttribState(compatState.currentVertexArray, index).enabled = true;
    }

    compatState.originalEnableVertexAttribArray.call(gl, index);
  }) as WeChatWebGLContextLike['enableVertexAttribArray'];

  gl.disableVertexAttribArray = ((index: number): void => {
    if (compatState.currentVertexArray && !compatState.replaying) {
      compatState.knownAttributeLocations.add(index);
      getVertexAttribState(compatState.currentVertexArray, index).enabled = false;
    }

    compatState.originalDisableVertexAttribArray.call(gl, index);
  }) as WeChatWebGLContextLike['disableVertexAttribArray'];

  gl.vertexAttribPointer = ((
    index: number,
    size: number,
    type: number,
    normalized: boolean,
    stride: number,
    offset: number,
  ): void => {
    if (compatState.currentVertexArray && !compatState.replaying) {
      compatState.knownAttributeLocations.add(index);
      Object.assign(getVertexAttribState(compatState.currentVertexArray, index), {
        buffer: compatState.currentArrayBuffer,
        integer: false,
        normalized,
        offset,
        size,
        stride,
        type,
      });
    }

    compatState.originalVertexAttribPointer.call(
      gl,
      index,
      size,
      type,
      normalized,
      stride,
      offset,
    );
  }) as WeChatWebGLContextLike['vertexAttribPointer'];

  const originalVertexAttribIPointer = compatState.originalVertexAttribIPointer;

  gl.vertexAttribIPointer = (
    index: number,
    size: number,
    type: number,
    stride: number,
    offset: number,
  ): void => {
    if (compatState.currentVertexArray && !compatState.replaying) {
      compatState.knownAttributeLocations.add(index);
      Object.assign(getVertexAttribState(compatState.currentVertexArray, index), {
        buffer: compatState.currentArrayBuffer,
        integer: true,
        normalized: false,
        offset,
        size,
        stride,
        type,
      });
    }

    if (originalVertexAttribIPointer) {
      originalVertexAttribIPointer.call(gl, index, size, type, stride, offset);
      return;
    }

    compatState.originalVertexAttribPointer.call(gl, index, size, type, false, stride, offset);
  };

  if (!compatState.originalVertexAttribDivisor) {
    return;
  }

  gl.vertexAttribDivisor = (index: number, divisor: number): void => {
    if (compatState.currentVertexArray && !compatState.replaying) {
      compatState.knownAttributeLocations.add(index);
      getVertexAttribState(compatState.currentVertexArray, index).divisor = divisor;
    }

    compatState.originalVertexAttribDivisor?.call(gl, index, divisor);
  };
};

const createCompatState = (
  gl: WeChatWebGLContextLike,
  requestedContextType: WebGLContextRequestType,
): WeChatWebGLCompatState => {
  const originalGetExtension = gl.getExtension.bind(gl) as WeChatWebGLContextLike['getExtension'];
  const nativeVertexArrayExtension = getAnyVertexArrayExtension(originalGetExtension);
  const hasNativeVertexArrayMethods =
    typeof gl.createVertexArray === 'function' &&
    typeof gl.bindVertexArray === 'function' &&
    typeof gl.deleteVertexArray === 'function';
  const webglVersion =
    requestedContextType === 'webgl2' && hasNativeVertexArrayMethods ? 2 : 1;
  const vaoMode: WeChatWebGLCompatMode =
    webglVersion === 2 && hasNativeVertexArrayMethods
      ? 'native'
      : nativeVertexArrayExtension || hasNativeVertexArrayMethods
        ? 'oes-bridge'
        : 'js-shim';

  const compatState: WeChatWebGLCompatState = {
    currentArrayBuffer: null,
    currentElementArrayBuffer: null,
    currentVertexArray: null,
    info: {
      hasAngleInstancedArrays: Boolean(originalGetExtension('ANGLE_instanced_arrays')),
      requestedContextType,
      vaoMode,
      webglVersion,
    },
    knownAttributeLocations: new Set(),
    nextVertexArrayId: 1,
    originalBindBuffer: gl.bindBuffer.bind(gl),
    originalBindVertexArray:
      typeof gl.bindVertexArray === 'function'
        ? gl.bindVertexArray.bind(gl)
        : null,
    originalCreateVertexArray:
      typeof gl.createVertexArray === 'function'
        ? gl.createVertexArray.bind(gl)
        : null,
    originalDeleteVertexArray:
      typeof gl.deleteVertexArray === 'function'
        ? gl.deleteVertexArray.bind(gl)
        : null,
    originalDisableVertexAttribArray: gl.disableVertexAttribArray.bind(gl),
    originalEnableVertexAttribArray: gl.enableVertexAttribArray.bind(gl),
    originalGetExtension,
    originalIsVertexArray:
      typeof gl.isVertexArray === 'function' ? gl.isVertexArray.bind(gl) : null,
    originalVertexAttribDivisor:
      typeof gl.vertexAttribDivisor === 'function'
        ? gl.vertexAttribDivisor.bind(gl)
        : null,
    originalVertexAttribIPointer:
      typeof gl.vertexAttribIPointer === 'function'
        ? gl.vertexAttribIPointer.bind(gl)
        : null,
    originalVertexAttribPointer: gl.vertexAttribPointer.bind(gl),
    replaying: false,
    vertexArrays: new Set(),
  };

  const extension =
    vaoMode === 'js-shim'
      ? createJsVertexArrayExtension(gl, compatState)
      : createNativeBackedVertexArrayExtension(compatState, nativeVertexArrayExtension);

  if (vaoMode === 'js-shim') {
    installJsVertexArrayStateTracking(gl, compatState);
  }

  if (vaoMode !== 'native' || webglVersion === 1) {
    patchVertexArrayMethods(gl, compatState, extension);
  }

  compatStateByContext.set(gl, compatState);
  logWeChatDebug('normalized webgl context', compatState.info);

  return compatState;
};

export const getWeChatWebGLCompatInfo = (
  context: unknown,
): WeChatWebGLCompatInfo | null => {
  if (!context || typeof context !== 'object') {
    return null;
  }

  return compatStateByContext.get(context)?.info ?? null;
};

export const ensureWeChatWebGLContextCompat = (
  context: unknown,
  requestedContextType: WebGLContextRequestType,
): unknown => {
  if (!isWebGLContextLike(context)) {
    return context;
  }

  const existingState = compatStateByContext.get(context);
  if (existingState) {
    return context;
  }

  createCompatState(context, requestedContextType);

  return context;
};

export const installWeChatCanvasGetContextCompat = (canvas: unknown): void => {
  if (!isCanvasLike(canvas) || wrappedCanvasSet.has(canvas)) {
    return;
  }

  const originalGetContext = canvas.getContext!.bind(canvas) as CanvasGetContext;

  canvas.getContext = ((contextId: string, options?: unknown): unknown => {
    const context = originalGetContext(contextId, options);

    if (!isWebGLContextRequestType(contextId) || !context) {
      return context;
    }

    return ensureWeChatWebGLContextCompat(context, contextId);
  }) as CanvasGetContext;

  wrappedCanvasSet.add(canvas);
};

export const installWeChatCreateCanvasCompat = (
  owner: WeChatCreateCanvasOwner,
): void => {
  if (
    !owner ||
    typeof owner !== 'object' ||
    typeof owner.createCanvas !== 'function' ||
    wrappedCreateCanvasOwners.has(owner as object)
  ) {
    return;
  }

  const originalCreateCanvas = owner.createCanvas.bind(owner);

  const compatibleCreateCanvas = () => {
    const canvas = originalCreateCanvas();
    installWeChatCanvasGetContextCompat(canvas);
    return canvas;
  };

  (
    owner as WeChatCreateCanvasOwner & {
      createCanvas: () => unknown;
    }
  ).createCanvas = compatibleCreateCanvas;

  wrappedCreateCanvasOwners.add(owner as object);
};
