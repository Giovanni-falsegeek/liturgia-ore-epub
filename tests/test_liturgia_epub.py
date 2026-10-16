import html
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

import liturgia_epub as l


D = date(2026, 11, 3)
X = {"x": "http://www.w3.org/1999/xhtml"}
N = {"n": "http://www.daisy.org/z3986/2005/ncx/"}


def fixture(slug, memoria=0, versioni=None, d=D, ore=None):
    """Struttura del selettore CEI con testi fittizi riconoscibili."""
    if versioni is None:
        versioni = {0: "Feria", 1: "San Martino", 7: "Altra memoria"}
    menu = "".join(f'<a data-liturgiatitolo="{s}">{n}</a>'
                   for s, n in (ore if ore is not None else l.ORE))
    schede = []
    if len(versioni) > 1:
        for ident, titolo in versioni.items():
            if ident == memoria:
                testo = f'<span class="titolo_memoria">{html.escape(titolo)}</span>'
                classe = "selected"
            else:
                testo = (f'<a class="titolo_memoria" href="{l.BASE}?data-liturgia={d:%Y%m%d}'
                         f'&amp;memoria={ident}"><span class="titolo_memoria">'
                         f'{html.escape(titolo)}</span></a>')
                classe = "linkable"
            schede.append(f'<div class="liturgia-delle-ore memoria {classe}">'
                          f'<p class="memoria-tipologia">Memoria 0</p>{testo}</div>')
    return (f'{menu}<div id="cci_content_page" data-data_liturgia="{d:%Y%m%d}" '
            f'data-selected_ora="{slug}" data-num_memorie="{len(versioni)}">'
            f'<span>{d.day:02d} {l.MESI[d.month-1]} {d.year}</span>'
            f'<div class="cci-opere-giorni-liturgia">{html.escape(versioni[memoria])}</div>'
            '<div>Grandezza Testo <a>A</a></div>'
            f'<article><p>Testo {slug} versione {memoria}.</p>'
            '<p>Ora terza</p><p>Preghiera terza.</p><p>Ora sesta</p><p>Preghiera sesta.</p>'
            '<p>Ora nona</p><p>Preghiera nona.</p></article>'
            '<div>Condividi</div></div>' + "".join(schede))


FERIA = fixture("lodi-mattutine", versioni={0: "Feria", 1: "San Martino"})
MARTINO = fixture("lodi-mattutine", memoria=1, versioni={0: "Feria", 1: "San Martino"})


