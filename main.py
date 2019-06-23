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
import params
import geoUtils
import game
import ux
from ux import BUTTON_LOCATION
import json
import re
import photos

########################
WORK_IN_PROGRESS = False
JUMP_TO_SURVEY_AFTER = False  # 2
########################

# ================================
# TEMPLATE API CALLS
# ================================

def send_message(p, msg, kb=None, markdown=True, inline_keyboard=False, one_time_keyboard=False,
                 sleepDelay=False, force_reply=False, remove_keyboard=False,
                 disable_web_page_preview=True):
    if p.isTelegramUser():
        return main_telegram.send_message(p, msg, kb, markdown, inline_keyboard, one_time_keyboard,
                           sleepDelay, force_reply, remove_keyboard, disable_web_page_preview)
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

def send_media_url(p, url_attachment, kb=None, caption=None):
    attach_type = url_attachment.split('.')[-1].lower()            
    if attach_type in ['jpg','png','jpeg']:
        send_photo_url(p, url=url_attachment, caption=caption)
    elif attach_type in ['mp3']:
        send_audio_mp3_url(p, url=url_attachment, caption=caption)        
    elif attach_type in ['gif']:
        send_animation_url(p, url=url_attachment, caption=caption)        
    elif attach_type in ['mp4']:
        send_video_url(p, url=url_attachment, caption=caption)        
    else:            
        error_msg = "Found attach_type: {}".format(attach_type)
        logging.error(error_msg)
        raise ValueError('Wrong attach type: {}'.format(error_msg))

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

def send_animation_url(p, url, kb=None, caption=None, inline_keyboard=False):
    if p.isTelegramUser():
        main_telegram.sendAnimationViaUrlOrId(p.chat_id, url, kb, caption, inline_keyboard)
    else:
        pass

def send_video_url(p, url, kb=None, caption=None, inline_keyboard=False):
    if p.isTelegramUser():
        main_telegram.sendVideoViaUrlOrId(p.chat_id, url, kb, caption, inline_keyboard)
    else:
        pass

def send_audio_mp3_url(p, url, kb=None, caption=None, inline_keyboard=False):
    if p.isTelegramUser():
        main_telegram.sendAudioViaUrlOrId(p.chat_id, url, kb, caption, inline_keyboard)
    else:
        pass


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

def broadcast(sender, msg, qry = None, exit_game=False,
              blackList_sender=False, sendNotification=True, test=False):

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
                if test and not p.isTester():
                    continue
                if blackList_sender and sender and p.getId() == sender.getId():
                    continue
                total += 1
                if send_message(p, msg, sleepDelay=True): #p.enabled
                    enabledCount += 1
                    if exit_game:
                        make_payer_exit_game(p)
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

# ---------
# Restart All
# ---------

def resetAll(qry = None, message=None):
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
                    #if p.state == INITIAL_STATE:
                    #    continue
                    #logging.debug('Restarting {}'.format(p.chat_id))
                    total += 1
                    make_payer_exit_game(p, message)
                sleep(0.1)
        except datastore_errors.Timeout:
            msg = '❗ datastore_errors. Timeout in broadcast :('
            tell_admin(msg)

    msg_admin = 'Resetted {} users.'.format(total)
    tell_admin(msg_admin)

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
    logging.debug("Tellling admin: " + msg)
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
# RESET PLAYER
# ================================
def make_payer_exit_game(p, message=None):
    game.exitGame(p)
    if message:
        send_message(p, message, remove_keyboard=True)
    redirectToState(p, INITIAL_STATE)


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


## +++++ BEGIN OF STATES +++++ ###

INITIAL_STATE = 'INITIAL'
START_STATE = 'START'
NOME_GRUPPO_STATE = 'NOME_GRUPPO'
SELFIE_INIZIALE_STATE = 'SELFIE_INIZIALE'
MISSION_INTRO_STATE = 'MISSION_INTRO'
GPS_STATE = 'GPS'
INDOVINELLO_STATE = 'INDOVINELLO'
POST_INDOVINELLO_STATE = 'POST_INDOVINELLO'
SELFIE_INDOVINELLO_STATE = 'SELFIE_INDOVINELLO'
SURVEY_STATE = 'SURVEY'
EMAIL_STATE = 'EMAIL'
END_STATE = 'END'


# ================================
# Initial State
# ================================

