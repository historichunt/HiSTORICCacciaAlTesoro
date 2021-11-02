
from airtable import Airtable
from random import shuffle, choice
from historic.config import params, settings
from historic.bot import utility, airtable_utils
import historic.bot.date_time_util as dtu
from historic.hunt_route import api_google, hunt_params
from historic.hunt_route.data_matrices import DataMatrices
from historic.hunt_route.routing import RoutePlanner

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

def get_hunt_settings(p, airtable_game_id):
    SETTINGS_TABLE = Airtable(airtable_game_id, 'Settings', api_key=settings.AIRTABLE_API_KEY)
    SETTINGS = {
        row['fields']['Name']:row['fields']['Value'] 
        for row in SETTINGS_TABLE.get_all() 
        if row['fields'].get('Name', False)
    }
    return SETTINGS

def get_hunt_ui(p, airtable_game_id, multilingual):    
    UI_TABLE = Airtable(airtable_game_id, 'UI', api_key=settings.AIRTABLE_API_KEY)
    table_rows = [
        row['fields'] 
        for row in UI_TABLE.get_all() 
    ]
    LANGS = params.LANGUAGES if multilingual else ['IT']
    UI = {
        lang: {
            r['VAR']: r[lang].strip()
            for r in table_rows
        }        
        for lang in LANGS
    }
    return UI

def get_all_missioni_random(p, airtable_game_id, mission_tab_name):
    MISSIONI_TABLE = Airtable(airtable_game_id, mission_tab_name, api_key=settings.AIRTABLE_API_KEY)
    MISSIONI_ALL = [row['fields'] for row in MISSIONI_TABLE.get_all() if row['fields'].get('ACTIVE',False)]    
    next_missioni = [
        m for m in MISSIONI_ALL if m['NOME'] in \
        [row.get('NEXT') for row in MISSIONI_ALL if row.get('NEXT',False)]
    ]
    missioni_not_next = [m for m in MISSIONI_ALL if m not in next_missioni]    
    
    missioni_tmp = [row for row in missioni_not_next if not row.get('FINALE',False)]
    missioni_finali = [row for row in missioni_not_next if row.get('FINALE',False)]    
    missione_finale = choice(missioni_finali) if missioni_finali else None    

    if missione_finale:
        missioni_finali.remove(missione_finale)
        missioni_tmp.extend(missioni_finali) # adding all missini_finali except one (the actual final one)

    shuffle(missioni_tmp)

    missioni_random = []
    while len(missioni_tmp) > 0:
        chosen_mission = missioni_tmp.pop()
        missioni_random.append(chosen_mission)
        next_mission_name = chosen_mission.get('NEXT',None)
        while next_mission_name:
            next_mission = next(m for m in next_missioni if next_mission_name==m.get('NOME',None))
            missioni_random.append(next_mission)            
            next_mission_name = next_mission.get('NEXT',None)
    if missione_finale:
        missioni_random.append(missione_finale)

    if p.is_admin_current_hunt(): 
        from historic.bot.bot_telegram import send_message   
        random_missioni_names = '\n'.join([' {}. {}'.format(n,x['NOME']) for n,x in enumerate(missioni_random,1)])
        send_message(p, "DEBUG Random missioni:\n{}".format(random_missioni_names))

    return missioni_random

def get_missioni_routing(p, airtable_game_id, mission_tab_name):
    
    from historic.bot.bot_telegram import send_message, send_photo_data

    MISSIONI_TABLE = Airtable(airtable_game_id, mission_tab_name, api_key=settings.AIRTABLE_API_KEY)
    MISSIONI_ALL = [row['fields'] for row in MISSIONI_TABLE.get_all() if row['fields'].get('ACTIVE',False)]    

    game_dm = DataMatrices(
        dataset_name = airtable_game_id,
        api = api_google
    )      

    route_planner = RoutePlanner(
        dm = game_dm,
        profile = api_google.PROFILE_FOOT_WALKING,
        metric = hunt_params.METRIC_DURATION,
        start_num = 1, 
        min_dst = 60, # 2 min
        max_dst = 600, # 10 min
        goal_tot_dst = 3600, # 1 h
        tot_dst_tolerance = 600, # ± 10 min
        min_route_size = None,
        max_route_size = None,
        check_convexity = False,
        overlapping_criteria = 'GRID',
        max_overalapping = 20, # 300, # in meters/grids, None to ignore this constraint
        stop_duration = 300, # da cambiare in 300 per 5 min
        num_attempts = 100000, # set to None for exaustive search
        random_seed = None, # only relevan if num_attempts is not None (non exhaustive serach)
        exclude_neighbor_dst = 60,    
        circular_route = True,
        num_best = 1,
        stop_when_num_best_reached = True,
        num_discarded = None,
        show_progress_bar = False
    )

    route_planner.build_routes()

    best_route_idx, stop_names, info, best_route_img = route_planner.get_routes(
        show_map=False,
        log=False
    )      

    if best_route_idx is None:
        send_message(p, "Problema selezione percorso")
        return None

    missioni_route = [
        next(m for m in MISSIONI_ALL if mission_name==m.get('NOME',None))
        for mission_name in stop_names
    ]

    if p.is_admin_current_hunt():                 
        info_text = '\n'.join(info)
        send_message(p, f"*DEBUG Routing missioni*:\n{info_text}", markdown=False)
        send_photo_data(p, best_route_img)
        selected_missioni_names = '\n'.join([' {}. {}'.format(n,x['NOME']) for n,x in enumerate(missioni_route,1)])
        send_message(p, "DEBUG Selected missioni:\n{}".format(selected_missioni_names))

    return missioni_route



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

    games_row = {}
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
    survey_row = {}
    survey_data = game_data['SURVEY_INFO']['COMPLETED']
    for row in survey_data:
        survey_row[row['QN']] = row['ANSWER'] # columns: Q1, Q2, ...
    results_survey_table.insert(survey_row)


