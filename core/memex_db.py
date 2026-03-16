"""
Memex - Personal AI Memory Database
Core layer: SQLite + FTS5
Zero external dependencies

Réteg rendszer:
    fontossag:  1=kritikus 2=fontos 3=normál 4=duma
    tipus:      #python #c @projekt !döntés !hiba !ötlet
    horgonyok:  szabad, AI generálja automatikusan
    iró:        ki írta - "human" | "claude-sonnet" | "gemini-2.0" | "llama-70b" stb.
    a2a_id:     Agent2Agent azonosító - melyik agent session írta
"""

import sqlite3
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "db" / "memex.db"


# ── Ismert AI azonosítók ──────────────────────────────────────────────────────
# Ezeket ismeri fel a rendszer automatikusan
AI_AZONOSITOK = {
    # Anthropic
    "claude-sonnet-4-20250514":  "claude-sonnet-4",
    "claude-opus-4-20250514":    "claude-opus-4",
    "claude-haiku-4-5":          "claude-haiku-4",
    # Google
    "gemini-2.0-flash":          "gemini-2.0-flash",
    "gemini-1.5-pro":            "gemini-1.5-pro",
    "gemma-27b":                 "gemma-27b",
    # Meta / Groq
    "llama-3.3-70b-versatile":   "llama-70b",
    "llama-3.2-3b":              "llama-3b",
    "llama3.2":                  "llama-3.2",
    # OpenAI
    "gpt-4o":                    "gpt-4o",
    "gpt-4o-mini":               "gpt-4o-mini",
    # Emberi
    "human":                     "human",
    "system":                    "system",
}


def ai_nev_normalizal(model: str) -> str:
    """API model nevet rövid azonosítóra normalizál"""
    return AI_AZONOSITOK.get(model, model or "human")


# ── Automatikus horgony generálás ─────────────────────────────────────────────

ISMERT_DOMAIN = {
    "python":            ["python", "def ", "import ", "pip ", ".py"],
    "javascript":        ["javascript", "js", "node", "npm", "const ", "let "],
    "c":                 ["malloc", "printf", "gcc", " int ", "->", ".c ", ".h "],
    "rust":              ["rust", "cargo", "fn ", "let mut", "unwrap"],
    "sql":               ["select ", "insert ", "update ", "delete ", "sqlite"],
    "méhészet":          ["méh", "keret", "méz", "anyaméh", "raj", "lép", "kaptár"],
    "tehénészet":        ["tehén", "borjú", "tőgy", "takarmány", "ellés", "fejés"],
    "növénytermesztés":  ["vetés", "aratás", "búza", "kukorica", "trágyázás"],
    "szőlészet":         ["szőlő", "bor", "metszés", "szüret", "must"],
    "egészség":          ["orvos", "gyógyszer", "beteg", "tünet", "vérvétel"],
    "döntés":            ["döntöttem", "úgy döntöttük", "elhatároztuk"],
    "probléma":          ["hiba", "nem működik", "probléma", "gond"],
    "megoldás":          ["megoldottam", "sikerült", "működik", "javítottam"],
    "ötlet":             ["ötlet", "mi lenne ha", "lehetne", "próbáljuk"],
}


def auto_horgony(tartalom: str, meglevo: list = None) -> list:
    horgonyok = set(meglevo or [])
    tartalom_lower = tartalom.lower()
    for domain, kulcsszavak in ISMERT_DOMAIN.items():
        for kw in kulcsszavak:
            if kw.lower() in tartalom_lower:
                horgonyok.add(domain)
                break
    if re.search(r'\d{4}[-./]\d{2}[-./]\d{2}', tartalom):
        horgonyok.add("dátum")
    if re.search(r'\d+\s*(kg|liter|méter|km|db|ft|eur|usd)', tartalom_lower):
        horgonyok.add("mérték")
    return sorted(list(horgonyok))


