import utility
import key
import telegram
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
BUTTON_CONTINUE_MULTI = ['⏭️ CONTINUA','🤔 E QUINDI?', '⏭️ AVANTI']
BUTTON_NEXT_MISSION = '🎳 PROSSIMA MISSIONE'
BUTTON_END = '🎇 FINE'
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

BUTTON_SI_CALLBACK = lambda x: telegram.InlineKeyboardButton(
    text = '✅ SI',
    callback_data = x
)

BUTTON_NO_CALLBACK = lambda x: telegram.InlineKeyboardButton(
    text = '❌ NO',
    callback_data = x
)


####################
# CONVERSATIONS
####################

MSG_WORK_IN_PROGRESS = "🏗 Il sistema è in aggiornamento, ti preghiamo di riprovare più tardi."
MSG_MISSION_N_TOT = '*🎳 Missione {}/{}*'
MSG_PRESS_TO_START = "Quando siete pronti per iniziare premete il pulsante."
MSG_GO = '🏃‍♂️🏃‍♀️ Si parte!'
MSG_WELCOME = 'Ciao! 😀 Benvenuto nella caccia al tesoro di hiSTORIC: *{}*!'
MSG_GROUP_NAME = 'Come prima cosa scegliete un *nome per la vostra squadra*.'
MSG_GROUP_NAME_OK = 'Bene, *{}* mi sembra un bellissimo nome! 😉'
MSG_GROUP_NAME_INVALID = 'Il nome che hai inserito deve contenere *solo lettere o spazi*.\nRiprova.'
MSG_GROUP_NAME_TOO_LONG = 'Il nome che hai inserito è troppo lungo.\nInseritene uno con *al massimo {} caratteri*.'
MSG_GPS_OK = '👏 Bravi, siete arrivati!'
MSG_GO_TO_PLACE = '📍 Recatevi nel seguente luogo e quando siete arrivati mandatemi la vostra posizione!'
MSG_TOO_EARLY = "⏱️Troppo presto! Prova tra {} secondi."
MSG_SELFIE_INIZIALE = '📷 Ora voglio vedere quanto belli siete.\nMandatemi un bel selfie di gruppo!\n\n⏱️ Appena mi invierete la foto darò il via al tempo.'
MSG_SELFIE_INIZIALE_OK = 'Fantastico! Siete stupendi! 😀\nOra possiamo inziare con la *prima missione*.'
MSG_START_TIME = "⏱ Via al tempo!"
MSG_TOO_FAR = "Siete ancora un po' lontani, il posto che dovete raggiungere è a *{} metri* in distanza aerea da dove vi trovate ora.\n\nSe pensate di essere arrivati al punto giusto potrebbe esserci un problema di aggiornamento del GPS del vostro dispositivo. In tal caso riprovate mandandomi la posizione premendo la graffetta 📎 in basso e mandatemi la posizione corretta sulla mappa."
MSG_ANSWER_OK = '🤗 Risposta esatta!'
MSG_ANSWER_ALMOST = '🙄 Ci sei quasi!'
MSG_ANSWER_WRONG_SG = '🤔 Risposta sbagliata, riprova!\n\n⚠️ Attenzione, hai totalizzato {} risposta sbagliata che comporta una penalità di {} secondi.'
MSG_ANSWER_WRONG_PL = '🤔 Risposta sbagliata, riprova!\n\n⚠️ Attenzione, hai totalizzato {} risposte sbagliate che comportano una penalità di {} secondi.'
MSG_ANSWER_WRONG_NO_PENALTY =  '🤔 Risposta sbagliata, riprova!'
MSG_INPUT_SELFIE_MISSIONE = "📷 Ora mandatemi un vostro selfie assieme all'oggetto dell'indovinello."
MSG_INPUT_RECORDING_MISSIONE = "🎤 Ora mandatemi una registrazione in base alle istruzioni."
MSG_WAIT_SELFIE_APPROVAL = 'Rimanete in attesa qualche istante prima che il selfie venga verificato.'
MSG_WAIT_VOICEE_APPROVAL = 'Rimanete in attesa qualche istante prima che la registrazione venga verificato.'
MSG_MEDIA_INPUT_MISSIONE_OK = 'Fantastico! 😀'
MSG_SELFIE_MISSIONE_WRONG = "🤔 Mi dispiace, il selfie non è stato accettato perché non rappresenta l'oggetto dell'indovinello.\n\n📷 Riprova a mandarmi un nuovo selfie!"
MSG_RECORDING_MISSIONE_WRONG = "🤔 Mi dispiace, la registrazione non è stata accettata.\n\n🎤 Riprova a mandarmi una nuova registrazione!"
# MSG_NEXT_GIOCO = '🎲 Ecco un piccolo gioco prima della prossima missione.'
MSG_TIME_STOP = '⏱ Stop al tempo!'
MSG_CONGRATS_PRE_SURVEY = '🎉 Bravissimi, avete concluso la caccia al tesoro! 🎊'
MSG_SURVEY_INTRO = '📋 Prima di dirvi quanto ci avete messo, vorrei farvi alcune domande...'
MSG_END = '🏆 Bravi!\n\nAvete completato la caccia al tesoro in *{1}*!!\n({2} tempo + {0} penalità)\n\nAvete completato le missioni in *{3}*!!\n({4} tempo + {0} penalità)'
MSG_GO_BACK_TO_START = '🏘 Ritorna al punto di partenza per la premiazione!'
MSG_END_NOTIFICATION = "La squadra *{0}* ha completato la caccia al tesoro in *{2}* ({3} tempo + {1} penalità).\nHa completato le missioni in *{4}*!! ({5} tempo + {1} penalità)."
MSG_WRONG_INPUT_USE_BUTTONS = '⛔️ Input non valido, usa i bottoni qui sotto 🎛'
MSG_WRONG_INPUT_INSERT_TEXT = '⛔️ Input non valido, devi rispondere con del testo.'
MSG_WRONG_INPUT_INSERT_TEXT_OR_BUTTONS = '⛔️ Input non valido, devi rispondere con del testo o usa i bottoni qui sotto 🎛'
MSG_WRONG_INPUT_SEND_PHOTO = "⛔️ Input non valido, devi mandarmi una foto. Usa l'iconda della macchina fotografica 📷 qua in basso o allega un'immagine dalla tua galleria con la graffetta 📎."
MSG_WRONG_INPUT_SEND_VOICE = "⛔️ Input non valido, devi mandarmi una registrazione vocale. Usa l'iconda del microfono 🎤 qua in basso."
MSG_WRONG_INPUT_SEND_LOCATION = '⛔️ Input non valido, devi mandarmi la tua posizione premendo il pulsante qua sotto o premendo sul simbolo della graffetta in basso 📎 e selezionando POSIZIONE dal menu che compare. Ricordati che devi avere il GPS attivo.'
MSG_NO_FORWARDING_ALLOWED = '⛔️ Input non valido! Non puoi inoltrarmi informazioni!'
MSG_EMAIL = '📧 Potete lasciarci i vostri indirizzi email (separati da spazio) per informarvi di altre iniziative simili?'
MSG_EMAIL_WRONG = '⛔️ Input non valido, devi inserire uno o più indirizzi email o premere su ⏩ SALTA.'
MSG_EXITED_FROM_GAME = "🚪 Sei uscito/a dal gioco!"
MSG_PRESS_FOR_NEXT_MISSION = "🎳 Premi sul pulsante per andare alla prossima missione."
MSG_PRESS_FOR_ENDING = "🎇 Premi sul pulsante per terminare il gioco."