# -*- coding: utf-8 -*-

# Set up requests
# see https://cloud.google.com/appengine/docs/standard/python/issue-requests#issuing_an_http_request
import requests_toolbelt.adapters.appengine
requests_toolbelt.adapters.appengine.monkeypatch()
#disable warnings
import requests
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.contrib.appengine.AppEnginePlatformWarning
)

import webapp2

import logging
from time import sleep

import utility
import key
import person
from person import Person
import main_fb
import main_telegram
import date_time_util as dtu
from parameters import PARAMS
import geoUtils
import game
import ux
from ux import STRINGS, BOTTONE_LOCATION
import json
import re
import photos

########################
ACTIVE_HUNT = False
WORK_IN_PROGRESS = False
SEND_NOTIFICATIONS_TO_GROUP = True
MANUAL_VALIDATION_SELFIE_INDOVINELLLI = True
JUMP_TO_SURVEY = False
########################


# ================================
# TEMPLATE API CALLS
# ================================

def send_message(p, msg, kb=None, markdown=True, inline_keyboard=False, one_time_keyboard=False,
                 sleepDelay=False, hide_keyboard=False, force_reply=False, remove_keyboard=False,
                 disable_web_page_preview=True):
    if p.isTelegramUser():
        return main_telegram.send_message(p, msg, kb, markdown, inline_keyboard, one_time_keyboard,
                           sleepDelay, hide_keyboard, force_reply, remove_keyboard, disable_web_page_preview)
    else:
        if kb is None:
            kb = p.getLastKeyboard()
        if kb:
            kb_flat = utility.flatten(kb)[:11] # no more than 11
            return main_fb.sendMessageWithQuickReplies(p, msg, kb_flat)
        else:
            return main_fb.sendMessage(p, msg)
        #main_fb.sendMessageWithButtons(p, msg, kb_flat)

def send_photo_png_data(p, file_data, filename):
    if p.isTelegramUser():
        main_telegram.sendPhotoFromPngImage(p.chat_id, file_data, filename)
    else:
        main_fb.sendPhotoData(p, file_data, filename)
        # send message to show kb
        kb = p.getLastKeyboard()
        if kb:
            msg = 'Opzioni disponibili:'
            kb_flat = utility.flatten(kb)[:11] # no more than 11
            main_fb.sendMessageWithQuickReplies(p, msg, kb_flat)

def send_photo_url(p, url, kb=None, caption=None, inline_keyboard=False):
    if p.isTelegramUser():
        main_telegram.sendPhotoViaUrlOrId(p.chat_id, url, kb, caption, inline_keyboard)
    else:
        #main_fb.sendPhotoUrl(p.chat_id, url)
        import requests
        file_data = requests.get(url).content
        main_fb.sendPhotoData(p, file_data, 'file.png')
        # send message to show kb
        kb = p.getLastKeyboard()
        if kb:
            msg = 'Opzioni disponibili:'
            kb_flat = utility.flatten(kb)[:11]  # no more than 11
            main_fb.sendMessageWithQuickReplies(p, msg, kb_flat)

def sendDocument(p, file_id):
    if p.isTelegramUser():
        main_telegram.sendDocument(p.chat_id, file_id)
    else:
        pass

def send_location(p, lat, lon):
    if p.isTelegramUser():
        main_telegram.sendLocation(p.chat_id, lat, lon)
    else:
        pass

def sendExcelDocument(p, sheet_tables, filename='file'):
    if p.isTelegramUser():
        # sheet_table = {'anagrafica': table}
        # table = [[header1, header2, ...], [row1_header1, row1_header2, ...], ...]
        main_telegram.sendExcelDocument(p.chat_id, sheet_tables, filename)
    else:
        pass

def sendTextDocument(p, text, filename='file'):
    if p.isTelegramUser():
        main_telegram.sendTextDocument(p.chat_id, text, filename)
    else:
        pass


