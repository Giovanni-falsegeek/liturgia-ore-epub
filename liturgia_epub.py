#!/usr/bin/env python3
"""Liturgia delle Ore (testi CEI, chiesacattolica.it) -> ePub di un mese.

Uso:
    python3 liturgia_epub.py 2026-11              # tutto novembre 2026
    python3 liturgia_epub.py 2026-11 --dal 10 --al 20   # solo dal 10 al 20 novembre
    python3 liturgia_epub.py 2026-11 --dal 15           # dal 15 a fine mese
    python3 liturgia_epub.py 2026-11 --giorni 1         # prova: solo il 1 del mese

Solo libreria standard (nessuna installazione). Le pagine scaricate restano in
una cartella di cache, quindi se si interrompe basta rilanciare: riparte da dove era.
"""
import argparse
import calendar
import html
import re
import sys
import time
import uuid
import zipfile
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

BASE = "https://www.chiesacattolica.it/la-liturgia-delle-ore/"
ORE = [
    ("invitatorio", "Invitatorio"),
    ("ufficio-delle-letture", "Ufficio delle letture"),
    ("lodi-mattutine", "Lodi mattutine"),
    ("ora-media", "Ora media"),
    ("vespri", "Vespri"),
    ("compieta", "Compieta"),
]
GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]

esc = html.escape


class Memorie(HTMLParser):
    """Legge le schede CEI, senza confondere menu, script e testo liturgico."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.schede, self.titolo = [], [], []
        self.attributi = {}
        self.ore = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classi = set(a.get("class", "").split())
        scheda = None
        if {"liturgia-delle-ore", "memoria"} <= classi:
            scheda = {"selected": "selected" in classi, "testo": [], "href": None}
            self.schede.append(scheda)
        if a.get("id") == "cci_content_page":
            self.attributi = a
        if tag == "a" and a.get("data-liturgiatitolo"):
            self.ore.append(a["data-liturgiatitolo"])
        if tag == "a" and "titolo_memoria" in classi:
            for _, _, card in reversed(self.stack):
                if card is not None:
                    card["href"] = a.get("href")
                    break
        if tag not in self.VOID:
            self.stack.append((tag, classi, scheda))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if any(tag in SKIP for tag, _, _ in self.stack):
            return
        if any("cci-opere-giorni-liturgia" in c for _, c, _ in self.stack):
            self.titolo.append(data)
        if any("titolo_memoria" in c for _, c, _ in self.stack):
            for _, _, card in reversed(self.stack):
                if card is not None:
                    card["testo"].append(data)
                    break


def normalizza(testo):
    return " ".join(testo.split())


def leggi_memorie(testo, d, slug, memoria=0):
    """Restituisce (titolo corrente, [(parametro memoria, titolo), ...]).

    Gli identificativi provengono dai link reali, non da data-num_memorie:
    quest'ultimo serve solo per accorgersi di alternative non riconosciute.
    """
    p = Memorie()
    p.feed(testo)
    p.close()
    a = p.attributi
    if a.get("data-data_liturgia") != f"{d:%Y%m%d}":
        raise ValueError("data liturgica della pagina errata o assente")
    if a.get("data-selected_ora") != slug:
        raise ValueError(f"la pagina non contiene l'ora richiesta: {slug}")
    titolo = normalizza("".join(p.titolo))
    if not titolo:
        raise ValueError("titolo liturgico assente")
    versioni, selezionate = {}, 0
    for card in p.schede:
        nome = normalizza("".join(card["testo"]))
        if not nome:
            raise ValueError("scheda memoria priva di titolo")
        if card["selected"]:
            ident = memoria
            selezionate += 1
            if nome != titolo:
                raise ValueError("memoria selezionata diversa dal titolo del testo")
        else:
            link = urlsplit(urljoin(BASE, card["href"] or ""))
            query = parse_qs(link.query)
            valori = query.get("memoria", [])
            if (link.scheme != "https" or link.netloc != urlsplit(BASE).netloc
                    or link.path != urlsplit(BASE).path
                    or query.get("data-liturgia") != [f"{d:%Y%m%d}"]
                    or len(valori) != 1 or not re.fullmatch(r"[0-9]+", valori[0])):
                raise ValueError("link della memoria non riconosciuto")
            ident = int(valori[0])
        if ident in versioni:
            raise ValueError("identificativi delle memorie duplicati: selezione non confermata")
        versioni[ident] = nome
    numero = a.get("data-num_memorie", "1")
    if not numero.isdigit() or int(numero) < 1:
        raise ValueError("numero delle memorie non riconosciuto")
    if p.schede:
        if selezionate != 1 or len(versioni) != int(numero):
            raise ValueError("non tutte le memorie indicate dalla CEI sono riconoscibili")
    elif int(numero) != 1 or memoria:
        raise ValueError("schede delle memorie mancanti: selezione non verificabile")
    else:
        versioni[0] = titolo
    return titolo, sorted(versioni.items())


# --------------------------------------------------------------------------
# Lettura della pagina
# --------------------------------------------------------------------------
BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "section",
         "article", "blockquote", "tr", "table", "header", "footer", "nav", "main",
         "aside", "form"}
SKIP = {"script", "style", "noscript", "svg", "template", "head"}


class Paragrafi(HTMLParser):
    """Trasforma l'HTML in paragrafi, ciascuno fatto di righe (i <br> vanno a capo)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paras, self.lines, self.cur, self.skip = [], [], "", 0

    def _riga(self):
        t = re.sub(r"\s+", " ", self.cur).strip()
        if t:
            self.lines.append(t)
        self.cur = ""

    def chiudi_paragrafo(self):
        self._riga()
        if self.lines:
            self.paras.append(self.lines)
            self.lines = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
        elif self.skip:
            return
        elif tag == "br":
            self._riga()
        elif tag in BLOCK:
            self.chiudi_paragrafo()

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
        elif self.skip:
            return
        elif tag in BLOCK:
            self.chiudi_paragrafo()

    def handle_data(self, data):
        if not self.skip:
            self.cur += data


