import json
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from unittest.mock import patch

import liturgia_epub as l

D = date(2026, 11, 3)


def cei(d, slug, memoria=0, festivo=False):
    titoli = {0: 'Feria CEI', 7: 'Memoria CEI'}
    menu = ['ufficio-delle-letture', 'ora-media']
    if not festivo:
        menu += ['compieta']
    elif d != D:
        menu += ['compieta-dopo-i-primi-vespri']
    cards = []
    for n, titolo in titoli.items():
        testo = (f'<span class="titolo_memoria">{titolo}</span>' if n == memoria else
                 f'<a class="titolo_memoria" href="{l.BASE}?data-liturgia={d:%Y%m%d}&amp;memoria={n}">{titolo}</a>')
        cards.append(f'<div class="liturgia-delle-ore memoria {"selected" if n == memoria else "linkable"}">{testo}</div>')
    return (''.join(f'<a data-liturgiatitolo="{s}">Ora</a>' for s in menu)
            + f'<div id="cci_content_page" data-data_liturgia="{d:%Y%m%d}" data-selected_ora="{slug}" data-num_memorie="2">'
            + f'<span>{d.day} {l.MESI[d.month - 1]} {d.year}</span>'
            + f'<div class="cci-opere-giorni-liturgia">{titoli[memoria]}</div>'
            + f'<div>Grandezza Testo</div><p>Testo CEI {slug} {memoria}</p>'
            + '<p>Ora terza</p><p>Testo terza</p><p>Ora sesta</p><p>Testo sesta</p>'
            + '<p>Ora nona</p><p>Testo nona</p><div>Condividi</div></div>' + ''.join(cards))


def profesores(percorso, cache, pausa):
    if percorso.endswith('.json'):
        meta = {'t': 'Calendario proprio Profesores', 'n': 'def'}
        testo = json.dumps({D.isoformat(): meta})
    elif percorso.startswith('inv/'):
        testo = '<div class="lo_titolo">SALMO 94</div><p>Invitatorio fonte P</p>'
    else:
        testo = ('<div class="intro"><p>Introduzione da omettere</p></div>'
                 '<div class="lo_titolo">INNO</div><p>Testo fonte P</p>'
                 '<div hidden><span>Nascosto</span><br/>Nascosto</div>'
                 '<div class="lo_titolo">ORAZIONE</div><p>Preghiera fonte P</p>')
    return testo, Path(percorso)


class FontiTest(unittest.TestCase):
    def test_ordine_fonti_alternative_e_indici_epub(self):
        richieste = []

        def scarica(d, slug, cache, pausa, memoria=0):
            richieste.append((d, slug, memoria))
            return cei(d, slug, memoria), Path('fittizio.html')

        with tempfile.TemporaryDirectory() as tmp, patch.object(l, 'scarica', scarica), patch.object(l, 'scarica_profesores', profesores):
            giorni = l.raccogli_giorno(D, Path(tmp), 0)
            self.assertEqual([g['memoria'] for g in giorni], [0, 7])
            self.assertTrue(all(slug not in ('invitatorio', 'lodi-mattutine', 'vespri') for _, slug, _ in richieste))
            for g in giorni:
                self.assertEqual([o[0] for o in g['ore']], ['lodi-mattutine', 'ufficio-delle-letture', 'ora-media', 'vespri', 'compieta'])
                self.assertIn('Calendario proprio', g['ore'][0][2])
                self.assertIn('Calendario proprio', g['ore'][3][2])
                testo = ' '.join(' '.join(p) for p in g['ore'][0][3])
                self.assertLess(testo.index('Invitatorio fonte P'), testo.index('Testo fonte P'))
                self.assertNotIn('Introduzione da omettere', testo)
                self.assertNotIn('Nascosto', testo)
            out = Path(tmp) / 'prova.epub'
            l.costruisci(giorni, 2026, 11, out)
            with zipfile.ZipFile(out) as z:
                for nome in z.namelist():
                    if nome.endswith(('.xhtml', '.opf', '.ncx', '.xml')):
                        ET.fromstring(z.read(nome))
                self.assertEqual(len([n for n in z.namelist() if n.startswith('OEBPS/g')]), 10)
                self.assertIn(b'ora-terza', z.read('OEBPS/nav.xhtml'))
                self.assertIn(b'profesores.pages.dev', z.read('OEBPS/content.opf'))

    def test_compieta_vigilia_resta_cei_e_vespri_restano_profesores(self):
        richieste = []

        def scarica(d, slug, cache, pausa, memoria=0):
            richieste.append((d, slug))
            return cei(d, slug, memoria, festivo=True), Path('fittizio.html')

        with patch.object(l, 'scarica', scarica), patch.object(l, 'scarica_profesores', profesores):
            g = l.raccogli_giorno(D, Path('.'), 0)[0]
        self.assertIn((date(2026, 11, 4), 'compieta-dopo-i-primi-vespri'), richieste)
        self.assertIn('vigilia', g['ore'][-1][2])
        self.assertIn('Profesores', g['ore'][3][2])

    def test_varianti_e_percorsi(self):
        percorsi = []

        def download(percorso, cache, pausa):
            percorsi.append(percorso)
            return profesores(percorso, cache, pausa)

        with patch.object(l, 'scarica_profesores', download):
            l.raccogli_profesores(D, Path('.'), 0)
        self.assertIn('inv/20261103-def.html', percorsi)
        self.assertIn('lodi/20261103-def.html', percorsi)
        self.assertIn('vesp/20261103.html', percorsi)

    def test_rifiuta_pagina_principale_testi_mancanti_e_nascosti(self):
        for raw in ['<div id="ttl">INNO ORAZIONE</div>', '<p>Errore</p>', '<div hidden>INNO</div><p>ORAZIONE</p>']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                l.estrai_profesores(raw, 'lodi')

    def test_data_assente_o_variante_non_valida(self):
        for data in [{}, {D.isoformat(): {'t': 'Titolo', 'n': '../altro'}}]:
            with self.subTest(data=data), patch.object(l, 'scarica_profesores', return_value=(json.dumps(data), Path('lit.json'))), self.assertRaises(ValueError):
                l.raccogli_profesores(D, Path('.'), 0)

    def test_lodi_ordinarie_e_santa_maria_in_sabato(self):
        for n in [0, 1, '1', 'sms']:
            percorsi = []

            def download(percorso, cache, pausa):
                percorsi.append(percorso)
                if percorso == 'lit.json':
                    return json.dumps({D.isoformat(): {'t': 'Titolo', 'n': n}}), Path(percorso)
                return profesores(percorso, cache, pausa)

            with self.subTest(n=n), patch.object(l, 'scarica_profesores', download):
                l.raccogli_profesores(D, Path('.'), 0)
                self.assertIn(f'lodi/20261103-{n}.html', percorsi)
                self.assertIn('inv/20261103.html', percorsi)

    def test_cache_profesores_separata_e_riutilizzata(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            f = cache / 'profesores' / 'inv' / '20261103.html'
            f.parent.mkdir(parents=True)
            f.write_text('Testo Profesores in cache', encoding='utf8')
            (cache / '20261103_invitatorio.html').write_text('Testo CEI', encoding='utf8')
            with patch.object(l, 'urlopen', side_effect=AssertionError('Rete non necessaria')):
                testo, percorso = l.scarica_profesores('inv/20261103.html', cache, 0)
            self.assertEqual(percorso, f)
            self.assertEqual(testo, 'Testo Profesores in cache')


if __name__ == '__main__':
    unittest.main()