def sendWaitingAction(p, action_type='typing', sleep_time=None):
    if p.isTelegramUser():
        main_telegram.sendWaitingAction(p.chat_id, action_type, sleep_time)
    else:
        pass


# ================================
# GENERAL FUNCTIONS
# ================================

# ---------
# BROADCAST
# ---------

BROADCAST_COUNT_REPORT = utility.unindent(
    """
    Messaggio inviato a {} persone
    Ricevuto da: {}
    Non rivevuto da : {} (hanno disattivato il bot)
    """
)

def broadcast(sender, msg, qry = None, restart_user=False,
              blackList_sender=False, sendNotification=True):

    from google.appengine.ext.db import datastore_errors
    from google.appengine.api.urlfetch_errors import InternalTransientError

    if qry is None:
        qry = Person.query()
    qry = qry.order(Person._key) #_MultiQuery with cursors requires __key__ order

    more = True
    cursor = None
    total, enabledCount = 0, 0

    while more:
        users, cursor, more = qry.fetch_page(100, start_cursor=cursor)
        for p in users:
            try:
                if not p.enabled:
                    continue
                if blackList_sender and sender and p.getId() == sender.getId():
                    continue
                total += 1
                if send_message(p, msg, sleepDelay=True): #p.enabled
                    enabledCount += 1
                    if restart_user:
                        restart(p)
            except datastore_errors.Timeout:
                msg = '❗ datastore_errors. Timeout in broadcast :('
                tell_admin(msg)
                #deferredSafeHandleException(broadcast, sender, msg, qry, restart_user, curs, enabledCount, total, blackList_ids, sendNotification)
                return
            except InternalTransientError:
                msg = 'Internal Transient Error, waiting for 1 min.'
                tell_admin(msg)
                sleep(60)
                continue

    disabled = total - enabledCount
    msg_debug = BROADCAST_COUNT_REPORT.format(total, enabledCount, disabled)
    logging.debug(msg_debug)
    if sendNotification:
        send_message(sender, msg_debug)
    #return total, enabledCount, disabled

def broadcastUserIdList(sender, msg, userIdList, blackList_sender, markdown):
    for id in userIdList:
        p = person.getPersonById(id)
        if not p.enabled:
            continue
        if blackList_sender and sender and p.getId() == sender.getId():
            continue
        send_message(p, msg, markdown=markdown, sleepDelay=True)

# ---------
# Restart All
# ---------

def restartAll(qry = None):
    from google.appengine.ext.db import datastore_errors
    if qry is None:
        qry = Person.query()
    qry = qry.order(Person._key)  # _MultiQuery with cursors requires __key__ order

    more = True
    cursor = None
    total = 0

    while more:
        users, cursor, more = qry.fetch_page(100, start_cursor=cursor)
        try:
            for p in users:
                if p.enabled:
                    if p.state == START_STATE:
                        continue
                    #logging.debug('Restarting {}'.format(p.chat_id))
                    total += 1
                    restart(p)
                sleep(0.1)
        except datastore_errors.Timeout:
            msg = '❗ datastore_errors. Timeout in broadcast :('
            tell_admin(msg)

    logging.debug('Restarted {} users.'.format(total))

# ================================
# UTILIITY TELL FUNCTIONS
# ================================

def tellMaster(msg, markdown=False, one_time_keyboard=False):
    for id in key.ADMIN_IDS:
        p = person.getPersonById(id)
        main_telegram.send_message(
            p, msg, markdown=markdown,
            one_time_keyboard=one_time_keyboard,
            sleepDelay=True
        )

def tell_admin(msg):
    logging.debug(msg)
    for id in key.ADMIN_IDS:
        p = person.getPersonById(id)
        send_message(p, msg, markdown=False)

def send_message_to_person(id, msg, markdown=False):
    p = Person.get_by_id(id)
    send_message(p, msg, markdown=markdown)
    if p and p.enabled:
        return True
    return False

# ================================
# RESTART
# ================================
def restart(p):
    send_message(p, STRINGS['MSG_WELCOME'])
    redirectToState(p, START_STATE)


