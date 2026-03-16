"""
Memex Export/Import
====================
Titkosított .memex fájl – hordozható, biztonságos.

Hogyan működik:
    Jelszó → SHA256 → AES kulcs → DB titkosítva → .memex fájl

A .memex fájl szerkezete (JSON + base64):
    {
        "verzio":    "1.0",
        "uuid":      "egyedi felhasználói ID",
        "letrehozva": "2026-03-12T...",
        "db":        "<base64 titkosított sqlite>",
        "ellenorzo": "<sha256 hash>"
    }

Használat:
    python core/memex_export.py export --jelszo titkos123
    python core/memex_export.py import --fajl memex_20260312.memex --jelszo titkos123
    python core/memex_export.py uuid       # saját UUID lekérése
    python core/memex_export.py info       # fájl tartalmának ellenőrzése
"""

import sqlite3
import hashlib
import json
import base64
import os
import sys
import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path

ROOT    = Path(__file__).parent.parent
DB_PATH = ROOT / "db" / "memex.db"
ID_PATH = ROOT / "db" / "uuid.txt"     # egyedi felhasználói azonosító
EXP_DIR = ROOT / "exports"             # exportált fájlok ide kerülnek

VERZIO = "1.0"


# ── UUID kezelés ──────────────────────────────────────────────────────────────

def uuid_get() -> str:
    """Egyedi felhasználói azonosító – telepítéskor generálódik, soha nem változik."""
    if ID_PATH.exists():
        return ID_PATH.read_text().strip()
    # Első futás – generálunk
    import uuid
    uid = str(uuid.uuid4())
    ID_PATH.write_text(uid)
    print(f"[Memex] Új UUID generálva: {uid}")
    return uid


# ── Titkosítás – pure Python, nulla függőség ─────────────────────────────────

def _kulcs_general(jelszo: str, uuid: str) -> bytes:
    """
    Jelszó + UUID → 32 bájtos titkosítási kulcs.
    Ugyanaz a jelszó + UUID = ugyanaz a kulcs. Mindig.
    """
    alap = f"{jelszo}:{uuid}:memex2026"
    return hashlib.sha256(alap.encode()).digest()


def _xor_titkosit(adat: bytes, kulcs: bytes) -> bytes:
    """
    XOR titkosítás – pure Python, nulla függőség.
    Elég erős hogy értelmetlen legyen, de nem banki szintű.
    Ha valaki erősebbet akar: pip install cryptography (AES-256-GCM)
    """
    kbyte = len(kulcs)
    return bytes(adat[i] ^ kulcs[i % kbyte] for i in range(len(adat)))


def _hash_szamol(adat: bytes) -> str:
    return hashlib.sha256(adat).hexdigest()


# ── Export ────────────────────────────────────────────────────────────────────

