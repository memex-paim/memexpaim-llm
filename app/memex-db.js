/**
 * Memex PAIM – Offline adatréteg
 * IndexedDB alapú – nincs WASM, nincs blokkolás, minden böngészőben működik
 */

const DB_NAME = 'memex';
const DB_VERSION = 2;
let idb = null;

// ── Inicializálás ─────────────────────────────────────────────────────────────

export function dbInit() {
  if (idb) return Promise.resolve(idb);
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = e => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('naplo')) {
        const s = db.createObjectStore('naplo', { keyPath: 'sorszam', autoIncrement: true });
        s.createIndex('iro', 'iro');
        s.createIndex('fontossag', 'fontossag');
        s.createIndex('torolve', 'torolve');
      }
      if (!db.objectStoreNames.contains('nevjegy')) {
        db.createObjectStore('nevjegy', { keyPath: 'kulcs' });
      }
      if (!db.objectStoreNames.contains('horgony_stat')) {
        db.createObjectStore('horgony_stat', { keyPath: 'horgony' });
      }
      if (!db.objectStoreNames.contains('sessions')) {
        const sess = db.createObjectStore('sessions', { keyPath: 'id', autoIncrement: true });
        sess.createIndex('letrehozva', 'letrehozva');
      }
    };
    req.onsuccess = e => { idb = e.target.result; resolve(idb); };
    req.onerror  = e => reject(e.target.error);
  });
}

// ── Segéd: IDB promise wrapperek ──────────────────────────────────────────────

function tx(stores, mode = 'readonly') {
  return idb.transaction(stores, mode);
}

function idbGet(store, key) {
  return new Promise((res, rej) => {
    const r = tx(store).objectStore(store).get(key);
    r.onsuccess = () => res(r.result);
    r.onerror   = () => rej(r.error);
  });
}

function idbGetAll(store) {
  return new Promise((res, rej) => {
    const r = tx(store).objectStore(store).getAll();
    r.onsuccess = () => res(r.result);
    r.onerror   = () => rej(r.error);
  });
}

function idbPut(store, obj) {
  return new Promise((res, rej) => {
    const t = tx(store, 'readwrite');
    const r = t.objectStore(store).put(obj);
    r.onsuccess = () => res(r.result);
    r.onerror   = () => rej(r.error);
  });
}

function idbAdd(store, obj) {
  return new Promise((res, rej) => {
    const t = tx(store, 'readwrite');
    const r = t.objectStore(store).add(obj);
    r.onsuccess = () => res(r.result);
    r.onerror   = () => rej(r.error);
  });
}

function idbDelete(store, key) {
  return new Promise((res, rej) => {
    const t = tx(store, 'readwrite');
    const r = t.objectStore(store).delete(key);
    r.onsuccess = () => res();
    r.onerror   = () => rej(r.error);
  });
}

// ── UUID ──────────────────────────────────────────────────────────────────────

export function uuidGet() {
  let uid = localStorage.getItem('memex_uuid');
  if (!uid) {
    uid = crypto.randomUUID().replace(/-/g, '');
    localStorage.setItem('memex_uuid', uid);
  }
  return uid;
}

// ── Auto horgony + típus felismerés ──────────────────────────────────────────

const DOMAIN_KULCSSZAVAK = {
  python:     ['python', 'def ', 'import ', 'pip ', '.py'],
  javascript: ['javascript', 'node', 'npm', 'const ', 'let '],
  sql:        ['select ', 'insert ', 'sqlite', 'adatbázis'],
  méhészet:   ['méh', 'keret', 'méz', 'anyaméh', 'kaptár'],
  tehénészet: ['tehén', 'borjú', 'tőgy', 'ellés', 'fejés'],
  döntés:     ['döntöttük', 'elhatároztuk'],
  probléma:   ['hiba', 'nem működik', 'error'],
  megoldás:   ['megoldottam', 'sikerült', 'működik'],
  ötlet:      ['ötlet', 'mi lenne ha', 'lehetne'],
};

export function autoHorgony(tartalom, meglevo = []) {
  const horgonyok = new Set(meglevo);
  const lower = tartalom.toLowerCase();
  for (const [domain, szavak] of Object.entries(DOMAIN_KULCSSZAVAK)) {
    if (szavak.some(s => lower.includes(s))) horgonyok.add(domain);
  }
  if (/\d{4}[-./]\d{2}[-./]\d{2}/.test(tartalom)) horgonyok.add('dátum');
  if (/\d+\s*(kg|liter|km|db|ft|eur|usd)/i.test(tartalom)) horgonyok.add('mérték');
  return [...horgonyok].sort();
}