LABEL = re.compile(r"^(V\.|R\.|℣\.|℟\.|Ant\.(?: ?\d+)?)$")
LABEL_INIZIO = re.compile(r"^(V\.|R\.|℣\.|℟\.|Ant\.(?: ?\d+)?)\s+(.*)$")
TITOLO = re.compile(r"^(SALMO|CANTICO|LETTURA|PRIMA LETTURA|SECONDA LETTURA|RESPONSORIO|INNO|"
                    r"ORAZIONE|PREGHIERA|INTERCESSIONI|INVOCAZIONI|BENEDIZIONE|CONCLUSIONE|"
                    r"ANTIFONA|COLLETTA|DAL|DALLA|DAI|DALLE|DAGLI)\b")


SOTTO_ORA = re.compile(r"^ora\s+(terza|sesta|nona)\.?$", re.IGNORECASE)


def dividi_sottotitoli(paras):
    """Se 'Ora terza/sesta/nona' è la prima riga di un paragrafo con altro testo, la separa."""
    out = []
    for p in paras:
        if len(p) > 1 and SOTTO_ORA.match(p[0]):
            out += [[p[0]], p[1:]]
        else:
            out.append(p)
    return out


def sottotitoli(paras):
    """[(id, etichetta)] per Ora terza / sesta / nona presenti nel testo."""
    ris = []
    for p in paras:
        m = SOTTO_ORA.match(p[0]) if len(p) == 1 else None
        if m:
            ris.append((f"ora-{m.group(1).lower()}", f"Ora {m.group(1).lower()}"))
    return ris


def unisci_etichette(paras):
    """'V.' / 'R.' / 'Ant.' da soli su una riga o in un paragrafo: li unisce al testo che segue."""
    interni = []
    for p in paras:
        out, i = [], 0
        while i < len(p):
            if LABEL.match(p[i]) and i + 1 < len(p):
                out.append(p[i] + " " + p[i + 1])
                i += 2
            else:
                out.append(p[i])
                i += 1
        interni.append(out)
    finale, i = [], 0
    while i < len(interni):
        p = interni[i]
        if len(p) == 1 and LABEL.match(p[0]) and i + 1 < len(interni):
            nxt = list(interni[i + 1])
            nxt[0] = p[0] + " " + nxt[0]
            finale.append(nxt)
            i += 2
        else:
            finale.append(p)
            i += 1
    return finale


