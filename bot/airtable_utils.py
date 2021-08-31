import collections
from airtable import Airtable
from bot import settings, game
import zipfile
from bot.utility import append_num_to_filename


def download_media_zip(hunt_password, table_name='Results', log=False):    
    import zipfile
    import requests
    import os
    import io
    table_id = game.HUNTS_PW[hunt_password]['Airtable_Game_ID']
    RESULTS_TABLE = Airtable(table_id, table_name, api_key=settings.AIRTABLE_API_KEY)
    table_entries = RESULTS_TABLE.get_all()
    zip_buffer = io.BytesIO()
    zf = zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED)
    unique_group_names_list = []
    for entry in table_entries:
        fields = entry['fields']
        group_name = fields.get('GROUP_NAME', None)
        if group_name is None:
            group_name = 'no_name'
        while group_name in unique_group_names_list:
            group_name = append_num_to_filename(group_name)
        unique_group_names_list.append(group_name)
        if log:
            print('Downloading group ', group_name)
        if 'GROUP_MEDIA_FILE_IDS' not in fields:
            continue  
        unique_media_names_list = []
        for media in fields['GROUP_MEDIA_FILE_IDS']:
            url = media['url']
            file_name = media['filename']   
            while file_name in unique_media_names_list:
                file_name = append_num_to_filename(file_name)
            unique_media_names_list.append(file_name)
            output_file = os.path.join(group_name, file_name)
            r = requests.get(url)
            zf.writestr(output_file, r.content)
    zf.close()
    if len(unique_group_names_list) == 0:
        return None
    zip_content = zip_buffer.getvalue()
    return zip_content

def download_media(hunt_password, output_file):    
    zip_content = download_media_zip(hunt_password, log=True)
    with open(output_file, 'wb') as output:
        output.write(zip_content)

def get_rows(table, view=None, filter=None, sort_key=None):
    rows = [r['fields'] for r in table.get_all(view=view)]
    if filter:
        rows = [r for r in rows if filter(r)]
    if sort_key:
        return sorted(rows, key=sort_key)
    else:
        return rows

def get_wrong_answers(hunt_password, table_name='Results'):
    from collections import defaultdict
    import json
    table_id = game.HUNTS_PW[hunt_password]['Airtable_Game_ID']
    RESULTS_TABLE = Airtable(table_id, table_name, api_key=settings.AIRTABLE_API_KEY)
    table_entries = RESULTS_TABLE.get_all()
    mission_error_dict = defaultdict(list)
    for entry in table_entries:
        fields = entry['fields']
        # group_name = fields['GROUP_NAME']
        if 'GAME VARS' not in fields:
            # empty row
            continue
        game_vars = json.loads(fields['GAME VARS'])
        completed_missioni = game_vars['MISSIONI_INFO']['COMPLETED']
        for m in completed_missioni:
            name = m['NOME']
            answers = m['wrong_answers']
            mission_error_dict[name].extend(answers)
    # with open(output_file, 'w') as f_out:
    #     # TODO: uppercase, sort and make frequency stats
    #     f_out.write(json.dumps(mission_error_dict, indent=3, ensure_ascii=False))
    mission_errors = json.dumps(mission_error_dict, indent=3, ensure_ascii=False)
    errors_digested = process_errori(mission_error_dict)
    return mission_errors, errors_digested

def process_errori(mission_error_dict):
    output = []
    # with open(output_file, 'w') as f_out:
    output.append("ERRORI piu' frequenti (Almeno 5 volte)\n")
    for tappa in mission_error_dict:
        counter = collections.Counter(mission_error_dict[tappa])
        output.append(f'TAPPA = {tappa}\n')
        output.append(f'  ERRORI TOTALI = {sum(counter.values())}\n')
        for (error, freq) in counter.most_common(5):
            output.append(f'   ERRORE = {error}   (con frequenza = {freq})\n')

    output.append("\n\nTUTTI GLI ERRORI (anche quelli poco frequenti, ad esempio occorsi solo una volta)")
    for tappa in mission_error_dict:
        counter = collections.Counter(mission_error_dict[tappa])
        output.append(f'TAPPA = {tappa}\n')
        output.append(f'  ERRORI TOTALI = {sum(counter.values())}\n')
        for (error, freq) in counter.most_common():
            output.append(f'   ERRORE = {error}   (con frequenza = {freq})\n')
    return '\n'.join(output)

if __name__ == "__main__":    
    import os
    password = input('Inserisci password caccia al tesoro: ').lower()
    assert password in game.HUNTS_PW, 'Incorrect password'
    hunt_name = game.HUNTS_PW[password]['Name']
    output_file = os.path.join('data', hunt_name.replace(' ', '_')[:20]+'.zip')
    download_media(password, output_file)
    # download_media_zip(password)
    # mission_error_dict = get_wrong_answers(password, os.path.join(outputdir, 'errori.txt'))
    # process_errori(mission_error_dict, os.path.join(outputdir, 'errori_processed.txt'))
