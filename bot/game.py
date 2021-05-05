
from airtable import Airtable
from random import shuffle, choice
from bot import settings, utility, airtable_utils
import bot.date_time_util as dtu

#################
# GAMES CONFIG
#################

HUNTS_CONFIG_TABLE = Airtable(
    settings.AIRTABLE_CONFIG_ID, 
    'Hunts', 
    api_key=settings.AIRTABLE_API_KEY
)

HUNTS = {} # pw -> hunt_details (all)

def reload_config():
    global HUNTS
    HUNTS = {
        r['Password'].lower(): r
        for r in [
            row['fields'] 
            for row in HUNTS_CONFIG_TABLE.get_all() 
            if 'Password' in row['fields']
        ]
    }
    # ACTIVE_HUNTS = {k:v for k,v in HUNTS.items() if v.get('Active',False)}

reload_config()


#################
# MISSIONI TABLE
#################
'''
NOME, ACTIVE, FINALE, NEXT, CATEGORIA, 
INTRO_MEDIA, INTRO_MEDIA_CAPTION, 
INTRODUZIONE_LOCATION, GPS, 
DOMANDA_MEDIA, DOMANDA_MEDIA_CAPTION, DOMANDA,
SOLUZIONI, INDIZIO_1, INDIZIO_2, 
PENALTY,
POST_MEDIA, POST_MEDIA_CAPTION, POST_MESSAGE,
INPUT_INSTRUCTIONS, INPUT_TYPE, INPUT_CONFIRMATION, POST_INPUT
'''

def get_settings(p, airtable_game_id):
    SETTINGS_TABLE = Airtable(airtable_game_id, 'Settings', api_key=settings.AIRTABLE_API_KEY)
    SETTINGS = {
        row['fields']['Name']:row['fields']['Value'] 
        for row in SETTINGS_TABLE.get_all() 
        if row['fields'].get('Name', False)
    }
    return SETTINGS

def get_random_missioni(p, airtable_game_id, mission_tab_name, initial_cat):
    import itertools
    MISSIONI_TABLE = Airtable(airtable_game_id, mission_tab_name, api_key=settings.AIRTABLE_API_KEY)
    MISSIONI_ALL = [row['fields'] for row in MISSIONI_TABLE.get_all() if row['fields'].get('ACTIVE',False)]    
    for row in MISSIONI_ALL:
        if 'FINALE' not in row:
            row['FINALE'] = False
        if 'CATEGORIA' not in row:
            row['CATEGORIA'] = ''
    NEXT_MISSIONI = [
        m for m in MISSIONI_ALL if m['NOME'] in \
        [row.get('NEXT') for row in MISSIONI_ALL if row.get('NEXT',False)]
    ]
    MISSIONI_NOT_NEXT = [m for m in MISSIONI_ALL if m not in NEXT_MISSIONI]    
    missioni_categories = list(set(row['CATEGORIA'] for row in MISSIONI_NOT_NEXT))
    missioni_tmp = [row for row in MISSIONI_NOT_NEXT if not row['FINALE']]
    missioni_finali = [row for row in MISSIONI_NOT_NEXT if row['FINALE']]    
    missione_finale = choice(missioni_finali) if missioni_finali else None    

    if missione_finale:
        missioni_finali.remove(missione_finale)
        missioni_tmp.extend(missioni_finali) # adding all missini_finali except one (the actual final one)
    missioni_cat_bucket = {
        cat:[row for row in missioni_tmp if row['CATEGORIA']==cat]
        for cat in missioni_categories
    }
    for missioni_list_cat in missioni_cat_bucket.values():
        shuffle(missioni_list_cat)   
    
    if initial_cat in missioni_categories and len(missioni_categories)>1:
        missioni_categories.remove(initial_cat)
        missioni_categories.insert(0, initial_cat)
    elif missione_finale:
        missione_finale_cat = missione_finale['CATEGORIA']
        missioni_categories.remove(missione_finale_cat)
        shuffle(missioni_categories)
        missioni_categories.append(missione_finale_cat)
    else:
        shuffle(missioni_categories)
    missioni_random = []
    round_robin_cat = itertools.cycle(missioni_categories)
    while sum(len(bucket) for bucket in missioni_cat_bucket.values()) > 0:
        cat = next(round_robin_cat)
        if len(missioni_cat_bucket[cat])>0:
            chosen_mission = missioni_cat_bucket[cat].pop()
            missioni_random.append(chosen_mission)
            next_mission_name = chosen_mission.get('NEXT',None)
            while next_mission_name:
                next_mission = next(m for m in NEXT_MISSIONI if next_mission_name==m.get('NOME',None))
                missioni_random.append(next_mission)
                next_mission_cat = next_mission['CATEGORIA']      
                expected_cat = next(round_robin_cat)
                while expected_cat != next_mission_cat:
                    expected_cat = next(round_robin_cat)
                # assert expected_cat == next_mission_cat, \
                #     f"Unexpected cat of NEXT mission: {expected_cat}/{next_mission_cat} (expected/found)"
                next_mission_name = next_mission.get('NEXT',None)
        elif missione_finale and missione_finale['CATEGORIA']==cat:
            missioni_random.append(missione_finale)
            missione_finale = None
    if missione_finale:
        missioni_random.append(missione_finale)
    # debug
    if p.is_manager(): 
        from bot.bot_telegram import send_message   
        random_missioni_names = '\n'.join([' {}. {}'.format(n,x['NOME']) for n,x in enumerate(missioni_random,1)])
        send_message(p, "DEBUG Random missioni:\n{}".format(random_missioni_names))
    return missioni_random

