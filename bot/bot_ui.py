import os
import json
import telegram
import random
from airtable import Airtable
from bot.params import ROOT_DIR, LANGUAGES

UI_DIR = os.path.join(ROOT_DIR, 'ui')

# lang -> var -> string
UI_DICT = None

def build_ui_dict():
    global UI_DICT
    UI_DICT = {
        lang: json.load(open(os.path.join(UI_DIR, f'{lang}.json')))
        for lang in LANGUAGES
    }

build_ui_dict()

class UI_LANG:
    
    def __init__(self, lang, ui_custom_dict=None):
        assert lang in LANGUAGES
        self.lang = lang
        self.ui_custom_dict = ui_custom_dict

    def get_var(self, var):
        if self.ui_custom_dict and var in self.ui_custom_dict[self.lang]:
            return self.ui_custom_dict[self.lang][var]
        return UI_DICT[self.lang].get(var, None)

    def __getattr__(self, attr):
        return self.get_var(attr)

# ui = lambda l: UI_LANG(l)

# ================================
# SPECIAL BUTTONS
# ================================

BUTTON_CONTINUE_MULTI = lambda l: [
    UI_LANG(l).BUTTON_CONTINUE_01,
    UI_LANG(l).BUTTON_CONTINUE_02,
    UI_LANG(l).BUTTON_CONTINUE_03
]

MSG_ANSWER_WRONG_NO_PENALTY =  lambda l: random.choice(
    [
        UI_LANG(l).MSG_ANSWER_WRONG_NO_PENALTY_01,
        UI_LANG(l).MSG_ANSWER_WRONG_NO_PENALTY_02,
        UI_LANG(l).MSG_ANSWER_WRONG_NO_PENALTY_03,
    ]
)

MSG_ANSWER_OK = lambda l: random.choice(
    [
        UI_LANG(l).MSG_ANSWER_OK_01, 
        UI_LANG(l).MSG_ANSWER_OK_02, 
        UI_LANG(l).MSG_ANSWER_OK_03
    ]
)

MSG_MEDIA_INPUT_MISSIONE_OK = lambda l: random.choice(
    [
        UI_LANG(l).MSG_MEDIA_INPUT_MISSIONE_OK_01,
        UI_LANG(l).MSG_MEDIA_INPUT_MISSIONE_OK_02
    ]
)

BUTTON_LOCATION = lambda l: {
    'text': UI_LANG(l).BUTTON_GPS,
    'request_location': True,
}

BUTTON_YES_CALLBACK = lambda x: telegram.InlineKeyboardButton(
    text = UI_LANG('IT').BUTTON_YES,
    callback_data = x
)


BUTTON_NO_CALLBACK = lambda x: telegram.InlineKeyboardButton(
    text = UI_LANG('IT').BUTTON_NO,
    callback_data = x
)

def sort_alphabetically():
    for lang in LANGUAGES:
        lang_dict = UI_DICT[lang]
        ui_file = os.path.join('ui', f'{lang}.json')
        with open(ui_file, 'w') as f_out:
            json.dump(lang_dict, f_out, indent=3, sort_keys=True, ensure_ascii=False)

def check_language_consistency():
    lang_keys = {
        lang: list(UI_DICT[lang].keys())
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

def download_ui_tsv():
    from bot import params
    import csv
    check_language_consistency()
    lang_dict = {
        lang: UI_DICT[lang]
        for lang in LANGUAGES
    }
    primary_lang = params.LANGUAGES[0]
    keys = lang_dict[primary_lang].keys()
    tsv_file = os.path.join(UI_DIR, 'UI.tsv')
    
    with open(tsv_file, 'w') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t')
        # header
        writer.writerow(['KEY','DESCRIPTION'] + params.LANGUAGES)
        for k in keys:
            writer.writerow([k,''] + [lang_dict[lang][k] for lang in params.LANGUAGES])


if __name__ == "__main__":
    # sort_alphabetically()
    # build_ui_dict()
    # check_language_consistency()
    download_ui_tsv()