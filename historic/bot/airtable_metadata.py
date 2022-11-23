from pyairtable import Table
from pyairtable.metadata import get_base_schema
from pyairtable.api import Base
from historic.config import settings
import json
import requests

tables_name_language = [
    'Instructions_IT',
    'Missioni_IT',
    'Survey_IT'
]

def get_hunt_schema(airtable_game_id, clean=True):
    '''
    json_data is a list of dictionaries, one per table
    each dictionary has the following structure (* marked preserved structure after clean)
        - id -> str
        * name -> str
        - primaryFieldId -> str
        * fields -> list(dict)
            * type -> str
            - option -> dict
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
    json_data = json.loads(response.text)['tables']

    k_set = set(['id', 'name', 'primaryFieldId', 'fields', 'views'])
    k_to_keep = ['name', 'fields']
    k_to_remove = k_set.difference(k_to_keep)
    fd_k_set = set(['type', 'options', 'id', 'name', 'description'])
    fd_k_to_keep = ['name', 'type', 'options']
    fd_k_to_remove = fd_k_set.difference(fd_k_to_keep)
    opt_k_set = set(['icon', 'color', 'isReversed', 'choices'])
    opt_k_to_keep = ['choices']
    opt_k_to_remove = opt_k_set.difference(opt_k_to_keep)
    for table_dict in json_data:
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
            if 'option' in fd:
                opt_dict = fd['option']
                opt_dict_ks = set(opt_dict.keys())
                assert opt_dict_ks <= opt_k_set  # subset
                if clean:
                    for k in opt_k_to_remove:
                        opt_dict.pop(k, None)

    return json_data

def download_hunt_schema(airtable_game_id, filepath, clean=True):

    json_data = get_hunt_schema(airtable_game_id, clean)
    
    with open(filepath, 'w') as fout:
        json.dump(json_data, fout, ensure_ascii=False, indent=3)

    

if __name__ == "__main__":
    from historic.bot.utils_cli import get_hunt_from_password

    hunt_name, airtable_game_id = get_hunt_from_password()    
    
    download_hunt_schema(
        airtable_game_id,
        filepath = 'hunt_schema/schema.json',
        clean = True
    )