def state_INITIAL(p, **kwargs):
    text_input = kwargs['text_input'] if 'text_input' in kwargs.keys() else None
    if text_input is None:
        pass #don't reply anything
    else: #text_input.lower().startswith('/start'):
        if not key.ACTIVE_HUNT:
            msg = "Ciao 😀\n" \
                  "In questo momento non c'è nessuna caccia al tesoro attiva.\n" \
                  "Vieni a trovarci su [historic](https://www.historictrento.it) " \
                  "o mandaci una email a historic.trento@gmail.com."
            send_message(p, msg)
        elif text_input.lower().startswith('/start '):
            hunt_password = text_input.lower().split()[1]
            if hunt_password in key.HUNTS:
                game.resetGame(p, hunt_password)
                game_name = key.HUNTS[hunt_password]['Name']
                send_message(p, ux.MSG_WELCOME.format(game_name))
                redirectToState(p, START_STATE)
            else:
                msg = '🙈 Non hai inserito la parola magica giusta per iniziare la caccia al tesoro.'
                send_message(p, msg)
        else:
            msg = "Ciao 😀\n" \
                  "C'è una caccia al tesoro in corso ma devi utilizzare il QR code per accedere.\n" \
                  "In alternativa digita /start seguito dalla *password* fornita dagli organizzatori."
            send_message(p, msg)

def state_START(p, **kwargs):
    text_input = kwargs['text_input'] if 'text_input' in kwargs.keys() else None
    giveInstruction = text_input is None
    if giveInstruction:
        kb = [[ux.BUTTON_START_GAME]]
        send_message(p, ux.MSG_PRESS_TO_START, kb)
    else:
        kb = p.getLastKeyboard()
        if text_input in utility.flatten(kb):
            if text_input == ux.BUTTON_START_GAME:
                send_message(p, ux.MSG_GO, remove_keyboard=True)
                sendWaitingAction(p, sleep_time=1)                
                redirectToState(p, NOME_GRUPPO_STATE)
        else:
            send_message(p, ux.MSG_WRONG_INPUT_USE_BUTTONS, kb)
            sendWaitingAction(p, sleep_time=1)
            repeatState(p)

# ================================
# Nome Gruppo State
# ================================

def state_NOME_GRUPPO(p, **kwargs):
    text_input = kwargs['text_input'] if 'text_input' in kwargs.keys() else None
    giveInstruction = text_input is None
    if giveInstruction:
        send_message(p, ux.MSG_GROUP_NAME)
    else:
        if text_input:
            if len(text_input) > params.MAX_TEAM_NAME_LENGTH:
                send_message(p, ux.MSG_GROUP_NAME_TOO_LONG.format(params.MAX_TEAM_NAME_LENGTH))
                return
            if not utility.hasOnlyLettersAndSpaces(text_input):
                send_message(p, ux.MSG_GROUP_NAME_INVALID)
                return
            game.setGroupName(p, text_input)
            send_message(p, ux.MSG_GROUP_NAME_OK.format(text_input))
            if game.send_notification_to_group(p):
                send_message(game.HISTORIC_GROUP, "Nuova squadra registrata: {}".format(text_input))
            redirectToState(p, SELFIE_INIZIALE_STATE)
        else:
            send_message(p, ux.MSG_WRONG_INPUT_INSERT_TEXT)
            sendWaitingAction(p, sleep_time=1)
            repeatState(p)

# ================================
# Selfie Iniziale State
# ================================

def state_SELFIE_INIZIALE(p, **kwargs):
    photo = kwargs['photo'] if 'photo' in kwargs.keys() else None
    giveInstruction = photo is None
    if giveInstruction:
        send_message(p, ux.MSG_SELFIE_INIZIALE)
    else:
        if photo:
            photo_file_id = photo[-1]['file_id']
            game.appendGroupSelfieFileId(p, photo_file_id)
            sendWaitingAction(p, sleep_time=1)
            send_message(p, ux.MSG_SELFIE_INIZIALE_OK)            
            if game.send_notification_to_group(p):
                send_photo_url(game.HISTORIC_GROUP, photo_file_id, caption='Selfie iniziale {}'.format(game.getGroupName(p)))
            send_message(p, ux.MSG_START_TIME, sleepDelay=True, remove_keyboard=True)
            game.setStartTime(p)
            redirectToState(p, MISSION_INTRO_STATE)
        else:
            send_message(p, ux.MSG_WRONG_INPUT_SEND_PHOTO)
            sendWaitingAction(p, sleep_time=1)
            repeatState(p)

