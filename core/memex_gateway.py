"""
Memex Gateway v2.2 - Claude API support + model választó
"""

import sys
import json
import os
import argparse
import urllib.request
import urllib.error
import threading
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _env_betolt():
    helyek = [
        ROOT / ".env",
        Path("/home/admin/server/memex/.env"),
        Path.home() / "server" / "memex" / ".env",
    ]
    for env_path in helyek:
        if env_path.exists():
            for sor in env_path.read_text().splitlines():
                sor = sor.strip()
                if sor and '=' in sor and not sor.startswith('#'):
                    k, v = sor.split('=', 1)
                    os.environ[k.strip()] = v.strip()
            print(f"[Memex] .env betöltve: {env_path}")
            return True
    print(f"[Memex] FIGYELEM: .env nem található! ROOT={ROOT}")
    return False

_env_betolt()

from core.memex_db import (
    init_db, bejegyez, keres,
    legutobbi, legfontosabb,
    system_prompt_build, horgony_lista,
    iro_statisztika, a2a_session_nyit, a2a_session_zar,
    ai_nev_normalizal, get_connection
)
from core.memex_export import (
    export_memex, import_memex, export_info,
    uuid_get, export_lista, lejarat_ellenorzes
)

OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL    = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash")
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY        = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY", "")
CEREBRAS_API_KEY    = os.getenv("CEREBRAS_API_KEY", "")
OLLAMA_URL          = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL        = os.getenv("OLLAMA_MODEL", "llama3.2")

# Claude modellek (Anthropic API)
CLAUDE_MODELEK = {
    "claude-sonnet-4-6":          "Claude Sonnet 4.6",
    "claude-opus-4-6":            "Claude Opus 4.6",
    "claude-haiku-4-5-20251001":  "Claude Haiku 4.5",
    "claude-sonnet-4-20250514":   "Claude Sonnet 4 (régi)",
}
CLAUDE_DEFAULT = "claude-sonnet-4-6"

OPENROUTER_MODELEK = {
    "anthropic/claude-sonnet-4-5":        "Claude Sonnet 4.5",
    "anthropic/claude-opus-4":            "Claude Opus 4",
    "google/gemini-2.0-flash":            "Gemini 2.0 Flash",
    "google/gemini-1.5-pro":              "Gemini 1.5 Pro",
    "google/gemma-2-27b-it":              "Gemma 2 27B",
    "meta-llama/llama-3.3-70b-versatile": "Llama 3.3 70B",
    "meta-llama/llama-3.2-3b-instruct":   "Llama 3.2 3B",
    "mistralai/mistral-large":            "Mistral Large",
    "deepseek/deepseek-r1":               "DeepSeek R1",
    "qwen/qwen-2.5-72b-instruct":         "Qwen 2.5 72B",
}

GEMINI_MODELEK = {
    "gemini-2.0-flash":  "Gemini 2.0 Flash",
    "gemini-1.5-pro":    "Gemini 1.5 Pro",
    "gemma-3-27b-it":    "Gemma 3 27B",
    "gemma-3-12b-it":    "Gemma 3 12B",
}

OPENAI_MODELEK = {
    "gpt-4o":       "GPT-4o",
    "gpt-4o-mini":  "GPT-4o Mini",
    "o1":           "o1",
    "o1-mini":      "o1 Mini",
    "o3-mini":      "o3 Mini",
}

GROQ_MODELEK = {
    "llama-3.3-70b-versatile":  "Llama 3.3 70B",
    "llama-3.1-70b-versatile":  "Llama 3.1 70B",
    "llama-3.1-8b-instant":     "Llama 3.1 8B Instant",
    "mixtral-8x7b-32768":       "Mixtral 8x7B",
    "gemma2-9b-it":             "Gemma 2 9B",
}

CEREBRAS_MODELEK = {
    "llama3.1-8b":   "Llama 3.1 8B",
    "llama3.1-70b":  "Llama 3.1 70B",
    "llama3.3-70b":  "Llama 3.3 70B",
}

