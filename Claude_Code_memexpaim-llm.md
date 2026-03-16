# Claude_Code_memexpaim-llm.md — Fejlesztési napló

## Mi ez?
Memex PAIM kiterjesztése WebLLM-mel — offline, böngészőben futó kis nyelvi modell.
GitHub repo: https://github.com/memex-paim/memexpaim-llm

> **pit.md** — tartalmazza a Claude chat exportból kinyert összes ötletet és víziót
> **README.md** — nyilvános dokumentáció GitHubon

---

## Architektúra döntések (2026-03-16)

- **Modell:** Qwen2.5 0.5B (multilinguális, magyar is, ~350MB letöltés)
- **Runtime:** WebLLM (WebGPU, Chrome böngésző, telepítés nélkül)
- **Adatbázis:** IndexedDB (már megvan a Memex PAIM-ból)
- **Első letöltés:** ~350MB WiFi-n egyszer, utána offline cached
- **RAM igény:** ~700MB összesen (GPU memória)
- **Platform:** PWA, Android Chrome

## Működési elv
```
Online:  PWA → Cloud AI (Claude/Gemini) → válaszol
Offline: PWA → WebLLM (Qwen2.5 0.5B) → IndexedDB (RAG) → válaszol
```

---

## Állapot

### ✅ Kész
- Alap Memex PAIM kód bemásolva a repóba
- LICENSE (CC BY-NC 4.0)
- README — ötlet dokumentálva, időbélyegzett (2026-03-16)
- Hang keresés (search tab mic gomb) — átvéve Memex PAIM-ból

### 🔲 Következő lépések
1. WebLLM library beépítése az index.html-be
2. Qwen2.5 0.5B modell betöltés tesztelése
3. Offline/online auto-váltás logika
4. RAG pipeline — IndexedDB keresés → kontextus → Qwen
5. Tesztelés Android Chrome-on

---

## Technikai jegyzetek
- WebLLM npm: `@mlc-ai/web-llm`
- CDN-ről is betölthető: `https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm`
- Qwen2.5-0.5B-Instruct-q4f16_1-MLC — ez a WebLLM modell azonosító
- WebGPU szükséges: Chrome 113+ Android-on támogatott