# ================================
# INTRO
# ================================

def state_MISSION_INTRO(p, **kwargs):
    text_input = kwargs['text_input'] if 'text_input' in kwargs.keys() else None
    giveInstruction = text_input is None
    if giveInstruction:
        current_indovinello = game.setNextIndovinello(p)
        indovinello_number = game.completedIndovinelloNumber(p) + 1
        total_indovinelli = game.getTotalIndovinelli(p)
        msg = '*🎳 Missione {}/{}*'.format(indovinello_number, total_indovinelli)
        send_message(p, msg)
        sendWaitingAction(p, sleep_time=1)
        if 'INTRO_MEDIA' in current_indovinello:
            caption = current_indovinello.get('INTRO_MEDIA_CAPTION',None)
            url_attachment = current_indovinello['INTRO_MEDIA'][0]['url']
            send_media_url(p, url_attachment, caption=caption)
            sendWaitingAction(p, sleep_time=3)
        msg = current_indovinello['INTRODUZIONE_LOCATION'] # '*Introduzione*: ' + 
        kb = [[ux.BUTTON_CONTINUE]]
        send_message(p, msg, kb)
        p.put()
    else:
        kb = p.getLastKeyboard()
        if text_input in utility.flatten(kb):
            if text_input == ux.BUTTON_CONTINUE:
                current_indovinello = game.getCurrentIndovinello(p)
                if 'GPS' in current_indovinello:
                    redirectToState(p, GPS_STATE)
                else:
                    redirectToState(p, INDOVINELLO_STATE)
            else:
                assert False
        else:
            send_message(p, ux.MSG_WRONG_INPUT_USE_BUTTONS)            

# ================================
# GPS state
# ================================

def state_GPS(p, **kwargs):
    text_input = kwargs['text_input'] if 'text_input' in kwargs.keys() else None    
    giveInstruction = text_input is None
    current_indovinello = game.getCurrentIndovinello(p)
    if giveInstruction:
        goal_position = [float(x) for x in current_indovinello['GPS'].split(',')]
        msg = ux.MSG_GO_TO_PLACE
        kb = [[BUTTON_LOCATION]]
        send_message(p, msg, kb)
        send_location(p, goal_position[0], goal_position[1])
    else:
        location = kwargs['location'] if 'location' in kwargs.keys() else None
        if location:            
            goal_position = [float(x) for x in current_indovinello['GPS'].split(',')]
            given_position = [location['latitude'], location['longitude']]
            distance = geoUtils.distance_meters(goal_position, given_position)
            if distance <= params.GPS_TOLERANCE_METERS:
                send_message(p, ux.MSG_GPS_OK, remove_keyboard=True)
                sendWaitingAction(p, sleep_time=1)
                redirectToState(p, INDOVINELLO_STATE)
            else:
                msg = ux.MSG_TOO_FAR.format(distance)
                send_message(p, msg)
        else:
            send_message(p, ux.MSG_WRONG_INPUT_SEND_LOCATION)

