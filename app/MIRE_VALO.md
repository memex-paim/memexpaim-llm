# Memex PAIM – Personal AI Memory

> AI forgets. The database remembers.

A privacy-first offline PWA that stores your personal notes, thoughts, and memories on your own device — no server, no cloud, no account required.

Live: **[memexpaim.com](https://memexpaim.com)**

---

## What it does

Memex PAIM is a personal knowledge base combined with an AI assistant. You save entries (text, voice, ideas, decisions) and later ask questions — the AI searches your own database to answer.

- **DB mode** 🗄 — searches your own entries
- **AI mode** 🤖 — answers from AI knowledge only (Claude / Gemini)
- **Voice input** 🎤 — speak instead of type, saved with `@voice` anchor automatically

---

## Architecture

```
app/
├── index.html      ← Entire app (~99% of runtime logic lives here)
├── memex-db.js     ← IndexedDB layer (storage engine)
├── sw.js           ← Service Worker (offline cache)
├── manifest.json   ← PWA manifest (Add to Home Screen / Play Store)
├── icon.svg        ← App icon
└── version.json    ← Update detection (bumped on every release)
```

**Storage:** IndexedDB — built into every browser, no file, no server
**AI:** Direct API calls to Claude (Anthropic) or Gemini (Google) from the browser
**API keys:** Stored in localStorage on your device only
**Export/Import:** JSON-based, optional XOR+SHA256 encryption with password

---

## Key features

| Feature | Details |
|---------|---------|
| 28 languages | Full UI translation, auto-detects browser language |
| Offline PWA | Works without internet after first load |
| Voice input | Web Speech API, Chrome/Safari, auto `@voice` anchor |
| Anchors | Tag entries with keywords, searchable and browsable |
| Auto-chunking | Text >500 words splits automatically into chunks |
| Time search | "yesterday", "last week", "3 days ago", "in January" |
| Related entries | 🔗 button finds the 3 most similar entries |
| Export/Import | Password-protected .memex file, always free |
| Update badge | 🆕 notification when a new version is available |
| A2A protocol | `/.well-known/agent.json` — ready for agent integration |

---

## How to use

### 1. Set up API key (sidebar)
- **Gemini** — free with a Google account → [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- **Claude** — paid, ~$5/month → [console.anthropic.com](https://console.anthropic.com)
- **Offline** — no AI, only database search

### 2. Save entries (Entry tab)
- Write anything: thoughts, decisions, facts, voice notes
- Add anchors: `work`, `idea`, `health` — or pick from the chip list
- Set priority: Critical / Important / Normal / Casual
- Text over 500 words → auto-splits into chunks

### 3. Search (Search tab)
- Type a word → finds matching entries
- `@anchor` → filters by anchor
- Time filters: `today`, `yesterday`, `last week`, `last month`
- Click anchor chips for one-tap search
- 🔗 Related — finds similar entries

### 4. Chat (Chat tab)
- 🗄 DB mode: "What did I write about X?" → searches your database
- 🤖 AI mode: ask anything, AI answers from its own knowledge
- 🎤 Voice: tap mic, speak, entry saved with `@voice`

### 5. Export / Import (Export tab)
- Export → downloads `.memex` file (optional password)
- Import → restores from `.memex` file
- Export is always free (GDPR principle)

---

## Business model

- **1 database free** — forever
- **Each additional database: $1** — one-time, Google Play IAP
- Gemini API: free (Google account)
- Claude API: paid (~$5/month, user's own key)

---

## Deployment

- **Hosting:** GitHub Pages (`memex-paim/memex-paim` repo, master branch)
- **Domain:** memexpaim.com (Cloudflare DNS, purchased 2026-03-14, expires ~2028-03-14)
- **HTTPS:** Let's Encrypt via GitHub Pages
- **Play Store:** TWA (Trusted Web Activity) — planned

---

## Release process

Every release **must** bump `version.json`:
```json
{"v":"YYYYMMDD-N"}
```
This triggers the 🆕 update badge for existing users.
