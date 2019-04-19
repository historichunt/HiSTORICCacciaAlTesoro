# -*- coding: utf-8 -*-

import utility
import key
from airtable import Airtable
from random import shuffle
import person
import params

#################
# INDOVINELLI
#################

INDOVINELLI_TABLE = Airtable(key.AIRTABLE_TABLE_MISSIONI_ID, 'Indovinelli', api_key=key.AIRTABLE_API_KEY)

def get_random_indovinelli():
    INDOVINELLI = [row['fields'] for row in utility.utify(INDOVINELLI_TABLE.get_all()) if row['fields'].get('ACTIVE',False)]
    # NOME, FINALE, INDOVINELLO, INDIZIO_1, INDIZIO_2, SOLUZIONI, INDIRIZZO, GPS

    INDOVINELLI_NOT_FINAL = [row for row in INDOVINELLI if not row.get('FINALE', False)]
    INDOVINELLI_FINAL = [row for row in INDOVINELLI if row.get('FINALE', False)]

    indovinelli_random = list(INDOVINELLI_NOT_FINAL)
    shuffle(indovinelli_random)    
    # random_indexes = [INDOVINELLI_NOT_FINAL.index(x) for x in indovinelli_random]        
    indovinelli_random.extend(INDOVINELLI_FINAL)    
    # if True:
    #     from main import tell_admin   
    #     random_indovinelli_names = [x['NOME'] for x in indovinelli_random]     
    #     tell_admin("Random indexes: {}".format(random_indexes))
    #     tell_admin("Random indovinelli: {}".format(random_indovinelli_names))
    return indovinelli_random

#################
# GIOCHI
#################

def get_random_giochi():
    GIOCHI_TABLE = Airtable(key.AIRTABLE_TABLE_MISSIONI_ID, 'Giochi', api_key=key.AIRTABLE_API_KEY)
    GIOCHI = [row['fields'] for row in utility.utify(GIOCHI_TABLE.get_all()) if row['fields'].get('ACTIVE',False)]
    # NOME, ISTRUZIONI, ATTACHMENT, SOLUZIONI
    # ATTACHMENT['url'] -> url of attachment

    giochi_random = list(GIOCHI)
    shuffle(giochi_random)
    return giochi_random

#################
# SURVEY
#################

SURVEY_TABLE = Airtable(key.AIRTABLE_CONFIG_ID, 'Survey', api_key=key.AIRTABLE_API_KEY)
SURVEY = [row['fields'] for row in utility.utify(SURVEY_TABLE.get_all())]

# DOMANDA, RISPOSTE
SURVEY_QUESTIONS = [s['DOMANDA'] for s in SURVEY]

def get_survey_data():
    return list(SURVEY)

#################
# RESULT GAME TABLE
#################

RESULTS_GAME_TABLE = Airtable(key.AIRTABLE_TABLE_RISULTATI_ID, 'Games', api_key=key.AIRTABLE_API_KEY)
RESULTS_SURVEY_TABLE = Airtable(key.AIRTABLE_TABLE_RISULTATI_ID, 'Survey', api_key=key.AIRTABLE_API_KEY)

RESULTS_GAME_TABLE_HEADERS = \
    ['ID', 'GROUP_NAME', 'NOME', 'COGNOME', 'USERNAME', 'EMAIL', \
    'START_TIME', 'END_TIME', 'ELAPSED GAME', 'ELAPSED MISSIONS', \
    'WRONG ANSWERS', 'PENALTY TIME', 'TOTAL TIME GAME', 'TOTAL TIME MISSIONS']