def estrai(testo_html, d, nome_ora):
    """Ritorna (sottotitolo, paragrafi). Solleva ValueError se la pagina non è quella attesa."""
    p = Paragrafi()
    p.feed(testo_html)
    p.close()
    p.chiudi_paragrafo()
    righe = [" ".join(x) for x in p.paras]

    data_attesa = f"{d.day} {MESI[d.month - 1]} {d.year}"
    data_re = re.compile(rf"\b0?{d.day}\s+{MESI[d.month - 1]}\s+{d.year}\b", re.I)
    if not any(data_re.search(r) for r in righe):
        raise ValueError(f"la pagina non riporta la data {data_attesa}")
    gi = next((i for i, r in enumerate(righe) if r.lower().startswith("grandezza testo")), None)
    if gi is None:
        raise ValueError("marcatore 'Grandezza Testo' non trovato")
    fine = next((i for i in range(gi + 1, len(righe)) if righe[i].lower().startswith("condividi")), None)
    if fine is None:
        raise ValueError("marcatore 'Condividi' non trovato")
    inizio = gi + 1
    while inizio < fine and re.fullmatch(r"(A\s*)+", righe[inizio]):
        inizio += 1
    corpo = p.paras[inizio:fine]
    if not corpo:
        raise ValueError("testo vuoto")
    if nome_ora.lower() == "ora media":
        corpo = dividi_sottotitoli(corpo)
    sotto = righe[gi - 1] if gi > 0 else ""
    if sotto.lower() == nome_ora.lower():
        sotto = ""
    return sotto, unisci_etichette(corpo)


def scarica(d, slug, cache, pausa, memoria=0):
    suffisso = f"_memoria-{memoria}" if memoria else ""
    f = cache / f"{d:%Y%m%d}_{slug}{suffisso}.html"
    if f.exists():
        return f.read_text("utf-8"), f
    parametri = {"data-liturgia": f"{d:%Y%m%d}", "ora": slug}
    if memoria:
        parametri["memoria"] = str(memoria)
    url = f"{BASE}?{urlencode(parametri)}"
    ultimo = None
    for tentativo in range(4):
        try:
            req = Request(url, headers={
                "User-Agent": "Mozilla/5.0 (uso personale, lettura offline)",
                "Accept-Language": "it-IT,it;q=0.9",
            })
            with urlopen(req, timeout=30) as r:
                testo = r.read().decode("utf-8", "replace")
            f.write_text(testo, "utf-8")
            time.sleep(pausa)
            return testo, f
        except (HTTPError, URLError, TimeoutError) as e:
            ultimo = e
            time.sleep(2 ** (tentativo + 1))
    raise RuntimeError(f"download fallito per {url}: {ultimo}")


def raccogli_giorno(d, cache, pausa):
    """Ogni versione ha tutte le sue ore scaricate e validate separatamente."""
    testo, f = scarica(d, "lodi-mattutine", cache, pausa)
    try:
        _, versioni = leggi_memorie(testo, d, "lodi-mattutine")
    except ValueError as e:
        raise ValueError(f"{f}: {e}") from e
    giorni = []
    for memoria, titolo in versioni:
        # Le Lodi espongono il menu delle ore della celebrazione selezionata.
        testo, f = scarica(d, "lodi-mattutine", cache, pausa, memoria)
        menu = Memorie()
        menu.feed(testo)
        menu.close()
        corrente, _ = leggi_memorie(testo, d, "lodi-mattutine", memoria)
        if corrente != titolo:
            raise ValueError(f"{f}: selezione della memoria non confermata; "
                             f"attesa '{titolo}', ricevuta '{corrente}'. "
                             f"Aggiornare tutte le pagine in cache del {d:%Y%m%d}: "
                             "gli identificativi CEI potrebbero essere cambiati.")
        ore = []
        for slug, nome in ORE:
            data_fonte, id_fonte, titolo_fonte = d, memoria, titolo
            slug_fonte = slug
            if slug not in menu.ore:
                serali = {"vespri": "secondi-vespri",
                          "compieta": "compieta-dopo-i-secondi-vespri"}
                if slug in serali and serali[slug] in menu.ore:
                    slug_fonte = serali[slug]
                elif slug in serali:
                    # La CEI pubblica i primi Vespri sotto la data della festa
                    # successiva, mentre qui si leggono la sera precedente.
                    data_fonte = d + timedelta(days=1)
                    id_fonte = 0
                    successivo, _ = scarica(data_fonte, "lodi-mattutine", cache, pausa)
                    titolo_fonte, _ = leggi_memorie(successivo, data_fonte, "lodi-mattutine")
                    slug_fonte = {"vespri": "primi-vespri",
                                  "compieta": "compieta-dopo-i-primi-vespri"}[slug]
                    menu_successivo = Memorie()
                    menu_successivo.feed(successivo)
                    menu_successivo.close()
                    if slug_fonte not in menu_successivo.ore:
                        raise ValueError(f"{d}: {nome} assenti anche nel menu CEI del giorno successivo")
                else:
                    raise ValueError(f"{d}: {nome} assenti nel menu CEI")
            testo, f = scarica(data_fonte, slug_fonte, cache, pausa, id_fonte)
            try:
                corrente, _ = leggi_memorie(testo, data_fonte, slug_fonte, id_fonte)
                if corrente != titolo_fonte:
                    raise ValueError(f"attesa '{titolo_fonte}', ricevuta '{corrente}'")
                _, paras = estrai(testo, data_fonte, nome)
            except ValueError as e:
                raise ValueError(f"{f} ({nome}, memoria {memoria}): {e}") from e
            sotto = corrente
            if data_fonte != d:
                sotto = f"{titolo} · {nome} della vigilia: {corrente}"
            ore.append((slug, nome, sotto, paras))
        giorni.append({"data": d, "memoria": memoria, "titolo": titolo, "ore": ore})
    return giorni


