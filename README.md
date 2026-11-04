# Presentazione semplice

Questo "programma" serve per creare un file ePub della liturgia delle ore partendo
dai testi di Profesores (https://profesores.pages.dev/data/) e della CEI
(https://www.chiesacattolica.it/la-liturgia-delle-ore/).
L'idea è di poter disporre di un file unico mensile per e-Reader senza dove avere
connessione a internet. Per utilizzare il programma:

- è necessario usare un computer desktop e aver installato Python 3
- basta scaricare il file: liturgia_epub.py e metterlo in una cartella
- dalla cartella si lancia il terminale e si dà il comando: py liturgia_epub.py aaaa-mm
  (sostituire "py" con "python3" su Mac e Linux; aaaa per l'anno, mm per il mese,
  ad es. 2026-12 per dicembre 2026).

Programma sviluppato con Claude free e Chatgpt plus.

# Liturgia delle Ore → ePub

Un piccolo programma Python per raccogliere in un ePub mensile i testi disponibili
sui siti Profesores e della Conferenza Episcopale Italiana, per la lettura personale offline.

**Progetto indipendente e non ufficiale, non affiliato alla CEI.** È un semplice
strumento da terminale; per i servizi e le applicazioni ufficiali fai riferimento
al [sito CEI](https://www.chiesacattolica.it/la-liturgia-delle-ore/).
Il download del programma non include testi liturgici, cache o ePub.

## Scarica il programma

**[Scarica il programma aggiornato](https://github.com/Giovanni-falsegeek/liturgia-ore-epub/archive/refs/heads/main.zip)**

L’archivio contiene il programma, le istruzioni, la licenza e i test.
La release v1.0.1 precedente usa ancora soltanto la CEI.
Estrai tutti i file in una cartella. Non occorre un account GitHub per scaricarli.

## Cosa serve

- Python 3.9 o successivo, scaricabile da [python.org](https://www.python.org/downloads/).
- Una connessione a internet durante il download dei testi.
- Un lettore ePub per aprire il risultato, anche offline.

Non servono pacchetti Python aggiuntivi.

## Come si usa

Apri il terminale nella cartella estratta. Su Windows esegui:

```console
py liturgia_epub.py 2026-11
```

Su macOS o Linux:

```console
python3 liturgia_epub.py 2026-11
```

Sostituisci `2026-11` con il mese desiderato, nel formato anno-mese.
Per provare soltanto il 3 novembre:

```console
py liturgia_epub.py 2026-11 --dal 3 --al 3
```

Attendi il messaggio `Creato:` e apri il file `.epub` indicato con il tuo lettore.

## Opzioni

| Opzione | Funzione |
| --- | --- |
| `--dal N` | Primo giorno (predefinito: 1) |
| `--al N` | Ultimo giorno (predefinito: fine mese) |
| `--giorni N` | Numero di giorni da scaricare, a partire da `--dal` |
| `-o CARTELLA` | Cartella di destinazione (predefinita: quella corrente) |
| `--cache CARTELLA` | Cartella della cache (predefinita: `cache_liturgia`) |
| `--pausa SEC` | Pausa tra le richieste (predefinita: 0.7 secondi) |

Il programma crea l’ePub, un riepilogo delle celebrazioni e una cache delle pagine.
Gli intervalli di giorni hanno nomi distinti dal volume del mese completo.
Un mese intero richiede qualche minuto. Se il download si interrompe, rilancia lo
stesso comando: le pagine già scaricate vengono riutilizzate.

## Memorie facoltative e indice

Ogni giorno contiene cinque sezioni, in questo ordine:

1. **Invitatorio e Lodi mattutine** — Profesores, nella stessa pagina, con
   l’introduzione ordinaria delle Lodi omessa dopo l’Invitatorio.
2. **Ufficio delle letture** — CEI.
3. **Ora media** — CEI, con Ora terza, sesta e nona come in precedenza.
4. **Vespri** — Profesores.
5. **Compieta** — CEI, comprese le varianti festive e della vigilia.

Ogni fonte segue il proprio calendario. I titoli delle celebrazioni possono quindi
essere diversi nello stesso giorno: il titolo Profesores compare nelle pagine
Invitatorio e Lodi e Vespri; le altre ore riportano il titolo CEI.
Sono incluse tutte le alternative del selettore CEI per le ore provenienti dalla
CEI. In ciascuna versione vengono ripetuti Invitatorio, Lodi e Vespri del giorno
di Profesores, senza adattarli alla memoria CEI.

L’indice segue data → celebrazione CEI → cinque sezioni, con Ora terza, sesta e
nona sotto Ora media. Nei giorni senza alternative resta data → sezioni.
I collegamenti Precedente, Indice e Successiva permettono la lettura sequenziale.
La Compieta festiva segue i collegamenti CEI e può provenire dalla data successiva;
i Vespri seguono sempre la data e il titolo indicati da Profesores.

I percorsi Profesores sono ricavati dagli indici `lit.json` e `vesp.json`:
`lodi/AAAAMMGG-N.html`, `inv/AAAAMMGG.html` (oppure `-def.html` per i defunti)
e `vesp/AAAAMMGG.html`. Sono riconosciute anche le varianti `sms` del sabato.
La cache Profesores si trova in `cache_liturgia/profesores/`, separata da quella CEI.
Se la data manca dagli indici o il testo non è disponibile, il programma si ferma:
non sostituisce le ore mancanti con la CEI. Per aggiornare gli indici, rimuovi
`lit.json` e `vesp.json` dalla tua cache Profesores e rilancia il programma.
Per aggiornare un testo già scaricato, rimuovi soltanto il suo file dalla cache.

## Se qualcosa non funziona

- Controlla mese e intervallo richiesti.
- Per un download fallito, controlla la connessione e riprova.
- Se compare un errore di data, ora o memoria, conserva il messaggio e il file
  della cache indicato. Il sito potrebbe avere cambiato struttura.
- Se gli identificativi CEI delle memorie sono cambiati, rimuovi dalla tua cache
  tutte le pagine della data segnalata e rilancia il comando.

Le pagine non valide vengono conservate per il controllo; in questi casi il
programma si ferma prima di generare un nuovo ePub parziale.

## Licenza e contenuti

Il software è distribuito con [licenza MIT](LICENSE). Questa licenza riguarda
esclusivamente il programma, non i testi scaricati da Profesores o dalla CEI.
I testi liturgici restano dei rispettivi titolari. Il programma li recupera sul
computer di chi lo esegue, per la lettura personale offline.

## Ringraziamenti

Il progetto è stato sviluppato con il supporto di **Claude (Anthropic)** e
**ChatGPT (OpenAI)** per codice, risoluzione dei problemi, test e documentazione.
Le scelte progettuali e la revisione finale restano a cura del responsabile del
progetto.

## Test

```console
py -m unittest discover -s tests -v
```

I test usano dati inventati e funzionano senza connessione. Verificano ordine,
fonti, calendari indipendenti, alternative CEI, Compieta della vigilia e indici ePub.
