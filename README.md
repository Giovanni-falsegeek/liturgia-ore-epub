# Liturgia delle Ore → ePub

Programma Python per creare un ePub mensile dai testi disponibili sul sito CEI.
Include tutte le celebrazioni alternative proposte dal sito, con indice gerarchico.
Richiede Python 3.9 o successivo e usa esclusivamente la libreria standard.

## Avvio rapido

Scarica il repository ed estrailo in una cartella. Su Windows:

```console
py liturgia_epub.py 2026-11 --dal 3 --al 3
```

Su macOS e Linux sostituisci `py` con `python3`. Per un mese intero ometti
`--dal` e `--al`. I file vengono generati sul computer di chi esegue il programma.

## Contenuti e licenza

Questo repository distribuisce solo il programma, documentazione e test con dati
inventati. Non contiene testi liturgici, cache o ePub. Il software è distribuito
con licenza MIT (vedi LICENSE). La licenza del software non si estende ai contenuti
CEI scaricati. Il progetto non è un prodotto ufficiale della CEI.

## Test

```console
py -m unittest discover -s tests -v
```

I test funzionano senza connessione e non scaricano contenuti. GitHub Actions
esegue gli stessi controlli su Windows e Linux, con Python 3.9 e 3.13.

## Istruzioni complete

