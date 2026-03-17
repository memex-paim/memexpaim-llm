# Claude_Code_Olvasdel.md — Működési útmutató

## Két repo, két projekt

| Repo | URL | Szerepe |
|------|-----|---------|
| `memex-paim/memex-paim` | github.com/memex-paim/memex-paim | **LIVE SITE** — ezt pusholjuk ha változtatni akarunk |
| `memex-paim/memexpaim-llm` | github.com/memex-paim/memexpaim-llm | Fejlesztési napló, dokumentáció, CCM.md |

---

## Két oldal — melyikhez nyúlunk?

| URL | Fájl a repoban | Szabad módosítani? |
|-----|---------------|-------------------|
| `memexpaim.com/app/` | `memex-paim/memex-paim` → `app/index.html` | 🚫 NEM — kész, ne nyúlj hozzá |
| `memexpaim.com/llm/` | `memex-paim/memex-paim` → `llm/index.html` | ✅ IGEN — ezen dolgozunk |

---

## Hol van a lokális klón?

```
/home/admin/server/memex-paim/       ← ide kell cd-zni ha llm/index.html-t módosítasz
/home/admin/server/memexpaim-llm/    ← napló, CCM, dokumentáció
```

---

## Munkafolyamat — ha változtatni akarunk

```bash
cd /home/admin/server/memex-paim
# ... szerkesztés: llm/index.html ...
git add llm/index.html
git commit -m "..."
git push origin master
```

GitHub Pages automatikusan frissül 1-2 percen belül → `memexpaim.com/llm/`

---

## Git konfig (memex-paim repo)

```
user.email = memexpaim@gmail.com
user.name  = Memex PAIM
branch     = master
```

---

## Mi van az llm/index.html-ben most?

- WebLLM beépítve (CDN: `esm.run/@mlc-ai/web-llm@0.2.79`)
- Modell választó a sidebarban: Qwen2.5 0.5B / Gemma 2 2B / Llama 3.2 1B
- Default modell: Qwen2.5-0.5B-Instruct-q4f32_1-MLC
- tok/s kijelző a topbarban valós időben
- Aktív modell neve lent a sidebarban