# ================================
# REDIRECT TO STATE
# ================================
def redirectToState(p, new_state, **kwargs):
    if p.state != new_state:
        logging.debug("In redirectToState. current_state:{0}, new_state: {1}".format(str(p.state), str(new_state)))
        # p.firstCallCategoryPath()
        p.setState(new_state)
    repeatState(p, **kwargs)


# ================================
# REPEAT STATE
# ================================
def repeatState(p, put=False, **kwargs):
    state = p.getState()
    methodName = "state_{}".format(state)
    method = possibles.get(methodName)
    if not method:
        msg = "State unknown: {}".format(state)
        send_message(p, msg, markdown=False)
    else:
        if put:
            p.put()
        method(p, **kwargs)

# ================================
# UNIVERSAL COMMANDS
# ================================

def dealWithUniversalCommands(p, input):
    from main_exception import deferredSafeHandleException
    if p.isAdmin():
        if input.startswith('/testText '):
            text = input.split(' ', 1)[1]
            if text:
                msg = '🔔 *Messaggio da hiSTORIC* 🔔\n\n' + text
                logging.debug("Test broadcast " + msg)
                send_message(p, msg)
                return True
        if input.startswith('/broadcast '):
            text = input.split(' ', 1)[1]
            if text:
                msg = '🔔 *Messaggio da hiSTORIC* 🔔\n\n' + text
                logging.debug("Starting to broadcast " + msg)
                deferredSafeHandleException(broadcast, p, msg)
                return True
        elif input.startswith('/restartBroadcast '):
            text = input.split(' ', 1)[1]
            if text:
                msg = '🔔 *Messaggio da hiSTORIC* 🔔\n\n' + text
                logging.debug("Starting to broadcast and restart" + msg)
                deferredSafeHandleException(broadcast, p, msg, restart_user=False)
                return True
        elif input.startswith('/textUser '):
            p_id, text = input.split(' ', 2)[1]
            if text:
                p = Person.get_by_id(p_id)
                if send_message(p, text, kb=p.getLastKeyboard()):
                    msg_admin = 'Message sent successfully to {}'.format(p.getFirstNameLastNameUserName())
                    tell_admin(msg_admin)
                else:
                    msg_admin = 'Problems sending message to {}'.format(p.getFirstNameLastNameUserName())
                    tell_admin(msg_admin)
                return True
        elif input.startswith('/restartUser '):
            p_id = input.split(' ')[1]
            p = Person.get_by_id(p_id)
            restart(p)
            msg_admin = 'User restarted: {}'.format(p.getFirstNameLastNameUserName())
            tell_admin(msg_admin)
            return True
        elif input == '/testlist':
            pass
            #p_id = key.FEDE_FB_ID
            #p = Person.get_by_id(p_id)
            #main_fb.sendMessageWithList(p, 'Prova lista template', ['one','twp','three','four'])
            #return True
        elif input == '/restartAll':
            deferredSafeHandleException(restartAll)
            return True
        elif input == '/restartAllNotInInitialState':
            deferredSafeHandleException(restartAll)
            return True
        elif input == '/testSpeech':
            redirectToState(p, 8)
            return True
    return False

## +++++ BEGIN OF STATES +++++ ###

START_STATE = 'START'
NOME_GRUPPO_STATE = 'NOME_GRUPPO'
SELFIE_INIZIALE_STATE = 'SELFIE_INIZIALE'
GPS_STATE = 'GPS'
INDOVINELLO_STATE = 'INDOVINELLO'
SELFIE_INDOVINELLO_STATE = 'SELFIE_INDOVINELLO'
GIOCO_STATE = 'GIOCO'
SURVEY_STATE = 'SURVEY'
EMAIL_STATE = 'EMAIL'
END_STATE = 'END'

