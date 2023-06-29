import sys
import collections
import requests
import os
import io
import json
from airtable import Airtable
from historic.config import settings
from historic.bot import game
import zipfile
from historic.bot.utility import append_num_to_filename, is_int_between
import random

def download_media_zip(hunt_password, table_name='Results', log=False):    
    from historic.config.params import MAX_SIZE_FILE_BYTES    
    base_id = game.HUNTS_PW[hunt_password]['Airtable_Game_ID']
    RESULTS_TABLE = Airtable(base_id, table_name, api_key=settings.AIRTABLE_API_KEY)
    table_entries = RESULTS_TABLE.get_all()
    zip_buffer = io.BytesIO()
    zf = zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED)
    unique_group_names_list = []
    total_size = 0
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
            zf_info = zf.getinfo(output_file)
            total_size += zf_info.file_size # zf_info.compress_size            
            if total_size > MAX_SIZE_FILE_BYTES:
                zf.close()
                return 'MAX'
    zf.close()
    if len(unique_group_names_list) == 0:
        return 0
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

def get_wrong_answers(hunt_password, table_name='Results', output_file=None, output_file_digested=None):
    from collections import defaultdict    
    base_id = game.HUNTS_PW[hunt_password]['Airtable_Game_ID']
    RESULTS_TABLE = Airtable(base_id, table_name, api_key=settings.AIRTABLE_API_KEY)
    table_entries = RESULTS_TABLE.get_all()
    mission_error_dict = defaultdict(list)
    for entry in table_entries:
        fields = entry['fields']
        # group_name = fields['GROUP_NAME']
        if 'GAME VARS' not in fields:
            # empty row
            continue
        game_vars = json.loads(fields['GAME VARS'])
        if 'MISSIONI_INFO' not in game_vars:
            # missing missioni (probably didn't start the hunt)
            continue
        completed_missioni = game_vars['MISSIONI_INFO']['COMPLETED']
        for m in completed_missioni:
            name = m['NOME']
            answers = m['wrong_answers'].lower()
            mission_error_dict[name].extend(answers)
    mission_errors = json.dumps(mission_error_dict, indent=3, ensure_ascii=False)
    errors_digested = process_errori(mission_error_dict)
    if output_file:
        with open(output_file, 'w') as f_out:
            # TODO: uppercase, sort and make frequency stats
            f_out.write(mission_errors)
    if output_file_digested:
        with open(output_file, 'w') as f_out:
            # TODO: uppercase, sort and make frequency stats
            f_out.write(errors_digested)
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

def get_report(hunt_password, table_name='Results'):
    base_id = game.HUNTS_PW[hunt_password]['Airtable_Game_ID']
    RESULTS_TABLE = Airtable(base_id, table_name, api_key=settings.AIRTABLE_API_KEY)
    table_entries = RESULTS_TABLE.get_all()

    result = []

    for entry in table_entries:
        row = entry['fields']
        # print(vars['ROUTE_DURATION_MIN'][0])
        finished = row.get('FINISHED', False)
        if not finished:
            # print(str(group_name)+'   NANANAN SKIP! NON hanno completato!')
            continue
        vars = json.loads(row['GAME VARS'])
        group_name = row.get('GROUP_NAME', '')
        quanto_ci_han_messo_in_secondi = vars['ELAPSED GAME']
        quanto_volevano_giocare_in_minuti = vars['ROUTE_DURATION_MIN']
        quanto_volevano_giocare_in_secondi = quanto_volevano_giocare_in_minuti * 60
        secondi_in_piu_rispetto_a_quanto_richiesto = quanto_ci_han_messo_in_secondi - quanto_volevano_giocare_in_secondi

        total_time_missions = vars['TOTAL TIME MISSIONS']
        nr_missions = vars['MISSIONI_INFO']['TOTAL']
        result.append(f'Group={group_name} / secondi in piu = {secondi_in_piu_rispetto_a_quanto_richiesto}  messo={quanto_ci_han_messo_in_secondi}-quantovolevano={quanto_volevano_giocare_in_secondi} /')
        result.append(f'Group={group_name} / secondi medi per missione = {total_time_missions/nr_missions}  total time missions={total_time_missions} / missions={nr_missions} /')
        result.append('')

    return '\n'.join(result)


if __name__ == "__main__":    
    from historic.bot.utils_cli import get_hunt_from_password

    hunt_name, password, airtable_game_id = get_hunt_from_password()    

    options = [
        '1. Scaricare media',
        '2. Scaricare errori',
        '3. Stampa statistiche squadre',
        '4. Testa missioni (random)',
        'q  Exit'
    ]
    
    while True:

        while True:            
            print('\nOpzioni:\n' + '\n'.join(options))
            opt = input('\nLa tua scelta --> ')
            if opt=='q':
                sys.exit()
            if is_int_between(opt, 1, len(options)):
                opt = int(opt)
                break
            print('\nScelta non valida, riprova.\n')

        hunt_name_no_space = hunt_name.replace(' ', '_')[:20]
        if opt==1:
            output_file = os.path.join('data', hunt_name_no_space + '.zip')
            download_media(password, output_file)
            # download_media_zip(password)
        elif opt==2:
            get_wrong_answers(
                password, 
                f'{hunt_name_no_space}_errori.txt', f'{hunt_name_no_space}_errori_digested.txt'
            )
        elif opt==3:
            print(get_report(password))
        elif opt==4:
            mission_table_name = 'Missioni_IT'
            start_lat_long = random.choice(game.get_all_missions_lat_lon(airtable_game_id, mission_table_name))
            missions = game.get_random_missions(airtable_game_id, mission_table_name, start_lat_long)
            random_missioni_names = '\n'.join([' {}. {}'.format(n,x['NOME']) for n,x in enumerate(missions,1)])
            print(random_missioni_names)