def tipus_felismer(tartalom: str) -> str:
    tartalom_lower = tartalom.lower()
    match = re.search(r'[#@!]\w+', tartalom)
    if match:
        return match.group(0)
    if any(kw in tartalom_lower for kw in ["döntöttük", "elhatároztuk"]):
        return "!döntés"
    if any(kw in tartalom_lower for kw in ["hiba", "nem működik", "error", "failed"]):
        return "!hiba"
    if any(kw in tartalom_lower for kw in ["ötlet", "mi lenne ha", "lehetne"]):
        return "!ötlet"
    if any(kw in tartalom_lower for kw in ["def ", "import ", ".py"]):
        return "#python"
    if any(kw in tartalom_lower for kw in ["malloc", "printf", "gcc"]):
        return "#c"
    if any(kw in tartalom_lower for kw in ["méh", "kaptár", "méz"]):
        return "@méhészet"
    if any(kw in tartalom_lower for kw in ["tehén", "borjú", "tőgy"]):
        return "@tehénészet"
    return ""


# ── Adatbázis ─────────────────────────────────────────────────────────────────

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS naplo (
            sorszam     INTEGER PRIMARY KEY AUTOINCREMENT,
            idobelyeg   TEXT NOT NULL,
            tartalom    TEXT NOT NULL,
            horgonyok   TEXT,
            tipus       TEXT DEFAULT '',
            fontossag   INTEGER DEFAULT 3,
            iro         TEXT DEFAULT 'human',
            a2a_id      TEXT DEFAULT '',
            hash        TEXT NOT NULL,
            torolve     INTEGER DEFAULT 0
        )
    """)

    # Migrációk - régi DB-re is működik
    for mezo, definicio in [
        ("tipus",    "TEXT DEFAULT ''"),
        ("iro",      "TEXT DEFAULT 'human'"),
        ("a2a_id",   "TEXT DEFAULT ''"),
    ]:
        try:
            c.execute(f"ALTER TABLE naplo ADD COLUMN {mezo} {definicio}")
        except Exception:
            pass

    c.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS naplo_fts
        USING fts5(
            tartalom,
            horgonyok,
            tipus,
            iro,
            content='naplo',
            content_rowid='sorszam',
            tokenize='unicode61'
        )
    """)

    c.execute("DROP TRIGGER IF EXISTS naplo_fts_insert")
    c.execute("""
        CREATE TRIGGER naplo_fts_insert
        AFTER INSERT ON naplo BEGIN
            INSERT INTO naplo_fts(rowid, tartalom, horgonyok, tipus, iro)
            VALUES (new.sorszam, new.tartalom, new.horgonyok, new.tipus, new.iro);
        END
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS nevjegy (
            kulcs   TEXT PRIMARY KEY,
            ertek   TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS horgony_stat (
            horgony     TEXT PRIMARY KEY,
            darab       INTEGER DEFAULT 1,
            utolso      TEXT
        )
    """)

    # AI azonosító statisztika
    c.execute("""
        CREATE TABLE IF NOT EXISTS iro_stat (
            iro         TEXT PRIMARY KEY,
            darab       INTEGER DEFAULT 1,
            elso        TEXT,
            utolso      TEXT
        )
    """)

    # A2A session tábla
    c.execute("""
        CREATE TABLE IF NOT EXISTS a2a_session (
            a2a_id      TEXT PRIMARY KEY,
            ai_nev      TEXT NOT NULL,
            indult      TEXT NOT NULL,
            lezarult    TEXT,
            leiras      TEXT
        )
    """)

    conn.commit()
    conn.close()
    print(f"Memex database ready: {DB_PATH}")


def a2a_session_nyit(ai_nev: str, leiras: str = "") -> str:
    """
    Új A2A session nyitása.
    Visszaad egy egyedi session ID-t amit az AI az összes bejegyzésébe belerak.
    """
    idobelyeg = datetime.now().isoformat()
    a2a_id = hashlib.sha256(f"{ai_nev}{idobelyeg}".encode()).hexdigest()[:16]

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO a2a_session (a2a_id, ai_nev, indult, leiras)
        VALUES (?, ?, ?, ?)
    """, (a2a_id, ai_nev, idobelyeg, leiras))
    conn.commit()
    conn.close()
    return a2a_id


def a2a_session_zar(a2a_id: str):
    """A2A session lezárása"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE a2a_session SET lezarult = ? WHERE a2a_id = ?",
              (datetime.now().isoformat(), a2a_id))
    conn.commit()
    conn.close()


