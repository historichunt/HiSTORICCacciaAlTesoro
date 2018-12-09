# -*- coding: utf-8 -*-

import key
from airtable import Airtable
import requests
import os

def downloadSelfies(table_name, output_dir):
    table_id = key.GAMES_ID[table_name]['Airtable_Table_ID']
    GAME_TABLE = Airtable(table_id, 'Games', api_key=key.AIRTABLE_API_KEY)
    table_entries = GAME_TABLE.get_all()
    for entry in table_entries:
        fields = entry['fields']
        group_name = fields['GROUP_NAME']
        output_dir_group = os.path.join(output_dir, group_name)
        os.mkdir(output_dir_group)
        for selfie in fields['GROUP_SELFIES']:
            url = selfie['url']
            file_name = selfie['filename']
            output_file = os.path.join(output_dir_group, file_name)
            r = requests.get(url)
            with open(output_file, 'wb') as output:
                output.write(r.content)


if __name__ == "__main__":
    #downloadSelfies('Suffragio_1_July_2018', '/Users/fedja/Downloads/caccia')
    downloadSelfies('SantaMassenza_09_December_2018', '/Users/fedja/Downloads/Caccia_Santa_Massenza_9_Dicembre')