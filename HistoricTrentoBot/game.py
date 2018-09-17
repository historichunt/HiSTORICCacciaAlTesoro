# -*- coding: utf-8 -*-

import utility
import key
from random import shuffle
import person
from airtable import Airtable

#################
# INDOVINELLI
#################

INDOVINELLI = utility.import_url_csv_to_dict_list(key.INDOVINELLI_URL)
# NOME, FINALE, INDOVINELLO, INDIZIO_1, INDIZIO_2, SOLUZIONI, INDIRIZZO, GPS

INDOVINELLI_NON_FINAL = [row for row in INDOVINELLI if row['FINALE'] != 'TRUE']
INDOVINELLI_FINALI = [row for row in INDOVINELLI if row['FINALE'] == 'TRUE']

def getRandomRiddles():
    riddle_random = list(INDOVINELLI_NON_FINAL)
    shuffle(riddle_random)
    riddle_random.extend(INDOVINELLI_FINALI)
    return riddle_random

#################
# GIOCHI
#################

GIOCHI = utility.import_url_csv_to_dict_list(key.GIOCHI_URL)
# NOME, ISTRUZIONI, IMG_URL, SOLUZIONI

def getRandomGiochi():
    giochi_random = list(GIOCHI)
    shuffle(giochi_random)
    return giochi_random

#################
# SURVEY
#################

SURVEY = [row for row in utility.import_url_csv_to_dict_list(key.SURVEY_URL) if not row['DOMANDA'].startswith('#')]
# DOMANDA, RISPOSTE
SURVEY_QUESTIONS = [s['DOMANDA'] for s in SURVEY]

def getSurveyData():
    return list(SURVEY)

#################
# GAME TABLE
#################

GAMES_TABLE = Airtable(key.AIRTABLE_TABLE_ID, 'Games', api_key=key.AIRTABLE_API_KEY)
SURVEY_TABLE = Airtable(key.AIRTABLE_TABLE_ID, 'Survey', api_key=key.AIRTABLE_API_KEY)

GENERAL_HEADERS = ['ID', 'GROUP_NAME', 'NOME', 'COGNOME', 'USERNAME', 'EMAIL', 'START_TIME', 'END_TIME', 'DURATION']

def saveGameData(p):
    import photos
    game_data = p.tmp_variables
    games_row = {}
    for h in GENERAL_HEADERS:
        games_row[h] = game_data[h]
    games_row['GROUP_SELFIES'] = [{'url': photos.prepareAndGetPhotoTelegramUrl(file_id)} for file_id in game_data['GROUP_SELFIES']]
    GAMES_TABLE.insert(games_row)
    survey_row = {'ID': game_data['ID']}
    for question in SURVEY_QUESTIONS:
        questions_data = game_data['SURVEY_INFO']['COMPLETED']
        answer = next(row['ANSWER'] for row in questions_data if row['DOMANDA'] == question)
        survey_row[question] = answer
    SURVEY_TABLE.insert(survey_row)


################################
# PEOPLE FOR GAME
################################

HISTORIC_GROUP = person.getPersonById(key.HISTORIC_GROUP_ID) #key.FEDE_T_ID
VALIDATOR = person.getPersonById(key.VALIDATOR_ID)

################################
# GAME MANAGEMENT FUNCTIONS
################################

def resetGame(p):
    riddles = getRandomRiddles()
    games = getRandomGiochi()
    survey = getSurveyData()
    p.tmp_variables = {}
    p.tmp_variables['ID'] = p.getId()
    p.tmp_variables['NOME'] = p.getFirstName(escapeMarkdown=False)
    p.tmp_variables['COGNOME'] = p.getLastName(escapeMarkdown=False)
    p.tmp_variables['USERNAME'] = p.getUsername(escapeMarkdown=False)
    p.tmp_variables['EMAIL'] = ''
    p.tmp_variables['INDOVINELLI_INFO'] = {'TODO': riddles, 'CURRENT': None, 'COMPLETED': [], 'TOTAL': len(riddles)}
    # riddle -> 'PHOTO_FILE_ID'
    p.tmp_variables['GIOCHI_INFO'] = {'TODO': games, 'CURRENT': None, 'COMPLETED': [], 'TOTAL': len(games)}
    p.tmp_variables['SURVEY_INFO'] = {'TODO': survey, 'CURRENT': None, 'COMPLETED': [], 'TOTAL': len(survey)}
    # question -> 'ANSWER'
    p.tmp_variables['GROUP_NAME'] = ''
    p.tmp_variables['GROUP_SELFIES'] = []
    p.tmp_variables['START_TIME'] = ''
    p.tmp_variables['END_TIME'] = ''
    p.tmp_variables['DURATION'] = 0 # seconda

def setGroupName(p, name):
    p.tmp_variables['GROUP_NAME'] = name

def getGroupName(p, escapeMarkdown=True):
    name = p.tmp_variables['GROUP_NAME']
    if escapeMarkdown:
        name = utility.escapeMarkdown(name)
    return name

def appendGroupSelfieFileId(p, file_id):
    p.tmp_variables['GROUP_SELFIES'].append(file_id)

def setStartTime(p, time):
    p.tmp_variables['START_TIME'] = time

def getStartTime(p):
    return p.tmp_variables['START_TIME']

def setEndTime(p, time):
    p.tmp_variables['END_TIME'] = time

def setDuration(p, ellapsed_sec):
    p.tmp_variables['DURATION'] = ellapsed_sec

def getEndTime(p):
    return p.tmp_variables['END_TIME']

def getTotalRiddles(p):
    return p.tmp_variables['INDOVINELLI_INFO']['TOTAL']

def remainingRiddlesNumber(p):
    riddle_info = p.tmp_variables['INDOVINELLI_INFO']
    return len(riddle_info['TODO'])

def completedRiddlesNumber(p):
    riddle_info = p.tmp_variables['INDOVINELLI_INFO']
    return len(riddle_info['COMPLETED'])

def setNextRiddle(p):
    riddle_info = p.tmp_variables['INDOVINELLI_INFO']
    todo_riddles = riddle_info['TODO']
    current_riddle = todo_riddles.pop(0)
    riddle_info['CURRENT'] = current_riddle
    return current_riddle

def getCurrentRiddle(p):
    riddle_info = p.tmp_variables['INDOVINELLI_INFO']
    return riddle_info['CURRENT']

def setCurrentRiddleAsCompleted(p, photo_file_id):
    riddle_info = p.tmp_variables['INDOVINELLI_INFO']
    current_riddle = riddle_info['CURRENT']
    current_riddle['PHOTO_FILE_ID'] = photo_file_id
    riddle_info['COMPLETED'].append(current_riddle)
    riddle_info['CURRENT'] = None

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

def setCurrentGameAsCompleted(p):
    game_info = p.tmp_variables['GIOCHI_INFO']
    game_info['COMPLETED'].append(game_info['CURRENT'])
    game_info['CURRENT'] = None

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
    return json.dumps(p.tmp_variables, indent=4)