def bejegyez(tartalom: str, horgonyok: list = None,
             fontossag: int = 3, tipus: str = "",
             iro: str = "human", a2a_id: str = "") -> int:
    """
    Add new entry - APPEND ONLY, never editable.

    iro:    ki írta - "human" | model neve pl "claude-sonnet-4" | "llama-70b"
    a2a_id: Agent2Agent session ID - melyik agent session írta (opcionális)
    """
    idobelyeg = datetime.now().isoformat()
    iro = ai_nev_normalizal(iro)
    horgonyok = auto_horgony(tartalom, horgonyok)
    if not tipus:
        tipus = tipus_felismer(tartalom)

    horgonyok_json = json.dumps(horgonyok, ensure_ascii=False)
    hash_alap = f"{idobelyeg}{tartalom}{horgonyok_json}{iro}"
    hash_ertek = hashlib.sha256(hash_alap.encode()).hexdigest()

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO naplo (idobelyeg, tartalom, horgonyok, tipus, fontossag, iro, a2a_id, hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (idobelyeg, tartalom, horgonyok_json, tipus, fontossag, iro, a2a_id, hash_ertek))
    sorszam = c.lastrowid

    # Horgony statisztika
    for h in horgonyok:
        c.execute("""
            INSERT INTO horgony_stat (horgony, darab, utolso)
            VALUES (?, 1, ?)
            ON CONFLICT(horgony) DO UPDATE SET
                darab = darab + 1, utolso = excluded.utolso
        """, (h, idobelyeg))

    # Író statisztika
    c.execute("""
        INSERT INTO iro_stat (iro, darab, elso, utolso)
        VALUES (?, 1, ?, ?)
        ON CONFLICT(iro) DO UPDATE SET
            darab = darab + 1, utolso = excluded.utolso
    """, (iro, idobelyeg, idobelyeg))

    conn.commit()
    conn.close()
    return sorszam


def torol(sorszam: int) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE naplo SET torolve = 1 WHERE sorszam = ?", (sorszam,))
    conn.commit()
    conn.close()
    return True


def _fts_query(kerdes: str) -> str:
    szavak = [s.strip() for s in kerdes.split() if s.strip()]
    if len(szavak) == 1:
        return szavak[0]
    return " OR ".join(f'"{s}"' for s in szavak)


def keres(kerdes: str, limit: int = 10,
          tipus_filter: str = "", horgony_filter: str = "",
          iro_filter: str = "") -> list:
    """
    Full text search.
    iro_filter: pl "claude-sonnet-4" - csak Claude által írt bejegyzések
    """
    conn = get_connection()
    c = conn.cursor()
    fts_q = _fts_query(kerdes)

    try:
        extra = ""
        params = [fts_q, limit]

        if tipus_filter:
            extra += " AND n.tipus = ?"
            params.insert(-1, tipus_filter)
        if horgony_filter:
            extra += " AND n.horgonyok LIKE ?"
            params.insert(-1, f"%{horgony_filter}%")
        if iro_filter:
            extra += " AND n.iro = ?"
            params.insert(-1, iro_filter)

        c.execute(f"""
            SELECT n.sorszam, n.idobelyeg, n.tartalom,
                   n.horgonyok, n.tipus, n.fontossag, n.iro, n.a2a_id
            FROM naplo n
            JOIN naplo_fts f ON n.sorszam = f.rowid
            WHERE naplo_fts MATCH ?
            AND n.torolve = 0
            {extra}
            ORDER BY n.fontossag ASC, rank, n.sorszam DESC
            LIMIT ?
        """, params)
        return [dict(r) for r in c.fetchall()]

    except Exception:
        c.execute("""
            SELECT sorszam, idobelyeg, tartalom, horgonyok, tipus, fontossag, iro, a2a_id
            FROM naplo
            WHERE (tartalom LIKE ? OR horgonyok LIKE ?)
            AND torolve = 0
            ORDER BY fontossag ASC, sorszam DESC
            LIMIT ?
        """, (f"%{kerdes}%", f"%{kerdes}%", limit))
        return [dict(r) for r in c.fetchall()]
    finally:
        conn.close()