export function tipusFeliismer(tartalom) {
  const m = tartalom.match(/[#@!]\w+/);
  if (m) return m[0];
  const l = tartalom.toLowerCase();
  if (['döntöttük', 'elhatároztuk'].some(k => l.includes(k))) return '!döntés';
  if (['hiba', 'error', 'nem működik'].some(k => l.includes(k))) return '!hiba';
  if (['ötlet', 'mi lenne ha'].some(k => l.includes(k))) return '!ötlet';
  if (['def ', 'import '].some(k => l.includes(k))) return '#python';
  return '';
}

// ── CRUD ──────────────────────────────────────────────────────────────────────

export async function bejegyez({ tartalom, horgonyok = [], fontossag = 3, tipus = '', iro = 'human', session_id = null }) {
  const idobelyeg = new Date().toISOString();
  const h = autoHorgony(tartalom, horgonyok);
  const t = tipus || tipusFeliismer(tartalom);
  const sorszam = await idbAdd('naplo', {
    idobelyeg, tartalom,
    horgonyok: JSON.stringify(h),
    tipus: t, fontossag, iro,
    hash: idobelyeg + tartalom,
    torolve: 0,
    session_id
  });
  // horgony statisztika
  for (const h_ of h) {
    const meglevo = await idbGet('horgony_stat', h_);
    await idbPut('horgony_stat', {
      horgony: h_,
      darab: (meglevo?.darab || 0) + 1,
      utolso: idobelyeg
    });
  }
  return sorszam;
}

export async function keres(kerdes, limit = 10, kizarChat = true) {
  const mindenki = await idbGetAll('naplo');
  const lower = kerdes.toLowerCase();
  return mindenki
    .filter(r => {
      if (r.torolve !== 0) return false;
      if (kizarChat && r.tartalom.startsWith('K: ')) return false;
      return r.tartalom.toLowerCase().includes(lower) ||
             r.horgonyok.toLowerCase().includes(lower) ||
             r.tipus.toLowerCase().includes(lower);
    })
    .sort((a, b) => a.fontossag - b.fontossag || b.sorszam - a.sorszam)
    .slice(0, limit);
}

export async function legutobbi(limit = 20, kizarChat = false) {
  const mindenki = await idbGetAll('naplo');
  return mindenki
    .filter(r => {
      if (r.torolve !== 0) return false;
      if (kizarChat) {
        if (r.tartalom.startsWith('K: ') || r.tartalom.startsWith('V: ')) return false;
        if (r.fontossag >= 4) return false;
      }
      return true;
    })
    .sort((a, b) => b.sorszam - a.sorszam)
    .slice(0, limit);
}

export async function legfontosabb(limit = 5) {
  const mindenki = await idbGetAll('naplo');
  return mindenki
    .filter(r => r.torolve === 0 && r.fontossag === 1)
    .sort((a, b) => b.sorszam - a.sorszam)
    .slice(0, limit);
}

export async function torol(sorszam) {
  const r = await idbGet('naplo', sorszam);
  if (r) { r.torolve = 1; await idbPut('naplo', r); }
}

export async function statisztika() {
  const mindenki = await idbGetAll('naplo');
  const aktiv = mindenki.filter(r => r.torolve === 0);
  const human = aktiv.filter(r => r.iro === 'human').length;
  return { ossz: aktiv.length, human, ai: aktiv.length - human };
}

export async function horgonyLista() {
  const ossz = await idbGetAll('horgony_stat');
  return ossz.sort((a, b) => b.darab - a.darab).slice(0, 10);
}

export async function horgonyListaOsszes() {
  const ossz = await idbGetAll('horgony_stat');
  return ossz.sort((a, b) => b.darab - a.darab);
}

export async function nevjegySet(kulcs, ertek) {
  await idbPut('nevjegy', { kulcs, ertek });
}

export async function nevjegyGet() {
  const rows = await idbGetAll('nevjegy');
  return Object.fromEntries(rows.map(r => [r.kulcs, r.ertek]));
}

export async function ujAdatbazis() {
  await new Promise((res, rej) => {
    const t = idb.transaction(['naplo', 'horgony_stat', 'sessions'], 'readwrite');
    t.objectStore('naplo').clear();
    t.objectStore('horgony_stat').clear();
    t.objectStore('sessions').clear();
    t.oncomplete = res;
    t.onerror = () => rej(t.error);
  });
}

// ── Session CRUD ──────────────────────────────────────────────────────────────

export async function sessionLetrehoz(nev = 'New Chat') {
  const letrehozva = new Date().toISOString();
  return await idbAdd('sessions', { nev, letrehozva, frissitve: letrehozva });
}

export async function sessionAtnevez(id, nev) {
  const sess = await idbGet('sessions', id);
  if (sess) { sess.nev = nev; sess.frissitve = new Date().toISOString(); await idbPut('sessions', sess); }
}

export async function sessionTorol(id) {
  await idbDelete('sessions', id);
}

export async function sessionLista() {
  const ossz = await idbGetAll('sessions');
  return ossz.sort((a, b) => b.id - a.id);
}

export async function sessionUzenetek(sessionId) {
  const mindenki = await idbGetAll('naplo');
  return mindenki
    .filter(r => r.torolve === 0 && r.session_id === sessionId)
    .sort((a, b) => a.sorszam - b.sorszam);
}

// ── System prompt az AI-nak ───────────────────────────────────────────────────

export async function systemPromptBuild() {
  const nevjegy = await nevjegyGet();
  const fontos  = await legfontosabb(3);
  const utobbi  = await legutobbi(5, true);
  const horgonyok = await horgonyLista();

  let prompt = '=== WHO I AM ===\n';
  for (const [k, v] of Object.entries(nevjegy)) {
    prompt += `${k}: ${v.slice(0, 100)}\n`;
  }
  prompt += '\nPersonal AI assistant. Respond in user\'s language.\nIMPORTANT: Keep responses under 1000 words. If the user asks you to generate a very long text (thousands of words), politely decline and explain it is too much data for a single entry.\n';
  if (horgonyok.length) {
    prompt += '\nTopics: ' + horgonyok.map(h => `${h.horgony}(${h.darab}x)`).join(', ') + '\n';
  }
  if (fontos.length) {
    prompt += '\n=== CRITICAL ===\n';
    for (const b of fontos) prompt += `[${b.idobelyeg.slice(0, 10)}] ${b.tartalom.slice(0, 150)}\n`;
  }
  if (utobbi.length) {
    prompt += '\n=== RECENT ===\n';
    for (const b of utobbi.slice(0, 3)) prompt += `[${b.idobelyeg.slice(0, 10)}] ${b.tartalom.slice(0, 150)}\n`;
  }
  return prompt.slice(0, 4000);
}

// ── Export / Import (.memex JSON) ─────────────────────────────────────────────

export async function exportMemex(jelszo = '') {
  const uid = uuidGet();
  const naplo = await idbGetAll('naplo');
  const nevjegy = await idbGetAll('nevjegy');
  const horgony_stat = await idbGetAll('horgony_stat');

  const adat = JSON.stringify({ naplo, nevjegy, horgony_stat });
  const kulcs = await _kulcsGeneral(jelszo, uid);
  const enc = new TextEncoder().encode(adat);
  const titkos = _xorTitkosit(enc, kulcs);
  const b64 = btoa(String.fromCharCode(...titkos));

  const csomag = JSON.stringify({
    verzio: '2.0', uuid: uid,
    letrehozva: new Date().toISOString(),
    db: b64
  });

  const blob = new Blob([csomag], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `memex_${new Date().toISOString().slice(0, 10)}.memex`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function importMemex(fajl, jelszo = '') {
  const szoveg = await fajl.text();
  const csomag = JSON.parse(szoveg);
  const importUuid = csomag.uuid;
  const kulcs = await _kulcsGeneral(jelszo, importUuid);
  const titkosBytes = Uint8Array.from(atob(csomag.db), c => c.charCodeAt(0));
  const dec = _xorTitkosit(titkosBytes, kulcs);
  const adat = JSON.parse(new TextDecoder().decode(dec));

  // Backup: jelenlegi adatok exportálva localStorage-ba
  const jelenlegiNaplo = await idbGetAll('naplo');
  localStorage.setItem('memex_backup_count', jelenlegiNaplo.length);

  // Törlés és betöltés
  await ujAdatbazis();
  const t = idb.transaction(['naplo', 'nevjegy', 'horgony_stat'], 'readwrite');
  for (const r of (adat.naplo || [])) {
    delete r.sorszam; // auto-increment újraszámolja
    t.objectStore('naplo').add(r);
  }
  for (const r of (adat.nevjegy || [])) t.objectStore('nevjegy').put(r);
  for (const r of (adat.horgony_stat || [])) t.objectStore('horgony_stat').put(r);

  await new Promise((res, rej) => { t.oncomplete = res; t.onerror = () => rej(t.error); });

  if (importUuid !== uuidGet()) localStorage.setItem('memex_uuid', importUuid);
  return true;
}

async function _kulcsGeneral(jelszo, uuid) {
  const alap = `${jelszo}:${uuid}:memex2026`;
  const enc = new TextEncoder().encode(alap);
  const hash = await crypto.subtle.digest('SHA-256', enc);
  return new Uint8Array(hash);
}

function _xorTitkosit(adat, kulcs) {
  const eredmeny = new Uint8Array(adat.length);
  for (let i = 0; i < adat.length; i++) {
    eredmeny[i] = adat[i] ^ kulcs[i % kulcs.length];
  }
  return eredmeny;
}
