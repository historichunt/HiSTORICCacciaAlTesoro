import utility
import key
from airtable import Airtable
from random import shuffle, choice
import ndb_person
from ndb_person import Person
import params

#################
# MISSIONI TABLE
#################
'''
NOME, ACTIVE, FINALE, CATEGORIA, 
INTRO_MEDIA, INTRO_MEDIA_CAPTION, 
INTRODUZIONE_LOCATION,
DOMANDA, SOLUZIONI,
INDIZIO_1, INDIZIO_2, 
GPS, REQUIRED_INPUT,
POST_MEDIA, POST_MEDIA_CAPTION,
POST_MESSAGE
'''

def get_settings(p, airtable_missioni_id):
    SETTINGS_TABLE = Airtable(airtable_missioni_id, 'Settings', api_key=key.AIRTABLE_API_KEY)
    SETTINGS = {
        row['fields']['Name']:row['fields']['Value'] 
        for row in SETTINGS_TABLE.get_all() 
        if row['fields'].get('Name', False)
    }
    return SETTINGS

def get_random_missioni(p, airtable_missioni_id, mission_tab_name, initial_cat):
    import itertools
    MISSIONI_TABLE = Airtable(airtable_missioni_id, mission_tab_name, api_key=key.AIRTABLE_API_KEY)
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
                assert next(round_robin_cat) == next_mission_cat
                next_mission_name = next_mission.get('NEXT',None)
        elif missione_finale and missione_finale['CATEGORIA']==cat:
            missioni_random.append(missione_finale)
            missione_finale = None
    if missione_finale:
        missioni_random.append(missione_finale)
    # debug
    if p.is_manager(): 
        from bot_telegram import send_message   
        random_missioni_names = '\n'.join([' {}. {}'.format(n,x['NOME']) for n,x in enumerate(missioni_random,1)])
        send_message(p, "DEBUG Random missioni:\n{}".format(random_missioni_names))
    return missioni_random

#################
# SURVEY
#################

SURVEY_TABLE = Airtable(key.AIRTABLE_CONFIG_ID, 'Survey', api_key=key.AIRTABLE_API_KEY)
SURVEY = [row['fields'] for row in SURVEY_TABLE.get_all()]

# DOMANDA, RISPOSTE
SURVEY_QUESTIONS = [s['DOMANDA'] for s in SURVEY]

def get_survey_data():
    return list(SURVEY)

#################
# RESULT GAME TABLE
#################

RESULTS_GAME_TABLE_HEADERS = \
    ['ID', 'GROUP_NAME', 'NOME', 'COGNOME', 'USERNAME', 'EMAIL', \
    'START_TIME', 'END_TIME', 'ELAPSED GAME', 'ELAPSED MISSIONS', \
    'PENALTIES', 'PENALTY TIME', 'COMPLETED', 'TOTAL TIME GAME', 'TOTAL TIME MISSIONS']

def save_game_data_in_airtable(p, save_survey):
    from bot_telegram import get_photo_url_from_telegram
    import json
    game_data = p.tmp_variables
    airtable_risultati_id = game_data['HUNT_INFO']['Airtable_Risultati_ID']

    RESULTS_GAME_TABLE = Airtable(airtable_risultati_id, 'Results', api_key=key.AIRTABLE_API_KEY)    

    games_row = {}
    for h in RESULTS_GAME_TABLE_HEADERS:
        games_row[h] = game_data[h]
    games_row['GAME VARS'] = json.dumps(game_data,ensure_ascii=False)
    games_row['GROUP_MEDIA_FILE_IDS'] = [
        {'url': get_photo_url_from_telegram(file_id)} 
        for file_id in game_data['GROUP_MEDIA_FILE_IDS']
    ]
    RESULTS_GAME_TABLE.insert(games_row)
    
    if save_survey:
        RESULTS_SURVEY_TABLE = Airtable(airtable_risultati_id, 'Survey', api_key=key.AIRTABLE_API_KEY)
        survey_row = {'ID': game_data['ID']}
        for question in SURVEY_QUESTIONS:
            questions_data = game_data['SURVEY_INFO']['COMPLETED']
            answer = next(row['ANSWER'] for row in questions_data if row['DOMANDA'] == question)
            survey_row[question] = answer
        RESULTS_SURVEY_TABLE.insert(survey_row)