def legutobbi(limit: int = 20, kizar_chat: bool = False) -> list:
    conn = get_connection()
    c = conn.cursor()
    if kizar_chat:
        c.execute("""
            SELECT sorszam, idobelyeg, tartalom, horgonyok, tipus, fontossag, iro, a2a_id
            FROM naplo WHERE torolve = 0
            AND tartalom NOT LIKE 'K: %'
            AND tartalom NOT LIKE 'V: %'
            AND fontossag < 4
            ORDER BY sorszam DESC LIMIT ?
        """, (limit,))
    else:
        c.execute("""
            SELECT sorszam, idobelyeg, tartalom, horgonyok, tipus, fontossag, iro, a2a_id
            FROM naplo WHERE torolve = 0
            ORDER BY sorszam DESC LIMIT ?
        """, (limit,))
    result = [dict(r) for r in c.fetchall()]
    conn.close()
    return result


def legfontosabb(limit: int = 10) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT sorszam, idobelyeg, tartalom, horgonyok, tipus, fontossag, iro, a2a_id
        FROM naplo WHERE torolve = 0 AND fontossag = 1
        ORDER BY sorszam DESC LIMIT ?
    """, (limit,))
    result = [dict(r) for r in c.fetchall()]
    conn.close()
    return result


def iro_statisztika() -> list:
    """Ki írt bele és mennyit - AI audit napló"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT iro, darab, elso, utolso FROM iro_stat ORDER BY darab DESC")
    result = [dict(r) for r in c.fetchall()]
    conn.close()
    return result


def horgony_lista() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT horgony, darab FROM horgony_stat ORDER BY darab DESC")
    result = [dict(r) for r in c.fetchall()]
    conn.close()
    return result


def nevjegy_set(kulcs: str, ertek: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO nevjegy (kulcs, ertek) VALUES (?, ?)",
              (kulcs, ertek))
    conn.commit()
    conn.close()


def nevjegy_get() -> dict:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT kulcs, ertek FROM nevjegy")
    result = {r["kulcs"]: r["ertek"] for r in c.fetchall()}
    conn.close()
    return result


def system_prompt_build() -> str:
    nevjegy = nevjegy_get()
    fontos = legfontosabb(3)
    utobbi = legutobbi(5, kizar_chat=True)
    horgonyok = horgony_lista()[:10]

    prompt = "=== WHO I AM ===\n"
    for k, v in nevjegy.items():
        prompt += f"{k}: {v[:100]}\n"

    prompt += "\nPersonal AI assistant. Respond in user's language.\n"

    if horgonyok:
        prompt += "\nTopics: " + ", ".join(f"{h['horgony']}({h['darab']}x)" for h in horgonyok) + "\n"

    if fontos:
        prompt += "\n=== CRITICAL ===\n"
        for b in fontos:
            prompt += f"[{b['idobelyeg'][:10]}] {b['tartalom'][:150]}\n"

    if utobbi:
        prompt += "\n=== RECENT ===\n"
        for b in utobbi[:3]:
            prompt += f"[{b['idobelyeg'][:10]}] {b['tartalom'][:150]}\n"

    return prompt[:4000]


def system_prompt_epitek() -> str:
    return system_prompt_build()


if __name__ == "__main__":
    init_db()

    # Teszt - különböző írók
    print("--- Human bejegyzés ---")
    bejegyez("Ma kiszedtem a keretet, sárga méz volt", fontossag=2, iro="human")

    print("--- Claude írja ---")
    sid = a2a_session_nyit("claude-sonnet-4", "Méhészeti tanácsadás")
    bejegyez("Az anyaméh tojási aktivitása normális tavasszal",
             fontossag=3, iro="claude-sonnet-4-20250514", a2a_id=sid)
    a2a_session_zar(sid)

    print("--- Llama írja ---")
    bejegyez("A tehén ellés előtt 24 órával általában étvágytalanná válik",
             fontossag=3, iro="llama-3.3-70b-versatile")

    print("\n--- Ki írt bele? ---")
    for i in iro_statisztika():
        print(f"  {i['iro']}: {i['darab']} bejegyzés")

    print("\n--- Keresés csak Claude bejegyzéseiben ---")
    for r in keres("anyaméh", iro_filter="claude-sonnet-4"):
        print(f"  [{r['iro']}] {r['tartalom']}")
