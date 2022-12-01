
from airtable import Airtable
from random import shuffle, choice
from historic.config import params, settings
from historic.bot import utility, airtable_utils
import historic.bot.date_time_util as dtu
from historic.routing import route_planner
from historic.routing.api import api_google
from historic.routing.data_matrices import DataMatrices
from historic.routing.route_planner import RoutePlanner
from historic.routing.metrics import METRIC_DISTANCE, METRIC_DURATION, METRICS
import numpy as np

# from historic.hunt_route.trento_open_params import fine_tuning_trento_open

#################
# GAMES CONFIG
#################

HUNTS_CONFIG_TABLE = Airtable(
    settings.AIRTABLE_CONFIG_ID, 
    'Hunts', 
    api_key=settings.AIRTABLE_API_KEY
)

HUNTS_PW = None # pw -> hunt_details (all)
HUNTS_NAME = None # name -> hunt_details (all)

def reload_config_hunt():
    global HUNTS_PW, HUNTS_NAME
    hunts = [
        row['fields'] 
        for row in HUNTS_CONFIG_TABLE.get_all() 
        if 'Password' in row['fields']
    ]
    for d in hunts:
        d['Password'] = d['Password'].lower()
    HUNTS_PW = {
        d['Password']: d
        for d in hunts
    }
    HUNTS_NAME = {
        d['Name']: d
        for d in hunts
    }
    

def is_person_hunt_admin(p, hunt_pw):
    if hunt_pw not in HUNTS_PW:
        return False
    hunt_admin_ids = HUNTS_PW[hunt_pw].get('Admins IDs',[])
    return p.get_id() in hunt_admin_ids

def get_hunts_that_person_admins(p):
    return [d for d in HUNTS_PW.values() if p.get_id() in d['Admins IDs']]

reload_config_hunt()


#################
# MISSIONI TABLE
#################
'''
NOME, ACTIVE, FINALE, NEXT, 
INTRO_MEDIA, INTRO_MEDIA_CAPTION, 
INTRODUZIONE_LOCATION, GPS, 
DOMANDA_MEDIA, DOMANDA_MEDIA_CAPTION, DOMANDA,
SOLUZIONI, INDIZIO_1, INDIZIO_2, 
PENALTY,
POST_MEDIA, POST_MEDIA_CAPTION, POST_MESSAGE,
INPUT_INSTRUCTIONS, INPUT_TYPE, INPUT_CONFIRMATION, POST_INPUT
'''

def get_hunt_settings(airtable_game_id):
    SETTINGS_TABLE = Airtable(airtable_game_id, 'Settings', api_key=settings.AIRTABLE_API_KEY)
    SETTINGS = {
        row['fields']['Name']:row['fields']['Value'] 
        for row in SETTINGS_TABLE.get_all() 
        if row['fields'].get('Name', False)
    }
    return SETTINGS

def get_hunt_ui(airtable_game_id, hunt_languages):    
    UI_TABLE = Airtable(airtable_game_id, 'UI', api_key=settings.AIRTABLE_API_KEY)
    table_rows = [
        row['fields'] 
        for row in UI_TABLE.get_all() 
    ]
    UI = {
        lang: {
            r['VAR']: r[lang].strip()
            for r in table_rows
        }        
        for lang in hunt_languages
    }
    return UI




#################
# RESULT GAME TABLE
#################

RESULTS_GAME_TABLE_HEADERS = \
    ['ID', 'GROUP_NAME', 'NOME', 'COGNOME', 'USERNAME', 'EMAIL', \
    'START_TIME', 'END_TIME', 'ELAPSED GAME', 'ELAPSED MISSIONS', \
    'PENALTIES', 'PENALTY TIME', 'FINISHED', 'TOTAL TIME GAME', 'TOTAL TIME MISSIONS']

def save_game_data_in_airtable(p):
    from historic.bot.bot_telegram import get_photo_url_from_telegram
    import json
    game_data = p.tmp_variables
    airtable_game_id = game_data['HUNT_INFO']['Airtable_Game_ID']

    RESULTS_GAME_TABLE = Airtable(
        airtable_game_id, 
        'Results', 
        api_key=settings.AIRTABLE_API_KEY
    )    

    games_row = {'LANGUAGE': p.language}
    for h in RESULTS_GAME_TABLE_HEADERS:
        games_row[h] = game_data[h]
    games_row['GAME VARS'] = json.dumps(game_data,ensure_ascii=False)
    games_row['GROUP_MEDIA_FILE_IDS'] = [
        {'url': get_photo_url_from_telegram(file_id)} 
        for file_id in game_data['GROUP_MEDIA_FILE_IDS']
    ]
    RESULTS_GAME_TABLE.insert(games_row)
    