################################
# GAME MANAGEMENT FUNCTIONS
################################

def reset_game(p, hunt_name, hunt_password):    
    '''
    Save current game info user tmp_variable
    '''    

    hunt_info = HUNTS_PW[hunt_password]
    airtable_game_id = hunt_info['Airtable_Game_ID']
    hunt_settings = get_hunt_settings(p, airtable_game_id)
    multilingual =  utility.get_str_param_boolean(hunt_settings, 'MULTILINGUAL')
    hunt_ui = get_hunt_ui(p, airtable_game_id, multilingual)
    instructions_table = Airtable(airtable_game_id, 'Instructions', api_key=settings.AIRTABLE_API_KEY)    
    survey_table = Airtable(airtable_game_id, 'Survey', api_key=settings.AIRTABLE_API_KEY)        
    p.current_hunt = hunt_password         
    # TODO: improve multilingual implementation
    mission_tab_name = 'Missioni_EN' if multilingual and p.language=='EN' else 'Missioni' 
    if hunt_settings.get('MISSIONS_SELECTION', None) == 'ROUTING':
        missioni = get_missioni_routing(p, airtable_game_id, mission_tab_name)
        if missioni is None:
            # problema selezione percorso
            return False
    else:
        # RANDOM - default
        missioni = get_all_missioni_random(p, airtable_game_id, mission_tab_name)        
    instructions_steps = airtable_utils.get_rows(
        instructions_table, view='Grid view',
        filter=lambda r: not r.get('Skip',False), 
    )
    survey = airtable_utils.get_rows(survey_table, view='Grid view')
    tvar = p.tmp_variables = {}  
    tvar['HUNT_NAME'] = hunt_name
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
    tvar['MISSIONI_INFO'] = {'TODO': missioni, 'CURRENT': None, 'COMPLETED': [], 'TOTAL': len(missioni)}
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
    return True

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
    name_username = p.get_first_last_username()
    group_name = p.tmp_variables.get('GROUP_NAME','')
    mission_info = p.tmp_variables.get('MISSIONI_INFO', None)
    if mission_info:
        completed = len(p.tmp_variables['MISSIONI_INFO']['COMPLETED'])
        total = p.tmp_variables['MISSIONI_INFO']['TOTAL']
        finished = p.tmp_variables['FINISHED']
        return '- {} {} {}/{} Finished={}'.format(name_username, group_name, completed, total, finished)
    else:
        return '- {} {} ?'.format(name_username, group_name)

def get_hunt_name(p):
    return p.tmp_variables['HUNT_NAME']

def get_notify_group_id(p):
    id_list = p.tmp_variables['Notify_Group ID']
    if id_list is None:
        return None
    return str(id_list[0])

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
    
    start_time = dtu.nowUtcIsoFormat()
    p.tmp_variables['START_TIME'] = start_time

def get_game_start_time(p):
    return p.tmp_variables['START_TIME']

def set_game_end_time(p, finished):
    end_time = dtu.nowUtcIsoFormat()
    p.tmp_variables['END_TIME'] = end_time
    p.tmp_variables['FINISHED'] = finished

def start_mission(p):
    start_time = dtu.nowUtcIsoFormat()    
    current_indovinello = getCurrentIndovinello(p)
    current_indovinello['wrong_answers'] = []
    current_indovinello['start_time'] = start_time
    p.tmp_variables['MISSION_TIMES'].append([start_time])

def set_end_mission_time(p):
    current_indovinello = getCurrentIndovinello(p)
    current_indovinello['end_time'] = dtu.nowUtcIsoFormat()

def set_mission_end_time(p):
    end_time = dtu.nowUtcIsoFormat()
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

def getTotalIndovinelli(p):
    return p.tmp_variables['MISSIONI_INFO']['TOTAL']

def remainingIndovinelloNumber(p):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    return len(indovinello_info['TODO'])

def completed_indovinello_number(p):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    return len(indovinello_info['COMPLETED'])

def setNextIndovinello(p):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    todo_missioni = indovinello_info['TODO']
    current_indovinello = todo_missioni.pop(0)
    indovinello_info['CURRENT'] = current_indovinello
    current_indovinello['wrong_answers'] = []    
    return current_indovinello

def getCurrentIndovinello(p):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    return indovinello_info['CURRENT']

def getCompletedIndovinello(p):
    game_info = p.tmp_variables['MISSIONI_INFO']
    return game_info['COMPLETED']

def append_group_media_input_file_id(p, file_id):
    p.tmp_variables['GROUP_MEDIA_FILE_IDS'].append(file_id)

def setCurrentIndovinelloAsCompleted(p):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    current_indovinello = indovinello_info['CURRENT']
    indovinello_info['COMPLETED'].append(current_indovinello)
    indovinello_info['CURRENT'] = None

def increase_wrong_answers_current_indovinello(p, answer, give_penalty, put=True):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    current_indovinello = indovinello_info['CURRENT']
    current_indovinello['wrong_answers'].append(answer)
    if give_penalty:
        p.tmp_variables['PENALTIES'] += 1
    if put:
        p.put()                

def is_multilingual(p):
    return p.tmp_variables['SETTINGS'].get('MULTILINGUAL', 'False') == 'True'

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

def set_email(p, email):
    p.tmp_variables['EMAIL'] = email

def debug_tmp_vars(p):
    import json
    #return json.dumps(p.tmp_variables['MISSIONI_INFO']['CURRENT'], indent=4)
    return json.dumps(p.tmp_variables, indent=4, ensure_ascii=False)