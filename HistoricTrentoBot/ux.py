# -*- coding: utf-8 -*-

import utility
import key

# ================================
# BUTTONS
# ================================

START_BUTTON = "🚩 START"
HELP_BUTTON = "🆘 HELP"

CHECK_ICON = '✅'
BULLET_SYMBOL = '∙'
RIGHT_ARROW_SYMBOL = '→'

BUTTON_SI = '✅ SI'
BUTTON_NO = '❌ NO'
BUTTON_INDIETRO = "🔙 INDIETRO"
BUTTON_INIZIO = "🏠 TORNA ALL'INIZIO"
BUTTON_INFO = "ℹ INFO"
BUTTON_ANNULLA = "❌ ANNULLA"
BUTTON_CONTATTACI = "📩 CONTATTACI"
BUTTON_ADMIN = "🔑 Admin"

BUTTON_START_GAME = '🎯 INIZIA IL GIOCO'
BUTTON_GPS = '📍 POSIZIONE'
BUTTON_SKIP_EMAIL = '⏩ SALTA'

BUTTON_LOCATION = {
    'text': BUTTON_GPS,
    'request_location': True,
}

BUTTON_SI_CALLBACK = lambda x: {
    'text': '✅ SI',
    'callback_data': x,
}

BUTTON_NO_CALLBACK = lambda x: {
    'text': '❌ NO',
    'callback_data': x,
}

####################
# CONVERSATIONS
####################

MSG_PRESS_TO_START = "Quando siete pronti per iniziare premete il pulsante. ⏱ Il cronometro partirà appena premete il pulsante."
MSG_GO = '🏃‍♂️🏃‍♀️ Si parte!'
MSG_WELCOME = 'Ciao! 😀 Benvenuto nel gioco di hiSTORIC di {}!'
MSG_GROUP_NAME = 'Come prima cosa scegliete un *nome per la vostra squadra*.'
MSG_GROUP_NAME_OK = 'Bene, *{}* mi sembra un bellissimo nome! 😉'
MSG_GROUP_NAME_INVALID = 'Il nome che hai inserito deve contenere *solo lettere o spazi*.\nRiprova.'
MSG_GROUP_NAME_TOO_LONG = 'Il nome che hai inserito è troppo lungo.\nInseritene uno con *al massimo 15 caratteri*.'
MSG_GPS_OK = 'Bravi, siete arrivati nei pressi della prossima missione!'
MSG_GO_TO_PLACE = '📍 Recatevi nel seguente luogo e quando siete arrivati mandatemi la vostra posizione!'
MSG_TOO_EARLY = "⏱️Troppo presto! Pensaci ancora un po'..."
MSG_SELFIE_INIZIALE = '📷 Ora voglio vedere quanto belli siete.\nMandatemi un bel selfie di gruppo!'
MSG_SELFIE_INIZIALE_OK = 'Fantastico! Siete stupendi! 😀\nOra possiamo inziare con la *prima missione*.'
MSG_TOO_FAR = "Siete ancora un po' lontani, il posto che dovete raggiungere è a *{} metri* in distanza aerea da dove vi trovate ora."
MSG_ANSWER_OK = '🤗 Risposta esatta!'
MSG_ANSWER_ALMOST = '🙄 Ci sei quasi!'
MSG_ANSWER_WRONG_SG = '🤔 Risposta sbagliata, riprova!\n\n⚠️ Attenzione, hai totalizzato {} risposta sbagliata che comporta una penalità di {} secondi.'
MSG_ANSWER_WRONG_PL = '🤔 Risposta sbagliata, riprova!\n\n⚠️ Attenzione, hai totalizzato {} risposte sbagliate che comportano una penalità di {} secondi.'
MSG_SELFIE_INDOVINELLO = "📷 Ora mandatemi un vostro selfie assieme all'oggetto dell'indovinello."
MSG_WAIT_SELFIE_APPROVAL = 'Rimanete in attesa qualche istante prima che il selfie venga verificato.'
MSG_SELFIE_INDOVINELLO_OK = 'Fantastico! 😀'
MSG_SELFIE_INDOVINELLO_WRONG = "🤔 Mi dispiace, il selfie non è stato accettato perché non rappresenta l'oggetto dell'indovinello.\nRiprova a mandarmi un nuovo selfie! 📷"
MSG_NEXT_MISSION = '🎳 Prossima missione...'
MSG_NEXT_GIOCO = '🎲 Ecco un piccolo gioco prima della prossima missione.'
MSG_SURVEY_INTRO = '⌚ Stop al tempo!\n\n🎉 Bravissimi, avete concluso la caccia al tesoro 🎊!\n\n📋 Prima di dirvi quanto ci avete messo, vorrei farvi alcune domande...'
MSG_END = '🏆 Bravi! Avete completato la caccia al tesoro in *{}* secondi!! ({} tempo + {} penalità)'
MSG_END_NOTIFICATION = "La squadra *{}* ha completato la caccia al tesoro in *{}* ({} tempo + {} penalità)"
MSG_WRONG_INPUT_USE_BUTTONS = '⛔️ Input non valido, usa i bottoni qui sotto 🎛'
MSG_WRONG_INPUT_USE_TEXT = '⛔️ Input non valido, devi rispondere con del testo.'
MSG_WRONG_INPUT_USE_TEXT_OR_BUTTONS = '⛔️ Input non valido, devi rispondere con del testo o usa i bottoni qui sotto 🎛'
MSG_WRONG_INPUT_SEND_PHOTO = "⛔️ Input non valido, devi mandarmi una foto. Usa l'iconda della macchina fotografica 📷 qua in basso o allega un'immagine dalla tua galleria con la graffetta 📎."
MSG_WRONG_INPUT_SEND_LOCATION = '⛔️ Input non valido, devi mandarmi la tua posizione premendo il pulsante qua sotto. Ricordati di abilitare il GPS.'
MSG_EMAIL = '📧 Potete scriverci un indirizzo email per contattarvi per altre iniziative simili?'
MSG_EMAIL_WRONG = '⛔️ Input non valido, devi inserire un indirizzo email o premere su SALTA.'
