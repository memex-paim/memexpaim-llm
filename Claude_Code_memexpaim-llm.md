# Claude_Code_memexpaim-llm.md — Fejlesztési napló

## Mi ez?
Memex PAIM kiterjesztése WebLLM-mel — offline, böngészőben futó kis nyelvi modell.
GitHub repo: https://github.com/memex-paim/memexpaim-llm

> **pit.md** — tartalmazza a Claude chat exportból kinyert összes ötletet és víziót
> **README.md** — nyilvános dokumentáció GitHubon

---

## Architektúra döntések (2026-03-16)

- **Modell:** Qwen3-0.6B (végleges döntés — lásd indoklás lent)
- **Runtime:** WebLLM (WebGPU, Chrome böngésző, telepítés nélkül)
- **Adatbázis:** IndexedDB (már megvan a Memex PAIM-ból)
- **Első letöltés:** ~1.4GB WiFi-n egyszer, utána offline cached
- **RAM igény:** ~1.4GB GPU memória
- **Kontextus ablak:** 4096 token (WebLLM korlát)
- **Platform:** PWA, Android Chrome

### Miért Qwen3-0.6B és nem más?
| | Qwen3-0.6B | Gemini Nano | SmolLM2 360M |
|-|-----------|-------------|--------------|
| RAM | ~1.4GB | ~2-3.5GB | ~400MB |
| Magyar | ✅ 100+ nyelv | ❌ nem garantált | ❌ csak angol |
| PWA-ból | ✅ | ❌ | ✅ |
| Bármely Android | ✅ | ❌ csak Pixel 8+ | ✅ |

## Működési elv
```
Online:  PWA → Cloud AI (Claude/Gemini) → válaszol
Offline: PWA → WebLLM (Qwen3-0.6B) → IndexedDB (RAG) → válaszol
```

## Mit fog tudni ha sikeres a fejlesztés
- Offline magyar nyelvű AI válasz saját adatokból
- RAG: a DB releváns bejegyzéseit kontextusként kapja
- Online/offline automatikus váltás
- Első letöltés után teljesen hálózat nélkül működik
- Bármely Android telefonon fut ahol van Chrome

## Mit NEM fog tudni
- Internetes keresés
- Valós idejű adatok
- Akkora tudás mint Claude/Gemini
- Komplex többlépéses következtetés

---

## Állapot

### ✅ Kész
- Alap Memex PAIM kód bemásolva a repóba
- LICENSE (CC BY-NC 4.0)
- README — ötlet dokumentálva, időbélyegzett (2026-03-16)
- Hang keresés (search tab mic gomb) — átvéve Memex PAIM-ból
- Modell kiválasztva: Qwen3-0.6B-q4f16_1-MLC

### 🔲 Következő lépések
1. WebLLM library beépítése az index.html-be
2. Qwen3-0.6B modell betöltés tesztelése
3. Offline/online auto-váltás logika
4. RAG pipeline — IndexedDB keresés → kontextus → Qwen
5. Tesztelés Android Chrome-on

---

## Technikai jegyzetek
- WebLLM CDN: `https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm`
- Modell azonosító: `Qwen3-0.6B-q4f16_1-MLC`
- WebGPU szükséges: Chrome 113+ Android-on támogatott