################################
# PEOPLE FOR GAME
################################

from ndb_utils import client
with client.context():
    HISTORIC_GROUP = ndb_person.get_person_by_id(key.HISTORIC_GROUP_ID) #key.FEDE_T_ID
    HISTORIC_GROUP_id = HISTORIC_GROUP.chat_id

################################
# GAME MANAGEMENT FUNCTIONS
################################

def reset_game(p, hunt_password):
    hunt_info = key.ACTIVE_HUNTS[hunt_password]
    airtable_missioni_id = hunt_info['Airtable_Missioni_ID']        
    settings = get_settings(p, airtable_missioni_id)
    p.current_hunt = hunt_password         
    initial_cat = settings.get('INITIAL_CAT', None)
    multilingual =  settings.get('MULTILINGUAL', 'False') == 'True'
    mission_tab_name = 'Missioni_EN' if multilingual and p.language=='EN' else 'Missioni'
    missioni = get_random_missioni(p, airtable_missioni_id, mission_tab_name, initial_cat)
    notify_group = hunt_info.get('Notify_Group', False)
    validator_id = hunt_info.get('Validator_ID', None)
    survey = get_survey_data()    
    p.tmp_variables = {}  
    p.tmp_variables['SETTINGS'] = settings      
    p.tmp_variables['HUNT_INFO'] = hunt_info
    p.tmp_variables['Notify_Group'] = notify_group
    p.tmp_variables['Validator_ID'] = validator_id
    p.tmp_variables['ID'] = p.get_id()
    p.tmp_variables['NOME'] = p.get_first_name(escape_markdown=False)
    p.tmp_variables['COGNOME'] = p.get_last_name(escape_markdown=False)
    p.tmp_variables['USERNAME'] = p.get_username(escape_markdown=False)
    p.tmp_variables['EMAIL'] = ''
    p.tmp_variables['MISSION_TIMES'] = []
    p.tmp_variables['MISSIONI_INFO'] = {'TODO': missioni, 'CURRENT': None, 'COMPLETED': [], 'TOTAL': len(missioni)}
    p.tmp_variables['SURVEY_INFO'] = {'TODO': survey, 'CURRENT': None, 'COMPLETED': [], 'TOTAL': len(survey)}
    # question -> 'ANSWER'
    p.tmp_variables['GROUP_NAME'] = ''
    p.tmp_variables['GROUP_MEDIA_FILE_IDS'] = []
    p.tmp_variables['START_TIME'] = ''
    p.tmp_variables['END_TIME'] = ''
    p.tmp_variables['ELAPSED'] = 0 # seconds
    p.tmp_variables['PENALTIES'] = 0    
    p.tmp_variables['PENALTY TIME'] = 0 # seconds
    p.tmp_variables['TOTAL TIME'] = 0 # seconds
    p.tmp_variables['COMPLETED'] = False # seconds

def user_in_game(p):
    return p.current_hunt is not None

def exit_game(p, save_data=True, put=True):
    if p.current_hunt is None:
        return False
    if save_data:
        completed = p.tmp_variables.get('COMPLETED', False)
        if not completed:
            set_empty_vars_for_airtable(p)
            set_game_end_time(p, completed=False)
        save_game_data_in_airtable(p, save_survey=completed)
    p.current_hunt = None
    p.tmp_variables = {}
    if put:
        p.put()
    return True

def get_game_stats(p):
    group_name = p.tmp_variables['GROUP_NAME']
    completed = len(p.tmp_variables['MISSIONI_INFO']['COMPLETED'])
    total = p.tmp_variables['MISSIONI_INFO']['TOTAL']
    return '{} {}/{}'.format(group_name, completed, total)

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
    name = p.tmp_variables['GROUP_NAME']
    if escape_markdown:
        name = utility.escape_markdown(name)
    return name

def set_game_start_time(p):
    import date_time_util as dtu
    start_time = dtu.nowUtcIsoFormat()
    p.tmp_variables['START_TIME'] = start_time

def get_game_start_time(p):
    return p.tmp_variables['START_TIME']

def set_game_end_time(p, completed):
    import date_time_util as dtu
    end_time = dtu.nowUtcIsoFormat()
    p.tmp_variables['END_TIME'] = end_time
    if completed:
        p.tmp_variables['COMPLETED'] = True

