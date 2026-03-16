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

## 2026-03-16 (folytatás)

### ✅ Első teszt — retro terminál UI
- Fekete háttér, zöld szöveg, monospace — terminál stílus
- WebGPU ellenőrzés, progress bar, streaming válasz
- Villogó kurzor amíg a Qwen gondolkodik
- memexpaim.com/llm címen elérhető

### ❌ HIBA — WebGPU shader hiba (első teszten)
```
ERROR: [Invalid ShaderModule (unlabeled)] is invalid.
While validating compute stage, entryPoint: "copy_single_page_kernel"
```
- **Ok:** a GPU driver nem támogat egy speciális WebGPU shader műveletet
- **Megoldandó:** q4f32 variáns kipróbálása, vagy más modell tesztelése először
- **Tennivaló:** chrome://gpu ellenőrzés, driver frissítés, q4f32 fallback

### ✅ Sebesség optimalizálás — /no_think
- Qwen3 alapból "gondolkodik" (chain-of-thought) → ezt ki kell kapcsolni
- RAG-nál nincs szükség gondolkodásra: az adat a DB-ből jön, Qwen csak formáz
- `/no_think` system promptban → ~2x gyorsabb válasz
- max_tokens: 256 → 128 (rövidebb = gyorsabb)

### ✅ System prompt architektúra terv
```
2 réteg:
1. FIX rész (10-15 token, soha nem változik):
   "Max 2 mondat. Nincs gondolkodás. Közvetlen válasz. /no_think"

2. DINAMIKUS rész (DB-ből, felhasználó írja):
   "Kontextus: [legfrissebb 2-3 DB bejegyzés]"
   → ez a felhasználó "írható system promptja"
```

### ✅ Idle újratöltés terv
- Ha a felhasználó X perce nem írt → csendben reset + DB frissítés
- Következő kérdésnél a KV cache már meleg → azonnali válasz
- Startup-kor mindig beolvassa a DB legfrissebb bejegyzéseit

### ✅ UI terv — végleges stílus (jövő)
- Teszt: retro terminál (marad amíg fejlesztünk)
- Végleges: minimális, világos, "nagy cégek stílusa" (Claude/ChatGPT)
  - Fehér/szürke háttér
  - Jó betűtípus (Inter, system-ui)
  - Kevés elem a felületen
  - Könnyű, letisztult szöveg

---

## Következő fejlesztési munkamenet

### 🔲 Teendők
1. ❗ WebGPU shader hiba javítása — q4f32 variáns vagy driver
2. Qwen3-0.6B sikeres betöltés tesztelése Chrome-ban
3. Offline/online auto-váltás logika
4. RAG pipeline — IndexedDB keresés → kontextus → Qwen
5. Idle refresh logika (5 perc után DB újratöltés)
6. Tesztelés Android Chrome-on
7. Végleges minimális UI megírása

---