# Provider → ENV kulcs + modell dict
PROVIDER_CONFIG = {
    "claude":      ("ANTHROPIC_API_KEY",  CLAUDE_MODELEK),
    "gemini":      ("GEMINI_API_KEY",     GEMINI_MODELEK),
    "openrouter":  ("OPENROUTER_API_KEY", OPENROUTER_MODELEK),
    "openai":      ("OPENAI_API_KEY",     OPENAI_MODELEK),
    "groq":        ("GROQ_API_KEY",       GROQ_MODELEK),
    "cerebras":    ("CEREBRAS_API_KEY",   CEREBRAS_MODELEK),
}

DB_KULCSSZAVAK = [
    "mit mondtam", "mikor mondtam", "mit írtam", "mikor írtam",
    "emlékszik", "emlékszel", "emlékezz", "keress", "keresd",
    "mi volt", "mi történt", "találd meg", "mutasd meg",
    "adatbázis", "napló", "bejegyzés", "korábban", "régebben",
    "tegnap", "múltkor", "tavaly", "az volt", "azt mondtam",
    "hogyan döntöttem", "mit határoztam", "what did i",
    "remember", "recall", "find in", "search", "when did",
]

def routing_dont(kerdes: str) -> str:
    k = kerdes.lower()
    for szo in DB_KULCSSZAVAK:
        if szo in k:
            return "db"
    return "mixed"


def auto_api_detect() -> str:
    # Prioritás: ha be van állítva API kulcs, azt használja
    # Claude kulcs elsőbbséget kap ha be van állítva
    if os.getenv("ANTHROPIC_API_KEY"):   return "claude"
    if os.getenv("GEMINI_API_KEY"):      return "gemini"
    if os.getenv("OPENROUTER_API_KEY"):  return "openrouter"
    if os.getenv("OPENAI_API_KEY"):      return "openai"
    if os.getenv("CEREBRAS_API_KEY"):   return "cerebras"
    if os.getenv("GROQ_API_KEY"):        return "groq"
    if _ollama_elerheto():               return "ollama"
    return "offline"


def _ollama_elerheto() -> bool:
    try:
        urllib.request.urlopen(f"{os.getenv('OLLAMA_URL','http://localhost:11434')}/api/tags", timeout=2)
        return True
    except Exception:
        return False


def _post(url, payload, headers):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise Exception(f"HTTP {e.code}: {e.read().decode()[:300]}")


def _get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise Exception(f"HTTP {e.code}: {e.read().decode()[:200]}")


def _modelek_leker(api: str) -> list:
    """Dinamikusan lekéri az adott provider elérhető modelljeit az API-tól."""
    key = os.getenv(PROVIDER_CONFIG[api][0], "") if api in PROVIDER_CONFIG else ""
    if not key and api not in ("ollama",):
        return []
    try:
        if api == "claude":
            r = _get("https://api.anthropic.com/v1/models",
                     {"x-api-key": key, "anthropic-version": "2023-06-01"})
            return [{"id": m["id"], "nev": m.get("display_name", m["id"]), "api": "claude"}
                    for m in r.get("data", [])
                    if m["id"].startswith("claude")]

        elif api == "gemini":
            r = _get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", {})
            return [{"id": m["name"].replace("models/", ""),
                     "nev": m.get("displayName", m["name"]),
                     "api": "gemini"}
                    for m in r.get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])]

        elif api in ("openai", "groq", "cerebras"):
            urls = {
                "openai":    "https://api.openai.com/v1/models",
                "groq":      "https://api.groq.com/openai/v1/models",
                "cerebras":  "https://api.cerebras.ai/v1/models",
            }
            r = _get(urls[api], {"Authorization": f"Bearer {key}"})
            modelek = []
            for m in sorted(r.get("data", []), key=lambda x: x["id"]):
                mid = m["id"]
                # Kizárjuk az embedding/whisper/tts modelleket
                if any(x in mid for x in ("embed", "whisper", "tts", "dall", "vision", "babbage", "davinci", "ada", "curie")):
                    continue
                modelek.append({"id": mid, "nev": mid, "api": api})
            return modelek

        elif api == "openrouter":
            r = _get("https://openrouter.ai/api/v1/models",
                     {"Authorization": f"Bearer {key}"})
            return [{"id": m["id"], "nev": m.get("name", m["id"]), "api": "openrouter"}
                    for m in r.get("data", [])]

        elif api == "ollama":
            r = _get(f"{os.getenv('OLLAMA_URL','http://localhost:11434')}/api/tags", {})
            return [{"id": m["name"], "nev": m["name"], "api": "ollama"}
                    for m in r.get("models", [])]

    except Exception as e:
        print(f"[Memex] Modell lekérés hiba ({api}): {e}")

    # Fallback: statikus lista
    if api in PROVIDER_CONFIG:
        _, model_dict = PROVIDER_CONFIG[api]
        return [{"id": mid, "nev": mnev, "api": api} for mid, mnev in model_dict.items()]
    return []


