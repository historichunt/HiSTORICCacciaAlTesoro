# -*- coding: utf-8 -*-

import key
from airtable import Airtable

def downloadSelfies(hunt_password, output_dir):
    import requests
    import os
    table_id = key.HUNTS[hunt_password]['Airtable_Risultati_ID']
    GAME_TABLE = Airtable(table_id, 'Games', api_key=key.AIRTABLE_API_KEY)
    table_entries = GAME_TABLE.get_all()
    for entry in table_entries:
        fields = entry['fields']
        group_name = fields['GROUP_NAME']
        output_dir_group = os.path.join(output_dir, group_name)
        os.mkdir(output_dir_group)
        print('Downloading selfies for group {}'.format(group_name))        
        for selfie in fields['GROUP_SELFIES']:
            url = selfie['url']
            file_name = selfie['filename']
            print('\t{}'.format(file_name))        
            output_file = os.path.join(output_dir_group, file_name)
            r = requests.get(url)
            with open(output_file, 'wb') as output:
                output.write(r.content)


if __name__ == "__main__":
    #downloadSelfies('Suffragio_1_July_2018', '/Users/fedja/Downloads/caccia')
    downloadSelfies('05_Aldeno_03_May_2019', '/Users/fedja/Downloads/05_Aldeno_03_May_2019')