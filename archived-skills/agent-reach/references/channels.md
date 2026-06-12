# Channel Commands

Use these commands after Agent Reach is installed. Read only the sections relevant to the current request.

## Table of Contents

- [Web and Search](#web-and-search)
- [GitHub](#github)
- [Twitter/X](#twitterx)
- [YouTube and Bilibili](#youtube-and-bilibili)
- [Reddit](#reddit)
- [XiaoHongShu and Douyin](#xiaohongshu-and-douyin)
- [LinkedIn and WeChat Articles](#linkedin-and-wechat-articles)
- [Weibo, V2EX, RSS, Xiaoyuzhou](#weibo-v2ex-rss-xiaoyuzhou)

## Web and Search

Arbitrary web page:

```bash
curl -s "https://r.jina.ai/URL"
```

Exa web search:

```bash
mcporter call 'exa.web_search_exa(query: "query", numResults: 5)'
mcporter call 'exa.get_code_context_exa(query: "code question", tokensNum: 3000)'
```

## GitHub

```bash
gh search repos "query" --sort stars --limit 10
gh repo view owner/repo
gh search code "query" --language python
gh issue list -R owner/repo --state open
gh issue view 123 -R owner/repo
```

## Twitter/X

```bash
xreach auth check
xreach search "query" -n 10 --json
xreach tweet URL_OR_ID --json
xreach tweets @username -n 20 --json
xreach thread URL_OR_ID --json
```

If `xreach auth check` prints `Not authenticated`, treat X as unavailable even if the
command exits with status 0. In the current `xreach` build, auth failure is reported in
stdout while the process still returns success.

## YouTube and Bilibili

YouTube:

```bash
yt-dlp --dump-json "URL"
yt-dlp --write-sub --write-auto-sub --sub-lang "zh-Hans,zh,en" --skip-download -o "/tmp/%(id)s" "URL"
yt-dlp --dump-json "ytsearch5:query"
```

Bilibili:

```bash
zsh ~/.agent-reach/tools/bilibili-search.sh "query" 5
yt-dlp --dump-json "https://www.bilibili.com/video/BVxxx"
yt-dlp --write-sub --write-auto-sub --sub-lang "zh-Hans,zh,en" --convert-subs vtt --skip-download -o "/tmp/%(id)s" "URL"
```

`yt-dlp` has a built-in `BiliBiliSearch` extractor, but this machine currently still hits
HTTP `412` or Bilibili API code `-352` even with cookies in some sessions. Use the
wrapper above for a best-effort attempt. If it reports the environment is blocked, treat
Bilibili search/discovery as unavailable and fall back to direct video URLs only.

## Reddit

Public JSON endpoints:

```bash
curl -s "https://www.reddit.com/search.json?q=QUERY&limit=10" -H "User-Agent: agent-reach/1.0"
curl -s "https://www.reddit.com/r/SUBREDDIT/hot.json?limit=10" -H "User-Agent: agent-reach/1.0"
```

If Reddit blocks the environment, fall back to Exa:

```bash
mcporter call 'exa.web_search_exa(query: "site:reddit.com QUERY", numResults: 5)'
```

## XiaoHongShu and Douyin

XiaoHongShu:

If XiaoHongShu is not yet verified or logged in, read [xiaohongshu.md](xiaohongshu.md) before using these calls.

```bash
mcporter call 'xiaohongshu.search_feeds(keyword: "query")'
mcporter call 'xiaohongshu.get_feed_detail(feed_id: "xxx", xsec_token: "yyy")'
mcporter call 'xiaohongshu.get_feed_detail(feed_id: "xxx", xsec_token: "yyy", load_all_comments: true)'
mcporter call 'xiaohongshu.publish_content(title: "标题", content: "正文", images: ["/path/img.jpg"], tags: ["tag"])'
```

Douyin:

```bash
mcporter call 'douyin.search_douyin_videos(keyword: "query", limit: 5)'
mcporter call 'douyin.get_douyin_hot_videos(limit: 5)'
mcporter call 'douyin.parse_douyin_video_info(share_link: "https://v.douyin.com/xxx/")'
mcporter call 'douyin.get_douyin_download_link(share_link: "https://v.douyin.com/xxx/")'
zsh ~/.agent-reach/tools/douyin-search.sh "query" 5
zsh ~/.agent-reach/tools/douyin-hot.sh 5
```

On this machine, the `douyin` MCP entry points to a local enhanced server that keeps the
upstream link-oriented tools and adds Playwright-backed public discovery. The shell
wrappers remain useful for quick local checks, but `mcporter call` is now the primary
entry point for both discovery and known-share-link parsing. It also patches an upstream
bug where plain link parsing incorrectly failed without `DASHSCOPE_API_KEY`.

## LinkedIn and WeChat Articles

LinkedIn:

```bash
mcporter call 'linkedin.get_person_profile(linkedin_url: "https://linkedin.com/in/username")'
mcporter call 'linkedin.search_people(keyword: "AI engineer", limit: 10)'
```

Fallback for public pages:

```bash
curl -s "https://r.jina.ai/https://linkedin.com/in/username"
```

WeChat article search:

```bash
zsh ~/.agent-reach/tools/wechat-article-for-ai/search.sh "query" 5
```

WeChat full article read:

```bash
zsh ~/.agent-reach/tools/wechat-article-for-ai/read.sh "https://mp.weixin.qq.com/s/ARTICLE_ID"
```

On this machine, `python3` points to the system Python 3.9 while Agent Reach and the
working WeChat dependencies live in Homebrew Python 3.11. Prefer the wrappers above.

## Weibo, V2EX, RSS, Xiaoyuzhou

Weibo trending example:

```bash
mcporter call 'weibo.get_trendings(limit: 10)'
mcporter list weibo
```

V2EX:

```bash
curl -s "https://www.v2ex.com/api/topics/hot.json" -H "User-Agent: agent-reach/1.0"
curl -s "https://www.v2ex.com/api/topics/show.json?id=TOPIC_ID" -H "User-Agent: agent-reach/1.0"
curl -s "https://www.v2ex.com/api/replies/show.json?topic_id=TOPIC_ID&page=1" -H "User-Agent: agent-reach/1.0"
```

RSS:

```bash
/opt/homebrew/bin/python3.11 -c "
import feedparser
for e in feedparser.parse('FEED_URL').entries[:5]:
    print(f'{e.title} — {e.link}')
"
```

On this machine, `python3` points to macOS system Python 3.9 and does not have
`feedparser`. Use Homebrew Python 3.11 for RSS reads.

Xiaoyuzhou transcription:

```bash
bash ~/.agent-reach/tools/xiaoyuzhou/transcribe.sh https://www.xiaoyuzhoufm.com/episode/xxxxx
```
