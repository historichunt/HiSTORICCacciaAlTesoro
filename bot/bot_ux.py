import os
import json
import telegram
import random
from airtable import Airtable
from bot import settings

UX_DIR = os.path.join(settings.ROOT_DIR, 'ux')
LANGS = ['IT','EN']

UX_DICT = None # lang -> var -> string

def reload_ux():
    global UX_DICT
    UX_DICT = {
        lang: json.load(open(os.path.join(UX_DIR, f'{lang}.json')))
        for lang in LANGS
    }

reload_ux()

class UX_LANG:
    
    def __init__(self, lang):
        assert lang in LANGS
        self.lang = lang

    def get_var(self, var):
        return UX_DICT[self.lang].get(var, None)

    def __getattr__(self, attr):
        return UX_DICT[self.lang].get(attr, None)

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