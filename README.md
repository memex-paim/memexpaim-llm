# Memex PAIM LLM — Offline AI with Local Language Model

> Your memory. Your AI. Your device. No internet required.

**Concept created:** March 2026
**Based on:** [Memex PAIM](https://github.com/memex-paim/memex-paim) — Personal AI Memory
**License:** [CC BY-NC 4.0](LICENSE) — free to use, not for commercial purposes

---

## The Idea

Memex PAIM LLM extends the original Memex PAIM app with a small language model that runs entirely inside the browser — no server, no cloud, no internet connection needed.

The concept was conceived in March 2026 as a solution for people who:
- Have limited or no internet access
- Cannot afford cloud AI API subscriptions
- Want 100% private AI that never sends data anywhere
- Live in areas with poor connectivity

---

## How It Works

```
Online mode:
  PWA → Cloud AI (Claude / Gemini) → answer

Offline mode:
  PWA → WebLLM (runs in browser) → local IndexedDB → answer
```

When internet is available, the app uses a powerful cloud AI (Claude, Gemini).
When offline, a small local language model takes over — trained on your own saved memories.

---

## The Architecture

```
┌─────────────────────────────────────────┐
│           Memex PAIM LLM (PWA)          │
│                                         │
│  ┌─────────────┐    ┌─────────────────┐ │
│  │  WebLLM     │    │  IndexedDB      │ │
│  │  (browser)  │◄───│  (your memory)  │ │
│  │  ~400MB RAM │    │  (local only)   │ │
│  └─────────────┘    └─────────────────┘ │
│         ▲                               │
│         │ RAG (context from DB)         │
│         │                               │
│  ┌─────────────┐                        │
│  │ Cloud AI    │ (online only)          │
│  │ Claude /    │                        │
│  │ Gemini      │                        │
│  └─────────────┘                        │
└─────────────────────────────────────────┘
```

**RAG = Retrieval Augmented Generation**
The local model doesn't need to "know" everything — it reads your saved entries as context and answers based on them. This makes even a tiny 360M parameter model surprisingly capable for personal use.

---

## Local Model Options

| Model | RAM usage | Status |
|-------|-----------|--------|
| **Qwen2.5-0.5B** | ~650MB | ✅ Current — accurate in English, 7-12 tok/s |
| Gemma-3n-E2B (Google) | ~600MB | ⏳ Next to test — on-device optimized, WebGPU-native |
| Gemma-3n-E4B (Google) | ~1.1GB | ⏳ Next to test — stronger, same weight file as E2B |
| SmolLM2 360M | ~400MB | ❌ Dropped — WebGPU shader-f16 error in Chrome |
| SmolLM2 135M | ~200MB | ❌ Dropped — same shader issue |

All models run via [WebLLM](https://webllm.mlc.ai/) — a library that runs language models directly in the browser using WebGPU. No installation, no Termux, no native app needed.

> **English only** — small models (~0.5B) are unreliable in other languages. The DB and queries should also be in English for RAG to work correctly.

---

## Key Principles

- **No installation** — runs in Chrome browser as a PWA
- **No internet required** — after first load and model download
- **No data leaves the device** — ever
- **Model downloads once** — cached in browser, reused offline
- **Auto switching** — cloud AI when online, local model when offline
- **Builds on Memex PAIM** — all existing features remain

---

## Who Is This For?

- People with limited or no internet access
- Privacy-conscious users who want zero data leakage
- Users in rural or low-connectivity areas
- Anyone who wants a personal AI that works anywhere, always

---

## Status

> **Active Development** — March 2026

- [x] Base concept defined
- [x] Architecture designed
- [x] Memex PAIM integrated as foundation
- [x] WebLLM integration (Qwen2.5-0.5B)
- [x] Local RAG pipeline (IndexedDB → top 5 results → context)
- [x] RSS sync + Readability.js (full article fetch)
- [x] Offline/online auto-switching
- [ ] Testing Google Gemma 3n (E2B / E4B) — next step
- [ ] Testing on Android Chrome

---

## Based On

This project builds directly on [Memex PAIM](https://github.com/memex-paim/memex-paim), which provides:
- PWA shell (installable on Android)
- IndexedDB storage
- Chat UI
- Export/Import system
- 28-language support

---

## License

[Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](LICENSE)

Free to use, share, and adapt — but **not for commercial purposes**.
The original author retains the right to commercial use.
