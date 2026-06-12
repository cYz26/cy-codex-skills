import { afterEach, beforeEach, describe, expect, test } from 'vitest';

import {
  getWeChatWebGLCompatInfo,
  installWeChatCanvasGetContextCompat,
  installWeChatCreateCanvasCompat,
} from '../src/platform/wechatWebGLCompat';
import { setWeChatDebugLoggingOverrideForTests } from '../src/platform/wechatDebug';

class MockWebGL1Context {
  readonly ARRAY_BUFFER = 34962;

  readonly ELEMENT_ARRAY_BUFFER = 34963;

  readonly operations: unknown[][] = [];

  constructor(
    private readonly options: {
      angleInstancedArrays?: object | null;
      vaoExtension?: {
        bindVertexArrayOES(vao: unknown | null): void;
        createVertexArrayOES(): unknown;
        deleteVertexArrayOES(vao: unknown | null): void;
        isVertexArrayOES?(vao: unknown): boolean;
      } | null;
    } = {},
  ) {}

  bindBuffer(target: number, buffer: unknown): void {
    this.operations.push(['bindBuffer', target, buffer]);
  }

  disableVertexAttribArray(index: number): void {
    this.operations.push(['disableVertexAttribArray', index]);
  }

  enableVertexAttribArray(index: number): void {
    this.operations.push(['enableVertexAttribArray', index]);
  }

  getExtension(name: string): unknown {
    if (name === 'ANGLE_instanced_arrays') {
      return this.options.angleInstancedArrays ?? null;
    }
    if (name === 'OES_vertex_array_object') {
      return this.options.vaoExtension ?? null;
    }

    return null;
  }

  vertexAttribDivisor(index: number, divisor: number): void {
    this.operations.push(['vertexAttribDivisor', index, divisor]);
  }

  vertexAttribIPointer(
    index: number,
    size: number,
    type: number,
    stride: number,
    offset: number,
  ): void {
    this.operations.push(['vertexAttribIPointer', index, size, type, stride, offset]);
  }

  vertexAttribPointer(
    index: number,
    size: number,
    type: number,
    normalized: boolean,
    stride: number,
    offset: number,
  ): void {
    this.operations.push([
      'vertexAttribPointer',
      index,
      size,
      type,
      normalized,
      stride,
      offset,
    ]);
  }
}

