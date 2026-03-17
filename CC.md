# CC.md — Memex PAIM LLM
> Pi5 | `/home/admin/server/memexpaim-llm/` (napló/docs)
> Fejlesztési fájl: `/home/admin/server/memex-paim/llm/index.html`

## Mi ez?
A Memex PAIM app kiterjesztése offline AI-val. Böngészőben futó PWA — nincs szerver, nincs telepítés, nincs felhő.
- **Online:** Cloud AI (Claude / Gemini API)
- **Offline:** Qwen2.5-0.5B WebLLM — WebGPU-n fut Chrome-ban, a telefon saját GPU-ján
- Saját IndexedDB adatbázisból dolgozik (RAG) — amit te mentettél, abból válaszol

## KRITIKUS — Repo struktúra
| Mit | Hol |
|-----|-----|
| **Fejlesztési fájl** | `/home/admin/server/memex-paim/llm/index.html` |
| **Live site** | `memexpaim.com/llm/` |
| **Repo** | `github.com/memex-paim/memex-paim` master branch |
| **Push = éles** | 1-2 perc után él GitHub Pages-en |
| Ez a mappa | Napló, dokumentáció, `naplo.md`, `pit.md` — NEM a fejlesztési kód |

**Push parancs:**
```bash
cd /home/admin/server/memex-paim
git add llm/index.html llm/version.json
git commit -m "..."
git push origin master
```
`llm/version.json` minden pushnál bumpolni kell → frissítési badge a usernek.

## Aktuális verzió
`v20260317-18` — látható a sidebar alján és a Debug panelben.

## Mi van megcsinálva
- ✅ WebLLM + Qwen2.5-0.5B betöltés, tok/s kijelző
- ✅ RAG pipeline — IndexedDB keres → top 5 találat → Qwen kontextusba
- ✅ RSS sync — allorigins.win CORS proxy, ~100 feed, deduplikáció, 30 nap auto törlés
- ✅ Readability.js (Mozilla) — teljes cikk lekérés, csak szöveg, reklám nélkül
- ✅ Source gombok (↗) — AI válasz után kattintható cikk linkek
- ✅ Ask Qwen — teljes cikk Qwen kontextusba → összefoglal
- ✅ Save to DB — cikk mentése `iro:'article'`-ként, örökre marad
- ✅ Hallucináció fix — strict system prompt + "DATABASE: empty" jelzés ha nincs adat
- ✅ Debug panel — DB stats, last 10 entry, verzió, WebGPU státusz
- ✅ Verziószám sidebar alján
- ✅ Export / Import (.memex), Entry, Search, Database, RSS panelek

## Panelek (sidebar)
Chat · Search · Entry · RSS · Database · Export · Debug

## Modell döntések — véglegesek
| Modell | Státusz |
|--------|---------|
| `Qwen2.5-0.5B-Instruct-q4f32_1-MLC` | ✅ Aktív — angolul pontos, 7-12 tok/s |
| Qwen3-0.6B | ❌ Elvetva — lassabb, magyarul ugyanolyan rossz |
| SmolLM2-360M | ❌ Elvetva — shader-f16 WebGPU hiba |

**Angol only** — kis modellek (~0.5B) magyarul használhatatlanok.
DB bejegyzések is angolul kell legyenek — RAG csak akkor működik ha DB és modell azonos nyelven van.

## RSS + Readability.js — a fő tesztelési módszer
Ez az egész RSS + Readability.js pipeline elsődlegesen arra való, hogy **teszteljük: tud-e a Qwen az adatbázisból válaszolni**.

Folyamat:
1. RSS sync → DB feltöltődik valós, friss angol szöveggel
2. Kérdés → Qwen RAG-gal keres a DB-ben → ha jó választ ad = RAG működik
3. Readability.js → teljes cikk bekerül → Qwen összefoglalja = kontextus kezelés tesztelve

Ha Qwen helyesen válaszol a DB tartalma alapján → az architektúra működik.
Ha hallucináll vagy "no data" → a RAG vagy a DB feltöltés a probléma.

## RSS architektúra
```
1. RSS sync → allorigins.win proxy → IndexedDB (iro:'rss', 30 nap auto törlés)
2. User kérdez → Qwen RAG: DB-ből keres, kiemeli a releváns híreket
3. AI válasz alatt: ↗ source gombok (cikkenként)
4. Kattintás → allorigins + Readability.js → csak szöveg
5. [Ask Qwen] → cikk a Qwen kontextusába → összefoglal
   [Save to DB] → elmenti iro:'article'-ként → örökre marad, kereshető
```
- `iro:'rss'` → 30 nap után auto törlődik
- `iro:'article'` → felhasználó szándékosan mentette, soha nem törlődik auto

## Következő fejlesztések
1. **Google link fallback** — ha DB üres → `google.com/search?q=...` kattintható link a válaszban
2. **Felhős AI generált DB bejegyzések** — Claude/Gemini online → angol bejegyzések → IndexedDB → Qwen offline ezekből dolgozik
3. **Felhasználói profil réteg** — AI ír profilt a userről → dinamikus system prompt rész

## Technikai részletek
- WebLLM CDN: `esm.run/@mlc-ai/web-llm@0.2.79`
- Readability.js CDN: `cdn.jsdelivr.net/npm/@mozilla/readability@0.5.0/Readability.js`
- DB: IndexedDB, `memex-db.js` kezeli
- FTS5-szerű keresés IndexedDB-ben (nem SQLite, böngésző oldali)
- Service Worker: offline cache, `llm/sw.js`
- `pendingArticle` változó: cikk szöveg injektálása következő Qwen kérésbe

## Kapcsolódó mappák
| Mappa | Szerep |
|-------|--------|
| `/home/admin/server/memex-paim/` | A repo lokális klónja — **ide kell cd-zni fejlesztéshez** |
| `/home/admin/server/memexpaim-llm/` | Ez a mappa — napló, dokumentáció |
| `/home/admin/server/memex/` | Archív — itt kezdődött a Memex PAIM fejlesztése |

## Hasznos fájlok ebben a mappában
- `naplo.md` — fejlesztési napló, mi vált be, mi nem, következő lépések
- `pit.md` / `pit_en.md` — vízió, ötletek (Claude chat exportból)
- `Claude_Code_memexpaim-llm.md` — technikai döntések naplója
- `rss_feeds.md` — ~180 előkészített RSS feed URL kategóriánként
