import { defineConfig } from 'vite';

const isWeChatDebugBuild =
  (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env
    ?.VITE_WECHAT_DEBUG === '1';

export default defineConfig({
  publicDir: false,
  define: {
    __WECHAT_DEBUG__: JSON.stringify(isWeChatDebugBuild),
  },
  build: {
    target: 'es2020',
    outDir: isWeChatDebugBuild
      ? 'build/wechat-runtime-debug'
      : 'build/wechat-runtime',
    emptyOutDir: true,
    cssCodeSplit: false,
    minify: isWeChatDebugBuild ? false : true,
    sourcemap: isWeChatDebugBuild,
    lib: {
      entry: 'src/wechat-main.ts',
      formats: ['cjs'],
      fileName: () => 'wechat-main.js',
    },
    rollupOptions: {
      output: {
        exports: 'named',
        inlineDynamicImports: true,
      },
    },
  },
});