# --------------------------------------------------------------------------
# Composizione dell'ePub
# --------------------------------------------------------------------------
CSS = """body{font-family:serif;line-height:1.45;margin:0 .6em}
h1{font-size:1.5em;margin:.6em 0 .1em}
h2{font-size:1.1em;font-weight:normal;margin:0 0 .2em}
h3{font-size:1em;margin:1.3em 0 .3em}
p{margin:0 0 .9em;text-align:left}
h2.sub{font-size:1.25em;font-weight:bold;margin:1.8em 0 .5em;padding-top:.5em;border-top:1px solid #999}
.sott{font-size:.85em;margin-bottom:1.2em;font-variant:small-caps}
.rubr{color:#a00;font-style:italic}
.nav{margin-top:2em;font-size:.9em;text-align:center}
.front{text-align:center;margin-top:25%}
.front h1{font-size:2em;margin-bottom:.3em}
.front h2{font-size:1.4em;margin-bottom:2em}
.piccolo{font-size:.85em}
"""


def riga_html(testo):
    m = LABEL_INIZIO.match(testo)
    if m:
        return f'<span class="rubr">{esc(m.group(1))}</span> {esc(m.group(2))}'
    return esc(testo)


def corpo_html(paras):
    out = []
    for p in paras:
        m = SOTTO_ORA.match(p[0]) if len(p) == 1 else None
        if m:
            ora = m.group(1).lower()
            out.append(f'<h2 class="sub" id="ora-{ora}">Ora {ora}</h2>')
        elif len(p) == 1 and (TITOLO.match(p[0]) or (p[0].isupper() and len(p[0]) > 3)):
            out.append(f"<h3>{esc(p[0])}</h3>")
        else:
            out.append("<p>" + "<br/>".join(riga_html(r) for r in p) + "</p>")
    return "\n".join(out)


def pagina(titolo, corpo):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            'lang="it" xml:lang="it">\n<head><meta charset="utf-8"/>'
            f'<title>{esc(titolo)}</title>'
            '<link rel="stylesheet" type="text/css" href="stile.css"/></head>\n'
            f'<body>\n{corpo}\n</body>\n</html>\n')


def etichetta_giorno(d):
    return f"{GIORNI[d.weekday()].capitalize()} {d.day} {MESI[d.month - 1]}"


def descrivi_periodo(giorni, anno, mese):
    """'ottobre 2026' (mese intero), '15–31 ottobre 2026' (arco) o '15 ottobre 2026' (un giorno)."""
    primo, ultimo = giorni[0]["data"].day, giorni[-1]["data"].day
    nome = MESI[mese - 1]
    if primo == 1 and ultimo == calendar.monthrange(anno, mese)[1]:
        return f"{nome} {anno}"
    if primo == ultimo:
        return f"{primo} {nome} {anno}"
    return f"{primo}–{ultimo} {nome} {anno}"


