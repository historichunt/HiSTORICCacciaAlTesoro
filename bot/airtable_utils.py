import collections
from airtable import Airtable
from bot import settings, game

def download_media(hunt_password, output_dir, table_name='Results'):    
    import requests
    import os
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    table_id = game.HUNTS[hunt_password]['Airtable_Game_ID']
    RESULTS_TABLE = Airtable(table_id, table_name, api_key=settings.AIRTABLE_API_KEY)
    table_entries = RESULTS_TABLE.get_all()
    for entry in table_entries:
        fields = entry['fields']
        group_name = fields.get('GROUP_NAME', None)
        if group_name is None:
            print('No group name, skipping')
            continue
        print('Downloading media for group {}'.format(group_name))        
        output_dir_group = os.path.join(output_dir, group_name)
        if os.path.exists(output_dir_group):
            print('\t Dir already present, skipping.')
            continue
        if 'GROUP_MEDIA_FILE_IDS' not in fields:
            print('\t No media, skipping.')
            continue
        os.mkdir(output_dir_group)        
        for media in fields['GROUP_MEDIA_FILE_IDS']:
            url = media['url']
            file_name = media['filename']
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
        return sorted(rows, settings=sort_key)
    else:
        return rows

def get_wrong_answers(hunt_password, output_file, table_name='Results'):
    from collections import defaultdict
    import json
    table_id = game.HUNTS[hunt_password]['Airtable_Game_ID']
    RESULTS_TABLE = Airtable(table_id, table_name, api_key=settings.AIRTABLE_API_KEY)
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
        f_out.write("ERRORI piu' frequenti (Almeno 5 volte)\n")
        for tappa in error_dict:
            counter = collections.Counter(error_dict[tappa])
            f_out.write(f'TAPPA = {tappa}\n')
            f_out.write(f'  ERRORI TOTALI = {sum(counter.values())}\n')
            for (error, freq) in counter.most_common(5):
                f_out.write(f'   ERRORE = {error}   (con frequenza = {freq})\n')

        f_out.write("\n\nTUTTI GLI ERRORI (anche quelli poco frequenti, ad esempio occorsi solo una volta)")
        for tappa in error_dict:
            counter = collections.Counter(error_dict[tappa])
            f_out.write(f'TAPPA = {tappa}\n')
            f_out.write(f'  ERRORI TOTALI = {sum(counter.values())}\n')
            for (error, freq) in counter.most_common():
                f_out.write(f'   ERRORE = {error}   (con frequenza = {freq})\n')


if __name__ == "__main__":    
    import os
    password = input('Inserisci password caccia al tesoro: ')
    assert password in game.HUNTS, 'Incorrect password'
    hunt_name = game.HUNTS[password]['Name']
    outputdir = os.path.join('data', hunt_name)
    os.makedirs(outputdir)
    download_media(password, os.path.join(outputdir, 'media'))
    error_dict = get_wrong_answers(password, os.path.join(outputdir, 'errori.txt'))
    process_errori(error_dict, os.path.join(outputdir, 'errori_processed.txt'))