class MemorieTest(unittest.TestCase):
    def test_identificativi_non_contigui_e_tre_versioni(self):
        self.assertEqual([v[0] for v in l.leggi_memorie(fixture("invitatorio"), D, "invitatorio")[1]], [0, 1, 7])

    def test_unica_celebrazione(self):
        testo = fixture("invitatorio", versioni={0: "Solennità"})
        self.assertEqual(l.leggi_memorie(testo, D, "invitatorio"), ("Solennità", [(0, "Solennità")]))

    def test_selezione_ignorata_data_ora_e_schede_errate(self):
        casi = [
            (FERIA, D, "lodi-mattutine", 1),
            (FERIA, date(2026, 11, 4), "lodi-mattutine", 0),
            (FERIA, D, "vespri", 0),
            (FERIA.replace('data-num_memorie="2"', 'data-num_memorie="3"'), D, "lodi-mattutine", 0),
            (FERIA.replace("memoria=1", "memoria=abc"), D, "lodi-mattutine", 0),
            (FERIA.replace("memoria=1", "memoria=1&amp;memoria=2"), D, "lodi-mattutine", 0),
        ]
        for args in casi:
            with self.subTest(args=args[1:]), self.assertRaises(ValueError):
                l.leggi_memorie(*args)

    def test_cache_e_parametro_http(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            vecchio = cache / "20261103_lodi-mattutine.html"
            vecchio.write_text(FERIA, encoding="utf-8")
            with patch.object(l, "urlopen") as download:
                self.assertEqual(l.scarica(D, "lodi-mattutine", cache, 0)[0], FERIA)
                download.assert_not_called()
                download.return_value.__enter__.return_value.read.return_value = MARTINO.encode()
                testo, nuovo = l.scarica(D, "lodi-mattutine", cache, 0, 1)
                self.assertEqual(testo, MARTINO)
                self.assertNotEqual(vecchio, nuovo)
                url = download.call_args.args[0].full_url
                self.assertEqual(parse_qs(urlsplit(url).query),
                                 {"data-liturgia": ["20261103"], "ora": ["lodi-mattutine"], "memoria": ["1"]})
                self.assertEqual(vecchio.read_text(encoding="utf-8"), FERIA)
            with patch.object(l, "urlopen") as download:
                l.scarica(D, "lodi-mattutine", cache, 0, 1)
                download.assert_not_called()

    def test_raccolta_tutte_le_ore_e_versioni(self):
        richieste = []
        def scarica(d, slug, cache, pausa, memoria=0):
            richieste.append((slug, memoria))
            return fixture(slug, memoria), Path("fixture.html")
        with patch.object(l, "scarica", side_effect=scarica):
            giorni = l.raccogli_giorno(D, Path("cache"), 0)
        self.assertEqual([g["memoria"] for g in giorni], [0, 1, 7])
        self.assertEqual({(s, m) for s, _ in l.ORE for m in (0, 1, 7)}, set(richieste))
        self.assertTrue(all(len(g["ore"]) == 6 for g in giorni))
        for g in giorni:
            for slug, _, _, paras in g["ore"]:
                self.assertIn([f"Testo {slug} versione {g['memoria']}."], paras)

    def test_download_errato_non_rinominato(self):
        def scarica(d, slug, cache, pausa, memoria=0):
            return fixture(slug, 0), Path("fixture.html")
        with patch.object(l, "scarica", side_effect=scarica), self.assertRaises(ValueError):
            l.raccogli_giorno(D, Path("cache"), 0)

    def test_cache_vecchia_con_memorie_riordinate(self):
        vecchie = {0: "Feria", 1: "San Colombano", 2: "San Clemente"}
        nuove = {0: "Feria", 1: "San Clemente", 2: "San Colombano"}
        def scarica(d, slug, cache, pausa, memoria=0):
            return fixture(slug, memoria, versioni=vecchie if memoria == 0 else nuove), Path("fixture.html")
        with patch.object(l, "scarica", side_effect=scarica):
            with self.assertRaisesRegex(ValueError, "identificativi CEI potrebbero essere cambiati"):
                l.raccogli_giorno(D, Path("cache"), 0)

    def test_ore_serali_celebrazione_e_vigilia(self):
        sabato = date(2026, 11, 7)
        domenica = date(2026, 11, 8)
        festive = l.ORE[:4] + [("primi-vespri", "Primi Vespri"),
                               ("secondi-vespri", "Secondi Vespri"),
                               ("compieta-dopo-i-primi-vespri", "Compieta"),
                               ("compieta-dopo-i-secondi-vespri", "Compieta")]
        richieste = []
        def scarica(d, slug, cache, pausa, memoria=0):
            richieste.append((d, slug))
            return fixture(slug, d=d, versioni={0: "Sabato" if d == sabato else "Domenica"},
                           ore=l.ORE[:4] if d == sabato else festive), Path("fixture.html")
        with patch.object(l, "scarica", side_effect=scarica):
            vigilia = l.raccogli_giorno(sabato, Path("cache"), 0)[0]
            festa = l.raccogli_giorno(domenica, Path("cache"), 0)[0]
        self.assertIn((domenica, "primi-vespri"), richieste)
        self.assertIn((domenica, "compieta-dopo-i-primi-vespri"), richieste)
        self.assertIn((domenica, "secondi-vespri"), richieste)
        self.assertIn((domenica, "compieta-dopo-i-secondi-vespri"), richieste)
        self.assertEqual(vigilia["data"], sabato)
        self.assertIn("vigilia", vigilia["ore"][-2][2])
        self.assertEqual(festa["ore"][-2][2], "Domenica")


class EpubTest(unittest.TestCase):
    def test_indice_spine_collegamenti_e_testi_distinti(self):
        with patch.object(l, "scarica", side_effect=lambda d, s, c, p, memoria=0:
                          (fixture(s, memoria, versioni={0: "Feria", 1: "San Martino"}), Path("fixture.html"))):
            giorni = l.raccogli_giorno(D, Path("cache"), 0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.epub"
            l.costruisci(giorni, 2026, 11, path)
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(z.infolist()[0].filename, "mimetype")
                self.assertEqual(z.infolist()[0].compress_type, zipfile.ZIP_STORED)
                self.assertEqual(z.read("mimetype"), b"application/epub+zip")
                self.assertEqual(len(z.namelist()), len(set(z.namelist())))
                documenti = {n: ET.fromstring(z.read(n)) for n in z.namelist()
                             if n.endswith((".xhtml", ".opf", ".ncx", ".xml"))}
                nav = documenti["OEBPS/nav.xhtml"]
                date_voci = nav.findall(".//x:nav/x:ol/x:li", X)
                self.assertEqual(len(date_voci), 1)
                celebrazioni = date_voci[0].findall("x:ol/x:li", X)
                self.assertEqual([v.find("x:a", X).text for v in celebrazioni], ["Feria", "San Martino"])
                for v in celebrazioni:
                    self.assertEqual(len(v.findall("x:ol/x:li", X)), 6)
                    self.assertEqual(len(v.findall("x:ol/x:li", X)[3].findall("x:ol/x:li", X)), 3)
                ncx = documenti["OEBPS/toc.ncx"]
                self.assertEqual(ncx.find('.//n:meta[@name="dtb:depth"]', N).get("content"), "4")
                self.assertEqual(len(ncx.findall(".//n:navPoint", N)), len(nav.findall(".//x:li", X)))
                opf = documenti["OEBPS/content.opf"]
                ns = {"o": "http://www.idpf.org/2007/opf"}
                manifest = {v.get("id"): v.get("href") for v in opf.findall("o:manifest/o:item", ns)}
                spine = [manifest[v.get("idref")] for v in opf.findall("o:spine/o:itemref", ns)]
                self.assertEqual(len(spine), 14)
                self.assertTrue(all("_m1_" not in s for s in spine[2:8]))
                self.assertTrue(all("_m1_" in s for s in spine[8:]))
                for filename, root in documenti.items():
                    ids = [v.get("id") for v in root.iter() if v.get("id")]
                    self.assertEqual(len(ids), len(set(ids)), filename)
                    for v in root.iter():
                        ref = v.get("href") or v.get("src")
                        if ref:
                            target, _, anchor = ref.partition("#")
                            resolved = "OEBPS/" + target
                            self.assertIn(resolved, z.namelist(), (filename, ref))
                            if anchor:
                                self.assertTrue(any(e.get("id") == anchor for e in documenti[resolved].iter()))
                prima = documenti["OEBPS/" + spine[7]]
                self.assertIn(spine[8], [a.get("href") for a in prima.findall(".//x:a", X)])

    def test_compatibilita_vecchio_formato_giorni(self):
        giorni = [{"data": D, "ore": [(s, n, "Titolo", [["Preghiera"]]) for s, n in l.ORE]}]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "vecchio.epub"
            l.costruisci(giorni, 2026, 11, p)
            with zipfile.ZipFile(p) as z:
                nav = ET.fromstring(z.read("OEBPS/nav.xhtml"))
                self.assertEqual(len(nav.findall(".//x:nav/x:ol/x:li/x:ol/x:li", X)), 6)


if __name__ == "__main__":
    unittest.main()
