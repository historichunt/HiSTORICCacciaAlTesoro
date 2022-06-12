# Change Log

## 0.10
- Add JP language in UI
- Multilingual working
- Menu buttons (0.10.4)

## 0.9
- hunt route
- open hunts

## 0.8
- changelog (questo file)
- interfaccia UI tramite google spreadsheet

## 0.7
Check airtable hunt

## 0.6
Implementazione video (in introduzione per test e in missioni come media input).
Utilizzo di Airtable view per l’ordine delle righe
Rimuovere colonna “ORDER” in tabella “Instructions” delle cacce

## 0.5
Nella tabella Hunts della base CONFIG, il campo “Notify_Group” non è più un flag ma una reference alla tabella Notifications.

## 0.4
Nuova versione base CONFIG (questa)
Rinominato tabella Managers -> People
Aggiunta del flag Global Admins per accedere a comandi globali tipo UPDATE
Per avere controllo su delle cacce (STATS, TERMINATE), basta assegnare una persona ad una caccia come ADMIN in tabella HUNTS
Nuova interfaccia Admin
Comandi tipo /update e /terminate non più disponibili (solo /broadcast per il momento)
Inserita richiesta di conferma dopo aver premuto il pulsante TERMINATE

## 0.3
Nella tabella UX di ogni caccia si può fare override delle stringhe definite nei file json del codice.
Rinominato messaggi (vedi RESET_HUNT_AFTER_COMPLETION): 
FINAL_MESSAGE -> MSG_FINAL_RESET_OFF/MSG_FINAL_RESET_ON
TERMINATE_MESSAGE -> MSG_HUNT_TERMINATED_RESET_OFF/MSG_HUNT_TERMINATED_RESET_ON"

## 0.2
Spostato UX (stringhe) in file json nel codice (https://github.com/kercos/HiSTORICCacciaAlTesoro/tree/master/ux). 
Le stringhe specifiche per ogni caccia (FINAL_MESSAGE, TERMINATE_MESSAGE) vanno specificate nella base della caccia all'interno della tabella UX. 
Eliminare le due righe corrispondenti (FINAL_MESSAGE, TERMINATE_MESSAGE) nella tabella SETTINGS della caccia."

## 0.1
Versione di base