def save_survey_data_in_airtable(p):
    game_data = p.tmp_variables
    airtable_game_id = game_data['HUNT_INFO']['Airtable_Game_ID']
    results_survey_table = Airtable(airtable_game_id, 'Survey Answers', api_key=settings.AIRTABLE_API_KEY)
    survey_row = {'LANGUAGE': p.language}
    survey_data = game_data['SURVEY_INFO']['COMPLETED']
    for row in survey_data:
        survey_row[row['QN']] = row['ANSWER'] # columns: Q1, Q2, ...
    results_survey_table.insert(survey_row)


################################
# GAME MANAGEMENT FUNCTIONS
################################

def get_hunt_languages(hunt_password):
    hunt_info = HUNTS_PW[hunt_password]
    airtable_game_id = hunt_info['Airtable_Game_ID']
    hunt_settings = get_hunt_settings(airtable_game_id)
    hunt_languages =  [
        l.strip()
        for l in hunt_settings['LANGUAGES'].upper().split(',')
        if l.strip() in params.LANGUAGES
    ]
    return hunt_languages

def load_game(p, hunt_password, test_hunt_admin=False):    
    '''
    Save current game info user tmp_variable
    '''    

    if not test_hunt_admin:        
        p.current_hunt = hunt_password  # avoid when testing
    hunt_info = HUNTS_PW[hunt_password]
    airtable_game_id = hunt_info['Airtable_Game_ID']
    hunt_settings = get_hunt_settings(airtable_game_id)
    hunt_languages =  get_hunt_languages(hunt_password)
    hunt_ui = get_hunt_ui(airtable_game_id, hunt_languages)
    instructions_table = Airtable(airtable_game_id, f'Instructions_{p.language}', api_key=settings.AIRTABLE_API_KEY)    
    survey_table = Airtable(airtable_game_id, f'Survey_{p.language}', api_key=settings.AIRTABLE_API_KEY)                
    instructions_steps = airtable_utils.get_rows(
        instructions_table, view='Grid view',
        filter=lambda r: not r.get('Skip',False), 
    )
    mission_tab_name = f'Missioni_{p.language}'
    survey = airtable_utils.get_rows(survey_table, view='Grid view')
    if not test_hunt_admin:
        p.tmp_variables = {} # resetting vars 
        # but we don't want to reset ADMIN_HUNT_NAME and ADMIN_HUNT_PW for admins (mission test)
    tvar = p.tmp_variables
    tvar['HUNT_NAME'] = hunt_info['Name']
    tvar['HUNT_LANGUAGES'] = hunt_languages
    tvar['TEST_HUNT_MISSION_ADMIN'] = test_hunt_admin
    tvar['HUNT_START_GPS'] = get_closest_mission_lat_lon(p, airtable_game_id, mission_tab_name)
    tvar['SETTINGS'] = hunt_settings    
    tvar['UI'] = hunt_ui    
    tvar['HUNT_INFO'] = hunt_info
    tvar['Notify_Group ID'] = hunt_info.get('Notify_Group ID', None)
    tvar['Validators IDs'] = hunt_info.get('Validators IDs', None)
    tvar['ID'] = p.get_id()
    tvar['NOME'] = p.get_first_name(escape_markdown=False)
    tvar['COGNOME'] = p.get_last_name(escape_markdown=False)
    tvar['USERNAME'] = p.get_username(escape_markdown=False)
    tvar['EMAIL'] = ''
    tvar['MISSION_TIMES'] = []
    tvar['INSTRUCTIONS'] = {'STEPS': instructions_steps, 'COMPLETED': 0}    
    tvar['SURVEY_INFO'] = {'TODO': survey, 'CURRENT': None, 'COMPLETED': [], 'TOTAL': len(survey)}
    tvar['GROUP_NAME'] = ''
    tvar['GROUP_MEDIA_FILE_IDS'] = []
    tvar['START_TIME'] = 0
    tvar['END_TIME'] = 0
    tvar['ELAPSED GAME'] = -1
    tvar['ELAPSED MISSIONS'] = -1
    tvar['PENALTY TIME'] = -1
    tvar['TOTAL TIME GAME'] = -1
    tvar['TOTAL TIME MISSIONS'] = -1
    tvar['PENALTIES'] = 0    
    tvar['PENALTY TIME'] = 0 # seconds
    tvar['FINISHED'] = False # seconds