#################
# RESULT GAME TABLE
#################

RESULTS_GAME_TABLE_HEADERS = \
    ['ID', 'GROUP_NAME', 'NOME', 'COGNOME', 'USERNAME', 'EMAIL', \
    'START_TIME', 'END_TIME', 'ELAPSED GAME', 'ELAPSED MISSIONS', \
    'PENALTIES', 'PENALTY TIME', 'FINISHED', 'TOTAL TIME GAME', 'TOTAL TIME MISSIONS']

def save_game_data_in_airtable(p):
    from bot.bot_telegram import get_photo_url_from_telegram
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

def reset_game(p, hunt_password):    
    '''
    Save current game info user tmp_variable
    '''    

    hunt_info = HUNTS[hunt_password]
    airtable_game_id = hunt_info['Airtable_Game_ID']
    hunt_settings = get_settings(p, airtable_game_id)
    instructions_table = Airtable(airtable_game_id, 'Instructions', api_key=settings.AIRTABLE_API_KEY)    
    survey_table = Airtable(airtable_game_id, 'Survey', api_key=settings.AIRTABLE_API_KEY)        
    p.current_hunt = hunt_password         
    initial_cat = hunt_settings.get('INITIAL_CAT', None)
    multilingual =  utility.get_str_param_boolean(hunt_settings, 'MULTILINGUAL')
    mission_tab_name = 'Missioni_EN' if multilingual and p.language=='EN' else 'Missioni'
    missioni = get_random_missioni(p, airtable_game_id, mission_tab_name, initial_cat)
    instructions_steps = airtable_utils.get_rows(
        instructions_table, filter=lambda r: not r.get('Skip',False), 
        sort_key=lambda r: r['ORDER']
    )
    survey = airtable_utils.get_rows(survey_table, sort_key=lambda r: r['QN'])
    tvar = p.tmp_variables = {}  
    tvar['SETTINGS'] = hunt_settings      
    tvar['HUNT_INFO'] = hunt_info
    tvar['Notify_Group'] = hunt_info.get('Notify_Group', False)
    tvar['Validator_ID'] = hunt_info.get('Validator_ID', None)
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

def send_notification_to_group(p):
    return p.tmp_variables['Notify_Group']

def manual_validation(p):
    return p.tmp_variables['Validator_ID'] != None

def get_validator_chat_id(p):
    validator_id = p.tmp_variables['Validator_ID']
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