```text
LITURGIA DELLE ORE IN ePub - COME USARE IL PROGRAMMA
====================================================

COSA FA
-------
Lo script "liturgia_epub.py" scarica dal sito della CEI (chiesacattolica.it) i testi
della Liturgia delle Ore e li raccoglie in un file ePub da leggere offline.

Per ogni giorno scarica le sei ore: Invitatorio, Ufficio delle letture, Lodi mattutine,
Ora media, Vespri, Compieta.

L'ePub contiene:
  - un frontespizio con il periodo (es. "ottobre 2026" oppure "15-31 ottobre 2026");
  - un indice gerarchico: data, celebrazione (quando ci sono alternative), sei ore;
  - nell'Ora media, i sottotitoli "Ora terza", "Ora sesta" e "Ora nona", presenti sia
    nel testo sia come voci dell'indice sotto "Ora media" (fino al quarto livello);
  - in fondo a ogni pagina i link "Precedente / Indice / Successiva".

COSA SERVE
----------
Solo Python 3.9 o successivo. Non occorre installare nient'altro.
  - Mac / Linux: si lancia con  python3
  - Windows:     si lancia con  py

Serve la connessione a internet solo mentre lo script scarica i testi. Il file ePub
prodotto si legge poi offline.

COME SI USA
-----------
1. Metti "liturgia_epub.py" in una cartella.
2. Apri il terminale (su Windows: Prompt dei comandi) in quella cartella.
3. Lancia il comando. Il mese si scrive nel formato AAAA-MM (anno-mese).

Mese intero (es. novembre 2026):
    python3 liturgia_epub.py 2026-11

Solo un arco di giorni (es. dal 10 al 20 novembre):
    python3 liturgia_epub.py 2026-11 --dal 10 --al 20

Dal 15 a fine mese:
    python3 liturgia_epub.py 2026-11 --dal 15

Fino a un certo giorno (es. dal 1 al 12):
    python3 liturgia_epub.py 2026-11 --al 12

Prova rapida di un solo giorno (utile per controllare che tutto funzioni):
    python3 liturgia_epub.py 2026-11 --giorni 1
  (--giorni N scarica N giorni a partire da --dal; per esempio
   --dal 15 --giorni 3 scarica il 15, il 16 e il 17.)

Prova della feria e di San Martino de Porres (3 novembre 2026):
    python3 liturgia_epub.py 2026-11 --dal 3 --al 3

Su Windows sostituisci "python3" con "py".

OPZIONI
-------
  --dal N        primo giorno da scaricare (default: 1)
  --al N         ultimo giorno da scaricare (default: fine del mese)
  --giorni N     scarica solo N giorni a partire da --dal
  -o CARTELLA    cartella dove salvare l'ePub (default: la cartella corrente)
  --cache CART.  cartella delle pagine scaricate (default: cache_liturgia)
  --pausa SEC    secondi di attesa tra una richiesta e l'altra (default: 0.7)

Esempio con cartella di destinazione:
    python3 liturgia_epub.py 2026-11 -o ~/Documents/Liturgia

FILE CHE VENGONO CREATI
-----------------------
  Liturgia-delle-Ore-2026-11.epub              mese intero
  Liturgia-delle-Ore-2026-11_10-20.epub        arco di giorni (10-20 novembre)
  Liturgia-delle-Ore-2026-11-riepilogo.txt     elenco dei giorni con il titolo
                                               liturgico di ciascuno
  cache_liturgia/                              pagine scaricate (vedi sotto)

Il nome dell'ePub riporta il periodo, quindi un arco di giorni non sovrascrive il
file del mese intero.

TEMPI E CACHE
-------------
Un mese intero richiede qualche minuto (circa 180 pagine di base, piu' quelle delle
celebrazioni alternative e delle ore serali festive, con una pausa tra le richieste).

Le pagine scaricate restano nella cartella "cache_liturgia". Se il programma si
interrompe, basta rilanciare lo stesso comando: riparte da dove era arrivato e non
riscarica quello che ha gia'. Le pagine ordinarie mantengono i nomi precedenti:
    20261103_lodi-mattutine.html
Ogni alternativa ha una cache separata, con l'identificativo CEI:
    20261103_lodi-mattutine_memoria-1.html
Anche le ore festive esplicite hanno nomi propri (es. secondi-vespri).
Se vuoi forzare un nuovo download, rimuovi dalla tua copia della cache solo i file
segnalati nell'errore e rilancia. I file non validi non vengono eliminati dallo script.
Se compare "identificativi CEI potrebbero essere cambiati", aggiorna tutte le pagine
di quella data (feria e alternative): il sito puo' riordinare le memorie, rendendo
incompatibili il vecchio selettore in cache e le nuove pagine. Il controllo sui titoli
impedisce di associare a un santo il testo di un altro.

MEMORIE FACOLTATIVE
-------------------
Sono incluse automaticamente tutte le versioni proposte dal selettore CEI: la
celebrazione ordinaria e ciascuna memoria alternativa, anche se sono piu' di due.
Il programma legge i collegamenti "memoria" reali: non cerca la parola "facoltativa"
nei titoli e non presume che gli identificativi siano consecutivi.

Ogni versione ha sei pagine proprie e i testi scaricati dalla CEI con il parametro
corretto. Non vengono copiate le preghiere della feria cambiando solo il titolo.
Alcune ore possono coincidere nella fonte: il 3 novembre 2026 Ora media e Compieta
sono uguali per le due versioni, mentre le altre quattro ore hanno testi diversi.

Esempio dell'indice:
    Martedi' 3 novembre 2026
      MARTEDI' - XXXI SETTIMANA DEL TEMPO ORDINARIO - III SETTIMANA DEL SALTERIO
        Invitatorio
        Ufficio delle letture
        Lodi mattutine
        Ora media
          Ora terza
          Ora sesta
          Ora nona
        Vespri
        Compieta
      SAN MARTINO DE PORRES, RELIGIOSO - Memoria - III SETTIMANA DEL SALTERIO
        (le sue sei ore, con i relativi testi)

L'indice EPUB 3 e quello per lettori piu' vecchi (toc.ncx) hanno la stessa gerarchia.
Nei giorni senza alternative l'indice resta data -> ore -> eventuali sotto-ore.
La lettura sequenziale segue prima le sei ore della versione ordinaria, poi quelle
di ciascuna alternativa, poi il giorno successivo. I link Precedente / Indice /
Successiva funzionano anche nel passaggio tra due versioni della stessa data.
Il riepilogo contiene una riga per ogni versione, con data, memoria=N e titolo CEI.

Il programma controlla data, ora, titolo e selezione della memoria prima di usare
ogni pagina. Se il sito ignora l'alternativa richiesta o indica altre versioni che
non si riescono a identificare, si interrompe con un errore: non genera un nuovo
ePub incompleto. Un ePub gia' esistente non viene modificato in caso di questi errori.

VESPRI E COMPIETA FESTIVI
-----------------------
Il menu CEI puo' usare "secondi-vespri" e "compieta-dopo-i-secondi-vespri" anziche'
i nomi generici. Lo script usa quei collegamenti per la sera della festa. Quando
il menu del giorno non presenta ore serali, cerca i primi Vespri e la relativa
Compieta nella data della festa successiva. Nell'ePub restano sotto la data della
sera in cui si pregano, con un sottotitolo che indica la celebrazione della vigilia.
Questo puo' richiedere pagine del giorno successivo anche alla fine del periodo.
Le vecchie pagine generiche della cache non vengono usate al posto delle ore festive.
```


## Ringraziamenti

Il progetto è stato sviluppato con il supporto di **Claude (Anthropic)** e **ChatGPT (OpenAI)** per la scrittura del codice, la risoluzione dei problemi, i test e la documentazione.

Le scelte progettuali e la revisione finale restano a cura del responsabile del progetto.
