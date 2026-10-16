# Presentazione semplice

Questo "programma" serve per creare un file ePub della liturgia delle ore partendo
dai testi CEI disponibili sul sito https://www.chiesacattolica.it/la-liturgia-delle-ore.
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
sul sito della Conferenza Episcopale Italiana, per la lettura personale offline.

**Progetto indipendente e non ufficiale, non affiliato alla CEI.** È un semplice
strumento da terminale; per i servizi e le applicazioni ufficiali fai riferimento
al [sito CEI](https://www.chiesacattolica.it/la-liturgia-delle-ore/).
Il download del programma non include testi liturgici, cache o ePub.

## Scarica il programma

**[Scarica Liturgia-ePub-v1.0.0.zip](https://github.com/Giovanni-falsegeek/liturgia-ore-epub/releases/download/v1.0.0/Liturgia-ePub-v1.0.0.zip)**

L’archivio contiene soltanto programma, queste istruzioni e licenza.
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

Sono incluse tutte le alternative proposte dal selettore CEI. Ciascuna celebrazione
ha sei pagine: Invitatorio, Ufficio delle letture, Lodi mattutine, Ora media,
Vespri e Compieta. I testi vengono scaricati separatamente; alcune ore possono
coincidere nella fonte.

L’indice segue data → celebrazione → ore, con Ora terza, sesta e nona sotto Ora
media. Nei giorni senza alternative resta data → ore. I collegamenti Precedente,
Indice e Successiva permettono la lettura sequenziale, anche tra le alternative.
Per le sere festive vengono selezionati i primi o secondi Vespri pertinenti dal
menu CEI; le pagine della vigilia possono provenire dalla data successiva.

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
esclusivamente il programma, non i testi scaricati dal sito CEI.
I testi liturgici restano dei rispettivi titolari. Il programma li recupera sul
computer di chi lo esegue, per la lettura personale offline.

## Ringraziamenti

Il progetto è stato sviluppato con il supporto di **Claude (Anthropic)** e
**ChatGPT (OpenAI)** per codice, risoluzione dei problemi, test e documentazione.
Le scelte progettuali e la revisione finale restano a cura del responsabile del
progetto.
