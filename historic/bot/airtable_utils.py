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

async def update_media_bucket(hunt_name, hunt_pw):
    from historic.bot.game import get_hunt_languages    
    from historic.bot.game import HUNTS_PW
    from historic.bot import airtable_utils
    from historic.config.params import GOOGLE_BUCKET_NAME, MEDIA_FIELDS_MISSIONS
    import requests
    from google.cloud import storage
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(GOOGLE_BUCKET_NAME)    
    hunt_config_dict = HUNTS_PW[hunt_pw]   
    game_id = hunt_config_dict['Airtable_Game_ID'] 
    hunt_languages = get_hunt_languages(hunt_pw)
    
    for l in hunt_languages:
        table_name = f'Missioni_{l}'
        hunt_missioni_table = Airtable(game_id, table_name, api_key=settings.AIRTABLE_API_KEY)
        missioni_row_dict_list = airtable_utils.get_rows(hunt_missioni_table)
        for mission in missioni_row_dict_list:
            for field in MEDIA_FIELDS_MISSIONS:
                # print(field)
                if field in mission:
                    media_field = mission[field][0]
                    url = media_field['url']
                    filename = media_field['filename']                
                    blob = bucket.blob(f'{hunt_name}/{filename}')           
                    request_response = requests.get(url, stream=True)
                    content_type = request_response.headers['content-type']
                    media_content = request_response.content
                    blob.upload_from_string(media_content, content_type=content_type) 
                    media_field['url'] = blob.public_url


def download_media_zip(hunt_password, table_name='Results', log=False, check_size=True):    
    from historic.config.params import MAX_SIZE_FILE_BYTES    
    base_id = game.HUNTS_PW[hunt_password]['Airtable_Game_ID']
    RESULTS_TABLE = Airtable(base_id, table_name, api_key=settings.AIRTABLE_API_KEY)
    table_entries = RESULTS_TABLE.get_all()
    zip_buffer = io.BytesIO()
    zf = zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED)
    unique_group_names_list = []
    total_size = 0
    num_entries = len(table_entries)
    for n,entry in enumerate(table_entries, start=1):
        fields = entry['fields']
        group_name = fields.get('GROUP_NAME', None)
        if group_name is None:
            group_name = 'no_name'
        while group_name in unique_group_names_list:
            group_name = append_num_to_filename(group_name)
        unique_group_names_list.append(group_name)
        if log:
            print(f'Downloading group {n}/{num_entries}', group_name)
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
            if check_size and total_size > MAX_SIZE_FILE_BYTES:
                zf.close()
                return 'MAX'
    zf.close()
    if len(unique_group_names_list) == 0:
        return 0
    zip_content = zip_buffer.getvalue()
    return zip_content

