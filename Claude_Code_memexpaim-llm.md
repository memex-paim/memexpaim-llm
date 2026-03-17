# Claude_Code_memexpaim-llm.md — Fejlesztési napló

## Mi ez?
Memex PAIM kiterjesztése WebLLM-mel — offline, böngészőben futó kis nyelvi modell.
GitHub repo: https://github.com/memex-paim/memexpaim-llm

> **pit.md** — tartalmazza a Claude chat exportból kinyert összes ötletet és víziót
> **README.md** — nyilvános dokumentáció GitHubon

---

## Architektúra döntések (2026-03-16)

- **Modell:** Qwen2.5-0.5B-Instruct-q4f32_1-MLC (végleges aktív modell — lásd indoklás lent)
- **Runtime:** WebLLM (WebGPU, Chrome böngésző, telepítés nélkül)
- **Adatbázis:** IndexedDB (már megvan a Memex PAIM-ból)
- **Első letöltés:** ~1.4GB WiFi-n egyszer, utána offline cached
- **RAM igény:** ~1.4GB GPU memória
- **Kontextus ablak:** 4096 token (WebLLM korlát)
- **Platform:** PWA, Android Chrome

### Miért Qwen2.5-0.5B és nem más?
| | Qwen2.5-0.5B | Qwen3-0.6B | SmolLM2 360M |
|-|-------------|------------|--------------|
| RAM | ~kisebb | ~1.4GB | ~400MB |
| Magyar | ❌ csak angol | ❌ csak angol | ❌ csak angol |
| Angol minőség | ✅ megfelelő | ✅ de lassabb | ⚠️ shader hiba |
| PWA-ból | ✅ | ✅ | ❌ hiba volt |
| Státusz | ✅ **aktív** | elvetva | elvetva |

**Konklúzió:** mindkét Qwen magyarul használhatatlan kis méretben. Döntés: angol only rendszer, Qwen2.5-0.5B az aktív modell.

## Alapkoncepció — Adatvédelem elsődleges

**A Qwen2.5 az elsődleges AI — az adatok nem hagyják el a felhasználó eszközét.**
Cloud AI (Claude/Gemini) csak akkor, ha a felhasználó tudatosan engedélyezi.

```
Alapértelmezett: PWA → Qwen2.5 (telefon, lokális, privát)
Fallback:        PWA → Cloud AI (csak ha felhasználó engedélyezi)
```

## Projekt kapcsolat — memexpaim-llm a Memex PAIM-ra épül

- **Memex PAIM** (`memex/`) = alap projekt, FastAPI backend (`memex_gateway.py`, port 8765)
- **memexpaim-llm** = erre épül, a Memex PAIM a backend és a felhasználói felület
- A Qwen2.5 a Memex PAIM UI-ján fut WebLLM-mel, de a backend már megvan

## Működési elv
```
Elsődleges: PWA → Qwen2.5 (telefon, WebLLM, offline, privát)
Fallback:   PWA → Cloud AI (Claude/Gemini, csak ha engedélyezett)
Web scraping (jövő): PWA → Memex PAIM backend → Playwright → szöveg → Qwen2.5
RSS (jövő): PWA → RSS feed-ek (Telex stb.) → IndexedDB → Qwen2.5
Web keresés gomb BE: PWA → Memex PAIM backend → Playwright → szöveg egyből chat ablakba (Qwen nem kell)
```

## Mit fog tudni ha sikeres a fejlesztés
- Offline AI válasz saját adatokból (angol)
- RAG: a DB releváns bejegyzéseit kontextusként kapja
- Online/offline automatikus váltás
- Első letöltés után teljesen hálózat nélkül működik
- Bármely Android telefonon fut ahol van Chrome
- RSS feed-ek automatikus frissítése (hírek, blogok)
- Web keresés toggle gomb (mint OpenWebUI) — felhasználó kapcsolja be/ki
  - BE: kérdés → RSS / Playwright fut → cikkek egyből chat ablakba, Qwen NEM foglalja össze
  - KI: normál Qwen2.5 válasz
  - Qwen csak akkor szól bele ha utána kérdez valamit pl. "melyik a legfontosabb?"
  - Qwen duplikáció szűrés: ha ugyanaz a téma 3x szerepel → csak 1x jelenik meg a chatben

### RSS forrás gyűjtemény
- **OPML formátum** — szabványos RSS gyűjtemény, importálható/exportálható
- Nem kell nulláról építeni — GitHub-on rengeteg kész OPML lista van
- **500 forrás bőven elég** angol nyelven a teljes lefedéshez
- Magyar források: Telex, Index, 444, HVG mind ad RSS-t
- Feedly / NewsBlur exportok is használhatók
- Az adatbázisban témák szerint csoportosítva tárolni