def build_missions(p, test_all=False):
    tvar = p.tmp_variables
    hunt_settings = tvar['SETTINGS']
    airtable_game_id = tvar['HUNT_INFO']['Airtable_Game_ID']
    mission_tab_name = f'Missioni_{p.language}'
    if test_all:
        missions_dict = get_missions_name_fields_dict(airtable_game_id, mission_tab_name, active=True)    
        missions = list(missions_dict.values())
    elif hunt_settings.get('MISSIONS_SELECTION', None) == 'ROUTING':
        missions = get_missioni_routing(p, airtable_game_id, mission_tab_name)
        if missions is None:            
            return False # problema selezione percorso
    else:
        # RANDOM - default
        start_lat_long = p.get_tmp_variable('HUNT_START_GPS')
        missions = get_random_missions(airtable_game_id, mission_tab_name, start_lat_long)

        if p.is_admin_current_hunt(): 
            from historic.bot.bot_telegram import send_message   
            random_missioni_names = '\n'.join([' {}. {}'.format(n,x['NOME']) for n,x in enumerate(missions,1)])
            send_message(p, "DEBUG Random missioni:\n{}".format(random_missioni_names))

    tvar['MISSIONI_INFO'] = {'TODO': missions, 'CURRENT': None, 'COMPLETED': [], 'TOTAL': len(missions)}
    return True

def get_missions_name_fields_dict(airtable_game_id, mission_tab_name, active=True):
    # name -> fields dict (table row)
    table = Airtable(airtable_game_id, mission_tab_name, api_key=settings.AIRTABLE_API_KEY)
    missions_name_fields_dict = {
        row['fields']['NOME']: row['fields'] 
        for row in table.get_all() 
        if row['fields'].get('ACTIVE',False)==active    
    }
    return missions_name_fields_dict

def get_final_missions_dict_names(missions_name_fields_dict):
    final_missions_names = [
        m_name
        for m_name,fields in missions_name_fields_dict.items() 
        if fields.get('FINALE', False)
    ]

    # final missions and those connected to them via NEXT
    all_final_missions_or_linked = []
    final_missions_and_linked_names = {}
    for final_mission in final_missions_names:
        linked_missions = [final_mission]
        final_missions_and_linked_names[final_mission] = linked_missions        
        while True:
            new_connections = [
                m_name
                for m_name,fields in missions_name_fields_dict.items() 
                if (
                    m_name not in linked_missions and
                    fields.get('NEXT', '') in linked_missions
                )
            ]
            if new_connections:
                linked_missions.extend(new_connections)
            else:
                break
        all_final_missions_or_linked.extend(linked_missions)
        linked_missions.remove(final_mission)

    remaining_missions_names = [
        m_name
        for m_name in missions_name_fields_dict
        if  m_name not in all_final_missions_or_linked
    ]

    assert len(remaining_missions_names)>0 
    # this could happen if all misions are linked
    # TODO: fix this

    return final_missions_and_linked_names, remaining_missions_names

def get_all_missions_lat_lon(airtable_game_id, mission_tab_name, exclude_finals_and_linked=True, exclude_in_next=True):

    MISSIONI_ACTIVE = get_missions_name_fields_dict(airtable_game_id, mission_tab_name, active=True)
    
    _, no_final_or_linked_names = get_final_missions_dict_names(MISSIONI_ACTIVE)

    # missions names in NEXT columns
    missions_names_in_next = [
        fields['NEXT'] for fields in MISSIONI_ACTIVE.values()
        if fields.get('NEXT',None)
    ]    
        
    # exlude to chose mission among those in the final group (and linked)
    all_gps = np.asarray(
        [
            utility.get_lat_lon_from_string(fields['GPS']) 
            for m_name, fields in MISSIONI_ACTIVE.items()
            if (
                (not exclude_finals_and_linked or m_name in no_final_or_linked_names) and     # check if in the chain of final missions
                (not exclude_in_next or m_name not in missions_names_in_next) and
                fields.get('GPS', None)
            )
        ]
    )

    return all_gps


