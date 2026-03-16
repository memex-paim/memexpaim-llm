# Memex PAIM LLM — Fejlesztési napló

> Semmi nem törlődik. Ami nem vált be: ❌ elvetett ötlet jelöléssel marad.
> Ami bevált: ✅ jelöléssel.

---

## 2026-03-16

### ✅ Modell döntés
- **Qwen3-0.6B-q4f16_1-MLC** — végleges választás
- WebLLM-ben fut, böngészőben, telepítés nélkül
- 100+ nyelv, magyar is
- ~1.4GB VRAM, ~350MB letöltés
- 4096 token kontextus ablak (WebLLM korlát)
- Referencia pont: Gemini Nano (gyorsabb de zárt, csak Pixel 8+)

### ✅ Sebesség és válasz stílus
- Becsült sebesség: ~10-20 tok/s Android mid-range GPU-n
- Várható válasz idő: 3-7 másodperc offline módban
- System prompt-tal rövid, tömör válaszokra kell szorítani
- Rövidebb válasz = kevesebb token = gyorsabb + jobban fér a kontextusba

### ✅ Működési elv
```
Online:  PWA → Cloud AI (Claude/Gemini) → válaszol
Offline: PWA → WebLLM (Qwen3-0.6B) → IndexedDB (RAG) → válaszol
```

### ✅ Alapdokumentumok elkészültek
- `LICENSE` — CC BY-NC 4.0 (kereskedelmi védelem)
- `README.md` — nyilvános projekt leírás
- `pit.md` + `pit_en.md` — vízió kiáltvány, kétnyelvű, időbélyegzett
- `Claude_Code_memexpaim-llm.md` — technikai fejlesztési napló

### ✅ Alap kód
- Memex PAIM teljes kód bemásolva alapként
- Hang keresés (search tab mic gomb) hozzáadva

---

## Következő fejlesztési munkamenet

### 🔲 Teendők
1. WebLLM library beépítése az index.html-be
2. Qwen3-0.6B betöltés tesztelése Chrome-ban
3. Offline/online auto-váltás logika
4. RAG pipeline — IndexedDB keresés → kontextus → Qwen
5. System prompt — rövid tömör válaszok
6. Tesztelés Android Chrome-on

---