def start_mission(p):
    import date_time_util as dtu
    start_time = dtu.nowUtcIsoFormat()    
    current_indovinello = getCurrentIndovinello(p)
    current_indovinello['wrong_answers'] = []
    current_indovinello['start_time'] = start_time
    p.tmp_variables['MISSION_TIMES'].append([start_time])

def set_end_mission_time(p):
    import date_time_util as dtu
    current_indovinello = getCurrentIndovinello(p)
    current_indovinello['end_time'] = dtu.nowUtcIsoFormat()

def set_mission_end_time(p):
    import date_time_util as dtu
    end_time = dtu.nowUtcIsoFormat()
    last_mission_time = p.tmp_variables['MISSION_TIMES'][-1]
    last_mission_time.append(end_time)
    mission_ellapsed = dtu.delta_seconds_iso(*last_mission_time)
    return mission_ellapsed

def set_empty_vars_for_airtable(p):
    tvar = p.tmp_variables    
    tvar['START_TIME'] = 0
    tvar['ELAPSED GAME'] = -1
    tvar['ELAPSED MISSIONS'] = -1
    tvar['PENALTY TIME'] = -1
    tvar['TOTAL TIME GAME'] = -1
    tvar['TOTAL TIME MISSIONS'] = -1
    p.put()

def set_elapsed_and_penalty_and_compute_total(p):
    import date_time_util as dtu
    tvar = p.tmp_variables    
    end_time = get_end_time(p)
    start_time = get_game_start_time(p)
    
    elapsed_sec_game = dtu.delta_seconds_iso(start_time, end_time)
    elapsed_sec_missions = sum(dtu.delta_seconds_iso(s, e) for s,e in tvar['MISSION_TIMES'])            

    wrong_answers, penalty_sec = get_total_penalty(p)
    penalty_hms = utility.sec_to_hms(penalty_sec)
    total_sec_game = elapsed_sec_game + penalty_sec
    total_sec_game_missions = elapsed_sec_missions + penalty_sec
    ellapsed_hms_game = utility.sec_to_hms(elapsed_sec_game)
    total_hms_game = utility.sec_to_hms(total_sec_game)    
    ellapsed_hms_missions = utility.sec_to_hms(elapsed_sec_missions)
    total_hms_missions = utility.sec_to_hms(total_sec_game_missions)    
    
    tvar['ELAPSED GAME'] = elapsed_sec_game
    tvar['ELAPSED MISSIONS'] = elapsed_sec_missions
    tvar['PENALTY TIME'] = penalty_sec # seconds
    tvar['TOTAL TIME GAME'] = elapsed_sec_game + penalty_sec
    tvar['TOTAL TIME MISSIONS'] = elapsed_sec_missions + penalty_sec
    p.put()
    return penalty_hms, total_hms_game, ellapsed_hms_game, total_hms_missions, ellapsed_hms_missions

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

def getTotalQuestions(p):
    return p.tmp_variables['SURVEY_INFO']['TOTAL']

def completedQuestionsNumber(p):
    survey_info = p.tmp_variables['SURVEY_INFO']
    return len(survey_info['COMPLETED'])

def setNextQuestion(p):
    survey_info = p.tmp_variables['SURVEY_INFO']
    todo_questions = survey_info['TODO']
    current_question = todo_questions.pop(0)
    survey_info['CURRENT'] = current_question
    return current_question

def getCurrentQuestion(p):
    survey_info = p.tmp_variables['SURVEY_INFO']
    return survey_info['CURRENT']

def setCurrentQuestionAsCompleted(p, answer):
    survey_info = p.tmp_variables['SURVEY_INFO']
    current_question = survey_info['CURRENT']
    current_question['ANSWER'] = answer
    survey_info['COMPLETED'].append(current_question)
    survey_info['CURRENT'] = None

def remainingQuestionsNumber(p):
    survey_info = p.tmp_variables['SURVEY_INFO']
    return len(survey_info['TODO'])

def setEmail(p, email):
    p.tmp_variables['EMAIL'] = email

def debugTmpVariables(p):
    import json
    #return json.dumps(p.tmp_variables['MISSIONI_INFO']['CURRENT'], indent=4)
    return json.dumps(p.tmp_variables, indent=4, ensure_ascii=False)