def get_closest_mission_lat_lon(p, airtable_game_id, mission_tab_name):    

    all_gps = get_all_missions_lat_lon(airtable_game_id, mission_tab_name)

    current_pos = np.asarray(p.get_location())
    dist_2 = np.sum((all_gps - current_pos)**2, axis=1)
    idx = np.argmin(dist_2)
    closest_gps = all_gps[idx].tolist()
    return closest_gps


def get_random_missions(airtable_game_id, mission_tab_name, start_lat_long):

    MISSIONI_ACTIVE = get_missions_name_fields_dict(airtable_game_id, mission_tab_name, active=True)

    start_lat_long_str = ', '.join([str(x) for x in start_lat_long])

    final_missions_and_linked_names, remaining_missions_names = \
        get_final_missions_dict_names(MISSIONI_ACTIVE)

    start_mission_name = [k for k,v in MISSIONI_ACTIVE.items() if v.get('GPS',None)==start_lat_long_str]

    assert len(start_mission_name) == 1
    start_mission_name = start_mission_name[0]    

    assert start_mission_name in remaining_missions_names
    remaining_missions_names.remove(start_mission_name)

    # missions names in NEXT columns
    missions_names_in_next = [
        fields['NEXT'] for fields in MISSIONI_ACTIVE.values()
        if fields.get('NEXT',None)
    ]
    
    remaining_missions_names_no_next = [
        m_name for m_name in MISSIONI_ACTIVE
        if (
            m_name in remaining_missions_names and
            m_name not in missions_names_in_next
        )
    ]

    chosen_final_mission_name = \
        choice(list(final_missions_and_linked_names.keys())) \
        if final_missions_and_linked_names \
        else None    
    
    if chosen_final_mission_name:
        # adding non chosen final missions and linked to remaining_missions_names_no_next
        # (only those with no NEXT)
        for f,linked_missions in final_missions_and_linked_names.items():
            if f == chosen_final_mission_name:
                continue
            for m in linked_missions:
                if m not in missions_names_in_next:
                    remaining_missions_names_no_next.append(m)
            remaining_missions_names_no_next.append(f) # this shouldn't have none by default
        
    shuffle(remaining_missions_names_no_next)

    remaining_missions_names_no_next.insert(0, start_mission_name)

    missioni_random_names = []
    
    for m in remaining_missions_names_no_next:
        missioni_random_names.append(m)
        next = MISSIONI_ACTIVE[m].get('NEXT', None)
        while next:
            missioni_random_names.append(next)
            next = MISSIONI_ACTIVE[next].get('NEXT', None)

    if chosen_final_mission_name:
        final_mission_linked = final_missions_and_linked_names[chosen_final_mission_name]
        final_mission_linked.reverse() # mission close to final at the end
        missioni_random_names.extend(final_mission_linked)
        missioni_random_names.append(chosen_final_mission_name)

    assert len(missioni_random_names) == len(MISSIONI_ACTIVE)

    missioni_random = [MISSIONI_ACTIVE[m] for m in missioni_random_names]    

    return missioni_random