def download_media(hunt_password, output_file):        
    with open(output_file, 'wb') as output:
        zip_content = download_media_zip(hunt_password, log=True, check_size=False)
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
            answers = [w.lower() for w in m['wrong_answers']]
            mission_error_dict[name].extend(answers)
    mission_errors = json.dumps(mission_error_dict, indent=3, ensure_ascii=False)
    errors_digested = process_errori(mission_error_dict)
    if output_file:
        with open(output_file, 'w') as f_out:
            # TODO: uppercase, sort and make frequency stats
            f_out.write(mission_errors)
    if output_file_digested:
        with open(output_file_digested, 'w') as f_out:
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
    from historic.bot import date_time_util as dtu
    base_id = game.HUNTS_PW[hunt_password]['Airtable_Game_ID']
    RESULTS_TABLE = Airtable(base_id, table_name, api_key=settings.AIRTABLE_API_KEY)
    table_entries = RESULTS_TABLE.get_all()

    result = []
    header = [
        'User Info',
        'Group Name', 
        'Finished',
        'Group Size', 
        'Total Missions',
        'Missions Completed',         
        'Elapsed Mission Min',
        'Elapsed Total Min',
        'Route Duration Min', 
        'Elapsed Difference Min'
    ]
    result.append(header)

    for entry in table_entries:
        row = entry['fields']
        finished = row.get('FINISHED', False)
        # if not finished:
        #     continue
        vars = json.loads(row['GAME VARS'])
        user_info = []
        for f in ['NOME', 'COGNOME', 'USERNAME']:
            if vars[f]:
                if f=='USERNAME':
                    user_info.append(f'@{vars[f]}')
                else:
                    user_info.append(vars[f])
        user_info = ' '.join(user_info)        
        group_name = row.get('GROUP_NAME', '')
        group_size = vars.get('GROUP_SIZE', '')
        elapsed_missions_min = vars['ELAPSED MISSIONS'] // 60
        elapsed_total_sec = vars['ELAPSED GAME']
        elapsed_total_min = elapsed_total_sec // 60
        # missions_times_list = [
        #     dtu.delta_seconds_iso(t[0], t[1]) if len(t)==2 else 0 
        #     for t in vars['MISSION_TIMES']
        # ]
        # missions_times_total_sec = sum(missions_times_list)
        # missions_times_total_min = missions_times_total_sec // 60
        completed_missions = vars.get('COMPLETED_MISSIONS','')
        incompleted_missions = vars.get('INCOMPLETED_MISSIONS','')
        total_missions = completed_missions + incompleted_missions
        route_duration_min = ''        
        route_duration_diff_min = ''
        if 'ROUTE_DURATION_MIN' in vars:
            route_duration_min = vars['ROUTE_DURATION_MIN']
            route_duration_sec = route_duration_min * 60
            route_duration_extra_sec = elapsed_total_sec - route_duration_sec # secondi_in_piu_rispetto_a_quanto_richiesto            
            route_duration_diff_min = route_duration_extra_sec // 60
        row_result = [
            user_info,
            group_name, 
            finished,
            group_size, 
            total_missions,
            completed_missions,             
            elapsed_missions_min,
            elapsed_total_min,
            route_duration_min, 
            route_duration_diff_min
        ]
        result.append(row_result)
    return '\n'.join(['\t'.join([str(f) for f in row]) for row in result])
    
    # with open(output_file, 'w') as f_out:
    #     f_out.write('\n'.join(['\t'.join([str(f) for f in row]) for row in result]))

async def main():
    from historic.bot.utils_cli import get_hunt_from_password

    hunt_name, password, airtable_game_id = get_hunt_from_password()    

    options = [
        '1. Scaricare media',
        '2. Scaricare errori',
        '3. Stampa statistiche squadre',
        '4. Testa missioni (random)',
        '5. Update media bucket'
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
            # Scaricare media
            output_file = os.path.join('data', hunt_name_no_space + '.zip')
            download_media(password, output_file)
        elif opt==2:
            # Scaricare errori
            get_wrong_answers(
                password, 
                output_file=f'{hunt_name_no_space}_errori.txt', 
                output_file_digested=f'{hunt_name_no_space}_errori_digested.txt'
            )
        elif opt==3:
            # Stampa statistiche squadre
            report_text = get_report(password)
            with open('data/stats.tsv', 'w') as f_out:
                f_out.write('\n'.join(['\t'.join([str(f) for f in row]) for row in report_text]))
        elif opt==4:
            # Testa missioni (random)
            mission_table_name = 'Missioni_IT'
            start_lat_long = random.choice(game.get_all_missions_lat_lon(airtable_game_id, mission_table_name))
            missions = game.get_random_missions(airtable_game_id, mission_table_name, start_lat_long)
            random_missioni_names = '\n'.join([' {}. {}'.format(n,x['NOME']) for n,x in enumerate(missions,1)])
            print(random_missioni_names)
        elif opt==5:            
            # update_media_bucket
            await update_media_bucket(hunt_name, password)

if __name__ == "__main__":  
    import asyncio  
    asyncio.run(main())
