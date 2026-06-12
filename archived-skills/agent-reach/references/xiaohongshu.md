# XiaoHongShu Workflow

Use this guide when the user asks to read, search, post, or debug XiaoHongShu through Agent Reach.

## When to Load This File

- `agent-reach doctor` mentions XiaoHongShu
- The user says `帮我配小红书`
- A `mcporter call 'xiaohongshu.*'` command fails
- You need to verify whether XiaoHongShu is truly logged in, not just configured

## Decision Tree

1. Confirm the transport exists:

```bash
mcporter list
mcporter list xiaohongshu
```

2. If `xiaohongshu` is missing entirely, install the container and register it.
3. If tools are listed but real calls fail, assume this is a login or upstream-runtime issue.
4. Prefer Cookie import over `check_login_status()` because the upstream login-check can panic with `EOF`.

## Install

Standard setup:

```bash
docker run -d --name xiaohongshu-mcp -p 18060:18060 xpzouying/xiaohongshu-mcp
mcporter config add xiaohongshu http://localhost:18060/mcp
```

Apple Silicon fallback:

```bash
docker run -d --name xiaohongshu-mcp -p 18060:18060 --platform linux/amd64 xpzouying/xiaohongshu-mcp
```

Recommended server setup with proxy:

```bash
docker run -d --name xiaohongshu-mcp -p 18060:18060 -e XHS_PROXY=http://user:pass@ip:port xpzouying/xiaohongshu-mcp
```

## Apple Silicon Preferred Path

On macOS Apple Silicon, prefer the upstream native binaries over the `linux/amd64` Docker image when the Docker route shows Chrome crashes, `qemu_chrome_*.core`, or `prctl: Invalid argument (22)`.

Native binaries from the upstream GitHub release:

- `xiaohongshu-login-darwin-arm64`
- `xiaohongshu-mcp-darwin-arm64`

Recommended local layout:

- binary dir: `~/.agent-reach/tools/xiaohongshu-native/current/`
- runtime dir: `~/.agent-reach/tools/xiaohongshu-native/runtime/`
- cookie file: `~/.agent-reach/tools/xiaohongshu-native/runtime/cookies.json`

Launch the native service from the runtime directory so it can read `cookies.json` via its default relative path.

If you need a persistent local service on macOS, use a LaunchAgent instead of a transient shell background job.

## Login

### Preferred: Cookie-Editor import

Ask the user to:

1. Log in at `https://www.xiaohongshu.com`
2. Open Cookie-Editor
3. Export either `Header String` or `JSON`
4. Send the result to Codex

Then run one of:

```bash
agent-reach configure xhs-cookies "key1=val1; key2=val2; ..."
```

```bash
agent-reach configure xhs-cookies '[{"name":"web_session","value":"xxx","domain":".xiaohongshu.com",...}]'
```

### Important: `--from-browser` is not enough

`agent-reach configure --from-browser chrome` only stores extracted XiaoHongShu cookies in `~/.agent-reach/config.yaml` when they are found. It does not itself prove that the `xiaohongshu-mcp` container is logged in.

For XiaoHongShu, treat `agent-reach configure xhs-cookies ...` as the authoritative login step because it writes cookies into the container path that the MCP server reads.

### Secondary option: QR login

If the user wants interactive login and the upstream image supports it, use:

```bash
mcporter call 'xiaohongshu.get_login_qrcode()'
```

Do not assume an HTTP login page exists at `http://localhost:18060/`; the current container returns `404` on `/`.

## Verification

Do not rely on a single check.

Use this sequence:

```bash
mcporter list xiaohongshu
```

Then try a real read/search call:

```bash
mcporter call 'xiaohongshu.search_feeds(keyword: "咖啡")'
```

or:

```bash
mcporter call 'xiaohongshu.list_feeds()'
```

Interpretation:

- `mcporter list xiaohongshu` succeeds and real calls return data: ready
- `mcporter list xiaohongshu` succeeds but real calls fail: container is up, login or runtime is broken
- `check_login_status()` returns `EOF`: treat as an upstream bug, not a definitive login result

## Known Failure Modes

### `check_login_status()` returns `EOF`

Current upstream behavior can panic inside the container when no valid cookies are present. This is common and should not be treated as proof that Docker or `mcporter` is broken.

If container logs say `failed to read cookies from tmp file: open cookies.json: no such file or directory`, the cookie file was written to the wrong path. The correct fallback path for this image is `/app/cookies.json`, not `/cookies.json`.

### `doctor` says available but real calls still fail

`agent-reach doctor` only checks that the MCP server is registered and responding at a basic level. It does not guarantee that XiaoHongShu cookies are valid.

### Browser extraction finds Bilibili but not XiaoHongShu

That usually means the user is not logged into XiaoHongShu in that browser profile, or `browser_cookie3` could not read those cookies.

### Container has repeated `core` or `qemu_chrome_*.core` files

That indicates the upstream browser process is crashing. Recreate the container and re-import fresh cookies:

```bash
docker rm -f xiaohongshu-mcp
docker run -d --name xiaohongshu-mcp -p 18060:18060 xpzouying/xiaohongshu-mcp
mcporter config add xiaohongshu http://localhost:18060/mcp
```

Then re-run the cookie import.

If this happens on Apple Silicon, stop spending time on the Docker image and switch to the native `darwin-arm64` binaries.

## Working Calls

Search:

```bash
mcporter call 'xiaohongshu.search_feeds(keyword: "query")'
```

Read detail:

```bash
mcporter call 'xiaohongshu.get_feed_detail(feed_id: "xxx", xsec_token: "yyy")'
```

Read detail with more comments:

```bash
mcporter call 'xiaohongshu.get_feed_detail(feed_id: "xxx", xsec_token: "yyy", load_all_comments: true)'
```

Post:

```bash
mcporter call 'xiaohongshu.publish_content(title: "标题", content: "正文", images: ["/absolute/path/image.jpg"])'
```