def get_missioni_routing(p, airtable_game_id, mission_tab_name):
    
    from historic.bot.bot_telegram import report_admins, send_message, send_photo_data

    MISSIONI_ACTIVE = get_missions_name_fields_dict(airtable_game_id, mission_tab_name, active=True)
    MISSIONI_SKIP = get_missions_name_fields_dict(airtable_game_id, mission_tab_name, active=False)

    game_dm = DataMatrices(
        dataset_name = airtable_game_id,
        api = api_google
    )      

    max_attempts = 15

    lat, long = p.get_tmp_variable('HUNT_START_GPS')
    start_idx = game_dm.get_coordinate_index(lat=lat, long=long)
    skip_points_idx = [
        game_dm.get_stop_name_index(m)
        for m in MISSIONI_SKIP
    ]

    profile = p.get_tmp_variable('ROUTE_TRANSPORT', api_google.PROFILE_FOOT_WALKING)
    duration_min = p.get_tmp_variable('ROUTE_DURATION_MIN', 60) # 1 h default
    circular_route = p.get_tmp_variable('ROUTE_CIRCULAR', False)

    # manual fine tuning - TODO: make it more robust
    # max_grid_overalapping, duration_tolerance_min = \
    #     fine_tuning_trento_open(profile, circular_route, duration_min)

    max_grid_overalapping = 20
    duration_tolerance_min = 10    
    route_planner = None                
    found_solution = False                    
    
    for _ in range(1,max_attempts+1): # attempts

        duration_sec = duration_min * 60
        duration_tolerance_sec = duration_tolerance_min * 60

        route_planner = RoutePlanner(
            dm = game_dm,
            profile = profile,
            metric = METRIC_DURATION,
            start_idx = start_idx, 
            min_dst = 60, # 2 min
            max_dst = 720, # 12 min
            goal_tot_dst = duration_sec,
            tot_dst_tolerance = duration_tolerance_sec,
            min_route_size = None,
            max_route_size = None,
            skip_points_idx = skip_points_idx,
            check_convexity = False,
            overlapping_criteria = 'GRID',
            max_overalapping = max_grid_overalapping, # in meters/grids, None to ignore this constraint
            stop_duration = 300, # da cambiare in 300 per 5 min
            num_attempts = 10000, # set to None for exaustive search
            random_seed = None, # only relevan if num_attempts is not None (non exhaustive serach)
            exclude_neighbor_dst = 60,    
            circular_route = circular_route,
            num_best = 1,
            stop_when_num_best_reached = True,
            num_discarded = None,
            show_progress_bar = False
        )

        route_planner.build_routes()

        if len(route_planner.solutions) > 0:
            found_solution = True
            break
        
        max_grid_overalapping += 20
        duration_tolerance_min += 10

    if found_solution:

        _, stop_names, info, best_route_img, estimated_duration_min = \
            route_planner.get_routes(
                show_map=False,
                log=False
            )      

        missioni_route = [
            MISSIONI_ACTIVE[mission_name]
            for mission_name in stop_names
        ]

        info_msg = \
            f'Ho selezionato per voi {len(stop_names)} tappe e dovreste metterci circa {estimated_duration_min} minuti. '\
            'Ovviamente dipende da quanto sarete veloci e abili a risolvere gli indovinelli! 😉'     
        send_message(p, info_msg)

        if p.is_admin_current_hunt():                 
            info_text = '\n'.join(info)
            send_message(p, f"🐛 DEBUG:\n\n{info_text}", markdown=False)
            send_photo_data(p, best_route_img)
            # selected_missioni_names = '\n'.join([' {}. {}'.format(n,x['NOME']) for n,x in enumerate(missioni_route,1)])
            # send_message(p, "DEBUG Selected missioni:\n{}".format(selected_missioni_names))
        notify_group_id = get_notify_group_id(p)
        if notify_group_id:
            squadra_name = get_group_name(p)
            info_text = f'La squadra {squadra_name} ha attenuto il seguente percorso:\n\n'
            info_text += '\n'.join(info)
            send_message(notify_group_id, info_text, markdown=False)
            send_photo_data(notify_group_id, best_route_img)
        return missioni_route

    else:
        error_msg = f'⚠️ User {p.get_id()} encountered error in routing:\n'\
                    f'dataset name = {airtable_game_id}\n'\
                    f'start num = {start_idx + 1}\n'\
                    f'duration min = {duration_min}\n'\
                    f'profile = {profile}\n'\
                    f'circular route = {circular_route}\n'
        report_admins(error_msg)
        return None


def is_mission_selection_routing_based(p):
    tvar = p.tmp_variables
    hunt_settings = tvar['SETTINGS']
    return hunt_settings.get('MISSIONS_SELECTION', None) == 'ROUTING'

def user_in_game(p):
    return p.current_hunt is not None

def exit_game(p, save_data=True, reset_current_hunt=True, put=True):
    if p.current_hunt is None:
        return False
    if save_data:
        finished = p.tmp_variables.get('FINISHED', False)
        if not finished:
            set_game_end_time(p, finished=False)
            save_game_data_in_airtable(p)
    if reset_current_hunt:
        p.current_hunt = None
    if put:
        p.put()
    return True

