import key
from airtable import Airtable
import collections

def download_selfies(hunt_password, output_dir):
    import game
    import requests
    import os
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    table_id = game.HUNTS[hunt_password]['Airtable_Game_ID']
    RESULTS_TABLE = Airtable(table_id, 'Results', api_key=key.AIRTABLE_API_KEY)
    table_entries = RESULTS_TABLE.get_all()
    for entry in table_entries:
        fields = entry['fields']
        group_name = fields.get('GROUP_NAME', None)
        if group_name is None:
            print('No group name, skipping')
            continue
        print('Downloading selfies for group {}'.format(group_name))        
        output_dir_group = os.path.join(output_dir, group_name)
        if os.path.exists(output_dir_group):
            print('\t Dir already present, skipping.')
            continue
        if 'GROUP_MEDIA_FILE_IDS' not in fields:
            print('\t No media, skipping.')
            continue
        os.mkdir(output_dir_group)        
        for selfie in fields['GROUP_MEDIA_FILE_IDS']:
            url = selfie['url']
            file_name = selfie['filename']
            print('\t{}'.format(file_name))        
            output_file = os.path.join(output_dir_group, file_name)
            r = requests.get(url)
            with open(output_file, 'wb') as output:
                output.write(r.content)

def get_rows(table, filter=None, sort_key=None):
    rows = [r['fields'] for r in table.get_all()]
    if filter:
        rows = [r for r in rows if filter(r)]
    if sort_key:
        return sorted(rows, key=sort_key)
    else:
        return rows

def get_wrong_answers(hunt_password, output_file):
    import game
    from collections import defaultdict
    import json
    table_id = game.HUNTS[hunt_password]['Airtable_Game_ID']
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
        # TODO: uppercase, sort and make frequency stats
        f_out.write(json.dumps(mission_wrong_ansers, indent=3, ensure_ascii=False))

    return mission_wrong_ansers

def process_errori(error_dict, output_file):
    with open(output_file, 'w') as f_out:
        for tappa in error_dict:
        counter = collections.Counter(d3[tappa])
        error_dict[tappa] = (error_dict[tappa],{'counter':sum(counter.values())})

        sorted_keys = sorted(error_dict, key=lambda tappa: error_dict[tappa][1]['counter'], reverse=True)

        sorted_dict = OrderedDict()
        for k in sorted_keys:
            sorted_dict[k] = error_dict[k]
    
        f_out.write("5 ERRORI piu' frequenti\n")
        for tappa in error_dict:
            counter = collections.Counter(error_dict[tappa][0])
            f_out.write(f'TAPPA = {tappa}\n')
            f_out.write(f'  ERRORI TOTALI = {sum(counter.values())}\n')
            for (error, freq) in counter.most_common(5):
                f_out.write(f'   ERRORE = {error}   (con frequenza = {freq})\n')

        f_out.write("\n\nTUTTI GLI ERRORI")
        for tappa in error_dict:
            counter = collections.Counter(error_dict[tappa][0])
            f_out.write(f'TAPPA = {tappa}\n')
            f_out.write(f'  ERRORI TOTALI = {sum(counter.values())}\n')
            for (error, freq) in counter.most_common():
                f_out.write(f'   ERRORE = {error}   (con frequenza = {freq})\n')


if __name__ == "__main__":
    password = '' # insert password here (do not commit)
    download_selfies(password, 'data/selfies')
    error_dict = get_wrong_answers(password, 'data/errori.txt')
    process_errori(error_dict, 'data/errori_processed.txt')
