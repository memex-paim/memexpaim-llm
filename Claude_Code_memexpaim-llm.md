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
- Modell azonosító: `Qwen2.5-0.5B-Instruct-q4f32_1-MLC` (aktív), Gemma 2: `gemma-2-2b-it-q4f16_1-MLC` (tesztelés alatt)
- WebGPU szükséges: Chrome 113+ Android-on támogatott
- Sebesség benchmark: Qwen2.5-0.5B → 7 tok/s A54-en, 12 tok/s PC Chrome-on
- Etalon: Gemini Nano ~45 tok/s (Pixel 9, Tensor G4 NPU-n)

---

## KRITIKUS — Repo és URL struktúra

**Ez a repo (`memexpaim-llm`) = `memexpaim.com/llm/`**

| Könyvtár | URL | Státusz |
|----------|-----|---------|
| `ui/index.html` | `memexpaim.com/llm/ui/` | ✅ **IDE DOLGOZUNK** |
| `app/` | `memexpaim.com/llm/app/` | 🚫 NE NYÚLJ HOZZÁ (kész Memex PAIM) |
| `memexpaim.com/app/` | másik repo | 🚫 NE NYÚLJ HOZZÁ |

**Fejlesztési fájl: `ui/index.html`**

---

## Modell döntések (2026-03-17)

| Modell | Státusz | Megjegyzés |
|--------|---------|------------|
| Qwen2.5-0.5B-Instruct-q4f32_1-MLC | ✅ aktív | PC+A54 tesztelve, angolul működik |
| gemma-2-2b-it-q4f16_1-MLC | 🔲 tesztelendő | jobb minőség, ~1.5GB |
| Qwen3-0.6B | ❌ elvetva | lassabb, magyarul ugyanolyan rossz |
| SmolLM2-360M | ❌ elvetva | shader hiba volt |

**Fontos:** kis modellek (~1B alatt) magyarul NEM megbízhatók → **angol only rendszer**

**Adatvédelem elsődleges:** Qwen2.5 az alap (offline, privát), Cloud AI csak ha felhasználó engedélyezi.

---

## RSS + Playwright architektúra ötlet (2026-03-17)

### Koncepció
~50 témára szabott, automatikus DB feltöltés RSS-ből + on-demand teljes cikk Playwright-tal.

### 1. réteg — RSS summaries (háttérben)
- 50 téma × 10-20 RSS forrás = ~1000 feed
- `feedparser` (Python) lekéri a híreket → FastAPI `/rss` endpoint → IndexedDB
- Qwen látja: "mi a mai sporthír?" → DB-ből válaszol

### 2. réteg — On-demand teljes cikk
- User kér egy cikket részletesen
- FastAPI `/fetch-article` → Playwright text módban (csak szöveg, sem kép sem JS)
- Szöveg visszakerül a Qwen-nek → részletes válasz

### Miért jó?
- Nincs külső függőség (saját Python + feedparser)
- Playwright text mód = gyors, könnyű
- IndexedDB-ben marad az adat → offline is működik

### Ami kell hozzá
1. FastAPI `/rss` endpoint (feedparser)
2. FastAPI `/fetch-article` endpoint (Playwright text mód)
3. LLM app RSS panel (feed URL-ek kezelése, szinkron gomb)
4. Chat: link detektálás → "részletes olvasás" ajánlat

### Megvalósítási terv (végleges döntés 2026-03-17)

**RSS szinkron:**
- `allorigins.win` CORS proxy — ingyenes, regisztráció nélkül
- Böngészőből közvetlenül, FastAPI nem kell
- `https://api.allorigins.win/raw?url=<rss_feed_url>`
- Működik mobiladaton is ✅

**Playwright (teljes cikk lekérés):**
- FastAPI kell hozzá (Python backend)
- FastAPI csak WiFi-n elérhető (192.168.0.64 lokális IP)
- Mobiladaton NEM működik ❌
- Megoldás later: Railway/fly.io felhőbe tenni a FastAPI-t

**[TERV — nem végleges] Playwright alternatíva — böngészőből, szerver nélkül:**
- allorigins.win lekéri az oldalt (CORS bypass)
- Readability.js (Mozilla Firefox olvasó mód library) kiveszi a cikk szövegét
- Nincs FastAPI, nincs Python, mobiladaton is működik ✅
- Korlát: csak konkrét URL-t nyit meg, nem keres

**[TERV — nem végleges] Web keresés böngészőből:**
- Google Custom Search API — ingyenes 100 keresés/nap, API key kell
- Böngészőből hívható, mobiladaton is megy
- Folyamat: User kérdés → Google CSE → 5 link → allorigins → Readability.js → Qwen
- Androidon, WiFi nélkül, szerver nélkül működne ✅
- Korlát: 100 keresés/nap ingyenes tier

**[TERV — nem végleges] Playwright (eredeti ötlet):**
- PC-n tökéletes, Chrome háttérben fut, AI irányítja
- Androidon nem megoldható PWA-ból natívan
- FastAPI + Python kell hozzá, csak WiFi-n elérhető
- Státusz: 🔲 döntés folyamatban

**Adatbázis méret kezelés:**
- RSS bejegyzések: 30 nap után auto törlés (~90MB max)
- Readability.js-sel megnyitott cikkek: megmaradnak (felhasználó szándékosan mentette)
- Különbség: `iro: 'rss'` → törlődik, `iro: 'article'` → marad

### 🔧 AKTÍV TESZT — ez az út

**Cél:** Qwen2.5 RAG tesztelése valós adattal

**Folyamat:**
1. Összegyűjteni angol nyelvű RSS csatornákat (hírek, tech, sport, tudomány stb.)
2. allorigins.win-en át lekérni az RSS feed-eket
3. Bejegyzések → IndexedDB (`iro: 'rss'`, 30 nap auto törlés)
4. User kérdez → Qwen DB-ből válaszol
5. "Meséld el részletesen" → allorigins + Readability.js → Qwen

**Státusz: 🔧 Következő fejlesztés — RSS panel az LLM app-ba**

### Ha nincs az adatbázisban — Google link fallback

Ha a Qwen nem talál releváns adatot a DB-ben, a válasz:
```
I don't have reliable information about this in my database.

🔍 Search: https://google.com/search?q=<kérdés>
```
- Nem nyitja meg automatikusan — felhasználó dönt
- Nem "nem tudom" zsákutca — hanem lehetőség
- A link kattintható, Chrome megnyílik
- Egyszerű, elegáns, biztonságos