def get_game_stats(p):
    name_username = p.get_first_last_username(escape_markdown=False)
    vars = p.tmp_variables
    group_name = vars.get('GROUP_NAME','') # gruppo non pervenuto
    email = vars.get('EMAIL','')
    mission_info = vars.get('MISSIONI_INFO', None)
    last_mod_hours = dtu.delta_time_now_utc_hours(p.last_mod)
    last_access_str = f'(ultimo accesso {last_mod_hours} ore fa)'
    stats = ['➡', f'{name_username}']
    if email:
        stats.append(email)
    if group_name:
        stats.append(f'gruppo: {group_name}')
    if mission_info:        
        completed = len(vars['MISSIONI_INFO']['COMPLETED'])
        total = vars['MISSIONI_INFO']['TOTAL']
        finished = vars['FINISHED']                        
        stats.append(f'Missioni: {completed}/{total}')
        if finished:
            stats.append('COMPLETATA')
        else:                         
            stats.append(last_access_str)
    else:
        stats.extend(['NON INIZIATA', last_access_str])
    stats.append(f'🐛 /debug_{p.get_id()}')
    stats.append(f'❌ /terminate_{p.get_id()}')
    return ' '.join(stats)

def get_hunt_name(p):
    return p.tmp_variables['HUNT_NAME']

def get_notify_group_id(p):
    id_list = p.tmp_variables['Notify_Group ID']
    if id_list is None:
        return None
    return str(id_list[0])

def notify_group(p, msg):
    from historic.bot.bot_telegram import send_message
    id_list = p.tmp_variables['Notify_Group ID']
    if id_list is None:
        return False
    return send_message(id_list, msg)


def manual_validation(p):
    return p.tmp_variables['Validators IDs'] != None

def get_validator_chat_id(p):
    validator_id = p.tmp_variables['Validators IDs']
    if validator_id:
        return validator_id[0].split('_')[1]
    return None

def set_group_name(p, name):
    p.tmp_variables['GROUP_NAME'] = name

def get_group_name(p, escape_markdown=True):
    if 'GROUP_NAME' not in p.tmp_variables:
        return None
    name = p.tmp_variables['GROUP_NAME']
    if escape_markdown:
        name = utility.escape_markdown(name)
    return name

def set_game_start_time(p):
    
    start_time = dtu.now_utc_iso_format()
    p.tmp_variables['START_TIME'] = start_time

def get_game_start_time(p):
    return p.tmp_variables['START_TIME']

def set_game_end_time(p, finished):
    end_time = dtu.now_utc_iso_format()
    p.tmp_variables['END_TIME'] = end_time
    p.tmp_variables['FINISHED'] = finished

def start_mission(p):
    start_time = dtu.now_utc_iso_format()    
    current_mission = get_current_mission(p)
    current_mission['wrong_answers'] = []
    current_mission['start_time'] = start_time
    p.tmp_variables['MISSION_TIMES'].append([start_time])

def set_end_mission_time(p):
    current_mission = get_current_mission(p)
    current_mission['end_time'] = dtu.now_utc_iso_format()

def set_mission_end_time(p):
    end_time = dtu.now_utc_iso_format()
    last_mission_time = p.tmp_variables['MISSION_TIMES'][-1]
    last_mission_time.append(end_time)
    mission_ellapsed = dtu.delta_seconds_iso(*last_mission_time)
    return mission_ellapsed

def set_elapsed_and_penalty_and_compute_total(p):
    tvar = p.tmp_variables    
    end_time = get_end_time(p)
    start_time = get_game_start_time(p)
    
    elapsed_sec_game = dtu.delta_seconds_iso(start_time, end_time)
    elapsed_sec_missions = sum(dtu.delta_seconds_iso(s, e) for s,e in tvar['MISSION_TIMES'])            

    _, penalty_sec = get_total_penalty(p)    
    
    total_sec_game = elapsed_sec_game + penalty_sec
    total_sec_game_missions = elapsed_sec_missions + penalty_sec
    
    # variables to print to users
    tvar['penalty_sec'] = penalty_sec
    tvar['penalty_hms'] = utility.sec_to_hms(penalty_sec)
    tvar['total_hms_game'] = utility.sec_to_hms(total_sec_game)    
    tvar['ellapsed_hms_game'] = utility.sec_to_hms(elapsed_sec_game)    
    tvar['total_hms_missions'] = utility.sec_to_hms(total_sec_game_missions)    
    tvar['ellapsed_hms_missions'] = utility.sec_to_hms(elapsed_sec_missions)    
    
    # variables to save in airtable
    tvar['ELAPSED GAME'] = elapsed_sec_game
    tvar['ELAPSED MISSIONS'] = elapsed_sec_missions
    tvar['PENALTY TIME'] = penalty_sec # seconds
    tvar['TOTAL TIME GAME'] = elapsed_sec_game + penalty_sec
    tvar['TOTAL TIME MISSIONS'] = elapsed_sec_missions + penalty_sec
    
    p.put()

