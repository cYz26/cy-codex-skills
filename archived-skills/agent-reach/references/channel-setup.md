# Channel Setup and Troubleshooting

Start with:

```bash
agent-reach doctor
```

Load only the section for the failing or requested channel.

## Table of Contents

- [Exa Search](#exa-search)
- [Twitter/X](#twitterx)
- [Bilibili](#bilibili)
- [XiaoHongShu](#xiaohongshu)
- [Douyin](#douyin)
- [LinkedIn](#linkedin)
- [WeChat](#wechat)
- [Weibo](#weibo)
- [Xiaoyuzhou](#xiaoyuzhou)
- [General Checks](#general-checks)

## Exa Search

Agent Reach usually configures Exa automatically. If not:

```bash
npm install -g mcporter
mcporter config add exa https://mcp.exa.ai/mcp
mcporter call 'exa.web_search_exa(query: "test", numResults: 1)'
```

## Twitter/X

Ask the user for cookies exported with Cookie-Editor, then run:

```bash
agent-reach configure twitter-cookies "PASTED_COOKIE_STRING"
```

If the user already logged into `x.com` in Chrome `Default`, try browser extraction first:

```bash
xreach auth extract --browser chrome --profile Default
xreach auth check
```

If extraction says `Could not find required X/Twitter cookies (auth_token, ct0)`, the
machine does not currently have an authenticated X browser session. That is a real blocker,
not an `xreach` install issue.

If the environment needs a proxy:

```bash
agent-reach configure proxy http://user:pass@host:port
xreach search "test" -n 1 --proxy "http://user:pass@host:port"
```

If `xreach` reports `fetch failed`, confirm `undici` is installed:

```bash
npm install -g undici
```

Current `xreach` builds may print `Not authenticated` while still exiting with code `0`.
Do not trust the exit status alone; inspect the text output.

## Bilibili

For direct video reads, `yt-dlp` already works:

```bash
yt-dlp --dump-json "https://www.bilibili.com/video/BVxxx"
```

For search/discovery, use the local wrapper so `SESSDATA` from
`~/.agent-reach/config.yaml` is injected:

```bash
zsh ~/.agent-reach/tools/bilibili-search.sh "query" 5
```

If raw `bilisearch` calls return HTTP `412`, it usually means the request is anonymous.
Use the wrapper instead of plain `yt-dlp "bilisearchN:query"`.

Current environment note: even with local cookies, Bilibili search can still be blocked
with HTTP `412` or API code `-352`. The wrapper now exits with a clear failure in that
case. Treat Bilibili discovery/search as unavailable until the account or IP stops being
challenged; keep direct video URL reads separate from that status.

## XiaoHongShu

For the full install/login/debug flow, load [xiaohongshu.md](xiaohongshu.md).

Requires Docker and `mcporter`:

```bash
docker run -d --name xiaohongshu-mcp -p 18060:18060 xpzouying/xiaohongshu-mcp
mcporter config add xiaohongshu http://localhost:18060/mcp
```

Preferred login flow:

```bash
agent-reach configure xhs-cookies "key1=val1; key2=val2"
```

If `agent-reach doctor` reports "MCP 已配置，但连接异常" while `mcporter list xiaohongshu` still shows tools, treat it as an upstream login-check issue first, not an install failure. In the current upstream image, `check_login_status()` can panic with `EOF` when no cookies are present. Use QR login or cookie import instead of relying on that health check alone.

`agent-reach configure --from-browser chrome` is not a sufficient XiaoHongShu login verification step by itself. It may populate `~/.agent-reach/config.yaml`, but you still need `agent-reach configure xhs-cookies ...` or another container-aware login path for the MCP server to use those cookies.

Apple Silicon fallback for the upstream image:

```bash
docker run -d --name xiaohongshu-mcp -p 18060:18060 --platform linux/amd64 xpzouying/xiaohongshu-mcp
```

## Douyin

The upstream `douyin-mcp-server` only covers known-share-link parsing and audio/text
extraction. On this machine, the recommended setup is a local enhanced MCP that preserves
those upstream tools and adds Playwright-backed discovery:

```bash
pip install douyin-mcp-server playwright
cat ~/.mcporter/mcporter.json
mcporter list douyin
```

Expected `~/.mcporter/mcporter.json` entry:

```json
{
  "mcpServers": {
    "douyin": {
      "command": "/opt/homebrew/bin/python3.11",
      "args": ["/Users/cY/.agent-reach/tools/douyin-enhanced-mcp.py"]
    }
  }
}
```

The enhanced server depends on these local files:

```bash
/Users/cY/.agent-reach/tools/douyin-enhanced-mcp.py
/Users/cY/.agent-reach/tools/douyin_discovery.py
```

This local wrapper also works around an upstream bug: the current
`douyin-mcp-server` eagerly initializes ASR even for `get_douyin_download_link` and
`parse_douyin_video_info`, which makes those tools fail with `DASHSCOPE_API_KEY` errors
even though link parsing itself should not require ASR.

Real discovery checks:

```bash
mcporter call 'douyin.search_douyin_videos(keyword: "query", limit: 5)'
mcporter call 'douyin.get_douyin_hot_videos(limit: 5)'
```

Quick local wrappers still exist:

```bash
zsh ~/.agent-reach/tools/douyin-search.sh "query" 5
zsh ~/.agent-reach/tools/douyin-hot.sh 5
```

This path uses a real browser to load public Douyin web pages and extract visible video
cards, so it is less sensitive to internal API signature changes than hardcoded request
scripts.

## LinkedIn

```bash
pip install linkedin-scraper-mcp
mcporter config add linkedin http://localhost:3000/mcp
mcporter list linkedin
```

If `mcporter list linkedin` reports `No LinkedIn profile found`, the dependency is installed but not initialized. Create the browser profile once:

```bash
/Users/cY/.agent-reach/tools/linkedin-mcp-venv/bin/linkedin-scraper-mcp --login --no-headless
```

Even when `mcporter list linkedin` shows tools or `agent-reach doctor` marks LinkedIn as available, real calls can still fail with `Authentication failed. Run with --login to re-authenticate.` Treat that as an authentication gap, not an installation problem.

After interactive login succeeds, re-run:

```bash
mcporter list linkedin
agent-reach doctor
```

Fallback to Jina Reader for public profiles if the MCP server is unavailable or the user does not want to log in interactively.

## WeChat

Search is provided by `miku_ai`, and article reading is provided by
`wechat-article-for-ai`.

Use the wrappers on this machine:

```bash
zsh ~/.agent-reach/tools/wechat-article-for-ai/search.sh "query" 5
zsh ~/.agent-reach/tools/wechat-article-for-ai/read.sh "https://mp.weixin.qq.com/s/ARTICLE_ID"
```

The important environment detail is that `python3` resolves to macOS system Python 3.9,
while the working Agent Reach dependencies are installed in Homebrew Python 3.11. If
`python3 main.py` fails with `ModuleNotFoundError`, the fix is to use the wrappers above
or run `/opt/homebrew/bin/python3.11` directly.

## RSS

The simple RSS path depends on `feedparser`. On this machine, it is available in Homebrew
Python 3.11, not the macOS system Python 3.9:

```bash
/opt/homebrew/bin/python3.11 -c "import feedparser; print(feedparser.__version__)"
```

## Weibo

```bash
pip install git+https://github.com/Panniantong/mcp-server-weibo.git
mcporter config add weibo --command 'mcp-server-weibo'
mcporter list weibo
```

## Xiaoyuzhou

The script is installed by Agent Reach. The user only needs to provide a Groq API key:

```bash
agent-reach configure groq-key gsk_xxxxx
```

## General Checks

List configured MCP backends and available tools before guessing function names:

```bash
mcporter list
mcporter list CHANNEL_NAME
```

After any fix, re-run:

```bash
agent-reach doctor
```