# ================================
# INDOVINELLO state
# ================================
def state_INDOVINELLO(p, **kwargs):
    text_input = kwargs['text_input'] if 'text_input' in kwargs.keys() else None
    giveInstruction = text_input is None
    current_indovinello = game.getCurrentIndovinello(p)
    if giveInstruction:
        game.set_mission_start_time(p)
        current_indovinello['start_time'] = dtu.nowUtcIsoFormat()        
        msg = current_indovinello['INDOVINELLO'] 
        if current_indovinello.get('INDIZIO_1',False):
            kb = [['💡 PRIMO INDIZIO']]
            send_message(p, msg, kb)
        else:
            send_message(p, msg, remove_keyboard=True)
        p.put()
    else:
        if text_input:            
            kb = p.getLastKeyboard()
            if text_input in utility.flatten(kb):
                now_string = dtu.nowUtcIsoFormat()
                if text_input == '💡 PRIMO INDIZIO':
                    before_string = current_indovinello['start_time']
                    ellapsed = dtu.delta_seconds_iso(before_string, now_string)
                    if ellapsed > params.MIN_SEC_INDIZIO_1 and current_indovinello.get('INDIZIO_1',False):
                        msg = '💡 *Indizio 1*: {}'.format(current_indovinello['INDIZIO_1'])
                        if current_indovinello.get('INDIZIO_2',False):
                            kb = [['💡 SECONDO INDIZIO']]
                            current_indovinello['indizio1_time'] = now_string
                            send_message(p, msg, kb)
                    else:
                        remaining = params.MIN_SEC_INDIZIO_1 - ellapsed
                        send_message(p, ux.MSG_TOO_EARLY.format(remaining))
                elif text_input == '💡 SECONDO INDIZIO' and current_indovinello.get('INDIZIO_2',False):
                    before_string = current_indovinello['indizio1_time']
                    ellapsed = dtu.delta_seconds_iso(before_string, now_string)
                    if ellapsed > params.MIN_SEC_INDIZIO_2 and current_indovinello.get('INDIZIO_2',False):
                        msg = '💡 *Indizio 2*: {}'.format(current_indovinello['INDIZIO_2'])                    
                        current_indovinello['indizio2_time'] = now_string
                        send_message(p, msg, remove_keyboard=True)
                    else:
                        remaining = params.MIN_SEC_INDIZIO_1 - ellapsed
                        send_message(p, ux.MSG_TOO_EARLY.format(remaining))
                else:
                    assert False
            else:
                correct_answers_upper = [x.strip() for x in current_indovinello['SOLUZIONI'].upper().split(',')]
                correct_answers_upper_word_set = set(utility.flatten([x.split() for x in correct_answers_upper]))
                if text_input.upper() in correct_answers_upper:
                    current_indovinello['end_time'] = dtu.nowUtcIsoFormat()
                    send_message(p, ux.MSG_ANSWER_OK, remove_keyboard=True)
                    if 'POST_MESSAGE' in current_indovinello:
                        redirectToState(p, POST_INDOVINELLO_STATE)
                    elif 'GPS' in current_indovinello and not current_indovinello.get('SKIP_SELFIE', False):
                        # only indovinelli with GPS require selfies
                        redirectToState(p, SELFIE_INDOVINELLO_STATE)
                    else:
                        complete_indovinello(p)
                # elif utility.answer_is_almost_correct(text_input.upper(), correct_answers_upper_word_set):
                #     send_message(p, ux.MSG_ANSWER_ALMOST)
                else:
                    game.increase_wrong_answers_current_indovinello(p, text_input)
                    wrong_answers, penalty_sec = game.get_total_penalty(p)
                    msg = ux.MSG_ANSWER_WRONG_SG if wrong_answers==1 else ux.MSG_ANSWER_WRONG_PL
                    send_message(p, msg.format(wrong_answers, penalty_sec))
        else:
            send_message(p, ux.MSG_WRONG_INPUT_INSERT_TEXT)

# ================================
# POST indovinello message
# ================================

def state_POST_INDOVINELLO(p, **kwargs):
    text_input = kwargs['text_input'] if 'text_input' in kwargs.keys() else None    
    giveInstruction = text_input is None
    current_indovinello = game.getCurrentIndovinello(p)
    if giveInstruction:
        if 'POST_MEDIA' in current_indovinello:
            caption = current_indovinello.get('POST_MEDIA_CAPTION',None)
            url_attachment = current_indovinello['POST_MEDIA'][0]['url']
            send_media_url(p, url_attachment, caption=caption)
            sendWaitingAction(p, sleep_time=3)
        msg = current_indovinello['POST_MESSAGE']
        kb = [[ux.BUTTON_CONTINUE]]
        send_message(p, msg, kb)
    else:
        kb = p.getLastKeyboard()
        if text_input in utility.flatten(kb):
            if text_input == ux.BUTTON_CONTINUE:
                complete_indovinello(p)
            else:
                assert False
        else:
            send_message(p, ux.MSG_WRONG_INPUT_USE_BUTTONS)
# ================================
# Selfie Indovinello
# ================================

