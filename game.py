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
GPS, SKIP_SELFIE,
POST_MEDIA, POST_MEDIA_CAPTION,
POST_MESSAGE
'''

def get_random_missioni(airtable_missioni_id):
    import itertools
    MISSIONI_TABLE = Airtable(airtable_missioni_id, 'Missioni', api_key=key.AIRTABLE_API_KEY)
    MISSIONI_ALL = [row['fields'] for row in MISSIONI_TABLE.get_all() if row['fields'].get('ACTIVE',False)]    
    for row in MISSIONI_ALL:
        if 'FINALE' not in row:
            row['FINALE'] = False
        if 'CATEGORIA' not in row:
            row['CATEGORIA'] = ''
    SETTINGS_TABLE = Airtable(airtable_missioni_id, 'Settings', api_key=key.AIRTABLE_API_KEY)
    SETTINGS = {row['fields']['Name']:row['fields']['Value'] for row in SETTINGS_TABLE.get_all() if row['fields'].get('Name', False)}
    initial_cat =   SETTINGS.get('INITIAL_CAT', None)
    missioni_categories = list(set(row['CATEGORIA'] for row in MISSIONI_ALL))
    missioni = [row for row in MISSIONI_ALL if not row['FINALE']]
    missioni_finali = [row for row in MISSIONI_ALL if row['FINALE']]    
    missione_finale = choice(missioni_finali) if missioni_finali else None
    if missione_finale:
        missioni_finali.remove(missione_finale)
        missioni.extend(missioni_finali)
    missioni_cat_bucket = {
        cat:[row for row in missioni if row['CATEGORIA']==cat]
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
    while len(missioni_random) < len(missioni):
        cat = next(round_robin_cat)
        if len(missioni_cat_bucket[cat])>0:
            missioni_random.append(missioni_cat_bucket[cat].pop())
    if missione_finale:
        missioni_random.append(missione_finale)
    # debug
    # if True: 
    #     from bot_telegram import tell_admin   
    #     random_missioni_names = '\n'.join([' {}. {}'.format(n,x['NOME']) for n,x in enumerate(missioni_random,1)])
    #     tell_admin("Random missioni:\n{}".format(random_missioni_names))
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
    'WRONG ANSWERS', 'PENALTY TIME', 'TOTAL TIME GAME', 'TOTAL TIME MISSIONS']

def save_game_data_in_airtable(p):
    from bot_telegram import get_photo_url_from_telegram
    import json
    game_data = p.tmp_variables
    airtable_risultati_id = game_data['HUNT_INFO']['Airtable_Risultati_ID']

    RESULTS_GAME_TABLE = Airtable(airtable_risultati_id, 'Results', api_key=key.AIRTABLE_API_KEY)
    RESULTS_SURVEY_TABLE = Airtable(airtable_risultati_id, 'Survey', api_key=key.AIRTABLE_API_KEY)

    games_row = {}
    for h in RESULTS_GAME_TABLE_HEADERS:
        games_row[h] = game_data[h]
    games_row['GAME VARS'] = json.dumps(game_data,ensure_ascii=False)
    games_row['GROUP_SELFIES'] = [
        {'url': get_photo_url_from_telegram(file_id)} 
        for file_id in game_data['GROUP_SELFIES']
    ]
    RESULTS_GAME_TABLE.insert(games_row)
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

################################
# GAME MANAGEMENT FUNCTIONS
################################

def resetGame(p, hunt_password):
    hunt_info = key.ACTIVE_HUNTS[hunt_password]
    airtable_missioni_id = hunt_info['Airtable_Missioni_ID']    
    missioni = get_random_missioni(airtable_missioni_id)
    notify_group = hunt_info.get('Notify_Group', False)
    validator_id = hunt_info.get('Validator_ID', None)
    survey = get_survey_data()
    p.current_hunt = hunt_password
    p.tmp_variables = {}
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
    p.tmp_variables['GROUP_SELFIES'] = []
    p.tmp_variables['START_TIME'] = ''
    p.tmp_variables['END_TIME'] = ''
    p.tmp_variables['ELAPSED'] = 0 # seconds
    p.tmp_variables['WRONG ANSWERS'] = 0    
    p.tmp_variables['PENALTY TIME'] = 0 # seconds
    p.tmp_variables['TOTAL TIME'] = 0 # seconds

def exitGame(p, put=True):
    if p.current_hunt is None:
        return False
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

def setGroupName(p, name):
    p.tmp_variables['GROUP_NAME'] = name

def getGroupName(p, escape_markdown=True):
    name = p.tmp_variables['GROUP_NAME']
    if escape_markdown:
        name = utility.escape_markdown(name)
    return name

def setStartTime(p):
    import date_time_util as dtu
    start_time = dtu.nowUtcIsoFormat()
    p.tmp_variables['START_TIME'] = start_time

def getStartTime(p):
    return p.tmp_variables['START_TIME']

def setEndTime(p):
    import date_time_util as dtu
    end_time = dtu.nowUtcIsoFormat()
    p.tmp_variables['END_TIME'] = end_time

def set_mission_start_time(p):
    import date_time_util as dtu
    start_time = dtu.nowUtcIsoFormat()
    p.tmp_variables['MISSION_TIMES'].append([start_time])

def set_mission_end_time(p):
    import date_time_util as dtu
    end_time = dtu.nowUtcIsoFormat()
    last_mission_time = p.tmp_variables['MISSION_TIMES'][-1]
    last_mission_time.append(end_time)
    mission_ellapsed = dtu.delta_seconds_iso(*last_mission_time)
    return mission_ellapsed

def set_elapsed_and_penalty_and_compute_total(p):
    import date_time_util as dtu
    tvar = p.tmp_variables    
    end_time = getEndTime(p)
    start_time = getStartTime(p)
    
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

def getEndTime(p):
    return p.tmp_variables['END_TIME']

def getTotalIndovinelli(p):
    return p.tmp_variables['MISSIONI_INFO']['TOTAL']

def remainingIndovinelloNumber(p):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    return len(indovinello_info['TODO'])

def completedIndovinelloNumber(p):
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

def appendGroupSelfieFileId(p, file_id):
    p.tmp_variables['GROUP_SELFIES'].append(file_id)

def setCurrentIndovinelloAsCompleted(p):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    current_indovinello = indovinello_info['CURRENT']
    indovinello_info['COMPLETED'].append(current_indovinello)
    indovinello_info['CURRENT'] = None

def increase_wrong_answers_current_indovinello(p, answer, put=True):
    indovinello_info = p.tmp_variables['MISSIONI_INFO']
    current_indovinello = indovinello_info['CURRENT']
    current_indovinello['wrong_answers'].append(answer)
    p.tmp_variables['WRONG ANSWERS'] += 1
    if put:
        p.put()                

def get_total_penalty(p):    
    WRONG_ANSWERS = p.tmp_variables['WRONG ANSWERS']
    penalty_time_sec = WRONG_ANSWERS * params.SEC_PENALITY_WRONG_ANSWER
    return WRONG_ANSWERS, penalty_time_sec

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