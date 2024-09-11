from historic.config import settings
import json
import requests
import re
from textwrap import dedent

SCHEMA_JSON_FULL = 'hunt_schema/schema.json'
SCHEMA_JSON_SIMPLIFIED = 'hunt_schema/schema_simplified.json'

URL_SCHEMA_FULL = 'https://github.com/historichunt/HiSTORICCacciaAlTesoro/blob/master/hunt_schema/schema.json'
URL_SCHEMA_SIMPLIFIED = 'https://github.com/historichunt/HiSTORICCacciaAlTesoro/blob/master/hunt_schema/schema_simplified.json'

FIELDS_KEYS_FULL = ['name', 'type', 'options']
FIELDS_KEYS_SIMPLIFIED = ['name']

TABLE_NAMES_RE = [
    r'Settings',
    r'UI',
    r'Instructions_..',
    r'Missioni_..',
    r'Survey_..',
    r'Survey Answers',
    r'Results',
]

def matched_table(name):
    for pattern in TABLE_NAMES_RE:
        if re.match(pattern, name):
            return pattern

def get_hunt_schema(airtable_game_id, clean=True):
    '''
    json returned from airtable is a list of dictionaries, one per table
    each dictionary has the following structure (* marked preserved structure after clean)
        - id -> str
        * name -> str
        - primaryFieldId -> str
        * fields -> list(dict)
            * type -> str
            * options -> dict
                - icon
                - color
                - isReversed -> bool
                * choices -> list(dict)
                    - id -> str
                    * name -> str
                    - color -> str
            - id -> str
            * name -> str
        - views -> dict
    '''

    url = f"https://api.airtable.com/v0/meta/bases/{airtable_game_id}/tables"

    # payload={}
    headers = {
        'Authorization': f'Bearer {settings.AIRTABLE_ACCESS_TOKEN}',
        # 'Cookie': 'brw=brwJKyttKj84lpEiz'
        }

    response = requests.request("GET", url, headers=headers) # data=payload
    hunt_schema = json.loads(response.text)['tables']

    k_set = set(['id', 'name', 'primaryFieldId', 'fields', 'views'])
    k_to_keep = ['name', 'fields']
    k_to_remove = k_set.difference(k_to_keep)
    fd_k_set = set(['type', 'options', 'id', 'name', 'description'])
    fd_k_to_keep = ['name', 'type', 'options']
    fd_k_to_remove = fd_k_set.difference(fd_k_to_keep)
    opt_k_set = set(['icon', 'color', 'isReversed', 'choices', 'dateFormat', 'durationFormat', 'timeFormat', 'timeZone', 'precision'])
    opt_k_to_keep = ['choices']
    opt_k_to_remove = opt_k_set.difference(opt_k_to_keep)
    # opt_choices_to_keep = ['name']
    for table_dict in hunt_schema:
        ks = set(table_dict.keys())
        assert set(ks)== k_set
        if clean:
            for k in k_to_remove:
                table_dict.pop(k, None)
        fields_list_dict = table_dict['fields']
        for fd in fields_list_dict:
            fd_ks = set(fd.keys())
            assert fd_ks <= fd_k_set # subset
            if clean:
                for k in fd_k_to_remove:
                    fd.pop(k, None)
            if 'options' in fd:
                opt_dict = fd['options']
                opt_dict_ks = set(opt_dict.keys())
                assert opt_dict_ks <= opt_k_set  # subset
                if clean:
                    for k in opt_k_to_remove:
                        opt_dict.pop(k, None)
                    if len(opt_dict)==0:
                        fd.pop('options', None)
                    else:
                        # choices
                        opt_dict['choices'] = [c['name'] for c in opt_dict['choices']]

    # process schema from list to table_name -> dict form
    hunt_schema = {
        d['name']: [
            {k:fields_list[k] for k in FIELDS_KEYS_FULL if k in fields_list}
            for fields_list in d['fields']
        ]
        for d in hunt_schema
    }
    # replace table_name (Survey_EN) with normalized (Survey_..)
    hunt_schema_norm = {
        table_name: value
        for table_name, value in hunt_schema.items()
        if matched_table(table_name)
    }

    return hunt_schema, hunt_schema_norm