def state_SELFIE_INDOVINELLO(p, **kwargs):
    photo = kwargs['photo'] if 'photo' in kwargs.keys() else None
    giveInstruction = photo is None
    if giveInstruction:
        send_message(p, ux.MSG_SELFIE_INDOVINELLO, remove_keyboard=True)
    else:
        if photo:
            photo_file_id = photo[-1]['file_id']
            current_indovinello = game.getCurrentIndovinello(p)
            current_indovinello['SELFIE'] = photo_file_id
            MANUAL_VALIDATION = game.manual_validation(p)
            if MANUAL_VALIDATION:
                squadra_name = game.getGroupName(p)
                indovinello_number = game.completedIndovinelloNumber(p) + 1
                indovinello_name = current_indovinello['NOME']
                # store a random password to make sure the approval is correct
                # (the team may have restarted the game in the meanwhile):
                approval_signature = utility.randomAlphaNumericString(5)
                current_indovinello['sign'] = approval_signature
                send_message(p, ux.MSG_WAIT_SELFIE_APPROVAL)
                inline_kb_validation = [
                    [
                        ux.BUTTON_SI_CALLBACK(json.dumps({'ok': True, 'uid':p.getId(), 'sign': approval_signature})),
                        ux.BUTTON_NO_CALLBACK(json.dumps({'ok': False, 'uid': p.getId(), 'sign': approval_signature})),
                    ]
                ]
                caption = 'Selfie indovinello {} squadra {} per indovinello {}'.format(indovinello_number, squadra_name, indovinello_name)
                logging.debug('Sending photo to validator')
                validator = game.get_validator(p)
                logging.debug("Validtor: {}".format(validator))
                send_photo_url(validator, photo_file_id, inline_kb_validation, caption=caption, inline_keyboard=True)
            else:
                approve_selfie_indovinello(p, approved=True, signature=None)
            p.put()
        else:
            send_message(p, ux.MSG_WRONG_INPUT_SEND_PHOTO)

def approve_selfie_indovinello(p, approved, signature):
    # need to double check if team is still waiting for approval
    # (e.g., could have restarted the game, or validator pressed approve twice in a row)
    current_indovinello = game.getCurrentIndovinello(p)
    MANUAL_VALIDATION = game.manual_validation(p)
    if current_indovinello is None or (MANUAL_VALIDATION and signature != current_indovinello['sign']):
        return False
    if approved:
        send_message(p, ux.MSG_SELFIE_INDOVINELLO_OK)
        photo_file_id = current_indovinello['SELFIE']
        if game.send_notification_to_group(p):
            squadra_name = game.getGroupName(p)
            indovinello_number = game.completedIndovinelloNumber(p) + 1
            indovinello_name = current_indovinello['NOME']
            caption = 'Selfie indovinello {} squadra {} per indovinello {}'.format(indovinello_number, squadra_name, indovinello_name)
            send_photo_url(game.HISTORIC_GROUP, photo_file_id, caption=caption)
        game.appendGroupSelfieFileId(p, photo_file_id)        
        complete_indovinello(p)
    else:
        send_message(p, ux.MSG_SELFIE_INDOVINELLO_WRONG)
    return True

def complete_indovinello(p):
    game.setCurrentIndovinelloAsCompleted(p)        
    jump_to_survey = JUMP_TO_SURVEY_AFTER and game.completedIndovinelloNumber(p) == JUMP_TO_SURVEY_AFTER
    if jump_to_survey or game.remainingIndovinelloNumber(p) == 0:
        # game over
        game.set_mission_end_time(p)
        game.setEndTime(p)
        send_message(p, ux.MSG_TIME_STOP)
        sendWaitingAction(p, sleep_time=1)
        send_message(p, ux.MSG_CONGRATS_PRE_SURVEY)
        sendWaitingAction(p, sleep_time=1)
        send_message(p, ux.MSG_SURVEY_INTRO)
        sendWaitingAction(p, sleep_time=1)
        redirectToState(p, SURVEY_STATE)
    else:        
        game.set_mission_end_time(p)
        redirectToState(p, MISSION_INTRO_STATE)


# ================================
# Survey State
# ================================

def state_SURVEY(p, **kwargs):
    text_input = kwargs['text_input'] if 'text_input' in kwargs.keys() else None
    giveInstruction = text_input is None
    if giveInstruction:
        current_question = game.setNextQuestion(p)
        questions_number = game.completedQuestionsNumber(p) + 1
        total_questions = game.getTotalQuestions(p)
        msg = '*Domanda {}/{}*: {}'.format(questions_number, total_questions, current_question['DOMANDA'])
        risposte = [x.strip() for x in current_question['RISPOSTE'].split(',')]
        kb = [risposte]
        send_message(p, msg, kb)
    else:
        kb = p.getLastKeyboard()
        current_question = game.getCurrentQuestion(p)
        question_type_open = current_question['TYPE'] == 'Open'
        if text_input:
            if text_input in utility.flatten(kb):
                answer = '' if question_type_open else text_input
                game.setCurrentQuestionAsCompleted(p, answer)
            elif question_type_open:
                game.setCurrentQuestionAsCompleted(p, text_input)
            else:
                send_message(p, ux.MSG_WRONG_INPUT_USE_BUTTONS)
                return
            if game.remainingQuestionsNumber(p) == 0:
                redirectToState(p, EMAIL_STATE)
            else:
                repeatState(p, put=True)
        else:
            if question_type_open:
                send_message(p, ux.MSG_WRONG_INPUT_INSERT_TEXT_OR_BUTTONS)
            else:
                send_message(p, ux.MSG_WRONG_INPUT_USE_BUTTONS)