def costruisci(giorni, anno, mese, percorso):
    periodo = descrivi_periodo(giorni, anno, mese)
    titolo_libro = f"Liturgia delle Ore – {periodo}"

    # elenco piatto di tutte le pagine, in ordine
    pagine = []
    for g in giorni:
        variante = f"_m{g['memoria']}" if g.get("memoria") else ""
        for n, (slug, nome, sotto, paras) in enumerate(g["ore"], 1):
            pagine.append({"file": f"g{g['data'].day:02d}{variante}_{n}_{slug}.xhtml", "g": g,
                           "nome": nome, "sotto": sotto, "paras": paras})

    files = {}
    for i, pg in enumerate(pagine):
        d = pg["g"]["data"]
        prec = pagine[i - 1]["file"] if i > 0 else None
        succ = pagine[i + 1]["file"] if i + 1 < len(pagine) else None
        nav = []
        if prec:
            nav.append(f'<a href="{prec}">‹ Precedente</a>')
        nav.append('<a href="nav.xhtml">Indice</a>')
        if succ:
            nav.append(f'<a href="{succ}">Successiva ›</a>')
        corpo = (f"<h1>{esc(pg['nome'])}</h1>\n"
                 f"<h2>{esc(etichetta_giorno(d))} {d.year}</h2>\n"
                 + (f'<p class="sott">{esc(pg["sotto"])}</p>\n' if pg["sotto"] else "")
                 + corpo_html(pg["paras"])
                 + '\n<p class="nav">' + " · ".join(nav) + "</p>")
        files[pg["file"]] = pagina(
            f"{pg['nome']} – {etichetta_giorno(d)} {d.year} – {pg['g'].get('titolo', pg['sotto'])}", corpo)

    # indice (EPUB 3) e toc.ncx (lettori più vecchi)
    contatore = [0]

    def voce(etichetta, href, figli=()):
        """Una voce d'indice con i suoi figli; ritorna (html <li>, xml navPoint del toc.ncx)."""
        contatore[0] += 1
        n = contatore[0]
        sub = [voce(*f) for f in figli]
        figli_li = f'<ol>{"".join(s[0] for s in sub)}</ol>' if sub else ""
        html_li = f'<li><a href="{href}">{esc(etichetta)}</a>{figli_li}</li>'
        xml = (f'<navPoint id="n{n}" playOrder="{n}"><navLabel><text>{esc(etichetta)}</text></navLabel>'
               f'<content src="{href}"/>{"".join(s[1] for s in sub)}</navPoint>')
        return html_li, xml

    li, ncx, per_data = [], [], {}
    for g in giorni:
        per_data.setdefault(g["data"], []).append(g)
    profondita = 1

    def profondita_voce(voci):
        return max((1 + profondita_voce(v[2]) for v in voci), default=0)

    for d, versioni in per_data.items():
        celebrazioni = []
        for g in versioni:
            mie = [p for p in pagine if p["g"] is g]
            ore_voci = [(p["nome"], p["file"],
                         [(lab, f'{p["file"]}#{sid}', ()) for sid, lab in sottotitoli(p["paras"])])
                        for p in mie]
            celebrazioni.append((g.get("titolo", "Celebrazione del giorno"), mie[0]["file"], ore_voci))
        figli = celebrazioni if len(versioni) > 1 else celebrazioni[0][2]
        radice = (f"{etichetta_giorno(d)} {d.year}", celebrazioni[0][1], figli)
        profondita = max(profondita, profondita_voce([radice]))
        h, x = voce(*radice)
        li.append(h)
        ncx.append(x)
    files["nav.xhtml"] = pagina("Indice", (
        f'<h1>{esc(titolo_libro)}</h1>\n<nav epub:type="toc" id="toc"><h2>Indice</h2>\n'
        f'<ol>{"".join(li)}</ol></nav>'))

    uid = f"urn:uuid:{uuid.uuid4()}"
    files["toc.ncx"] = (
        '<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
        f'<head><meta name="dtb:uid" content="{uid}"/><meta name="dtb:depth" content="{profondita}"/></head>'
        f'<docTitle><text>{esc(titolo_libro)}</text></docTitle><navMap>{"".join(ncx)}</navMap></ncx>')
    files["stile.css"] = CSS
    files["frontespizio.xhtml"] = pagina(titolo_libro, (
        '<div class="front">\n<h1>Liturgia delle Ore</h1>\n'
        f'<h2>{esc(periodo)}</h2>\n'
        '<p>Per ogni giorno: Invitatorio, Ufficio delle letture, Lodi mattutine, '
        'Ora media, Vespri, Compieta.</p>\n'
        '<p>Quando la CEI propone più celebrazioni, ogni versione ha le sue sei ore '
        'e una voce separata nell’indice.</p>\n'
        '<p class="piccolo">Testi della Conferenza Episcopale Italiana, '
        'da chiesacattolica.it</p>\n'
        '<p><a href="nav.xhtml">Vai all\'indice ›</a></p>\n</div>'))

    manifest = ['<item id="front" href="frontespizio.xhtml" media-type="application/xhtml+xml"/>',
                '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
                '<item id="css" href="stile.css" media-type="text/css"/>']
    spine = ['<itemref idref="front"/>', '<itemref idref="nav"/>']
    for i, pg in enumerate(pagine):
        manifest.append(f'<item id="p{i}" href="{pg["file"]}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="p{i}"/>')
    modificato = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    opf = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bid" xml:lang="it">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:identifier id="bid">{uid}</dc:identifier><dc:title>{esc(titolo_libro)}</dc:title>'
           '<dc:language>it</dc:language>'
           '<dc:source>https://www.chiesacattolica.it/la-liturgia-delle-ore/</dc:source>'
           f'<meta property="dcterms:modified">{modificato}</meta></metadata>'
           f'<manifest>{"".join(manifest)}</manifest><spine toc="ncx">{"".join(spine)}</spine></package>')
    container = ('<?xml version="1.0" encoding="utf-8"?>\n'
                 '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" '
                 'media-type="application/oebps-package+xml"/></rootfiles></container>')

    with zipfile.ZipFile(percorso, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        for nome, contenuto in files.items():
            z.writestr(f"OEBPS/{nome}", contenuto, compress_type=zipfile.ZIP_DEFLATED)


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Liturgia delle Ore CEI -> ePub mensile")
    ap.add_argument("mese", help="mese nel formato AAAA-MM, es. 2026-11")
    ap.add_argument("-o", "--cartella", default=".", help="dove salvare l'ePub (default: cartella corrente)")
    ap.add_argument("--cache", default="cache_liturgia", help="cartella per le pagine scaricate")
    ap.add_argument("--dal", type=int, default=1, help="primo giorno del mese da scaricare (default: 1)")
    ap.add_argument("--al", type=int, default=0, help="ultimo giorno da scaricare (default: fine mese)")
    ap.add_argument("--giorni", type=int, default=0,
                    help="solo N giorni a partire da --dal (per provare)")
    ap.add_argument("--pausa", type=float, default=0.7, help="secondi tra una richiesta e l'altra")
    a = ap.parse_args()

    m = re.fullmatch(r"(\d{4})-(\d{1,2})", a.mese)
    if not m or not 1 <= int(m.group(1)) <= 9999 or not 1 <= int(m.group(2)) <= 12:
        sys.exit("Formato mese non valido: usa AAAA-MM, ad esempio 2026-11")
    if a.giorni < 0 or a.pausa < 0:
        sys.exit("--giorni e --pausa non possono essere negativi")
    anno, mese = int(m.group(1)), int(m.group(2))
    fine_mese = calendar.monthrange(anno, mese)[1]
    primo = a.dal
    ultimo = a.al or fine_mese
    if a.giorni:
        ultimo = min(ultimo, primo + a.giorni - 1)
    if not 1 <= primo <= ultimo <= fine_mese:
        sys.exit(f"Intervallo non valido: {MESI[mese - 1]} {anno} va dal 1 al {fine_mese}, "
                 f"e --dal non può superare --al (richiesto: {primo}–{ultimo})")

    cache = Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    out_dir = Path(a.cartella)
    out_dir.mkdir(parents=True, exist_ok=True)

    giorni, riepilogo = [], []
    for n in range(primo, ultimo + 1):
        d = date(anno, mese, n)
        try:
            versioni = raccogli_giorno(d, cache, a.pausa)
        except (ValueError, RuntimeError) as e:
            sys.exit(f"\nERRORE {d:%d/%m/%Y}: {e}\n"
                     "Le pagine in cache sono conservate per il controllo. "
                     "Nessun ePub parziale viene generato.")
        giorni.extend(versioni)
        for g in versioni:
            riepilogo.append(f"{d:%Y-%m-%d} | memoria={g['memoria']} | {g['titolo']}")
            print(f"{d:%d/%m/%Y}  [memoria={g['memoria']}] {g['titolo']}")

    base = f"Liturgia-delle-Ore-{anno}-{mese:02d}"
    if not (primo == 1 and ultimo == fine_mese):
        base += f"_{primo:02d}-{ultimo:02d}"
    epub = out_dir / f"{base}.epub"
    costruisci(giorni, anno, mese, epub)
    (out_dir / f"{base}-riepilogo.txt").write_text("\n".join(riepilogo) + "\n", "utf-8")

    print(f"\nCreato: {epub}")
    print(f"Incluse {len(giorni)} celebrazioni in {ultimo - primo + 1} giorni.")


if __name__ == "__main__":
    main()
