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
        table_name: [
            {k:fields_list[k] for k in FIELDS_KEYS_FULL if k in fields_list}
            for fields_list in d['fields']
        ]
        for d in hunt_schema
        if (table_name := matched_table(d['name']))
    }

    return hunt_schema

'''
Make sure you chose the real `template`
'''
def download_gold_hunt_schema(
        airtable_game_id, filepath_full, filepath_simplified, clean=True):

    # full schema (list of dict)
    # - {'name': 'Settings', 'fields': [{'type': '...', 'name': 'Name' }, ...]
    # - {'name': 'UI',
    # - ...
    hunt_schema_full = get_hunt_schema(airtable_game_id, clean)

    with open(filepath_full, 'w') as fout:
        json.dump(hunt_schema_full, fout, ensure_ascii=False, indent=3)

    hunt_schema_simplified = {
        table_name: [d['name'] for d in fields_info]
        for table_name, fields_info in hunt_schema_full.items()
    }

    with open(filepath_simplified, 'w') as fout:
        json.dump(hunt_schema_simplified, fout, ensure_ascii=False, indent=3)


def check_hunt_schema(airtable_game_id):
    with open(SCHEMA_JSON_FULL) as fin:
        schema_gold = json.load(fin)
    hunt_schema = get_hunt_schema(airtable_game_id)
    for table_name, hunt_fields in hunt_schema.items():
        table_name = matched_table(table_name)
        if not table_name:
            return dedent(f'''
                Table `{table_name}` is not a correct table name.
                Please check simplified schema: {URL_SCHEMA_SIMPLIFIED}
            ''')

        hunt_fields_names = [f['name'] for f in hunt_fields]
        gold_fields = schema_gold[table_name]
        gold_field_names = [f['name'] for f in gold_fields]
        if hunt_fields_names != gold_field_names:
            return dedent(f'''
                Table `{table_name}` does not have the correct fields.
                Found: `{hunt_fields_names}`
                Correct: `{gold_field_names}`
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