describe('wechatWebGLCompat', () => {
  beforeEach(() => {
    setWeChatDebugLoggingOverrideForTests(false);
  });

  afterEach(() => {
    setWeChatDebugLoggingOverrideForTests(undefined);
  });

  test('bridges native OES vertex array extensions for WebGL1 contexts', () => {
    const nativeCalls: unknown[][] = [];
    const nativeVao = { label: 'native-vao' };
    const nativeExtension = {
      bindVertexArrayOES(vao: unknown | null): void {
        nativeCalls.push(['bindVertexArrayOES', vao]);
      },
      createVertexArrayOES(): unknown {
        nativeCalls.push(['createVertexArrayOES']);
        return nativeVao;
      },
      deleteVertexArrayOES(vao: unknown | null): void {
        nativeCalls.push(['deleteVertexArrayOES', vao]);
      },
      isVertexArrayOES(vao: unknown): boolean {
        nativeCalls.push(['isVertexArrayOES', vao]);
        return vao === nativeVao;
      },
    };
    const canvas = {
      getContext(contextId: string): unknown {
        if (contextId === 'webgl') {
          return new MockWebGL1Context({
            angleInstancedArrays: { supported: true },
            vaoExtension: nativeExtension,
          });
        }

        return null;
      },
    };

    installWeChatCanvasGetContextCompat(canvas);

    const gl = canvas.getContext('webgl') as MockWebGL1Context & {
      bindVertexArray(vao: unknown | null): void;
      createVertexArray(): unknown;
      deleteVertexArray(vao: unknown | null): void;
      getExtension(name: string): unknown;
      isVertexArray(vao: unknown): boolean;
    };

    expect(getWeChatWebGLCompatInfo(gl)).toEqual({
      hasAngleInstancedArrays: true,
      requestedContextType: 'webgl',
      vaoMode: 'oes-bridge',
      webglVersion: 1,
    });

    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    gl.deleteVertexArray(vao);
    expect(gl.isVertexArray(vao)).toBe(true);
    expect(gl.getExtension('OES_vertex_array_object')).toBeTruthy();
    expect(nativeCalls).toEqual([
      ['createVertexArrayOES'],
      ['bindVertexArrayOES', nativeVao],
      ['deleteVertexArrayOES', nativeVao],
      ['isVertexArrayOES', nativeVao],
    ]);
  });

  test('treats a failed webgl2 request without native VAO methods as a WebGL1-compatible path', () => {
    const canvas = {
      getContext(contextId: string): unknown {
        if (contextId === 'webgl2') {
          return new MockWebGL1Context();
        }

        return null;
      },
    };

    installWeChatCanvasGetContextCompat(canvas);

    const gl = canvas.getContext('webgl2');

    expect(getWeChatWebGLCompatInfo(gl)).toEqual({
      hasAngleInstancedArrays: false,
      requestedContextType: 'webgl2',
      vaoMode: 'js-shim',
      webglVersion: 1,
    });
  });

  test('installs a JS VAO shim that replays WebGL state when OES is unavailable', () => {
    const gl = new MockWebGL1Context();
    const canvas = {
      getContext(contextId: string): unknown {
        if (contextId === 'webgl') {
          return gl;
        }

        return null;
      },
    };
    const arrayBuffer = { label: 'positions' };
    const indexBuffer = { label: 'indices' };
    const integerBuffer = { label: 'instances' };

    installWeChatCanvasGetContextCompat(canvas);

    const normalizedContext = canvas.getContext('webgl') as MockWebGL1Context & {
      bindVertexArray(vao: unknown | null): void;
      createVertexArray(): unknown;
      deleteVertexArray(vao: unknown | null): void;
      getExtension(name: string): {
        isVertexArrayOES?(vao: unknown): boolean;
      } | null;
      vertexAttribIPointer(
        index: number,
        size: number,
        type: number,
        stride: number,
        offset: number,
      ): void;
      vertexAttribDivisor(index: number, divisor: number): void;
    };
    const vaoExtension = normalizedContext.getExtension('OES_vertex_array_object');

    expect(getWeChatWebGLCompatInfo(normalizedContext)).toEqual({
      hasAngleInstancedArrays: false,
      requestedContextType: 'webgl',
      vaoMode: 'js-shim',
      webglVersion: 1,
    });
    expect(vaoExtension).toBeTruthy();

    const vao = normalizedContext.createVertexArray();
    expect(vaoExtension?.isVertexArrayOES?.(vao)).toBe(true);

    normalizedContext.bindVertexArray(vao);
    normalizedContext.bindBuffer(normalizedContext.ARRAY_BUFFER, arrayBuffer);
    normalizedContext.enableVertexAttribArray(2);
    normalizedContext.vertexAttribPointer(2, 4, 5126, false, 16, 0);
    normalizedContext.vertexAttribDivisor(2, 1);
    normalizedContext.bindBuffer(normalizedContext.ELEMENT_ARRAY_BUFFER, indexBuffer);
    normalizedContext.bindBuffer(normalizedContext.ARRAY_BUFFER, integerBuffer);
    normalizedContext.enableVertexAttribArray(5);
    normalizedContext.vertexAttribIPointer(5, 1, 5124, 4, 0);
    normalizedContext.bindVertexArray(null);

    gl.operations.length = 0;
    normalizedContext.bindVertexArray(vao);

    expect(gl.operations).toEqual([
      ['bindBuffer', normalizedContext.ELEMENT_ARRAY_BUFFER, indexBuffer],
      ['bindBuffer', normalizedContext.ARRAY_BUFFER, arrayBuffer],
      ['vertexAttribPointer', 2, 4, 5126, false, 16, 0],
      ['enableVertexAttribArray', 2],
      ['vertexAttribDivisor', 2, 1],
      ['bindBuffer', normalizedContext.ARRAY_BUFFER, integerBuffer],
      ['vertexAttribIPointer', 5, 1, 5124, 4, 0],
      ['enableVertexAttribArray', 5],
      ['vertexAttribDivisor', 5, 0],
      ['bindBuffer', normalizedContext.ARRAY_BUFFER, integerBuffer],
    ]);

    normalizedContext.deleteVertexArray(vao);
    expect(vaoExtension?.isVertexArrayOES?.(vao)).toBe(false);
  });

  test('wraps canvases created after runtime prep through wx.createCanvas compatibility', () => {
    const owner = {
      createCanvas(): {
        getContext(contextId: string): unknown;
      } {
        return {
          getContext(contextId: string): unknown {
            if (contextId === 'webgl') {
              return new MockWebGL1Context();
            }

            return null;
          },
        };
      },
    };

    installWeChatCreateCanvasCompat(owner);

    const canvas = owner.createCanvas();
    const gl = canvas.getContext('webgl');

    expect(getWeChatWebGLCompatInfo(gl)?.vaoMode).toBe('js-shim');
  });
});
