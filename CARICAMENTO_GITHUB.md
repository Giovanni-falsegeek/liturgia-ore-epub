# Caricamento iniziale su GitHub

1. Accedi a GitHub e crea un nuovo repository chiamato `liturgia-ore-epub`.
2. Seleziona **Private**. Lascia vuote le opzioni per README, licenza e gitignore:
   questi file sono già preparati qui.
3. Dalla pagina del repository scegli il caricamento di file esistenti e carica
   il contenuto di questa cartella, compresi `.github`, `.gitignore` e `.gitattributes`.
   Non caricare lo ZIP come unico file e non caricare la cartella di lavoro originaria.
4. Conferma il primo commit. Nella sezione Actions controlla l'esito dei test.

In alternativa, con Git e GitHub CLI già installati e autenticati, apri il terminale
in questa cartella ed esegui:

```console
git init -b main
git add .
git diff --cached --stat
git commit -m "Prima versione: generazione ePub con memorie alternative"
gh repo create liturgia-ore-epub --private --source=. --remote=origin --push
```

Usa uno solo dei due metodi. Il repository non è ancora stato creato online.
Git può richiedere la configurazione del tuo nome e indirizzo email per il commit.

## Passaggio futuro a pubblico

Il repository è già predisposto: README, licenza MIT, test automatici e istruzioni.
Quando vorrai renderlo pubblico, modifica la visibilità nelle impostazioni GitHub.
Conserva fuori dal repository i contenuti CEI anche nei commit futuri.
La licenza MIT riguarda solo il software; non concede diritti sui testi scaricati.