def save_game_data_in_airtable(p):
    import photos
    import json
    game_data = p.tmp_variables
    games_row = {}
    for h in RESULTS_GAME_TABLE_HEADERS:
        games_row[h] = game_data[h]
    games_row['GAME VARS'] = json.dumps(game_data,ensure_ascii=False)
    games_row['GROUP_SELFIES'] = [
        {'url': photos.prepareAndGetPhotoTelegramUrl(file_id)} 
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

HISTORIC_GROUP = person.getPersonById(key.HISTORIC_GROUP_ID) #key.FEDE_T_ID
VALIDATOR = person.getPersonById(key.VALIDATOR_ID)

################################
# GAME MANAGEMENT FUNCTIONS
################################

def resetGame(p):
    indovinelli = get_random_indovinelli()
    games = get_random_giochi()
    survey = get_survey_data()
    p.tmp_variables = {}
    p.tmp_variables['ID'] = p.getId()
    p.tmp_variables['NOME'] = p.getFirstName(escapeMarkdown=False)
    p.tmp_variables['COGNOME'] = p.getLastName(escapeMarkdown=False)
    p.tmp_variables['USERNAME'] = p.getUsername(escapeMarkdown=False)
    p.tmp_variables['EMAIL'] = ''
    p.tmp_variables['MISSION_TIMES'] = []
    p.tmp_variables['INDOVINELLI_INFO'] = {'TODO': indovinelli, 'CURRENT': None, 'COMPLETED': [], 'TOTAL': len(indovinelli)}
    # indovinello -> 'PHOTO_FILE_ID'
    p.tmp_variables['GIOCHI_INFO'] = {'TODO': games, 'CURRENT': None, 'COMPLETED': [], 'TOTAL': len(games)}
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

def setGroupName(p, name):
    p.tmp_variables['GROUP_NAME'] = name

def getGroupName(p, escapeMarkdown=True):
    name = p.tmp_variables['GROUP_NAME']
    if escapeMarkdown:
        name = utility.escapeMarkdown(name)
    return name

def appendGroupSelfieFileId(p, file_id):
    p.tmp_variables['GROUP_SELFIES'].append(file_id)

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
    return p.tmp_variables['INDOVINELLI_INFO']['TOTAL']

def remainingIndovinelloNumber(p):
    indovinello_info = p.tmp_variables['INDOVINELLI_INFO']
    return len(indovinello_info['TODO'])

def completedIndovinelloNumber(p):
    indovinello_info = p.tmp_variables['INDOVINELLI_INFO']
    return len(indovinello_info['COMPLETED'])

def setNextIndovinello(p):
    indovinello_info = p.tmp_variables['INDOVINELLI_INFO']
    todo_indovinelli = indovinello_info['TODO']
    current_indovinello = todo_indovinelli.pop(0)
    indovinello_info['CURRENT'] = current_indovinello
    return current_indovinello

def getCurrentIndovinello(p):
    indovinello_info = p.tmp_variables['INDOVINELLI_INFO']
    return indovinello_info['CURRENT']

def getCompletedIndovinello(p):
    game_info = p.tmp_variables['INDOVINELLI_INFO']
    return game_info['COMPLETED']

def setCurrentIndovinelloAsCompleted(p, photo_file_id):
    indovinello_info = p.tmp_variables['INDOVINELLI_INFO']
    current_indovinello = indovinello_info['CURRENT']
    current_indovinello['PHOTO_FILE_ID'] = photo_file_id
    indovinello_info['COMPLETED'].append(current_indovinello)
    indovinello_info['CURRENT'] = None

def getTotalGames(p):
    return p.tmp_variables['GIOCHI_INFO']['TOTAL']

def remainingGamesNumber(p):
    game_info = p.tmp_variables['GIOCHI_INFO']
    return len(game_info['TODO'])

def completedGamesNumber(p):
    game_info = p.tmp_variables['GIOCHI_INFO']
    return len(game_info['COMPLETED'])

def setNextGame(p):
    game_info = p.tmp_variables['GIOCHI_INFO']
    todo_game = game_info['TODO']
    current_game = todo_game.pop(0)
    game_info['CURRENT'] = current_game
    return current_game

def getCurrentGame(p):
    game_info = p.tmp_variables['GIOCHI_INFO']
    return game_info['CURRENT']

def getCompletedGames(p):
    game_info = p.tmp_variables['GIOCHI_INFO']
    return game_info['COMPLETED']

def setCurrentGameAsCompleted(p):
    game_info = p.tmp_variables['GIOCHI_INFO']
    game_info['COMPLETED'].append(game_info['CURRENT'])
    game_info['CURRENT'] = None

def increase_wrong_answers_current_indovinello(p, put=True):
    indovinello_info = p.tmp_variables['INDOVINELLI_INFO']
    current_indovinello = indovinello_info['CURRENT']
    current_indovinello['wrong_answers'] += 1
    p.tmp_variables['WRONG ANSWERS'] += 1
    if put:
        p.put()                

def increase_wrong_answers_current_game(p, put=True):
    game_info = p.tmp_variables['GIOCHI_INFO']
    current_game = game_info['CURRENT']
    current_game['wrong_answers'] += 1
    p.tmp_variables['WRONG ANSWERS'] += 1
    if put:
        p.put()                

def get_penalty_current_game(p):
    wrong_answers = 0
    current_game = getCurrentGame(p)
    if current_game:
        wrong_answers += current_game.get('wrong_answers',0)
    penalty_time_sec = wrong_answers * params.SEC_PENALITY_WRONG_ANSWER
    return wrong_answers, penalty_time_sec

def get_penalty_current_indovinello(p):
    wrong_answers = 0
    current_indovinello = getCurrentIndovinello(p)
    if current_indovinello:
        wrong_answers += current_indovinello.get('wrong_answers',0)
    penalty_time_sec = wrong_answers * params.SEC_PENALITY_WRONG_ANSWER
    return wrong_answers, penalty_time_sec

def get_total_penalty(p):    
    wrong_answers = p.tmp_variables['WRONG ANSWERS']
    # wrong_answers = 0
    # for var in (p.tmp_variables['INDOVINELLI_INFO'], p.tmp_variables['GIOCHI_INFO']):
    #     wrong_answers += sum(g.get('wrong_answers',0) for g in var['COMPLETED'])
    #     if var['CURRENT']:
    #         wrong_answers += var['CURRENT'].get('wrong_answers',0)
    penalty_time_sec = wrong_answers * params.SEC_PENALITY_WRONG_ANSWER
    return wrong_answers, penalty_time_sec

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
    #return json.dumps(p.tmp_variables['INDOVINELLI_INFO']['CURRENT'], indent=4)
    return json.dumps(p.tmp_variables, indent=4, ensure_ascii=False)