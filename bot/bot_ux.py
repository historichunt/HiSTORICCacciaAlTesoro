import os
import json
import telegram
import random
from airtable import Airtable
from bot.params import ROOT_DIR, LANGUAGES

UX_DIR = os.path.join(ROOT_DIR, 'ux')

# lang -> var -> string
UX_DICT = {
    lang: json.load(open(os.path.join(UX_DIR, f'{lang}.json')))
    for lang in LANGUAGES
}

class UX_LANG:
    
    def __init__(self, lang, ux_custom_dict=None):
        assert lang in LANGUAGES
        self.lang = lang
        self.ux_custom_dict = ux_custom_dict

    def get_var(self, var):
        if self.ux_custom_dict and var in self.ux_custom_dict[self.lang]:
            return self.ux_custom_dict[self.lang][var]
        return UX_DICT[self.lang].get(var, None)

    def __getattr__(self, attr):
        return self.get_var(attr)

# ux = lambda l: UX_LANG(l)

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

def check_language_consistency():
    lang_keys = {
        lang: list(UX_DICT[lang].keys())
        for lang in LANGUAGES
    }
    lang_keys_length = {
        lang: len(lang_keys[lang])
        for lang in LANGUAGES
    }
    all_lengths = list(lang_keys_length.values())
    assert len(set(all_lengths))==1, \
        f"Different lenghts: {lang_keys_length}"
    length = all_lengths[0]
    for i in range(length):
        i_keys = {
            lang: lang_keys[lang][i]
            for lang in LANGUAGES
        }
        if len(set(i_keys.values()))!=1:
            assert False, f'Keys mismatch at line {i+2}: {i_keys}'


if __name__ == "__main__":
    check_language_consistency()