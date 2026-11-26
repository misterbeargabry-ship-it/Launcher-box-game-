# GAMEBOX PC v2.0

Launcher gaming desktop per Windows 10/11, sviluppato in Python 3 con
PySide6, SQLite e ADB. Permette di organizzare, importare e avviare
giochi PC (.exe) e app/giochi Android (.apk tramite emulatore).

---

## 1. Requisiti

- Windows 10 o Windows 11
- Python 3.10 o superiore ([python.org](https://www.python.org/downloads/),
  seleziona **"Add Python to PATH"** durante l'installazione)
- (Per gli APK) un emulatore Android gia' installato, ad esempio
  **BlueStacks**, **NoxPlayer**, **MEmu**, oppure l'Android Emulator di
  Android Studio. In alternativa, un dispositivo Android reale con il
  **debug USB** attivato.
- Android Platform Tools (ADB) — scaricabili gratuitamente dal sito
  ufficiale Android: https://developer.android.com/tools/releases/platform-tools
  (molti emulatori includono gia' un proprio ADB: in tal caso basta
  indicarne il percorso nelle Impostazioni di GAMEBOX PC).

---

## 2. Avvio rapido (senza creare l'eseguibile)

1. Estrai la cartella `GAMEBOX_PC` dove preferisci (es. `C:\GAMEBOX_PC`).
2. Fai doppio clic su **`Avvia_GAMEBOX.bat`**.
   - Al primo avvio lo script crea automaticamente un ambiente virtuale
     Python (`venv`) e installa tutte le dipendenze da `requirements.txt`.
   - Ai lanci successivi l'avvio sara' immediato.
3. Si aprira' la finestra di GAMEBOX PC.

Se preferisci farlo manualmente da terminale:

```bat
cd GAMEBOX_PC
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## 3. Creare l'eseguibile GAMEBOX.exe

1. Apri la cartella `GAMEBOX_PC` su Windows.
2. Fai doppio clic su **`build.bat`** (oppure eseguilo da terminale).
3. Lo script:
   - crea/attiva un ambiente virtuale;
   - installa le dipendenze, incluso PyInstaller;
   - genera l'eseguibile con `pyinstaller --onefile --windowed`;
   - prepara le sottocartelle `data`, `Games`, `APK`, `Downloads` accanto
     all'eseguibile.
4. Al termine troverai **`GAMEBOX.exe`** dentro la cartella `dist\`.
5. Copia l'intera cartella `dist` dove vuoi distribuire il programma:
   contiene l'eseguibile e le cartelle dati necessarie per il
   funzionamento (libreria, database, download).

> Nota: il database SQLite e il file delle impostazioni vengono creati
> automaticamente al primo avvio nella sottocartella `data/`, accanto
> all'eseguibile (o al file `main.py` in modalita' sviluppo).

---

## 4. Funzionalita' principali

### Schermata di avvio e Home stile console
- All'apertura, GAMEBOX PC mostra una schermata di boot animata (logo
  pulsante + anello di caricamento rotante) per circa 1,8 secondi.
- La prima pagina ("🏠 Home") e' una dashboard in stile console: fila
  orizzontale di copertine grandi, sfondo con bagliore dinamico che
  cambia colore in base al gioco selezionato, navigazione con le
  frecce della tastiera (◀ ▶), Invio/Spazio per avviare, click/doppio
  click con il mouse.
- Il ciclo di animazione dello sfondo e del bordo luminoso gira a un
  intervallo interno di ~8 ms (~120 Hz) per la massima fluidita'
  possibile. La fluidita' realmente visibile dipende pero' dal monitor:
  su schermi a 60 Hz l'immagine restera' comunque vincolata a 60 Hz; su
  monitor a 120 Hz o superiori si vedra' piu' fluida.
- Non si tratta di una copia pixel-per-pixel dell'interfaccia PS5 (design
  proprietario Sony, non riproducibile): e' un'interfaccia originale,
  ispirata nello spirito (grandi copertine, sfondo dinamico, selezione
  evidenziata), coerente con il tema grafico nero/blu/viola di GAMEBOX PC.

### Libreria giochi
- Aggiunta manuale di giochi PC tramite selezione del file `.exe`.
- Importazione di file `.apk` (copiati in modo permanente nella cartella
  `APK/`).
- Copertine personalizzate (opzionali), categorie, ricerca testuale.
- Rilevamento delle applicazioni gia' installate su Windows (lettura del
  registro di sistema, chiavi "Uninstall") per importarle rapidamente.
- Eliminazione dalla libreria (il file originale non viene toccato).
- Creazione di collegamenti rapidi: se il pacchetto opzionale `pywin32` e'
  installato viene creato un vero collegamento `.lnk`; altrimenti viene
  generato un file `.bat` equivalente e funzionante.

### Supporto Windows
- Avvio dei giochi tramite `subprocess.Popen` sull'eseguibile autorizzato
  dall'utente, eseguito nella sua cartella di lavoro originale.
- Nessun percorso o azione viene inventata: ogni gioco punta a un file
  realmente presente sul disco, verificato prima dell'avvio.

### Supporto Android (APK)
GAMEBOX PC **non esegue file APK direttamente su Windows** (tecnicamente
impossibile senza un motore di compatibilita'): si appoggia ad ADB per
pilotare un emulatore Android gia' installato dall'utente, oppure un
dispositivo fisico con debug USB attivo.
- Importazione e conservazione permanente dei file `.apk`.
- Rilevamento automatico del nome del pacchetto tramite `aapt` (se
  disponibile negli Android SDK Build-Tools); altrimenti puoi inserirlo
  manualmente.
- Installazione sull'emulatore/dispositivo con `adb install`.
- Elenco dei pacchetti installati, avvio e disinstallazione.
- Indicatore di stato ADB/emulatore sempre visibile nella pagina "APK
  Android" e nella Dashboard.

### Download
- Aggiunta di collegamenti a installer da **fonti ufficiali** indicate
  dall'utente (nessun contenuto piratato, nessun aggiramento di DRM).
- Download in background con barra di progresso in tempo reale.
- Calcolo automatico dell'hash SHA-256 del file scaricato e confronto
  con un hash atteso (se fornito dall'utente/distributore ufficiale),
  per verificare l'integrita' prima dell'installazione.
- Apertura rapida della cartella di destinazione.

### Impostazioni
- Risoluzione dell'interfaccia (richiede riavvio).
- Tema grafico (Scuro Blu/Viola).
- Percorsi personalizzabili per libreria, APK e download.
- Percorso ADB/aapt ed eseguibile dell'emulatore Android (con pulsante
  "Avvia emulatore").
- Supporto controller/gamepad tramite `pygame` (rilevamento e nome dei
  dispositivi collegati).

---

## 5. Struttura del progetto

```
GAMEBOX_PC/
├── main.py                 # Punto di ingresso dell'app
├── database.py              # Schema e connessione SQLite
├── game_manager.py          # Libreria giochi, avvio EXE, rilevamento app
├── apk_manager.py           # Gestione APK tramite ADB
├── download_manager.py      # Download con progresso e verifica SHA-256
├── settings.py               # Impostazioni persistenti (JSON)
├── requirements.txt
├── build.bat                 # Genera GAMEBOX.exe con PyInstaller
├── Avvia_GAMEBOX.bat          # Avvio rapido da sorgente
├── README.md
├── ui/
│   ├── main_window.py         # Finestra principale + menu laterale
│   ├── dashboard_page.py
│   ├── library_page.py
│   ├── apk_page.py
│   ├── download_page.py
│   ├── settings_page.py
│   ├── styles.py                # Tema grafico QSS
│   └── widgets/
│       └── game_card.py
├── assets/
│   ├── icons/                    # Icona applicazione (gamebox.ico/.png)
│   └── covers/                    # Copertine importate dall'utente
├── data/                            # Database SQLite + settings.json (creati al primo avvio)
├── Games/                            # Cartella di riferimento/collegamenti rapidi
├── APK/                               # File APK importati
└── Downloads/                          # File scaricati
```

---

## 6. Limitazioni note (dichiarate onestamente)

- Il rilevamento automatico delle app installate (lettura registro di
  Windows) funziona **solo su Windows**; su altri sistemi la funzione e'
  disabilitata con un messaggio esplicativo.
- L'esecuzione di APK **non avviene nativamente su Windows**: e' sempre
  necessario un emulatore Android installato separatamente e raggiungibile
  da ADB.
- Il rilevamento del "nome pacchetto" di un APK richiede lo strumento
  `aapt` (incluso negli Android SDK Build-Tools); se non disponibile va
  inserito manualmente nell'interfaccia.
- La creazione di collegamenti `.lnk` reali richiede il pacchetto opzionale
  `pywin32`; senza di esso viene creato un file `.bat` funzionalmente
  equivalente.
- Il supporto controller tramite `pygame` richiede che il pacchetto sia
  installato (incluso in `requirements.txt`).

---

## 7. Supporto

In caso di errori, GAMEBOX PC mostra sempre un messaggio esplicativo
nell'interfaccia (nessun crash silenzioso). Controlla innanzitutto:
- che Python e le dipendenze siano installate correttamente;
- che i percorsi configurati nelle Impostazioni esistano davvero;
- che, per gli APK, l'emulatore sia avviato e visibile con
  `adb devices` da riga di comando.


## 8. Novita' della versione 2.0

- Percorsi separati per risorse incluse e dati scrivibili: il database e le
  impostazioni vengono salvati nella cartella dati utente (AppData\\Local\\GAMEBOX_PC su Windows), anche con PyInstaller.
- Salvataggio atomico delle impostazioni e recupero del JSON danneggiato
  tramite copia `settings.json.corrotto`.
- Database SQLite con timeout e modalita' WAL per ridurre i conflitti di accesso.
- Download temporanei `.part`, verifica della dimensione ricevuta e pubblicazione
  del file solo dopo il completamento.
- Se viene fornito uno SHA-256, un hash errato blocca il completamento e il file
  non viene presentato come verificato. Senza hash il download e' indicato come
  non verificato, non come sicuro.
- Controllo del formato SHA-256, nomi file ripuliti, gestione dei nomi duplicati,
  timeout di rete e annullamento con pulizia del file temporaneo.
- Protezione contro l'avvio doppio e la rimozione di un download attivo.
- Build Windows aggiornata e versione mostrata nell'interfaccia: v2.0.

### Limiti che restano

GAMEBOX PC v2.0 e' un launcher, non un emulatore PS5/Xbox. Avvia giochi PC
Windows tramite i rispettivi eseguibili e gestisce APK appoggiandosi a un
emulatore Android esterno collegato ad ADB. Non garantisce compatibilita'
universale, FPS specifici o prestazioni di emulazione.