def get_elapsed_and_penalty_and_total_hms(p):
    tvar = p.tmp_variables 
    return \
        tvar['penalty_hms'], \
        tvar['total_hms_game'], \
        tvar['ellapsed_hms_game'], \
        tvar['total_hms_missions'], \
        tvar['ellapsed_hms_missions'] \

def get_end_time(p):
    return p.tmp_variables['END_TIME']

def get_total_missions(p):
    return p.tmp_variables['MISSIONI_INFO']['TOTAL']

def get_num_remaining_missions(p):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    return len(indovinello_info['TODO'])

def get_num_compleded_missions(p):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    return len(indovinello_info['COMPLETED'])

def set_next_mission(p, current_mission=None):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']    
    if current_mission is None:
        todo_missioni = indovinello_info['TODO']
        current_mission = todo_missioni.pop(0)
    indovinello_info['CURRENT'] = current_mission
    current_mission['wrong_answers'] = []    
    return current_mission

def get_current_mission(p):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    return indovinello_info['CURRENT']

def append_group_media_input_file_id(p, file_id):
    p.tmp_variables['GROUP_MEDIA_FILE_IDS'].append(file_id)

def set_current_mission_as_completed(p):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    current_mission = indovinello_info['CURRENT']
    indovinello_info['COMPLETED'].append(current_mission)
    indovinello_info['CURRENT'] = None

def increase_wrong_answers_current_indovinello(p, answer, give_penalty, put=True):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    current_mission = indovinello_info['CURRENT']
    current_mission['wrong_answers'].append(answer)
    if give_penalty:
        p.tmp_variables['PENALTIES'] += 1
    if put:
        p.put()                

def get_total_penalty(p):    
    PENALTIES = p.tmp_variables['PENALTIES']
    SEC_PENALITY_WRONG_ANSWER = int(p.tmp_variables['SETTINGS']['SEC_PENALITY_WRONG_ANSWER'])
    penalty_time_sec = PENALTIES * SEC_PENALITY_WRONG_ANSWER
    return PENALTIES, penalty_time_sec

def get_tot_survey_questions(p):
    return p.tmp_variables['SURVEY_INFO']['TOTAL']

def get_num_completed_survey_questions(p):
    survey_info = p.tmp_variables['SURVEY_INFO']
    return len(survey_info['COMPLETED'])

def increase_intro_completed(p):
    p.tmp_variables['INSTRUCTIONS']['COMPLETED'] += 1

def set_next_survey_question(p):
    survey_info = p.tmp_variables['SURVEY_INFO']
    todo_questions = survey_info['TODO']
    current_question = todo_questions.pop(0)
    survey_info['CURRENT'] = current_question
    return current_question

def get_current_survey_question(p):
    survey_info = p.tmp_variables['SURVEY_INFO']
    return survey_info['CURRENT']

def set_current_survey_question_as_completed(p, answer):
    survey_info = p.tmp_variables['SURVEY_INFO']
    current_question = survey_info['CURRENT']
    current_question['ANSWER'] = answer
    survey_info['COMPLETED'].append(current_question)
    survey_info['CURRENT'] = None

def get_remaing_survey_questions_number(p):
    survey_info = p.tmp_variables['SURVEY_INFO']
    return len(survey_info['TODO'])

def debug_tmp_vars(p):
    import json
    #return json.dumps(p.tmp_variables['MISSIONI_INFO']['CURRENT'], indent=4)
    return json.dumps(p.tmp_variables, indent=4, ensure_ascii=False)