# ================================
# Survey State
# ================================

def state_EMAIL(p, **kwargs):
    text_input = kwargs['text_input'] if 'text_input' in kwargs.keys() else None
    giveInstruction = text_input is None
    if giveInstruction:
        kb = [[ux.BUTTON_SKIP_EMAIL]]
        send_message(p, ux.MSG_EMAIL, kb)
    else:
        if text_input:
            if text_input == ux.BUTTON_SKIP_EMAIL:
                redirectToState(p, END_STATE)
            else: 
                if utility.check_email(text_input):                
                    game.setEmail(p, text_input)
                    redirectToState(p, END_STATE)
                else:
                    send_message(p, ux.MSG_EMAIL_WRONG)
        else:
            send_message(p, ux.MSG_WRONG_INPUT_USE_BUTTONS)

# ================================
# Final State
# ================================

def state_END(p, **kwargs):
    text_input = kwargs['text_input'] if 'text_input' in kwargs.keys() else None
    giveInstruction = text_input is None
    if giveInstruction:        
        penalty_hms, total_hms_game, ellapsed_hms_game, \
        total_hms_missions, ellapsed_hms_missions = game.set_elapsed_and_penalty_and_compute_total(p)
        msg = ux.MSG_END.format(penalty_hms, \
            total_hms_game, ellapsed_hms_game, total_hms_missions, ellapsed_hms_missions)        
        send_message(p, msg, remove_keyboard=True)
        if game.send_notification_to_group(p):
            msg_group = ux.MSG_END_NOTIFICATION.format(game.getGroupName(p), penalty_hms, \
                total_hms_game, ellapsed_hms_game, total_hms_missions, ellapsed_hms_missions)
            send_message(game.HISTORIC_GROUP, msg_group)        
        game.save_game_data_in_airtable(p)
        send_message(p, ux.MSG_GO_BACK_TO_START)        
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

# ================================
# ADMIN COMMANDS
# ================================

def deal_with_admin_commands(p, text_input):
    from main_exception import deferredSafeHandleException
    if p.isAdmin():
        if text_input == '/update':
            key.reload_config()
            send_message(p, "Reloaded config table")
            return True
        if text_input == '/debug':
            #send_message(p, game.debugTmpVariables(p), markdown=False)
            sendTextDocument(p, game.debugTmpVariables(p), filename='tmp_vars.json')
            return True
        if text_input == '/testInlineKb':
            send_message(p, "Test inline keypboard", kb=[[ux.BUTTON_SI_CALLBACK('test'), ux.BUTTON_NO_CALLBACK('test')]], inline_keyboard=True)
            return True
        if text_input == '/random':
            from random import shuffle
            numbers = ['1','2','3','4','5']
            shuffle(numbers)
            numbers_str = ', '.join(numbers)
            send_message(p, numbers_str)
            return True
        if text_input == '/exception':
            1/0
            return True
        if text_input == '/wait':
            import time
            for i in range(5):
                send_message(p, str(i+1))
                time.sleep(i+1)
            send_message(p, "end")
            return True
        if text_input.startswith('/testText '):
            text = text_input.split(' ', 1)[1]
            msg = '🔔 *Messaggio da hiSTORIC* 🔔\n\n' + text
            logging.debug("Test broadcast " + msg)
            send_message(p, msg)
            return True
        if text_input.startswith('/broadcast '):
            text = text_input.split(' ', 1)[1]
            msg = '🔔 *Messaggio da hiSTORIC* 🔔\n\n' + text
            logging.debug("Starting to broadcast " + msg)
            deferredSafeHandleException(broadcast, p, msg)
            return True
        if text_input.startswith('/resetBroadcast '):
            text = text_input.split(' ', 1)[1]
            msg = '🔔 *Messaggio da hiSTORIC* 🔔\n\n' + text
            logging.debug("Starting to broadcast and reset players" + msg)
            deferredSafeHandleException(broadcast, p, msg, exit_game=True)
            return True
        if text_input.startswith('/testBroadcast '):
            text = text_input.split(' ', 1)[1]
            msg = '🔔 *Messaggio da hiSTORIC* 🔔\n\n' + text            
            deferredSafeHandleException(broadcast, p, msg, exit_game=True, test=True)
            return True
        if text_input.startswith('/textUser '):
            p_id, text = text_input.split(' ', 2)[1]
            p = Person.get_by_id(p_id)
            if send_message(p, text, kb=p.getLastKeyboard()):
                msg_admin = 'Message sent successfully to {}'.format(p.getFirstNameLastNameUserName())
                tell_admin(msg_admin)
            else:
                msg_admin = 'Problems sending message to {}'.format(p.getFirstNameLastNameUserName())
                tell_admin(msg_admin)
            return True
        if text_input.startswith('/resetUser '):
            p_id = ' '.join(text_input.split(' ')[1:])
            p = Person.get_by_id(p_id)
            if p:
                make_payer_exit_game(p, message=ux.MSG_EXITED_FROM_GAME)
                msg_admin = 'User resetted: {}'.format(p.getFirstNameLastNameUserName())
                tell_admin(msg_admin)                
            else:
                msg_admin = 'No user found: {}'.format(p_id)
                tell_admin(msg_admin)
            return True
        if text_input == '/resetAll':
            deferredSafeHandleException(resetAll)
            return True
    return False

