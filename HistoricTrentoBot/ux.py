# -*- coding: utf-8 -*-

import utility
import key

CONVERSAZIONI = utility.import_url_csv_to_dict_list(key.CONVERSAZIONI_URL)
# NAME,DESCRIPTION,STRING_IT,STRING_EN

STRINGS = {row['NAME']:row['STRING_IT'] for row in CONVERSAZIONI} #.replace('\\n','\n')

# ================================
# BUTTONS
# ================================

BOTTONE_LOCATION = {
    'text': STRINGS['BUTTON_GPS'],
    'request_location': True,
}

SI_BUTTON = lambda x: {
    'text': '✅ SI',
    'callback_data': x,
}

NO_BUTTON = lambda x: {
    'text': '❌ NO',
    'callback_data': x,
}


START_BUTTON = "🚩 START"
HELP_BUTTON = "🆘 HELP"

CHECK_ICON = '✅'
BULLET_SYMBOL = '∙'
RIGHT_ARROW_SYMBOL = '→'

BOTTONE_SI = '✅ SI'
BOTTONE_NO = '❌ NO'
BOTTONE_INDIETRO = "🔙 INDIETRO"
BOTTONE_INIZIO = "🏠 TORNA ALL'INIZIO"
BOTTONE_INFO = "ℹ INFO"
BOTTONE_ANNULLA = "❌ ANNULLA"
BOTTONE_CONTATTACI = "📩 CONTATTACI"
BOTTONE_ADMIN = "🔑 Admin"