def _openrouter(system, user, model=""):
    key = os.getenv("OPENROUTER_API_KEY", "")
    model = OPENROUTER_MODELEK.get(model or OPENROUTER_MODEL, model or OPENROUTER_MODEL)
    r = _post("https://openrouter.ai/api/v1/chat/completions",
        {"model": model, "messages": [{"role":"system","content":system},{"role":"user","content":user}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}",
         "HTTP-Referer":"https://memex.local","X-Title":"Memex"})
    return r["choices"][0]["message"]["content"], r.get("id",""), model


def _claude(system, user, model=""):
    """Anthropic Claude API – direkt hívás"""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise Exception("ANTHROPIC_API_KEY nincs beállítva")
    # Ha model üres vagy nem Claude modell → default
    if not model or model not in CLAUDE_MODELEK:
        model = CLAUDE_DEFAULT
    print(f"[Memex] Claude model: {model}")
    r = _post(
        "https://api.anthropic.com/v1/messages",
        {
            "model": model,
            "max_tokens": 2048,
            "system": system,
            "messages": [{"role": "user", "content": user}]
        },
        {
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01"
        }
    )
    return r["content"][0]["text"], r.get("id",""), model


def _gemini(system, user, model=""):
    key = os.getenv("GEMINI_API_KEY", "")
    if not model:
        model = os.getenv("GEMINI_MODEL", "gemma-3-27b-it")
    r = _post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        {"contents":[{"parts":[{"text":f"{system}\n\n{user}"}]}]},
        {"Content-Type":"application/json"}
    )
    return r["candidates"][0]["content"]["parts"][0]["text"], "", model


