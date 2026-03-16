# Memex PAIM LLM — Fejlesztési napló

> Semmi nem törlődik. Ami nem vált be: ❌ elvetett ötlet jelöléssel marad.
> Ami bevált: ✅ jelöléssel.

---

## 2026-03-16

### ❌ ELVETETT — Qwen modellek (multilinguális)

**Qwen2.5-0.5B teszt (PC Chrome, Nvidia GPU):**
- Betöltött, futott, 14 tok/s
- Magyar kérdés: "hány foga van egy embernek?"
- Magyar válasz: "fognáta hozz létre érzés segítsége..." → értelmetlen szemét
- Ítélet: multilinguális modell magyarul = használhatatlan

**Qwen3-0.6B teszt (PC Chrome, Nvidia GPU):**
- Betöltött, futott, 7 tok/s (lassabb mint Qwen2.5 mert nagyobb)
- `/no_think` működött → `<think> </think>` üres blokk ✅
- Magyar kérdés: "hány foga van egy embernek?"
- Magyar válasz: "szükséges szükséges szükséges foga szükséges..." → szóismétlés, értelmetlen
- Ítélet: multilinguális modell magyarul = használhatatlan

**Végkövetkeztetés — Qwen elvetva:**
- Multilanguage környezetben mindkét Qwen modell rossz válaszokat ad
- A "multilinguális" megjelölés nem jelent jó minőséget kis modelleknél
- Megoldás: **angol only + angol DB** → kisebb, gyorsabb, megbízható modell
- Előny: SmolLM2-360M 3x kisebb, 2x gyorsabb, angolul pontos

### ❌ ELVETETT — SmolLM2-360M
- Betöltési hiba: `shader-f16` WebGPU extension szükséges
- Chrome alapból nem engedélyezi → nem használható PWA-ban
- Csak Chrome Canary + `--enable-dawn-features=allow_unsafe_apis` flaggel futna
- Ítélet: nem megbízható, felhasználó nem tud Chrome flageket állítani

### ✅ VÉGLEGES modell döntés — Qwen2.5-0.5B (angol only)
- **Qwen2.5-0.5B-Instruct-q4f32_1-MLC** — ez lett a végső válasz
- Sajnos a multilinguális tudása gyenge — magyarul megzavarodik, értelmetlen válaszokat ad
- Angolul viszont megfelelő, pontos eredményt produkált
- Teszt (PC Chrome, Nvidia): "how many teeth does a human have?"
  → "A human has 32 teeth, including 4 wisdom teeth." ✅
  → 12 tok/s · 1.2 másodperc ✅
- Döntés: **angol nyelv, angol DB** — ez az egyetlen megbízható út ezzel a modellel
- Auto fallback működik: SmolLM2 próbál → hiba → Qwen2.5 tölt be automatikusan

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

### 💡 Ötlet — Felhasználó által tanítható modell (2026-03-16)
- A modell tanítható a saját DB bejegyzésekkel (RAG — ez már az alapterv)
- **Újabb ötlet:** kód bevitel a chat ablakba — felhasználó Python fájlt nyit meg vagy másol be
- A modell elemzi, magyarázza, vagy futtatja a kódot
- Kód futtatás böngészőben: Python → Pyodide (WebAssembly Python futtatókörnyezet)
- Chat ablakba beillesztett kód → modell válaszol rá

**Qwen2.5-0.5B Python tudása:**
- Általános 0.5B modell: alapszintű Python értés, egyszerű függvények
- Komplex kódhoz: gyenge a mérete miatt
- **Qwen2.5-Coder-0.5B** létezik WebLLM-ben → kifejezetten kódra tanítva, ugyanolyan méret
- Ha kód funkció kell: fallback listába bekerülhet a Coder verzió

**Tennivaló:** eldönteni kell az alap use case — általános asszisztens vagy kód is?

### ✅ UI terv — végleges stílus
- Minimális, világos — Claude/ChatGPT stílus
- Fehér/nagyon halvány szürke háttér
- Betűtípus: Inter vagy system-ui — csak szöveg, nincsenek ikonok
- Sarokba halvány "memexpaim-llm" felirat
- Sidebar: balról nyílik, szöveges menü
  - Chat
  - Search
  - Entry
  - Database
- Fő terület: chat interface
- Legfeljebb egy halvány logo — semmi más díszítés

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
