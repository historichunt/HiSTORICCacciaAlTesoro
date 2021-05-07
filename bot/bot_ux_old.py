import os
import json
import telegram
import random
from airtable import Airtable
from bot import settings

UX_DIR = os.path.join(settings.ROOT_DIR, 'ux')
LANGS = ['IT','EN']

UX_TABLE = Airtable(settings.AIRTABLE_CONFIG_ID, 'UX', api_key=settings.AIRTABLE_API_KEY)
UX_DICT = None

def reload_ux():
    global UX_DICT
    UX_DICT = {
        r['VAR']: {
            lang: v.strip()
            for lang,v in r.items() if lang!='VAR'
            # 'IT': ...
            # 'EN': ...
        }
        for r in [
            row['fields'] 
            for row in UX_TABLE.get_all() 
        ]
    }

reload_ux()

class UX_LANG:
    
    def __init__(self, lang):
        assert lang in ['IT','EN']
        self.lang = lang

    def get_var(self, var):
        return UX_DICT.get(var, {self.lang: None})[self.lang]

    def __getattr__(self, attr):
        return UX_DICT.get(attr, {self.lang: None})[self.lang]

ux = lambda l: UX_LANG(l)

# ================================
# SPECIAL BUTTONS
# ================================

BUTTON_CONTINUE_MULTI = lambda l: [
        UX_LANG(l).BUTTON_CONTINUE_01,
        UX_LANG(l).BUTTON_CONTINUE_02,
        UX_LANG(l).BUTTON_CONTINUE_03
    ]

MSG_ANSWER_WRONG_NO_PENALTY =  lambda l: random.choice(
    [
        UX_LANG(l).MSG_ANSWER_WRONG_NO_PENALTY_01,
        UX_LANG(l).MSG_ANSWER_WRONG_NO_PENALTY_02,
        UX_LANG(l).MSG_ANSWER_WRONG_NO_PENALTY_03,
    ]
)

MSG_ANSWER_OK = lambda l: random.choice(
    [
        UX_LANG(l).MSG_ANSWER_OK_01, 
        UX_LANG(l).MSG_ANSWER_OK_02, 
        UX_LANG(l).MSG_ANSWER_OK_03
    ]
)

MSG_MEDIA_INPUT_MISSIONE_OK = lambda l: random.choice(
    [
        UX_LANG(l).MSG_MEDIA_INPUT_MISSIONE_OK_01,
        UX_LANG(l).MSG_MEDIA_INPUT_MISSIONE_OK_02
    ]
)

BUTTON_LOCATION = lambda l: {
    'text': UX_LANG(l).BUTTON_GPS,
    'request_location': True,
}

BUTTON_YES_CALLBACK = lambda x: telegram.InlineKeyboardButton(
    text = UX_LANG('IT').BUTTON_YES,
    callback_data = x
)


BUTTON_NO_CALLBACK = lambda x: telegram.InlineKeyboardButton(
    text = UX_LANG('IT').BUTTON_NO,
    callback_data = x
)

def export_airtable_UX_to_file():
    for lang in LANGS: 
        out_file = os.path.join(UX_DIR, f'{lang}.json')
        lang_key_values = {k:v[lang] for k,v in UX_DICT.items()}
        with open(out_file, 'w') as f_out:
            json.dump(
                lang_key_values, 
                f_out, 
                indent=3, 
                ensure_ascii=False, 
                sort_keys=lambda x: x[0]
            )
        


if __name__ == "__main__":
    export_airtable_UX_to_file()