def _groq(system, user, model=""):
    key = os.getenv("GROQ_API_KEY", "")
    if not model:
        model = "llama-3.3-70b-versatile"
    r = _post("https://api.groq.com/openai/v1/chat/completions",
        {"model":model,"messages":[{"role":"system","content":system},{"role":"user","content":user}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    return r["choices"][0]["message"]["content"], r.get("id",""), model


def _openai(system, user, model=""):
    key = os.getenv("OPENAI_API_KEY", "")
    if not model:
        model = "gpt-4o-mini"
    r = _post("https://api.openai.com/v1/chat/completions",
        {"model":model,"messages":[{"role":"system","content":system},{"role":"user","content":user}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    return r["choices"][0]["message"]["content"], r.get("id",""), model


def _cerebras(system, user, model=""):
    key = os.getenv("CEREBRAS_API_KEY", "")
    if not model:
        model = "llama3.1-8b"
    r = _post("https://api.cerebras.ai/v1/chat/completions",
        {"model":model,"messages":[{"role":"system","content":system},{"role":"user","content":user}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    return r["choices"][0]["message"]["content"], r.get("id",""), model


def _ollama(system, user, model=""):
    url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    mod = model or os.getenv("OLLAMA_MODEL", "llama3.2")
    r = _post(f"{url}/api/chat",
        {"model":mod,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"stream":False},
        {"Content-Type":"application/json"})
    return r["message"]["content"], "", mod



def _offline_keres(kerdes):
    t = keres(kerdes, limit=5)
    if not t:
        return f"[OFFLINE] Nincs találat: '{kerdes}'", "", "offline"
    return "[OFFLINE]\n" + "\n".join(f"[{x['idobelyeg'][:10]}] {x['tartalom']}" for x in t), "", "offline"


def _hatter_ment(kerdes, valasz, mnev, sid):
    try:
        a2a_id = a2a_session_nyit(mnev, f"kerdes: {kerdes[:50]}")
        bejegyez(f"K: {kerdes}", ["kerdes"], fontossag=4, iro="human")
        bejegyez(f"V: {valasz[:300]}", ["valasz"], fontossag=4, iro=mnev, a2a_id=sid or a2a_id)
        a2a_session_zar(a2a_id)
    except Exception as e:
        print(f"[Memex] Háttér mentés hiba: {e}")


def _ai_hivas(api, system, user, model):
    if   api == "openrouter": return _openrouter(system, user, model)
    elif api == "claude":     return _claude(system, user, model)
    elif api == "gemini":     return _gemini(system, user, model)
    elif api == "groq":       return _groq(system, user, model)
    elif api == "openai":     return _openai(system, user, model)
    elif api == "cerebras":   return _cerebras(system, user, model)
    elif api == "ollama":     return _ollama(system, user, model)
    else:                     return _offline_keres(user)


def python_hid(kerdes: str, api: str = "auto", model: str = "", explicit_routing: str = None) -> str:
    if api == "auto":
        api = auto_api_detect()

    routing = explicit_routing if explicit_routing else routing_dont(kerdes)
    print(f"[Memex] API: {api} | model: {model or 'default'} | routing: {routing}")

    talalatok = []
    if routing in ("db", "both", "mixed"):
        talalatok = keres(kerdes, limit=5)

    if routing == "db" and not talalatok:
        routing = "ai"
        print(f"[Memex] DB: nincs találat → AI")

    if routing == "ai":
        system = "Personal AI assistant. Respond in the user's language. Answer from your own knowledge only."
        user = f"Question: {kerdes}"
    elif routing == "db" and talalatok:
        system = system_prompt_build()
        user = "Answer ONLY from these personal memory records:\n\n"
        for t in talalatok:
            user += f"- [{t['idobelyeg'][:10]}] ({t.get('iro','human')}) {t['tartalom']}\n"
        user += f"\nQuestion: {kerdes}"
    else:
        system = system_prompt_build()
        user = f"Question: {kerdes}"
        if talalatok:
            user += "\n\nContext from memory:\n"
            for t in talalatok:
                user += f"- [{t['idobelyeg'][:10]}] ({t.get('iro','human')}) {t['tartalom']}\n"

    try:
        valasz, sid, mnev = _ai_hivas(api, system, user, model)
    except Exception as e:
        print(f"[Memex] Hiba ({api}): {e} → offline")
        valasz, sid, mnev = _offline_keres(kerdes)

    threading.Thread(target=_hatter_ment, args=(kerdes, valasz, mnev, sid), daemon=True).start()
    return valasz


def api_info() -> dict:
    return {
        "auto":             auto_api_detect(),
        "claude":           bool(os.getenv("ANTHROPIC_API_KEY")),
        "claude_default":   CLAUDE_DEFAULT,
        "gemini":           bool(os.getenv("GEMINI_API_KEY")),
        "openrouter":       bool(os.getenv("OPENROUTER_API_KEY")),
        "groq":             bool(os.getenv("GROQ_API_KEY")),
        "openai":           bool(os.getenv("OPENAI_API_KEY")),
        "cerebras":         bool(os.getenv("CEREBRAS_API_KEY")),
        "ollama":           _ollama_elerheto(),
        "offline":          True,
    }


def http_api_indit(host: str = "0.0.0.0", port: int = 8765):
    try:
        from fastapi import FastAPI, UploadFile, File
        from fastapi.responses import HTMLResponse, FileResponse
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
        from pydantic import BaseModel

        app = FastAPI(title="Memex", version="2.2")
        app.add_middleware(CORSMiddleware, allow_origins=["*"],
                           allow_methods=["*"], allow_headers=["*"])

        class KerdesInput(BaseModel):
            kerdes: str
            api: str = "auto"
            model: str = ""
            routing: str = "auto"

        class BejegyzesInput(BaseModel):
            tartalom: str
            horgonyok: list = []
            fontossag: int = 3
            tipus: str = ""
            iro: str = "human"
            a2a_id: str = ""

        class KulcsInput(BaseModel):
            tipus: str
            kulcs: str

        class ExportInput(BaseModel):
            jelszo: str = ""

        @app.get("/", response_class=HTMLResponse)
        def ui():
            ui_path = ROOT / "ui" / "index.html"
            if ui_path.exists():
                return HTMLResponse(ui_path.read_text(encoding="utf-8"))
            return HTMLResponse("<h1>Memex fut</h1>")

        @app.get("/app", response_class=HTMLResponse)
        @app.get("/app/", response_class=HTMLResponse)
        def pwa_index():
            p = ROOT / "app" / "index.html"
            if p.exists():
                return HTMLResponse(
                    p.read_text(encoding="utf-8"),
                    headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
                )
            return HTMLResponse("<h1>App mappa nem található</h1>", status_code=404)

        @app.get("/app/{fajlnev:path}")
        def pwa_fajl(fajlnev: str):
            p = ROOT / "app" / fajlnev
            if not p.exists() or not p.is_file():
                from fastapi import HTTPException
                raise HTTPException(404, "Nem található")
            # sw.js és index.html soha ne cache-eljen
            no_cache = fajlnev in ("sw.js", "index.html")
            headers = {"Cache-Control": "no-cache, no-store, must-revalidate"} if no_cache else {}
            return FileResponse(str(p), headers=headers)

        @app.post("/kerdes")
        def kerdes_ep(inp: KerdesInput):
            api = inp.api if inp.api != "auto" else auto_api_detect()
            # Ha a user explicit módot választott, azt használjuk; különben auto-detect
            routing = inp.routing if inp.routing in ("ai", "db", "both") else routing_dont(inp.kerdes)

            # ── AI MÓD: DB egyáltalán nem érintett ──────────────────────────
            if routing == "ai":
                system = "Personal AI assistant. Respond in the user's language. Answer from your own knowledge only."
                try:
                    valasz, sid, mnev = _ai_hivas(api, system, f"Question: {inp.kerdes}", inp.model)
                except Exception as e:
                    valasz = f"[AI hiba] {api} nem elérhető: {e}"
                    sid, mnev = "", api
                threading.Thread(target=_hatter_ment, args=(inp.kerdes, valasz, mnev, sid), daemon=True).start()
                return {"valasz": valasz, "routing": "ai"}

            # ── DB+AI MÓD: két külön hívás ──────────────────────────────────
            if routing in ("both", "mixed"):
                system_db = system_prompt_build()
                talalatok = keres(inp.kerdes, limit=5)
                db_valasz = None
                if talalatok:
                    db_user = "Answer ONLY from these personal memory records:\n\n"
                    for t in talalatok:
                        db_user += f"- [{t['idobelyeg'][:10]}] ({t.get('iro','human')}) {t['tartalom']}\n"
                    db_user += f"\nQuestion: {inp.kerdes}"
                    try:
                        db_valasz, _, _ = _ai_hivas(api, system_db, db_user, inp.model)
                    except Exception:
                        db_valasz = None
                ai_system = "Personal AI assistant. Respond in the user's language. Answer from your own knowledge only."
                try:
                    ai_valasz, ai_sid, ai_mnev = _ai_hivas(api, ai_system, f"Question: {inp.kerdes}", inp.model)
                except Exception:
                    ai_valasz, ai_sid, ai_mnev = _offline_keres(inp.kerdes)
                combined = (db_valasz + "\n\n" + ai_valasz) if db_valasz else ai_valasz
                threading.Thread(target=_hatter_ment, args=(inp.kerdes, combined, ai_mnev, ai_sid), daemon=True).start()
                return {"valasz": combined, "db_valasz": db_valasz, "ai_valasz": ai_valasz, "routing": "both"}

            # ── DB MÓD ──────────────────────────────────────────────────────
            valasz = python_hid(inp.kerdes, api, inp.model, explicit_routing="db")
            return {"valasz": valasz, "routing": "db"}

        @app.post("/bejegyez")
        def bejegyez_ep(inp: BejegyzesInput):
            sorszam = bejegyez(inp.tartalom, inp.horgonyok,
                               inp.fontossag, inp.tipus, inp.iro, inp.a2a_id)
            return {"sorszam": sorszam, "status": "ok"}

        @app.get("/keres")
        def keres_ep(q: str, limit: int = 10, iro: str = ""):
            return {"talalatok": keres(q, limit, iro_filter=iro)}

        @app.get("/info")
        def info():
            return api_info()

        @app.get("/stat")
        def stat_ep():
            try:
                import sqlite3
                db_path = ROOT / "db" / "memex.db"
                con = sqlite3.connect(str(db_path))
                cur = con.cursor()
                ossz  = cur.execute("SELECT COUNT(*) FROM bejegyzesek").fetchone()[0]
                human = cur.execute("SELECT COUNT(*) FROM bejegyzesek WHERE iro='human'").fetchone()[0]
                ai_db = ossz - human
                con.close()
                meret_kb = round(db_path.stat().st_size / 1024, 1) if db_path.exists() else 0
                return {"ossz": ossz, "human": human, "ai": ai_db, "meret_kb": meret_kb}
            except Exception as e:
                return {"ossz": 0, "human": 0, "ai": 0, "meret_kb": 0, "hiba": str(e)}

        @app.get("/irok")
        def irok_ep():
            return {"irok": iro_statisztika()}

        @app.get("/modelek_lista")
        def modelek_lista_ep(api: str = ""):
            aktiv_api = auto_api_detect()
            api_filter = api if api else aktiv_api
            modelek = _modelek_leker(api_filter)
            return {"modelek": modelek, "auto_api": aktiv_api}

        @app.post("/api_kulcs")
        def api_kulcs_ment(inp: KulcsInput):
            kulcs_map = {p: cfg[0] for p, cfg in PROVIDER_CONFIG.items()}
            env_nev = kulcs_map.get(inp.tipus)
            if not env_nev:
                return {"error": "Ismeretlen tipus"}
            env_path = ROOT / ".env"
            sorok = env_path.read_text().splitlines() if env_path.exists() else []
            uj = []; talalt = False
            for sor in sorok:
                if sor.startswith(f"{env_nev}="):
                    uj.append(f"{env_nev}={inp.kulcs}"); talalt = True
                else:
                    uj.append(sor)
            if not talalt:
                uj.append(f"{env_nev}={inp.kulcs}")
            env_path.write_text("\n".join(uj) + "\n")
            os.environ[env_nev] = inp.kulcs
            print(f"[Memex] API kulcs mentve: {env_nev}")
            return {"status": "ok", "tipus": inp.tipus}

        @app.get("/uuid")
        def uuid_ep():
            return {"uuid": uuid_get()}

        @app.post("/export")
        def export_ep(inp: ExportInput):
            try:
                fajl = export_memex(inp.jelszo)
                return {"status": "ok", "fajl": fajl.name,
                        "meret_kb": round(fajl.stat().st_size / 1024, 1),
                        "letoltes": f"/export_letoltes/{fajl.name}"}
            except Exception as e:
                return {"status": "hiba", "uzenet": str(e)}

        @app.get("/export_letoltes/{fajlnev}")
        def export_letoltes(fajlnev: str):
            fajl = ROOT / "exports" / fajlnev
            if not fajl.exists():
                return {"hiba": "Fájl nem található"}
            return FileResponse(path=str(fajl), filename=fajlnev,
                                media_type="application/octet-stream")

        @app.post("/import")
        async def import_ep(eroszak: bool = False, jelszo: str = "", fajl: UploadFile = File(...)):
            try:
                tmp = ROOT / "exports" / f"import_tmp_{fajl.filename}"
                tmp.write_bytes(await fajl.read())
                ok = import_memex(str(tmp), jelszo, eroszak)
                tmp.unlink(missing_ok=True)
                if ok:
                    return {"status": "ok", "uzenet": "Adatbázis sikeresen importálva"}
                else:
                    return {"status": "hiba", "uzenet": "Rossz jelszó vagy eltérő UUID"}
            except Exception as e:
                return {"status": "hiba", "uzenet": str(e)}

        @app.post("/uj_adatbazis")
        def uj_adatbazis_ep():
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("DELETE FROM naplo")
                c.execute("DELETE FROM naplo_fts")
                c.execute("DELETE FROM horgony_stat")
                c.execute("DELETE FROM iro_stat")
                c.execute("DELETE FROM a2a_session")
                conn.commit()
                conn.close()
                return {"status": "ok", "uzenet": "Új adatbázis létrehozva"}
            except Exception as e:
                return {"status": "hiba", "uzenet": str(e)}

        @app.get("/export_lista")
        def export_lista_ep():
            exp_dir = ROOT / "exports"
            exp_dir.mkdir(exist_ok=True)
            fajlok = sorted(exp_dir.glob("*.memex"), reverse=True)
            return {"exportok": [{"nev": f.name,
                                   "meret_kb": round(f.stat().st_size / 1024, 1),
                                   "letoltes": f"/export_letoltes/{f.name}"}
                                  for f in fajlok]}

        @app.get("/prompt")
        def prompt_ep():
            return {"prompt": system_prompt_build()}

        @app.get("/horgonyok")
        def horgonyok_ep():
            return {"horgonyok": horgony_lista()}

        @app.get("/modelek")
        def modelek_ep():
            return {"modelek": OPENROUTER_MODELEK}

        print(f"\n  Memex UI:    http://localhost:{port}")
        print(f"  Hálózaton:   http://192.168.0.64:{port}")
        print(f"  API docs:    http://localhost:{port}/docs")
        uvicorn.run(app, host=host, port=port, log_level="warning")

    except ImportError:
        print("Telepítsd: pip install fastapi uvicorn python-multipart --break-system-packages")
        sys.exit(1)


def mcp_indit():
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Tool, TextContent
        import asyncio

        server = Server("memex")

        @server.list_tools()
        async def tools():
            return [
                Tool(name="memex_kerdes", description="Kerdes a Memex szemelyes memoriahoz",
                     inputSchema={"type":"object","properties":{"kerdes":{"type":"string"},"api":{"type":"string","default":"auto"},"model":{"type":"string","default":""},"routing":{"type":"string","default":"auto"}},"required":["kerdes"]}),
                Tool(name="memex_bejegyez", description="Uj bejegyzes a Memexbe",
                     inputSchema={"type":"object","properties":{"tartalom":{"type":"string"},"fontossag":{"type":"integer","default":3},"iro":{"type":"string","default":"human"}},"required":["tartalom"]}),
                Tool(name="memex_keres", description="Kereses az adatbazisban",
                     inputSchema={"type":"object","properties":{"q":{"type":"string"},"iro":{"type":"string","default":""}},"required":["q"]}),
                Tool(name="memex_info", description="Memex statusz",
                     inputSchema={"type":"object","properties":{}}),
            ]

        @server.call_tool()
        async def tool_hivas(name, arguments):
            if name == "memex_kerdes":
                v = python_hid(arguments["kerdes"], arguments.get("api","auto"),
                               arguments.get("model",""), arguments.get("routing",None))
                return [TextContent(type="text", text=v)]
            elif name == "memex_bejegyez":
                s = bejegyez(arguments["tartalom"], fontossag=arguments.get("fontossag",3),
                             iro=arguments.get("iro","human"))
                return [TextContent(type="text", text=f"Mentve: #{s}")]
            elif name == "memex_keres":
                t = keres(arguments["q"], iro_filter=arguments.get("iro",""))
                return [TextContent(type="text", text="\n".join(
                    f"[{x['idobelyeg'][:10]}] ({x.get('iro','?')}) {x['tartalom']}"
                    for x in t) or "Nincs talalat")]
            elif name == "memex_info":
                return [TextContent(type="text", text=json.dumps(api_info(), ensure_ascii=False, indent=2))]

        print("[MCP] Memex MCP szerver indul...")
        asyncio.run(stdio_server(server))

    except ImportError:
        print("Telepítsd: pip install mcp --break-system-packages")
        sys.exit(1)


if __name__ == "__main__":
    init_db()

    parser = argparse.ArgumentParser(description="Memex Gateway v2.2")
    parser.add_argument("--mod",    choices=["python","api","mcp"], default="python")
    parser.add_argument("--kerdes", type=str)
    parser.add_argument("--api",    type=str, default="auto")
    parser.add_argument("--model",  type=str, default="")
    parser.add_argument("--port",   type=int, default=8765)
    args = parser.parse_args()

    if args.mod == "python":
        info = api_info()
        print("\n--- API statusz ---")
        for k, v in info.items():
            if k not in ("modelek","claude_modelek"): print(f"  {k}: {v}")
        kerdes = args.kerdes or "Mit tudok a Memex projektrol?"
        print(f"\n--- Kerdes: {kerdes} ---\n")
        print(python_hid(kerdes, args.api, args.model))

    elif args.mod == "api":
        http_api_indit(port=args.port)

    elif args.mod == "mcp":
        mcp_indit()
