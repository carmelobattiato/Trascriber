# AudioScript - Trascrizione e Registrazione Audio Professionale

![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10-blue)


AudioScript è un'applicazione desktop con una GUI moderna (costruita con Tkinter/ttk) per la trascrizione **e la registrazione** audio professionale. Utilizza i potenti modelli Whisper di OpenAI per la trascrizione e include funzionalità di registrazione e riproduzione integrate. Consente agli utenti di:

*   Trascrivere facilmente file audio WAV (e altri formati caricati).
*   Registrare nuovo audio direttamente dall'applicazione.
*   Riprodurre audio registrato o caricato.
*   Selezionare diversi modelli Whisper per variare il compromesso velocità/accuratezza.
*   Scegliere la lingua per la trascrizione.
*   Sfruttare l'accelerazione GPU dove disponibile (MPS su Mac, DirectML su Windows).

![image](https://github.com/user-attachments/assets/6743d78d-4540-4133-ab92-ceaa9a4572dd)

---

## Features

*   **GUI User-Friendly:** Interfaccia pulita e intuitiva costruita con Tkinter e temi ttk.
*   **Integrazione Whisper:** Sfrutta Whisper di OpenAI per una precisione di trascrizione all'avanguardia.
*   **Selezione Modello Whisper:** Scegli tra vari modelli (`tiny`, `base`, `small`, `medium`, `large`) per bilanciare velocità e precisione.
*   **Supporto Lingue (Trascrizione):** Trascrivi audio in diverse lingue (Italiano, Inglese, Francese, Tedesco, Spagnolo, Giapponese, Cinese supportati inizialmente).
*   **Registrazione Audio Diretta:**
    *   Registra audio da un microfono collegato.
    *   Opzioni per selezionare **Sample Rate** e **Canali** (Mono/Stereo) per la registrazione.
    *   **Visualizzazione Forma d'Onda Live:** Guarda la forma d'onda mentre registri.
    *   **Timer di Registrazione:** Monitora la durata della registrazione in tempo reale.
*   **Riproduzione Audio:**
    *   Riproduci l'audio registrato all'interno dell'app.
    *   Carica e riproduci file audio esistenti (supporta WAV, MP3 e altri formati tramite `soundfile`).
*   **Salvataggio Registrazioni:** Salva l'audio registrato in formato **WAV** o **MP3**.
*   **Integrazione Registrazione/Trascrizione:** Opzione per impostare automaticamente un file audio appena salvato per la trascrizione.
*   **Accelerazione GPU:**
    *   Utilizza Metal Performance Shaders (MPS) su Mac compatibili.
    *   Utilizza DirectML su Windows con GPU integrate/discrete compatibili (tramite `torch-directml`).
    *   Fallback graduale alla CPU se la GPU non è disponibile o non configurata.
*   **Aggiornamenti in Tempo Reale (Trascrizione):** Visualizza i risultati della trascrizione man mano che vengono generati.
*   **Output Console:** Monitora il processo di trascrizione, visualizza log e dettagli dei file audio.
*   **Controllo Trascrizione:** Avvia e interrompi gradualmente il processo di trascrizione.
*   **Esportazione Facile (Trascrizione):**
    *   Copia il testo completo della trascrizione negli appunti.
    *   Salva la trascrizione in un file di testo (`.txt`).
*   **Indicazione di Progresso:** Feedback visivo sull'attività corrente e barra di avanzamento durante il caricamento del modello e la trascrizione.
*   **Info File Audio:** Visualizza automaticamente durata, canali e sample rate del file WAV selezionato (nella scheda Trascrizione) o dell'audio caricato/registrato (nella scheda Registra).

## Requisiti

*   **Sistema Operativo:**
    *   Windows 10/11 (Testato)
    *   macOS (Dovrebbe funzionare, specialmente con supporto MPS)
    *   Linux (Dovrebbe funzionare, supporto GPU dipende dall'installazione PyTorch, potrebbe richiedere `libportaudio2`)
*   **Python:** Versione 3.9 o 3.10 (Raccomandato per compatibilità Whisper, PyTorch, sounddevice).
*   **RAM:** 8GB minimo, 16GB+ raccomandato per modelli più grandi (`medium`, `large`).
*   **Disk Space:** Fino a 10GB se si scaricano tutti i modelli Whisper, ~2GB per il modello `large`.
*   **FFmpeg:** Richiesto da Whisper *e* per salvare in formato **MP3**. Deve essere installato e accessibile nel PATH di sistema.
    *   **Windows:** Scarica da [ffmpeg.org](https://ffmpeg.org/download.html) e aggiungi al PATH, o installa tramite package manager come Chocolatey (`choco install ffmpeg`) o Scoop (`scoop install ffmpeg`).
    *   **macOS:** Installa via Homebrew: `brew install ffmpeg`.
    *   **Linux (Debian/Ubuntu):** `sudo apt update && sudo apt install ffmpeg`.
*   **PortAudio:** Richiesto dalla libreria `sounddevice` per la registrazione/riproduzione audio.
    *   **Windows:** Solitamente incluso con Python o installabile separatamente se necessario.
    *   **macOS:** Installato con Homebrew potrebbe risolvere dipendenze (`brew install portaudio`).
    *   **Linux (Debian/Ubuntu):** `sudo apt update && sudo apt install libportaudio2`.
*   **Microfono:** Necessario per utilizzare la funzione di registrazione. L'applicazione richiederà i permessi di accesso al microfono al sistema operativo.

## Installazione

Segui questi passaggi per configurare AudioScript:

1.  **Clona il Repository:**
    ```bash
    git clone https://github.com/carmelobattiato/Trascriber.git # Sostituisci con l'URL del tuo repo
    cd audioscript # O il nome della cartella clonata
    ```

2.  **Installa Python:**
    Assicurati di avere Python 3.9 o 3.10 installato. Puoi scaricarlo da [python.org](https://www.python.org/). Durante l'installazione su Windows, assicurati di selezionare "Add Python to PATH".

3.  **Crea e Attiva un Ambiente Virtuale:** (Altamente Raccomandato)
    ```bash
    # Crea un ambiente virtuale chiamato 'venv'
    python -m venv venv

    # Attivalo:
    # Windows (cmd/powershell)
    .\venv\Scripts\activate
    # macOS/Linux (bash/zsh)
    source venv/bin/activate
    ```
    Dovresti vedere `(venv)` apparire all'inizio del prompt del terminale.

4.  **Installa le Dipendenze:**
    *   **Aggiorna Pip:**
        ```bash
        python -m pip install --upgrade pip
        ```
    *   **Installa PyTorch:** Scegli il comando che corrisponde al tuo sistema e alla configurazione GPU. Visita il [sito web di PyTorch](https://pytorch.org/get-started/locally/) per i comandi più recenti se necessario.

        *   **GPU NVIDIA (CUDA):** (Verifica la compatibilità della tua versione CUDA)
            ```bash
            # Esempio per CUDA 11.8 - Modifica se necessario
            pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
            ```
        *   **Windows con DirectML (Intel/AMD/NVIDIA):**
            ```bash
            pip install torch-directml
            # PyTorch CPU è necessario come base
            pip install torch torchaudio
            ```
        *   **macOS (CPU o MPS):**
            ```bash
            pip install torch torchaudio
            ```
        *   **Solo CPU (Qualsiasi OS):**
            ```bash
            pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
            ```

    *   **Installa Whisper:**
        ```bash
        pip install -U openai-whisper
        # O per la versione git più recente:
        # pip install git+https://github.com/openai/whisper.git
        ```
    *   **Installa Librerie Audio e GUI:**
        ```bash
        pip install sounddevice soundfile pydub numpy # sounddevice per rec/play, soundfile per caricamento/WAV, pydub per MP3
        ```
        *(Nota: numpy potrebbe essere già installato come dipendenza di PyTorch o Whisper)*
    *   **(Opzionale ma raccomandato) Installa setuptools-rust:** Richiesto dal tokenizer usato in Whisper se si compila dal sorgente o per certi aggiornamenti.
        ```bash
        pip install setuptools-rust
        ```

5.  **Scarica Modelli Whisper:**
    La prima volta che selezioni un modello nell'applicazione (nella scheda Trascrizione), verrà scaricato automaticamente (~decine di MB a ~1.5GB a seconda del modello). I modelli sono tipicamente cachati in `~/.cache/whisper` (Linux/macOS) o `C:\Users\<TuoUtente>\.cache\whisper` (Windows). *Non è necessario* pre-scaricarli a meno che tu non lo desideri.

6.  **Verifica FFmpeg e PortAudio:**
    Assicurati che FFmpeg sia installato e accessibile (vedi Requisiti). Apri un nuovo terminale e esegui:
    ```bash
    ffmpeg -version
    ```
    Se questo comando funziona, Whisper e Pydub dovrebbero trovarlo. Assicurati anche che PortAudio sia disponibile (vedi Requisiti).

## Usage

1.  **Attiva l'Ambiente Virtuale:**
    Se hai chiuso il terminale, naviga nuovamente nella directory `audioscript` e attiva l'ambiente virtuale (`.\venv\Scripts\activate` o `source venv/bin/activate`).

2.  **Avvia l'Applicazione:**
    ```bash
    python main.py
    ```

3.  **Utilizzo dell'Interfaccia:**
    *   **Navigazione tra Schede:** Usa le schede in alto per passare tra "Trascrizione" e "Registra & Riproduci".

    *   **Scheda Trascrizione:**
        *   **Seleziona File Audio:** Clicca "Sfoglia..." per scegliere un file `.wav` (o un file salvato dalla scheda Registra). I dettagli del file appariranno nel log della console.
        *   **Scegli Opzioni:**
            *   Seleziona il `Modello` desiderato (es. `large` per qualità migliore, `base` per velocità). La descrizione si aggiorna automaticamente.
            *   Seleziona la `Lingua (Trascrizione)` dell'audio.
            *   Spunta `Usa GPU` se vuoi tentare l'accelerazione hardware (richiede hardware compatibile e installazione corretta di PyTorch/DirectML). Passa il mouse sulla casella per dettagli.
        *   **Avvia Trascrizione:** Clicca "✓ Avvia Trascrizione".
        *   **Monitora Progresso:**
            *   La barra di stato in basso mostra la fase corrente (Caricamento modello, Trascrizione...).
            *   La barra di avanzamento si anima durante l'elaborazione attiva.
            *   La scheda "Console e Log" mostra messaggi dettagliati da Whisper.
            *   La scheda "Trascrizione" (nel notebook dei risultati) mostra il testo trascritto.
        *   **Interrompi Trascrizione:** Clicca "⨯ Interrompi Trascrizione" se necessario.
        *   **Ottieni Risultati:**
            *   Clicca "📋 Copia Testo" per copiare il testo.
            *   Clicca "💾 Salva Testo" per salvare il testo in un file `.txt`.

    *   **Scheda Registra & Riproduci:**
        *   **Opzioni Audio:** Seleziona il `Sample Rate (Hz)` e i `Canali` (Mono/Stereo) desiderati *prima* di registrare.
        *   **Registra:** Clicca "● Record" per iniziare la registrazione. Vedrai la forma d'onda live e il timer di registrazione. Clicca "■ Stop Recording" per fermare.
        *   **Salva Registrazione:** Dopo aver fermato la registrazione, ti verrà chiesto un nome file. Scegli il formato (WAV/MP3). Puoi scegliere se impostare questo file salvato per la trascrizione nella scheda apposita.
        *   **Carica Audio:** Clicca "Load Audio" per caricare un file audio esistente (WAV, MP3, ecc.). La forma d'onda verrà visualizzata.
        *   **Riproduci:** Clicca "▶ Play" per ascoltare l'audio attualmente registrato o caricato. Clicca "■ Stop Playing" per fermare la riproduzione.
        *   **Stato:** La barra di stato in basso e l'etichetta di stato nella scheda forniscono feedback sull'azione corrente (Recording..., Playing..., Saved...).

## Troubleshooting

*   **Errori di Trascrizione (CUDA out of memory, etc.):**
    *   Vedi la sezione Troubleshooting del README precedente (modelli grandi, GPU VRAM, FFmpeg non trovato).
*   **Problemi di Registrazione/Riproduzione:**
    *   **Nessun dispositivo audio / Errore PortAudio:**
        *   Assicurati che un microfono (per registrare) e altoparlanti/cuffie (per riprodurre) siano collegati e selezionati come predefiniti nel tuo sistema operativo.
        *   Verifica che `PortAudio` sia installato correttamente (vedi Requisiti, specialmente per Linux).
        *   Controlla i permessi dell'applicazione per accedere al microfono nel tuo sistema operativo (Windows Privacy Settings, macOS Security & Privacy).
        *   Prova a selezionare un diverso Sample Rate o Canali (alcuni dispositivi potrebbero non supportare tutte le combinazioni).
    *   **Errore Salvataggio MP3:**
        *   Assicurati che `FFmpeg` sia installato correttamente e nel PATH di sistema. Pydub lo richiede per l'esportazione MP3.
    *   **Registrazione/Riproduzione a scatti o distorta:**
        *   Potrebbe essere un problema di performance. Prova a chiudere altre applicazioni che consumano molte risorse.
        *   Assicurati che i driver audio siano aggiornati.
        *   Un Sample Rate molto alto (es. 48000 Hz) con Stereo potrebbe richiedere più risorse CPU/disco. Prova 16000 Hz Mono per la trascrizione.
*   **Prestazioni Lente (Trascrizione):**
    *   Vedi la sezione Troubleshooting del README precedente (modelli, GPU, qualità audio).
*   **Trascrizione Inaccurata / Problemi Lingua:**
    *   Vedi la sezione Troubleshooting del README precedente (selezione lingua, modello, qualità audio).
*   **Problemi DirectML (Windows):**
    *   Vedi la sezione Troubleshooting del README precedente (installazione `torch-directml`, driver).
*   **Applicazione Non Si Avvia / Errori Modulo Non Trovato:**
    *   Assicurati di aver attivato l'ambiente virtuale (`venv`).
    *   Verifica che tutte le dipendenze (inclusi `sounddevice`, `soundfile`, `pydub`) siano installate correttamente con `pip list`.

## Future Implementations / Roadmap

Questo progetto è funzionale ma può essere esteso ulteriormente. Potenziali miglioramenti futuri includono:

*   **[✓] Più Formati Audio:** Parzialmente implementato (caricamento MP3/ecc, salvataggio MP3).
*   **[ ] Elaborazione Batch (Trascrizione):** Possibilità di selezionare più file o una cartella per la trascrizione.
*   **[ ] Diarizzazione Speaker (Trascrizione):** Identificare ed etichettare diversi speaker.
*   **[ ] Timestamp (Trascrizione):** Opzione per includere timestamp (per parola o segmento) nell'output.
*   **[ ] Più Formati Esportazione (Trascrizione):** Salvare trascrizioni come SRT, VTT, DOCX, etc.
*   **[ ] Barra Progresso Deterministica (Trascrizione):** Mostrare percentuale effettiva basata sull'audio processato.
*   **[ ] Salvataggio Configurazione:** Ricordare ultimo modello, lingua, opzioni audio, dimensione finestra.
*   **[ ] Internazionalizzazione UI:** Tradurre la GUI stessa in altre lingue.
*   **[✓] Input Audio Diretto:** Implementato tramite la scheda di registrazione.
*   **[ ] Migliore Gestione Errori:** Messaggi di errore più specifici nella GUI.
*   **[ ] Opzioni Pre-processing:** Riduzione rumore base o normalizzazione audio.
*   **[ ] Selezione Dispositivo Input/Output (Registrazione/Riproduzione):** Permettere all'utente di scegliere microfono/altoparlanti.
*   **[ ] Indicatore Volume/Clipping (Registrazione):** Mostrare il livello del segnale in ingresso.
*   **[ ] Pausa/Riprendi Registrazione:** Mettere in pausa e riprendere la registrazione audio.
*   **[ ] Editing Audio Base (Registrazione):** Funzionalità semplice come il taglio (trim).

## Contributing

I contributi sono benvenuti! Se desideri aiutare a migliorare AudioScript, segui questi passaggi:

1.  **Forka il repository.**
2.  **Crea un nuovo branch** per la tua feature o bug fix:
    ```bash
    git checkout -b feature/your-feature-name # o fix/your-bug-fix
    ```
3.  **Apporta le tue modifiche.** Cerca di seguire lo stile del codice esistente.
4.  **Testa accuratamente le tue modifiche.**
5.  **Committa le tue modifiche:**
    ```bash
    git commit -m "feat: Add feature X" -m "Detailed description of changes." # O fix:, chore:, docs:, etc.
    ```
6.  **Pusha sul tuo fork:**
    ```bash
    git push origin feature/your-feature-name
    ```
7.  **Apri una Pull Request** contro il branch `main` del repository originale. Fornisci una descrizione chiara delle tue modifiche e del perché sono necessarie.

Se trovi un bug o hai un suggerimento per una feature, apri prima una issue nella scheda "Issues" del repository GitHub per discuterne.

---