STATES = {
    START_STATE: 'Initial state',
    NOME_GRUPPO_STATE: 'Richiesta nome gruppo',
    SELFIE_INIZIALE_STATE: 'Richiesta di invio selfie di gruppo',
    GPS_STATE: 'Invio GPS e conferma raggiungimento posto',
    SELFIE_INDOVINELLO_STATE: 'Selfie indovinello',
    INDOVINELLO_STATE: 'In a mission',
    GIOCO_STATE: 'In a game',
    SURVEY_STATE: 'In survey',
    EMAIL_STATE: 'Asking email',
    END_STATE: 'Final state'
}


# ================================
# Initial State
# ================================

def state_START(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    if giveInstruction:
        kb = [[STRINGS['BUTTON_START_GAME']]]
        p.setLastKeyboard(kb)
        send_message(p, STRINGS['MSG_PRESS_TO_START'], kb)
    else:
        kb = p.getLastKeyboard()
        if input in utility.flatten(kb):
            if input == STRINGS['BUTTON_START_GAME']:
                send_message(p, STRINGS['MSG_GO'], hide_keyboard=True)
                sendWaitingAction(p, sleep_time=1)
                game.resetGame(p)
                redirectToState(p, NOME_GRUPPO_STATE)
        else:
            send_message(p, STRINGS['MSG_WRONG_INPUT_USE_BUTTONS'], kb)

# ================================
# Nome Gruppo State
# ================================

def state_NOME_GRUPPO(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    if giveInstruction:
        send_message(p, STRINGS['MSG_GROUP_NAME'])
    else:
        if input != '':
            if len(input) > 15:
                send_message(p, STRINGS['MSG_GROUP_NAME_TOO_LONG'])
                return
            if not utility.hasOnlyLettersAndSpaces(input):
                send_message(p, STRINGS['MSG_GROUP_NAME_INVALID'])
                return
            game.setGroupName(p, input)
            send_message(p, STRINGS['MSG_GROUP_NAME_OK'].format(input))
            if SEND_NOTIFICATIONS_TO_GROUP:
                send_message(game.HISTORIC_GROUP, "Nuova squadra registrata: {}".format(input))
            redirectToState(p, SELFIE_INIZIALE_STATE)
        else:
            send_message(p, STRINGS['MSG_WRONG_INPUT_USE_TEXT'])

# ================================
# Selfie Iniziale State
# ================================

def state_SELFIE_INIZIALE(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    photo = kwargs['photo'] if 'photo' in kwargs.keys() else None
    giveInstruction = input is None
    if giveInstruction:
        send_message(p, STRINGS['MSG_SELFIE_INIZIALE'])
    else:
        if photo:
            photo_file_id = photo[-1]['file_id']
            game.appendGroupSelfieFileId(p, photo_file_id)
            sendWaitingAction(p, sleep_time=1)
            send_message(p, STRINGS['MSG_SELFIE_INIZIALE_OK'].format(input))
            game.setStartTime(p, dtu.nowUtcIsoFormat())
            if SEND_NOTIFICATIONS_TO_GROUP:
                send_photo_url(game.HISTORIC_GROUP, photo_file_id, caption='Selfie iniziale {}'.format(game.getGroupName(p)))
            redirectToState(p, GPS_STATE)
        else:
            send_message(p, STRINGS['MSG_WRONG_INPUT_SEND_PHOTO'])

# ================================
# GPS state
# ================================

def state_GPS(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    location = kwargs['location'] if 'location' in kwargs.keys() else None
    giveInstruction = input is None
    if giveInstruction:
        current_riddle = game.setNextRiddle(p)
        goal_position = [float(x) for x in current_riddle['GPS'].split(',')]
        msg = '*Introduzione al luogo*: ' + current_riddle['INTRODUZIONE_LOCATION'] + '\n\n' + STRINGS['MSG_GO_TO_PLACE']
        kb = [[BOTTONE_LOCATION]]
        send_message(p, msg, kb)
        send_location(p, goal_position[0], goal_position[1])
        p.put()
    else:
        if location:
            current_riddle = game.getCurrentRiddle(p)
            goal_position = [float(x) for x in current_riddle['GPS'].split(',')]
            given_position = [location['latitude'], location['longitude']]
            distance = geoUtils.distance_meters(goal_position, given_position)
            if distance <= PARAMS['GPS_TOLERANCE_METERS']:
                send_message(p, STRINGS['MSG_GPS_OK'], remove_keyboard=True)
                sendWaitingAction(p, sleep_time=1)
                redirectToState(p, INDOVINELLO_STATE)
            else:
                msg = STRINGS['MSG_TOO_FAR'].format(distance)
                send_message(p, msg)
        else:
            send_message(p, STRINGS['MSG_WRONG_INPUT_SEND_LOCATION'])

# ================================
# INDOVINELLO state
# ================================

def state_INDOVINELLO(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    current_riddle = game.getCurrentRiddle(p)
    if giveInstruction:
        current_riddle['start_time'] = dtu.nowUtcIsoFormat()
        riddle_number = game.completedRiddlesNumber(p) + 1
        total_riddles = game.getTotalRiddles(p)
        msg = '*Indovinello {}/{}*: {}'.format(riddle_number, total_riddles, current_riddle['INDOVINELLO'])
        kb = [['💡 PRIMO INDIZIO']]
        send_message(p, msg, kb)
        p.put()
    else:
        if input != '':
            correct_answers_upper = [x.strip() for x in current_riddle['SOLUZIONI'].upper().split(',')]
            correct_answers_upper_word_set = set(utility.flatten([x.split() for x in correct_answers_upper]))
            #if input in utility.flatten(kb):
            now_string = dtu.nowUtcIsoFormat()
            if input == '💡 PRIMO INDIZIO':
                before_string = current_riddle['start_time']
                ellapsed = dtu.delta_seconds_iso(before_string, now_string)
                if ellapsed > PARAMS['MIN_SEC_INDIZIO_1']:
                    msg = '💡 *Indizio 1*: {}'.format(current_riddle['INDIZIO_1'])
                    kb = [['💡 SECONDO INDIZIO']]
                    current_riddle['indizio1_time'] = now_string
                    p.setLastKeyboard(kb, put=True)
                    send_message(p, msg, kb)
                else:
                    send_message(p, STRINGS['MSG_TOO_EARLY'])
            elif input == '💡 SECONDO INDIZIO':
                before_string = current_riddle['indizio1_time']
                ellapsed = dtu.delta_seconds_iso(before_string, now_string)
                if ellapsed > PARAMS['MIN_SEC_INDIZIO_2']:
                    msg = '💡 *Indizio 2*: {}'.format(current_riddle['INDIZIO_2'])
                    kb = []
                    current_riddle['indizio2_time'] = now_string
                    p.setLastKeyboard(kb, put=True)
                    send_message(p, msg, remove_keyboard=True)
                else:
                    send_message(p, STRINGS['MSG_TOO_EARLY'])
            elif input.upper() in correct_answers_upper:
                send_message(p, STRINGS['MSG_ANSWER_OK'])
                redirectToState(p, SELFIE_INDOVINELLO_STATE)
            elif any(x in correct_answers_upper_word_set for x in input.upper().split()):
                send_message(p, STRINGS['MSG_ANSWER_ALMOST'])
            else:
                send_message(p, STRINGS['MSG_ANSWER_WRONG'])
        else:
            send_message(p, STRINGS['MSG_WRONG_INPUT_USE_TEXT'])

# ================================
# Selfie Iniziale State
# ================================

def state_SELFIE_INDOVINELLO(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    photo = kwargs['photo'] if 'photo' in kwargs.keys() else None
    giveInstruction = input is None
    if giveInstruction:
        send_message(p, STRINGS['MSG_SELFIE_INDOVINELLO'], remove_keyboard=True)
    else:
        if photo:
            photo_file_id = photo[-1]['file_id']
            current_riddle = game.getCurrentRiddle(p)
            current_riddle['SELFIE'] = photo_file_id
            if MANUAL_VALIDATION_SELFIE_INDOVINELLLI:
                squadra_name = game.getGroupName(p)
                riddle_number = game.completedRiddlesNumber(p) + 1
                indovinello_name = current_riddle['NOME']
                # store a random password to make sure the approval is correct
                # (the team may have restarted the game in the meanwhile):
                approval_signature = utility.randomAlphaNumericString(5)
                current_riddle['sign'] = approval_signature
                send_message(p, STRINGS['MSG_WAIT_SELFIE_APPROVAL'])
                inline_kb_validation = [
                    [
                        ux.SI_BUTTON(json.dumps({'ok': True, 'uid':p.getId(), 'sign': approval_signature})),
                        ux.NO_BUTTON(json.dumps({'ok': False, 'uid': p.getId(), 'sign': approval_signature})),
                    ]
                ]
                caption = 'Selfie indovinello {} squadra {} per indovinello {}'.format(riddle_number, squadra_name, indovinello_name)
                logging.debug('Sending photo to validator')
                send_photo_url(game.VALIDATOR, photo_file_id, inline_kb_validation, caption=caption, inline_keyboard=True)
            else:
                approve_selfie_indovinello(p, approved=True, signature=None)
            p.put()
        else:
            send_message(p, STRINGS['MSG_WRONG_INPUT_SEND_PHOTO'])

def approve_selfie_indovinello(p, approved, signature):
    # need to double check if team is still waiting for approval
    # (e.g., could have restarted the game, or validator pressed approve twice in a row)
    current_riddle = game.getCurrentRiddle(p)
    if current_riddle is None or (MANUAL_VALIDATION_SELFIE_INDOVINELLLI and signature != current_riddle['sign']):
        return False
    if approved:
        send_message(p, STRINGS['MSG_SELFIE_INDOVINELLO_OK'])
        photo_file_id = current_riddle['SELFIE']
        if SEND_NOTIFICATIONS_TO_GROUP:
            squadra_name = game.getGroupName(p)
            riddle_number = game.completedRiddlesNumber(p) + 1
            indovinello_name = current_riddle['NOME']
            caption = 'Selfie indovinello {} squadra {} per indovinello {}'.format(riddle_number, squadra_name, indovinello_name)
            send_photo_url(game.HISTORIC_GROUP, photo_file_id, caption=caption)
        game.appendGroupSelfieFileId(p, photo_file_id)
        game.setCurrentRiddleAsCompleted(p, photo_file_id)
        sendWaitingAction(p, sleep_time=1)
        if JUMP_TO_SURVEY or game.remainingRiddlesNumber(p) == 0:
            end_time = dtu.nowUtcIsoFormat()
            game.setEndTime(p, end_time)
            send_message(p, STRINGS['MSG_SURVEY_INTRO'])
            redirectToState(p, SURVEY_STATE)
        else:
            send_message(p, STRINGS['MSG_NEXT_GIOCO'])
            redirectToState(p, GIOCO_STATE)
    else:
        send_message(p, STRINGS['MSG_SELFIE_INDOVINELLO_WRONG'])
    return True

# ================================
# GIOCHI state
# ================================

def state_GIOCO(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    if giveInstruction:
        current_game = game.setNextGame(p)
        game_number = game.completedGamesNumber(p) + 1
        total_games = game.getTotalGames(p)
        msg = '*Gioco {}/{}*: {}'.format(game_number, total_games, current_game['ISTRUZIONI'])
        send_photo_url(p, url=current_game['IMG_URL'])
        send_message(p, msg)
        p.put()
    else:
        current_game = game.getCurrentGame(p)
        if input != '':
            correct_answers_upper = [x.strip() for x in current_game['SOLUZIONI'].upper().split(',')]
            if input.upper() in correct_answers_upper:
                send_message(p, STRINGS['MSG_ANSWER_OK'])
                game.setCurrentGameAsCompleted(p)
                send_message(p, STRINGS['MSG_NEXT_MISSION'])
                sendWaitingAction(p, sleep_time=1)
                redirectToState(p, GPS_STATE)
            else:
                send_message(p, STRINGS['MSG_ANSWER_WRONG'])
        else:
            send_message(p, STRINGS['MSG_WRONG_INPUT_USE_TEXT'])

# ================================
# Survey State
# ================================

def state_SURVEY(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    if giveInstruction:
        current_question = game.setNextQuestion(p)
        questions_number = game.completedQuestionsNumber(p) + 1
        total_questions = game.getTotalQuestions(p)
        msg = '*Domanda {}/{}*: {}'.format(questions_number, total_questions, current_question['DOMANDA'])
        risposte = [x.strip() for x in current_question['RISPOSTE'].split(',')]
        kb = [risposte]
        p.setLastKeyboard(kb, put=True)
        send_message(p, msg, kb)
    else:
        kb = p.getLastKeyboard()
        current_question = game.getCurrentQuestion(p)
        question_type_open =  current_question['TYPE']=='Open'
        if input:
            if input in utility.flatten(kb):
                answer = '' if question_type_open else input
                game.setCurrentQuestionAsCompleted(p, answer)
            elif question_type_open:
                game.setCurrentQuestionAsCompleted(p, input)
            else:
                send_message(p, STRINGS['MSG_WRONG_INPUT_USE_BUTTONS'])
                return
            if game.remainingQuestionsNumber(p) == 0:
                redirectToState(p, EMAIL_STATE)
            else:
                repeatState(p, put=True)
        else:
            if question_type_open:
                send_message(p, STRINGS['MSG_WRONG_INPUT_USE_TEXT_OR_BUTTONS'])
            else:
                send_message(p, STRINGS['MSG_WRONG_INPUT_USE_BUTTONS'])

# ================================
# Survey State
# ================================

def state_EMAIL(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    if giveInstruction:
        kb = [[STRINGS['BUTTON_SKIP_EMAIL']]]
        send_message(p, STRINGS['MSG_EMAIL'], kb)
    else:
        if input != '':
            if input == STRINGS['BUTTON_SKIP_EMAIL']:
                redirectToState(p, END_STATE)
            elif re.match(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]+$", input):
                game.setEmail(p, input)
                redirectToState(p, END_STATE)
            else:
                send_message(p, STRINGS['MSG_EMAIL_WRONG'])
        else:
            send_message(p, STRINGS['MSG_WRONG_INPUT_USE_BUTTONS'])

# ================================
# Final State
# ================================

def state_END(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    if giveInstruction:
        end_time = game.getEndTime(p)
        start_time = game.getStartTime(p)
        ellapsed_sec = dtu.delta_seconds_iso(start_time, end_time)
        min, sec = divmod(ellapsed_sec, 60)
        hour, min = divmod(min, 60)
        time_str = "%d:%02d:%02d" % (hour, min, sec)
        msg = STRINGS['MSG_END'].format(time_str)
        send_message(p, msg, hide_keyboard=True)
        msg_group = "La squadra *{}* ha completato la caccia al tesoro in *{}*".format(game.getGroupName(p), time_str)
        if SEND_NOTIFICATIONS_TO_GROUP:
            send_message(game.HISTORIC_GROUP, msg_group)
        game.setDuration(p, ellapsed_sec)
        game.saveGameData(p)
    else:
        pass


## +++++ END OF STATES +++++ ###

def dealWithCallbackQuery(callback_query_dict):
    callback_query_data = json.loads(callback_query_dict['data'])
    approved = callback_query_data['ok']
    user_id = callback_query_data['uid']
    approval_signature = callback_query_data['sign']
    p = person.getPersonById(user_id)
    squadra_name = game.getGroupName(p)
    callback_query_id = callback_query_dict['id']
    chat_id = callback_query_dict['from']['id']
    message_id = callback_query_dict['message']['message_id']
    main_telegram.deleteMessage(chat_id, message_id)
    validation_success = approve_selfie_indovinello(p, approved, signature=approval_signature)
    if validation_success:
        if approved:
            answer = "Messaggio di conferma inviato alla squadra {}!".format(squadra_name)
        else:
            answer = "Inviato messsaggio di rifare il selfie alla squadra {}!".format(squadra_name)
    else:
        answer = "Problema di validazione. La squadra {} ha ricomnciato il gioco " \
                 "o l'approvazione è stata mandata più volte".format(squadra_name)
    main_telegram.answerCallbackQuery(callback_query_id, answer)


def dealWithUserInteraction(chat_id, name, last_name, username, application, text,
                            location, contact, photo, document, voice):

    p = person.getPersonByChatIdAndApplication(chat_id, application)

    if p is None:
        p = person.addPerson(chat_id, name, last_name, username, application)
        tellMaster("New {} user: {}".format(application, p.getFirstNameLastNameUserName()))
    else:
        modified, was_disabled = p.updateUserInfo(name, last_name, username)
        if was_disabled:
            msg = "Bot riattivato!"
            send_message(p, msg)
    if p.isAdmin():
        if text == '/debug':
            #send_message(p, game.debugTmpVariables(p), markdown=False)
            sendTextDocument(p, game.debugTmpVariables(p))
        elif text == '/testInlineKb':
            send_message(p, "Test inline keypboard", kb=[[ux.SI_BUTTON('test'), ux.NO_BUTTON('test')]], inline_keyboard=True)
    if WORK_IN_PROGRESS and p.getId() not in key.ADMIN_IDS:
        send_message(p, "🏗 Il sistema è in aggiornamento, ti preghiamo di riprovare più tardi.")
    elif text.lower().startswith('/start'):
        if not ACTIVE_HUNT:
            msg = "Ciao 😀\n" \
                  "In questo momento la caccia al tesoro non è attiva.\n" \
                  "Vieni a trovarci su [historic](https://www.historictrento.it) " \
                  "o contattaci via email a historic.trento@gmail.com."
            send_message(p, msg)
        elif text.lower() == '/start {}'.format(key.CURRENT_GAME_SECRET_START_MSG.lower()):
            restart(p)
        else:
            msg = "Ciao 😀\n" \
                  "C'è una caccia al tesoro in corso ma devi utilizzare il QR code per accedere.\n" \
                  "In alternativa digita /start seguito dalla *password* fornita dagli organizzatori."
            send_message(p, msg)
    elif text == '/state':
        state = p.getState()
        msg = "You are in state {}: {}".format(state, STATES.get(state, '(unknown)'))
        send_message(p, msg)
    elif text == '/refresh':
        repeatState(p)
    elif text in ['/help', 'HELP', 'AIUTO']:
        pass
        #redirectToState(p, HELP_STATE)
    elif text in ['/stop', 'STOP']:
        p.setEnabled(False, put=True)
        msg = "🚫 Hai *disabilitato* il bot.\n" \
              "In qualsiasi momento puoi riattivarmi scrivendomi qualcosa."
        send_message(p, msg)
    else:
        if not dealWithUniversalCommands(p, input=text):
            state = p.getState()
            logging.debug("Sending {} to state {} with input {}".format(p.getFirstName(), state, text))
            repeatState(p, input=text, location=location, contact=contact, photo=photo, document=document,
                        voice=voice)


app = webapp2.WSGIApplication([
    ('/telegram_me', main_telegram.MeHandler),
    ('/telegram_set_webhook', main_telegram.SetWebhookHandler),
    ('/telegram_get_webhook_info', main_telegram.GetWebhookInfo),
    ('/telegram_delete_webhook', main_telegram.DeleteWebhook),
    ('/photos/([^/]+)?', photos.DownloadPhotoHandler),
    (key.FACEBOOK_WEBHOOK_PATH, main_fb.WebhookHandler),
    (key.TELEGRAM_WEBHOOK_PATH, main_telegram.WebhookHandler)
], debug=False)

possibles = globals().copy()
possibles.update(locals())