**Lefedett témák 500 forrással:**
- Tőzsde, pénzügy, crypto
- Politika, világhírek
- Tech, AI, startup
- Sport, e-sport
- Tudomány, egészség
- Kultúra, film, zene
- Gaming
- Lifestyle

### RSS + Playwright kombinált hírolvasó folyamat
```
1. lépés — áttekintés:
  Felhasználó: "mik a hírek?"
  → RSS behoz címeket + rövid leírásokat (link is benne van!)
  → Qwen2.5 deduplikál (ha 3x írták az olajválságot → 1x jelenik meg)
  → chat: témák listája

2. lépés — teljes cikk:
  Felhasználó: "a Messi gól érdekel"
  → Qwen2.5 kiveszi az RSS linkjét
  → Playwright megnyitja, teljes szöveget hozza
  → chat ablakba kerül a teljes cikk

Közben: RSS folyamatosan frissül a háttérben
```

**Miért jó ez a kombináció:**
- RSS = gyors, szerver nélkül, CORS-mentes, link is benne van
- Playwright = teljes cikk ha kell, képek, részletek
- Qwen2.5 = csak deduplikál és linket ad át, nem kell nagy modell
- Felhasználó maga olvassa a tartalmat, Qwen nem foglalja össze alapból

### Dátum és idő — Qwen2.5 nem tudja magától
- Kis modellek nem tudják a mai dátumot (tanítási adat korlát)
- **Megoldás:** PWA mindig betáplálja a kontextusba:
  - `new Date()` → pontos dátum/idő JavaScriptből
  - IndexedDB timestamp → utolsó bejegyzés ideje
- Qwen2.5 kontextus minden kérésnél:
```
"Today is 2026-03-17.
Last DB entry: 2026-03-16 evening.
User asks: ..."
```
- Ennek köszönhetően tudja mondani:
  - "tegnap este elmentetted hogy..."
  - "3 napja nem volt bejegyzés"
  - "ma reggel óta ez és ez történt"

### System prompt architektúra
**Két réteg — mint az Anthropic modellekénél:**

**1. Rendszer szintű prompt (be van égetve, felhasználó NEM látja, NEM módosíthatja)**
```
"Today is {dátum}, {idő}.
You are a personal AI assistant.
Answer in max 3 sentences. Be concise and direct."
```
- PWA automatikusan generálja indulásnál
- Első sor mindig dinamikus: aktuális dátum + idő
- Felhasználó nem érheti el, nem írhatja felül
- **Miért fontos:** Qwen2.5-0.5B nagyon érzékeny a system promptra
  - Ha felülírják → értelmetlen válaszok, rendszer összeomlik
  - Kis modellnél ez kritikus stabilitási kérdés

**2. Felhasználói szintű prompt (opcionálisan testre szabható)**
- Neve, preferenciái, nyelv stb.
- Ez módosítható — de a rendszer szintű prompt felett van, azt nem érinti

## Mit NEM fog tudni
- Magyar nyelv (csak angol megbízható)
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
- Modell azonosító: `Qwen2.5-0.5B-Instruct-q4f32_1-MLC`
- Qwen3-0.6B tesztelve volt, de elvetva (lassabb, magyarul ugyanolyan rossz)
- **Fontos:** csak angolul működik megbízhatóan — DB és kérdések is angolul kell!
- WebGPU szükséges: Chrome 113+ Android-on támogatott

---

## Platform kompatibilitás (2026-03-17 — megerősítve)

### PWA / offline működés
- A `sw.js` Service Worker és `manifest.json` jól meg van írva
- Chrome Android helyi hálózaton (HTTP, `192.168.0.64`) is regisztrálja a SW-t — **megerősítve Samsung A54-en**
- PWA telepítési gomb megjelenik Chrome-ban ✅
- Update esetén sárga "update" felirat jelenik meg az UI-ban ✅

### Ki tudja futtatni?
| Platform | Fut? |
|----------|------|
| Android + Chrome (2018+) | ✅ igen |
| iPhone/iPad + Safari (iOS 15.4+) | ✅ igen |
| iPhone/iPad + Chrome | ✅ igen (WebKit motor, mint Safari) |
| Huawei (2019 utáni, Google nélkül) | ⚠️ valószínűleg igen (Chromium alapú böngésző) |
| Egyéb kínai Android (Xiaomi, OPPO stb.) | ✅ igen, ha van Chrome |
| Régi iOS (15.4 alatt) | ⚠️ layout-törés lehet (dvh CSS unit) |

**Összefoglalás:** ha van Chrome a telefonon, fut. Ez a felhasználók 95%+.
