
def http_api_indit(host: str = "0.0.0.0", port: int = 8765):
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse, JSONResponse
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
        from pydantic import BaseModel

        app = FastAPI(title="Memex API", version="2.1")

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        class KerdesInput(BaseModel):
            kerdes: str
            api: str = "auto"
            model: str = ""
            routing: str = "auto"   # ← FIX: routing mező hozzáadva

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

        # ── UI ────────────────────────────────────────────────────────────────

        @app.get("/", response_class=HTMLResponse)
        def ui():
            ui_path = ROOT / "ui" / "index.html"
            if ui_path.exists():
                return ui_path.read_text(encoding="utf-8")
            return HTMLResponse("<h1>Memex API fut</h1><p>UI: ui/index.html hiányzik</p>")

        # ── API kulcs mentés ──────────────────────────────────────────────────

        @app.post("/api_kulcs")
        def api_kulcs_ment(inp: KulcsInput):
            env_path = ROOT / ".env"
            kulcs_map = {
                "openrouter": "OPENROUTER_API_KEY",
                "claude":     "ANTHROPIC_API_KEY",
                "gemini":     "GEMINI_API_KEY",
                "groq":       "GROQ_API_KEY",
                "openai":     "OPENAI_API_KEY",
            }
            env_nev = kulcs_map.get(inp.tipus)
            if not env_nev:
                return JSONResponse({"error": "Ismeretlen API tipus"}, status_code=400)

            sorok = []
            if env_path.exists():
                sorok = env_path.read_text().splitlines()

            talalt = False
            uj_sorok = []
            for sor in sorok:
                if sor.startswith(f"{env_nev}="):
                    uj_sorok.append(f"{env_nev}={inp.kulcs}")
                    talalt = True
                else:
                    uj_sorok.append(sor)

            if not talalt:
                uj_sorok.append(f"{env_nev}={inp.kulcs}")

            env_path.write_text("\n".join(uj_sorok) + "\n")
            os.environ[env_nev] = inp.kulcs

            global OPENROUTER_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
            global GROQ_API_KEY, OPENAI_API_KEY
            if env_nev == "OPENROUTER_API_KEY":  OPENROUTER_API_KEY = inp.kulcs
            if env_nev == "ANTHROPIC_API_KEY":   ANTHROPIC_API_KEY  = inp.kulcs
            if env_nev == "GEMINI_API_KEY":      GEMINI_API_KEY     = inp.kulcs
            if env_nev == "GROQ_API_KEY":        GROQ_API_KEY       = inp.kulcs
            if env_nev == "OPENAI_API_KEY":      OPENAI_API_KEY     = inp.kulcs

            return {"status": "ok", "tipus": inp.tipus, "mentve": env_path.name}

        # ── Alap endpointok ───────────────────────────────────────────────────

        @app.get("/info")
        def info():
            return api_info()

        @app.post("/kerdes")
        def kerdes_ep(inp: KerdesInput):
            # ← FIX: routing átadva a python_hid-nek
            explicit = inp.routing if inp.routing not in ("auto", "") else None
            valasz = python_hid(inp.kerdes, inp.api, inp.model, explicit_routing=explicit)
            return {"kerdes": inp.kerdes, "valasz": valasz}

        @app.post("/bejegyez")
        def bejegyez_ep(inp: BejegyzesInput):
            sorszam = bejegyez(
                inp.tartalom, inp.horgonyok,
                inp.fontossag, inp.tipus,
                inp.iro, inp.a2a_id
            )
            return {"sorszam": sorszam, "status": "ok"}

        @app.get("/keres")
        def keres_ep(q: str, limit: int = 20, iro: str = ""):
            return {"talalatok": keres(q, limit, iro_filter=iro)}

        @app.get("/irok")
        def irok_ep():
            return {"irok": iro_statisztika()}

        @app.get("/stat")
        def stat_ep():
            """DB statisztika: bejegyzés szám, írók, meret"""
            import sqlite3
            db_path = ROOT / "db" / "memex.db"
            try:
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM bejegyzesek")
                ossz = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM bejegyzesek WHERE iro='human'")
                human = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM bejegyzesek WHERE iro!='human'")
                ai_db = c.fetchone()[0]
                conn.close()
                meret_kb = round(db_path.stat().st_size / 1024, 1) if db_path.exists() else 0
                return {
                    "ossz": ossz,
                    "human": human,
                    "ai": ai_db,
                    "meret_kb": meret_kb
                }
            except Exception as e:
                return {"ossz": 0, "human": 0, "ai": 0, "meret_kb": 0, "hiba": str(e)}

        @app.get("/modelek_lista")
        def modelek_lista_ep():
            """Elérhető modellek listája"""
            modelek = [
                {"id": "gemma-3-27b-it",           "nev": "Gemma 3 27B",        "limit": "ingyenes"},
                {"id": "gemini-2.0-flash",          "nev": "Gemini 2.0 Flash",   "limit": "ingyenes"},
                {"id": "gemini-1.5-pro",            "nev": "Gemini 1.5 Pro",     "limit": "ingyenes"},
                {"id": "gemma-3-12b-it",            "nev": "Gemma 3 12B",        "limit": "ingyenes"},
            ]
            return {"modelek": modelek, "aktualis": os.getenv("GEMINI_MODEL", "gemma-3-27b-it")}

        @app.get("/prompt")
        def prompt_ep():
            return {"prompt": system_prompt_build()}

        @app.get("/horgonyok")
        def horgonyok_ep():
            return {"horgonyok": horgony_lista()}

        @app.get("/modelek")
        def modelek_ep():
            return {"modelek": OPENROUTER_MODELEK}

        print(f"\n Memex UI:  http://localhost:{port}")
        print(f"   API docs: http://localhost:{port}/docs")
        print(f"   Hálózaton: http://192.168.0.64:{port}")
        uvicorn.run(app, host=host, port=port, log_level="warning")

    except ImportError:
        print("Telepítsd: pip install fastapi uvicorn --break-system-packages")
        sys.exit(1)
