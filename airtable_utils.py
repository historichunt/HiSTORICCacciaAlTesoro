import key
from airtable import Airtable

def download_selfies(hunt_password, output_dir):
    import requests
    import os
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    table_id = key.HUNTS[hunt_password]['Airtable_Risultati_ID']
    RESULTS_TABLE = Airtable(table_id, 'Results', api_key=key.AIRTABLE_API_KEY)
    table_entries = RESULTS_TABLE.get_all()
    for entry in table_entries:
        fields = entry['fields']
        group_name = fields['GROUP_NAME']
        output_dir_group = os.path.join(output_dir, group_name)
        os.mkdir(output_dir_group)
        print('Downloading selfies for group {}'.format(group_name))        
        for selfie in fields['GROUP_MEDIA_FILE_IDS']:
            url = selfie['url']
            file_name = selfie['filename']
            print('\t{}'.format(file_name))        
            output_file = os.path.join(output_dir_group, file_name)
            r = requests.get(url)
            with open(output_file, 'wb') as output:
                output.write(r.content)

def get_wrong_answers(hunt_password, output_file):
    from collections import defaultdict
    import json
    table_id = key.HUNTS[hunt_password]['Airtable_Risultati_ID']
    RESULTS_TABLE = Airtable(table_id, 'Results', api_key=key.AIRTABLE_API_KEY)
    table_entries = RESULTS_TABLE.get_all()
    mission_wrong_ansers = defaultdict(list)
    for entry in table_entries:
        fields = entry['fields']
        # group_name = fields['GROUP_NAME']
        game_vars = json.loads(fields['GAME VARS'])
        completed_missioni = game_vars['MISSIONI_INFO']['COMPLETED']
        for m in completed_missioni:
            name = m['NOME']
            answers = m['wrong_answers']
            mission_wrong_ansers[name].extend(answers)
    with open(output_file, 'w') as f_out:
        f_out.write(json.dumps(mission_wrong_ansers, indent=3, ensure_ascii=False))


if __name__ == "__main__":
    # download_selfies('password', '/Users/fedja/Downloads/outputdir')
    get_wrong_answers('historicalvino19', 'calavino_errori.txt')