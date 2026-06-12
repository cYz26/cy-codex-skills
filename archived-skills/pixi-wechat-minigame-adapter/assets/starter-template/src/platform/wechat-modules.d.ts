declare module 'pixi.js/unsafe-eval';

declare module '../tools/build-wechat.mjs' {
  export interface BuildWeChatProjectOptions {
    repoRoot?: string;
    buildProfile?: 'debug' | 'release';
    runtimeDir?: string;
    outputDir?: string;
    publicDir?: string;
    wechatAppId?: string;
    wechatLibVersion?: string;
  }

  export function buildWeChatProject(options?: BuildWeChatProjectOptions): Promise<void>;
}

declare module '../tools/audit-wechat-build.mjs' {
  export interface AuditCheck {
    name: string;
    passed: boolean;
    details: string;
  }

  export interface AuditTopFile {
    path: string;
    sizeBytes: number;
    sizeLabel: string;
  }

  export interface AuditWeChatBuildResult {
    ok: boolean;
    buildProfile: 'debug' | 'release';
    outputDir: string;
    minigameDir: string;
    miniprogramSizeBytes: number;
    miniprogramSizeLabel: string;
    topFiles: AuditTopFile[];
    checks: AuditCheck[];
  }

  export interface AuditWeChatBuildOptions {
    repoRoot?: string;
    buildProfile?: 'debug' | 'release';
    outputDir?: string;
    reportPath?: string | null;
    topFileCount?: number;
  }

  export function auditWeChatBuild(
    options?: AuditWeChatBuildOptions
  ): Promise<AuditWeChatBuildResult>;
  export function renderAuditSummary(audit: AuditWeChatBuildResult): string;
}
