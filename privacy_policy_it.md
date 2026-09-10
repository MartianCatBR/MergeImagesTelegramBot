# Informativa sulla privacy — MergeImages

MergeImages tratta i file e i messaggi inviati volontariamente dagli utenti per eseguire le operazioni richieste. Immagini, PDF, GIF, testi OCR e contenuti dei codici QR elaborati non vengono inviati automaticamente all’amministratore.

Il servizio può trattare l’ID Telegram, il nome pubblico, la lingua, le preferenze, gli eventi di utilizzo e i ticket di assistenza. I log generali non devono memorizzare gli username; la colonna legacy può rimanere per compatibilità. Lo username viene usato solo nel flusso dei ticket quando è necessario contattare l’utente.

L’amministratore può ricevere metriche aggregate, tra cui il numero di azioni, immagini generate, codici QR, operazioni OCR, conversioni e utenti attivi. Quando un utente apre un ticket, il testo, il nome pubblico, lo username e l’ID Telegram possono essere inviati all’amministratore per analizzare il problema e rispondere. Non inserire password, token o documenti privati nei ticket.

La ricerca visiva richiede una conferma esplicita prima di inviare un’immagine a Telegra.ph o Catbox.moe e utilizzarla successivamente con Google Lens. Questi servizi hanno proprie politiche di conservazione. Gli endpoint del Mini App usano `initData` firmato da Telegram; CORS è limitato tramite `MINIAPP_ALLOWED_ORIGINS`, e CORS non sostituisce l’autenticazione. La diagnostica è riservata all’amministratore.

Il messaggio di supporto può essere inviato al massimo una volta dopo sette giorni di utilizzo e, separatamente, una volta quando viene raggiunta la quota di crediti. L’operatore deve definire i periodi di conservazione per file temporanei, database, log e ticket e offrire procedure di cancellazione o anonimizzazione. Non pubblicare mai token, chiavi API, database di produzione o credenziali.