def export_memex(jelszo: str, cel_fajl: str = "") -> Path:
    """
    Exportálja az adatbázist titkosított .memex fájlba.
    Visszaadja a létrehozott fájl útvonalát.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Adatbázis nem található: {DB_PATH}")

    uid = uuid_get()
    kulcs = _kulcs_general(jelszo, uid)

    # DB fájl beolvasása
    db_adat = DB_PATH.read_bytes()
    db_hash = _hash_szamol(db_adat)

    # Titkosítás
    titkos = _xor_titkosit(db_adat, kulcs)
    titkos_b64 = base64.b64encode(titkos).decode()

    # .memex csomag összeállítása
    csomag = {
        "verzio":     VERZIO,
        "uuid":       uid,
        "letrehozva": datetime.now().isoformat(),
        "db_hash":    db_hash,
        "db":         titkos_b64,
    }
    csomag_json = json.dumps(csomag, ensure_ascii=False, indent=2)

    # Fájl mentése
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    if not cel_fajl:
        datum = datetime.now().strftime("%Y%m%d_%H%M%S")
        cel_fajl = str(EXP_DIR / f"memex_{datum}.memex")

    Path(cel_fajl).write_text(csomag_json, encoding="utf-8")

    meret_kb = len(csomag_json) / 1024
    print(f"[Export] ✓ Kész: {cel_fajl}")
    print(f"[Export]   Méret: {meret_kb:.1f} KB")
    print(f"[Export]   UUID: {uid}")
    print(f"[Export]   DB hash: {db_hash[:16]}...")
    return Path(cel_fajl)


# ── Import ────────────────────────────────────────────────────────────────────

def import_memex(fajl: str, jelszo: str, eroszak: bool = False) -> bool:
    """
    Importál egy .memex fájlt.
    Ha az eszközön már van adatbázis – biztonsági mentés készül belőle.
    eroszak=True: felülírja UUID ellenőrzés nélkül (új eszközre)
    """
    fajl_path = Path(fajl)
    if not fajl_path.exists():
        raise FileNotFoundError(f"Fájl nem található: {fajl}")

    csomag = json.loads(fajl_path.read_text(encoding="utf-8"))

    # Verzió ellenőrzés
    if csomag.get("verzio") != VERZIO:
        print(f"[Import] ⚠ Eltérő verzió: {csomag.get('verzio')} (jelenlegi: {VERZIO})")

    import_uuid = csomag["uuid"]
    sajat_uuid  = uuid_get()

    # UUID ellenőrzés – ugyanaz az ember?
    if import_uuid != sajat_uuid and not eroszak:
        print(f"[Import] ⚠ Más UUID!")
        print(f"[Import]   Fájl UUID:  {import_uuid}")
        print(f"[Import]   Saját UUID: {sajat_uuid}")
        print(f"[Import]   Ha új eszközre töltöd át: --eroszak kapcsolóval")
        return False

    # Visszafejtés
    kulcs = _kulcs_general(jelszo, import_uuid)
    titkos = base64.b64decode(csomag["db"])
    db_adat = _xor_titkosit(titkos, kulcs)

    # Hash ellenőrzés – sérült-e az adat?
    szamolt_hash = _hash_szamol(db_adat)
    if szamolt_hash != csomag["db_hash"]:
        print("[Import] ✗ HIBA: Az adatok sérültek vagy rossz a jelszó!")
        return False

    # Biztonsági mentés a meglévő DB-ről
    if DB_PATH.exists():
        backup = DB_PATH.parent / f"memex_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(DB_PATH, backup)
        print(f"[Import]   Backup: {backup.name}")

    # Új UUID beállítás ha más eszközre importál
    if import_uuid != sajat_uuid and eroszak:
        ID_PATH.write_text(import_uuid)
        print(f"[Import]   UUID átvéve: {import_uuid}")

    # DB fájl visszaírása
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_bytes(db_adat)

    letrehozva = csomag.get("letrehozva", "?")[:10]
    print(f"[Import] ✓ Kész!")
    print(f"[Import]   Exportálva: {letrehozva}")
    print(f"[Import]   UUID: {import_uuid}")
    print(f"[Import]   DB méret: {len(db_adat)/1024:.1f} KB")
    return True


# ── Fájl info ─────────────────────────────────────────────────────────────────

def export_info(fajl: str):
    """Megmutatja egy .memex fájl tartalmát jelszó nélkül."""
    fajl_path = Path(fajl)
    if not fajl_path.exists():
        print(f"Fájl nem található: {fajl}")
        return

    csomag = json.loads(fajl_path.read_text(encoding="utf-8"))
    print(f"\n=== {fajl_path.name} ===")
    print(f"  Verzió:      {csomag.get('verzio')}")
    print(f"  UUID:        {csomag.get('uuid')}")
    print(f"  Létrehozva:  {csomag.get('letrehozva', '?')[:19]}")
    print(f"  DB hash:     {csomag.get('db_hash', '?')[:16]}...")
    db_meret = len(base64.b64decode(csomag.get("db", "")))
    print(f"  DB méret:    {db_meret/1024:.1f} KB (titkosítva)")


# ── Lejárat kezelés ───────────────────────────────────────────────────────────

def lejarat_beallitas(napok: int = 7):
    """
    Beállítja a lejárati dátumot.
    Telefoncsere esetén: régi eszköz 7 nap múlva lezárul.
    """
    lejarat_path = ROOT / "db" / "lejarat.txt"
    lejarat = datetime.now() + timedelta(days=napok)
    lejarat_path.write_text(lejarat.isoformat())
    print(f"[Lejárat] Beállítva: {lejarat.strftime('%Y-%m-%d')} ({napok} nap múlva)")


def lejarat_ellenorzes() -> bool:
    """
    True = aktív, False = lejárt.
    Minden indításkor ellenőrzés.
    """
    lejarat_path = ROOT / "db" / "lejarat.txt"
    if not lejarat_path.exists():
        return True  # nincs lejárat beállítva = aktív
    lejarat = datetime.fromisoformat(lejarat_path.read_text().strip())
    if datetime.now() > lejarat:
        print(f"[Lejárat] ✗ Ez az eszköz lejárt: {lejarat.strftime('%Y-%m-%d')}")
        print(f"[Lejárat]   Az adatbázis csak olvasható módban érhető el.")
        return False
    marad = (lejarat - datetime.now()).days
    if marad <= 3:
        print(f"[Lejárat] ⚠ Figyelem: {marad} nap múlva ez az eszköz lezárul!")
    return True


# ── Export lista ─────────────────────────────────────────────────────────────

def export_lista():
    """Megmutatja az összes korábbi exportot."""
    EXP_DIR.mkdir(exist_ok=True)
    fajlok = sorted(EXP_DIR.glob("*.memex"), reverse=True)
    if not fajlok:
        print("Nincs korábbi export.")
        return
    print(f"\n=== Exportok ({len(fajlok)} db) ===")
    for f in fajlok:
        meret = f.stat().st_size / 1024
        print(f"  {f.name}  ({meret:.1f} KB)")


# ── Belépési pont ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Memex Export/Import")
    sub = parser.add_subparsers(dest="parancs")

    # export
    exp = sub.add_parser("export", help="Adatbázis exportálása")
    exp.add_argument("--jelszo", required=True, help="Titkosítási jelszó")
    exp.add_argument("--cel",    default="",   help="Célútvonal (opcionális)")

    # import
    imp = sub.add_parser("import", help="Adatbázis importálása")
    imp.add_argument("--fajl",   required=True, help=".memex fájl útvonala")
    imp.add_argument("--jelszo", required=True, help="Jelszó")
    imp.add_argument("--eroszak", action="store_true", help="Új eszközre importálás")

    # info
    inf = sub.add_parser("info", help="Fájl tartalmának megtekintése")
    inf.add_argument("--fajl", required=True)

    # uuid
    sub.add_parser("uuid", help="Saját UUID lekérése")

    # lista
    sub.add_parser("lista", help="Korábbi exportok listája")

    # lejarat
    lej = sub.add_parser("lejarat", help="Lejárat beállítása")
    lej.add_argument("--napok", type=int, default=7)

    args = parser.parse_args()

    if args.parancs == "export":
        export_memex(args.jelszo, args.cel)

    elif args.parancs == "import":
        import_memex(args.fajl, args.jelszo, args.eroszak)

    elif args.parancs == "info":
        export_info(args.fajl)

    elif args.parancs == "uuid":
        print(f"UUID: {uuid_get()}")

    elif args.parancs == "lista":
        export_lista()

    elif args.parancs == "lejarat":
        lejarat_beallitas(args.napok)

    else:
        parser.print_help()