'''
Make sure you chose the real `template`
'''
def download_gold_hunt_schema(
        airtable_game_id, filepath_full, filepath_simplified, clean=True):

    # full schema (list of dict)
    # - {'name': 'Settings', 'fields': [{'type': '...', 'name': 'Name' }, ...]
    # - {'name': 'UI',
    # - ...
    _, hunt_schema_norm  = get_hunt_schema(airtable_game_id, clean)

    with open(filepath_full, 'w') as fout:
        json.dump(hunt_schema_norm, fout, ensure_ascii=False, indent=3)

    hunt_schema_simplified = {
        table_name: [d['name'] for d in fields_info]
        for table_name, fields_info in hunt_schema_norm.items()
    }

    with open(filepath_simplified, 'w') as fout:
        json.dump(hunt_schema_simplified, fout, ensure_ascii=False, indent=3)


def check_hunt_schema(airtable_game_id, hunt_languages):

    with open(SCHEMA_JSON_FULL) as fin:
        schema_gold = json.load(fin)

    hunt_schema, hunt_schema_norm = get_hunt_schema(airtable_game_id)

    missing_table_lang = [
        table_name_lang
        for table_name in ['Instructions', 'Missioni','Survey']
        for lang in hunt_languages
        if (table_name_lang := f'{table_name}_{lang}') not in hunt_schema.keys()
    ]
    if missing_table_lang:
        return dedent(f'''
            Missing the following tables in base:\n
            Missing: `{missing_table_lang}`
        ''')

    for table_name, hunt_table_fields in hunt_schema_norm.items():
        table_name = matched_table(table_name) # normalized
        if not table_name:
            return dedent(f'''
                Table `{table_name}` is not a correct table name.
                Please check simplified schema: {URL_SCHEMA_SIMPLIFIED}
            ''')
        hunt_table_fields_names = [f['name'] for f in hunt_table_fields]
        if table_name == 'UI':
            # get set languages in UI but remove 'VAR'
            ui_languages = list(hunt_table_fields_names)
            ui_languages.remove('VAR')
            if set(ui_languages) != set(hunt_languages):
                return dedent(f'''
                    Table `{table_name}` does not have the correct language fields.\n
                    Found: `{ui_languages}`\n
                    Correct: `{hunt_languages}`\n
                    Please check simplified schema: {URL_SCHEMA_SIMPLIFIED}
                ''')
            continue
        if table_name == 'Survey_..':
            pass
            # TODO: chek all Survey_lang tables have the same number of questions
            # do NOT continue (check if fields are same as in gold)
        if table_name == 'Survey Answers':
            # DRAFT TODO...
            # first_lang = hunt_languages[0]
            # table_survey_first_lang = hunt_schema[f'Survey_{first_lang}']
            # survey_table = Airtable(game_id, f'Survey_{p.language}', api_key=settings.AIRTABLE_ACCESS_TOKEN)
            # ...TODO: check it has fields 'N', 'LANGUAGE', 'Q1', 'Q2', ..., 'Qmax' as in Survey_LANG

            # check it has fields 'N', 'LANGUAGE', 'Q1', 'Q2', ..., 'Q\d+'
            wrong_field_names = [
                field_name
                for field_name in hunt_table_fields_names
                if (
                    field_name not in ['N','LANGUAGE']
                    and
                    not re.match('Q\d+', field_name)
                )
            ]
            if wrong_field_names:
                return dedent(f'''
                    Table `{table_name}` contains the following wrong fields:\n
                    Wrong fields: `{wrong_field_names}`\n
                    Correct: `TODO...`\n
                    Please check simplified schema: {URL_SCHEMA_SIMPLIFIED}
                ''')
            continue
        # check if table fields are same as in gold
        gold_table_fields = schema_gold[table_name]
        gold_table_fields_names = [f['name'] for f in gold_table_fields]
        if hunt_table_fields_names != gold_table_fields_names:
            return dedent(f'''
                Table `{table_name}` does not have the correct fields.\n
                Found: `{hunt_table_fields_names}`\n
                Correct: `{gold_table_fields_names}`\n
                Please check simplified schema: {URL_SCHEMA_SIMPLIFIED}
            ''')

if __name__ == "__main__":
    from historic.bot.utils_cli import get_hunt_from_password

    hunt_name, password, airtable_game_id = get_hunt_from_password()

    download_gold_hunt_schema(
        airtable_game_id,
        filepath_full = SCHEMA_JSON_FULL,
        filepath_simplified = SCHEMA_JSON_SIMPLIFIED,
        clean = True
    )