def deal_with_tester_commands(p, text_input):
    # logging.debug("In deal_with_tester_commands with user:{} istester:{}".format(p.getId(), p.isTester()))
    if p.isTester():
        if text_input == '/stats':
            stats_list_str = '\n'.join(["/stats_{}".format(k) for k in key.HUNTS.keys()])
            msg = "Available stats:\n{}".format(stats_list_str)
            send_message(p, msg, markdown=False)
            return True
        if text_input.startswith('/stats_'):
            hung_pw = text_input.split('_', 1)[1]
            if hung_pw in key.HUNTS:
                msg = 'Stats:\n\n{}'.format(person.getPeopleOnHuntStats(hung_pw))
                send_message(p, msg, markdown=False)
            else:
                msg = 'Wrong stats command'
                send_message(p, msg, markdown=False)
            return True
        return False


def deal_with_universal_command(p, text):
    if text.startswith('/start'):
        state_INITIAL(p, text_input=text)
        return True
    if text == '/exit':
        make_payer_exit_game(p, ux.MSG_EXITED_FROM_GAME)
        return True
    if text == '/state':
        state = p.getState()
        msg = "You are in state {}".format(state)
        send_message(p, msg, markdown=False)
        return True
    if text == '/refresh':
        repeatState(p)
        return True
    if text in ['/help', 'HELP', 'AIUTO']:
        pass
        #redirectToState(p, HELP_STATE)
        return True
    if text in ['/stop']:
        p.setEnabled(False, put=True)
        msg = "🚫 Hai *disabilitato* il bot.\n" \
              "In qualsiasi momento puoi riattivarmi scrivendomi qualcosa."
        send_message(p, msg)
        return True
    return False


def dealWithUserInteraction(chat_id, name, last_name, username, application, text,
                            location, contact, photo, document, voice):

        p = person.getPersonByChatIdAndApplication(chat_id, application)

        if p is None:
            p = person.addPerson(chat_id, name, last_name, username, application)
            tellMaster("New {} user: {}".format(application, p.getFirstNameLastNameUserName(escapeMarkdown=False)))
        else:
            _, was_disabled = p.updateUserInfo(name, last_name, username)
            if was_disabled:
                msg = "Bot riattivato!"
                send_message(p, msg)
        
        if WORK_IN_PROGRESS and not p.isTester():
            send_message(p, ux.MSG_WORK_IN_PROGRESS)    
            return
                
        if text:
            if deal_with_admin_commands(p, text):
                return
            if deal_with_tester_commands(p, text):
                return
            if deal_with_universal_command(p, text):
                return

        state = p.getState()
        logging.debug("Sending {} to state {} with text_input {}".format(p.getFirstName(), state, text))
        repeatState(p, text_input=text, location=location, contact=contact, photo=photo, document=document, voice=voice)


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
