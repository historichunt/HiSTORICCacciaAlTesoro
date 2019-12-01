import logging
import bot_telegram
from bot_telegram import BOT, send_message, send_location, send_typing_action, \
    report_master, send_text_document, send_media_url, \
    broadcast, tell_admin, reset_all_users
import utility
import telegram
import ndb_person
from ndb_person import Person
from ndb_person import client_context
import bot_ux
import game
import time
import params
import key
import geoUtils
import date_time_util as dtu
import json
import random

# ================================
# CONFIG
# ================================
WORK_IN_PROGRESS = False
JUMP_TO_SURVEY_AFTER = False  # 2


# ================================
# RESTART
# ================================
def restart_multi(users):
    for u in users:
        redirect_to_state(u, state_INITIAL)

def restart(user):
    redirect_to_state(user, state_INITIAL)

# ================================
# REDIRECT TO STATE
# ================================
def redirect_to_state(user, new_function, message_obj=None):
    new_state = new_function.__name__
    if user.state != new_state:
        logging.debug("In redirect_to_state. current_state:{0}, new_state: {1}".format(str(user.state), str(new_state)))
        user.set_state(new_state)
    repeat_state(user, message_obj)

def redirect_to_state_multi(users, new_function, message_obj=None):
    reversed_users = list(reversed(users)) # so that game creator is last
    for u in reversed_users:
        redirect_to_state(u, new_function, message_obj)


# ================================
# REPEAT STATE
# ================================
def repeat_state(user, message_obj=None):
    state = user.state
    if state is None:
        restart(user)
        return
    method = possibles.get(state)
    if not method:
        msg = "⚠️ User {} sent to unknown method state: {}".format(user.chat_id, state)
        report_master(msg)
        restart(user)
    else:
        method(user, message_obj)

# ================================
# Initial State
# ================================

def state_INITIAL(p, message_obj=None, **kwargs):    
    if message_obj is None:
        if key.ARE_THERE_ACTIVE_HUNTS:
            switch_language_button = p.ux().BUTTON_ENGLISH if p.language=='IT' else p.ux().BUTTON_ITALIAN
            kb = [
                [switch_language_button],
                [p.ux().BUTTON_INFO]
            ]            
            send_message(p, p.ux().MSG_WELCOME_START, kb)
        else:
            send_message(p, p.ux().MSG_NO_HUNTS)
    else: 
        text_input = message_obj.text
        if text_input:
            kb = p.get_keyboard()
            if text_input in utility.flatten(kb):
                if text_input == p.ux().BUTTON_INFO:
                    send_message(p, p.ux().MSG_HISTORIC_INFO, remove_keyboard=True)
                    send_typing_action(p, sleep_time=5)
                    repeat_state(p)
                elif text_input == p.ux().BUTTON_ITALIAN:
                    p.set_language('IT')
                    repeat_state(p)
                elif text_input == p.ux().BUTTON_ENGLISH:
                    p.set_language('EN')                
                    repeat_state(p)           
                else:
                    assert False
                return
            if text_input.lower() == '/start':
                repeat_state(p)
                return
            if text_input.lower().startswith('/start '):
                hunt_password = text_input.lower().split()[1]
            else: 
                hunt_password = text_input.lower()
            if hunt_password in key.ACTIVE_HUNTS:                    
                game.reset_game(p, hunt_password)
                game_name = key.ACTIVE_HUNTS[hunt_password]['Name']
                send_message(p, p.ux().MSG_WELCOME.format(game_name), remove_keyboard=True)
                redirect_to_state(p, state_START)
            else:
                msg = '🙈 Non hai inserito la parola magica giusta per iniziare la caccia al tesoro.'
                send_message(p, msg)
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS, kb)

def state_START(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    if give_instruction:
        switch_language_button = p.ux().BUTTON_ENGLISH if p.language=='IT' else p.ux().BUTTON_ITALIAN
        kb = [[p.ux().BUTTON_START_GAME],[switch_language_button]]
        send_message(p, p.ux().MSG_PRESS_TO_START, kb)
    else:
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input in utility.flatten(kb):
            if text_input == p.ux().BUTTON_ITALIAN:
                p.set_language('IT')
                repeat_state(p)
            elif text_input == p.ux().BUTTON_ENGLISH:
                p.set_language('EN')                
                repeat_state(p)     
            elif text_input == p.ux().BUTTON_START_GAME:
                send_message(p, p.ux().MSG_GO, remove_keyboard=True)
                send_typing_action(p, sleep_time=1)                
                redirect_to_state(p, state_NOME_GRUPPO)
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS, kb)

# ================================
# Nome Gruppo State
# ================================

def state_NOME_GRUPPO(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    if give_instruction:
        send_message(p, p.ux().MSG_GROUP_NAME)
    else:
        text_input = message_obj.text
        if text_input:
            if len(text_input) > params.MAX_TEAM_NAME_LENGTH:
                send_message(p, p.ux().MSG_GROUP_NAME_TOO_LONG.format(params.MAX_TEAM_NAME_LENGTH))
                return
            if not utility.hasOnlyLettersAndSpaces(text_input):
                send_message(p, p.ux().MSG_GROUP_NAME_INVALID)
                return
            game.set_group_name(p, text_input)
            send_message(p, p.ux().MSG_GROUP_NAME_OK.format(text_input))
            if game.send_notification_to_group(p):
                send_message(game.HISTORIC_GROUP, "Nuova squadra registrata: {}".format(text_input))
            redirect_to_state(p, state_SELFIE_INIZIALE)
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_INSERT_TEXT)

# ================================
# Selfie Iniziale State
# ================================

def state_SELFIE_INIZIALE(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    if give_instruction:
        send_message(p, p.ux().MSG_SELFIE_INIZIALE)
    else:
        photo = message_obj.photo
        if photo:
            photo_file_id = photo[-1]['file_id']
            game.append_group_media_input_file_id(p, photo_file_id)
            send_typing_action(p, sleep_time=1)
            send_message(p, p.ux().MSG_SELFIE_INIZIALE_OK)            
            if game.send_notification_to_group(p):
                BOT.send_photo(game.HISTORIC_GROUP_id, photo=photo_file_id, caption='Selfie iniziale {}'.format(game.get_group_name(p)))
            send_message(p, p.ux().MSG_START_TIME, sleepDelay=True, remove_keyboard=True)
            game.set_game_start_time(p)
            redirect_to_state(p, state_MISSION_INTRO)
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_SEND_PHOTO)

# ================================
# INTRO
# ================================

def state_MISSION_INTRO(p, message_obj=None, **kwargs):        
    give_instruction = message_obj is None
    if give_instruction:
        current_indovinello = game.setNextIndovinello(p)        
        indovinello_number = game.completed_indovinello_number(p) + 1
        total_missioni = game.getTotalIndovinelli(p)
        msg = p.ux().MSG_MISSION_N_TOT.format(indovinello_number, total_missioni)
        send_message(p, msg, remove_keyboard=True)
        send_typing_action(p, sleep_time=1)        
        if 'INTRODUZIONE_LOCATION' not in current_indovinello:
            redirect_to_state(p, state_GPS)
            return
        if 'INTRO_MEDIA' in current_indovinello:
            caption = current_indovinello.get('INTRO_MEDIA_CAPTION',None)
            url_attachment = current_indovinello['INTRO_MEDIA'][0]['url']
            send_media_url(p, url_attachment, caption=caption)
            send_typing_action(p, sleep_time=1)
        msg = current_indovinello['INTRODUZIONE_LOCATION'] # '*Introduzione*: ' + 
        kb = [[random.choice(bot_ux.BUTTON_CONTINUE_MULTI(p.language))]]
        send_message(p, msg, kb)
        p.put()
    else:
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input in utility.flatten(kb):
            if text_input in bot_ux.BUTTON_CONTINUE_MULTI(p.language):
                current_indovinello = game.getCurrentIndovinello(p)
                redirect_to_state(p, state_GPS)
            else:
                assert False
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS)            

# ================================
# GPS state
# ================================  

def state_GPS(p, message_obj=None, **kwargs):        
    give_instruction = message_obj is None
    current_indovinello = game.getCurrentIndovinello(p)
    if 'GPS' not in current_indovinello:
        redirect_to_state(p, state_DOMANDA)
        return
    if give_instruction:
        goal_position = [float(x) for x in current_indovinello['GPS'].split(',')]
        msg = p.ux().MSG_GO_TO_PLACE
        kb = [[bot_ux.BUTTON_LOCATION(p.language)]]
        send_message(p, msg, kb)
        send_location(p, goal_position[0], goal_position[1])
    else:
        location = message_obj.location
        if location:            
            goal_position = [float(x) for x in current_indovinello['GPS'].split(',')]
            lat, lon = location['latitude'], location['longitude']
            p.set_location(lat, lon)
            given_position = [lat, lon]
            distance = geoUtils.distance_meters(goal_position, given_position)
            GPS_TOLERANCE_METERS = int(p.tmp_variables['SETTINGS']['GPS_TOLERANCE_METERS'])
            if distance <= GPS_TOLERANCE_METERS:
                send_message(p, p.ux().MSG_GPS_OK, remove_keyboard=True)
                send_typing_action(p, sleep_time=1)
                redirect_to_state(p, state_DOMANDA)
            else:
                msg = p.ux().MSG_TOO_FAR.format(distance)
                send_message(p, msg)
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_SEND_LOCATION)

# ================================
# DOMANDA state
# ================================
def state_DOMANDA(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    current_indovinello = game.getCurrentIndovinello(p)
    if give_instruction:
        if 'DOMANDA_MEDIA' in current_indovinello:
            caption = current_indovinello.get('DOMANDA_MEDIA_CAPTION',None)
            url_attachment = current_indovinello['DOMANDA_MEDIA'][0]['url']
            send_media_url(p, url_attachment, caption=caption)
            send_typing_action(p, sleep_time=1)                
        msg = current_indovinello['DOMANDA'] 
        if current_indovinello.get('INDIZIO_1',False):
            kb = [[p.ux().BUTTON_FIRST_HINT]]
            send_message(p, msg, kb)
        else:
            send_message(p, msg, remove_keyboard=True)
        game.start_mission(p)
        p.put()
        if 'SOLUZIONI' not in current_indovinello:
            # if there is no text required go to required_input (photo or voice)
            assert 'REQUIRED_INPUT' in current_indovinello
            redirect_to_state(p, state_MEDIA_INPUT_MISSION)
    else:
        text_input = message_obj.text
        if text_input:            
            kb = p.get_keyboard()
            if text_input in utility.flatten(kb):
                now_string = dtu.nowUtcIsoFormat()
                MIN_SEC_INDIZIO_1 = int(p.tmp_variables['SETTINGS']['MIN_SEC_INDIZIO_1'])
                MIN_SEC_INDIZIO_2 = int(p.tmp_variables['SETTINGS']['MIN_SEC_INDIZIO_2'])
                if text_input == p.ux().BUTTON_FIRST_HINT:
                    before_string = current_indovinello['start_time']
                    ellapsed = dtu.delta_seconds_iso(before_string, now_string)
                    if ellapsed > MIN_SEC_INDIZIO_1 and current_indovinello.get('INDIZIO_1',False):
                        msg = '💡 *Indizio 1*: {}'.format(current_indovinello['INDIZIO_1'])
                        if current_indovinello.get('INDIZIO_2',False):
                            kb = [[p.ux().BUTTON_SECOND_HINT]]
                            current_indovinello['indizio1_time'] = now_string
                            send_message(p, msg, kb)
                        else:
                            send_message(p, msg, remove_keyboard=True)
                    else:
                        remaining = MIN_SEC_INDIZIO_1 - ellapsed
                        send_message(p, p.ux().MSG_TOO_EARLY.format(remaining))
                elif text_input == p.ux().BUTTON_SECOND_HINT and current_indovinello.get('INDIZIO_2',False):
                    before_string = current_indovinello['indizio1_time']
                    ellapsed = dtu.delta_seconds_iso(before_string, now_string)
                    if ellapsed > MIN_SEC_INDIZIO_2 and current_indovinello.get('INDIZIO_2',False):
                        msg = '💡 *Indizio 2*: {}'.format(current_indovinello['INDIZIO_2'])                    
                        current_indovinello['indizio2_time'] = now_string
                        send_message(p, msg, remove_keyboard=True)
                    else:
                        remaining = MIN_SEC_INDIZIO_1 - ellapsed
                        send_message(p, p.ux().MSG_TOO_EARLY.format(remaining))
                else:
                    assert False
            else:
                correct_answers_upper = [x.strip() for x in current_indovinello['SOLUZIONI'].upper().split(',')]
                #correct_answers_upper_word_set = set(utility.flatten([x.split() for x in correct_answers_upper]))
                if text_input.upper() in correct_answers_upper:
                    game.set_end_mission_time(p)
                    send_message(p, bot_ux.MSG_ANSWER_OK(p.language), remove_keyboard=True)
                    send_typing_action(p, sleep_time=1)
                    if send_post_message(p, current_indovinello):
                        redirect_to_state(p, state_COMPLETE_MISSION)
                    elif 'REQUIRED_INPUT' in current_indovinello:
                        # only missioni with GPS require selfies
                        redirect_to_state(p, state_MEDIA_INPUT_MISSION)
                    else:
                        redirect_to_state(p, state_COMPLETE_MISSION)
                # elif utility.answer_is_almost_correct(text_input.upper(), correct_answers_upper_word_set):
                #     send_message(p, p.ux().MSG_ANSWER_ALMOST)
                else:
                    give_penalty = current_indovinello.get('PENALTÀ',False)
                    game.increase_wrong_answers_current_indovinello(p, text_input, give_penalty)
                    if give_penalty:
                        penalties, penalty_sec = game.get_total_penalty(p)
                        msg = p.ux().MSG_ANSWER_WRONG_SG if penalties==1 else p.ux().MSG_ANSWER_WRONG_PL
                        send_message(p, msg.format(penalties, penalty_sec))
                    else:
                        send_message(p, bot_ux.MSG_ANSWER_WRONG_NO_PENALTY(p.language))
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_INSERT_TEXT)

def send_post_message(p, current_indovinello):
    if 'POST_MESSAGE' in current_indovinello:                        
        if 'POST_MEDIA' in current_indovinello:
            caption = current_indovinello.get('POST_MEDIA_CAPTION',None)
            url_attachment = current_indovinello['POST_MEDIA'][0]['url']
            send_media_url(p, url_attachment, caption=caption)
            send_typing_action(p, sleep_time=1)
        msg = current_indovinello['POST_MESSAGE']
        send_message(p, msg, remove_keyboard=True)
        send_typing_action(p, sleep_time=1)
        return True
    return False

# ================================
# MEDIA INPUT (photo, voice)
# ================================

def state_MEDIA_INPUT_MISSION(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    current_indovinello = game.getCurrentIndovinello(p)
    input_type = current_indovinello['REQUIRED_INPUT'] # PHOTO, VOICE
    assert input_type in ['PHOTO','VOICE']
    if give_instruction:
        msg = p.ux().MSG_INPUT_SELFIE_MISSIONE if input_type == 'PHOTO' else p.ux().MSG_INPUT_RECORDING_MISSIONE
        send_message(p, msg, remove_keyboard=True)
    else:
        assert input_type in ['PHOTO', 'VOICE'] # missing video
        photo = message_obj.photo
        voice = message_obj.voice
        logging.debug("input_type: {} photo: {} voice: {}".format(input_type, photo, voice))
        if input_type == 'PHOTO' and (photo is None or len(photo)==0):            
            send_message(p, p.ux().MSG_WRONG_INPUT_SEND_PHOTO)
            return
        if input_type == 'VOICE' and voice is None:          
            send_message(p, p.ux().MSG_WRONG_INPUT_SEND_VOICE)
            return        
        file_id = photo[-1]['file_id'] if input_type=='PHOTO' else voice['file_id']
        current_indovinello['MEDIA_INPUT_ID_TYPE'] = [file_id, input_type]
        if current_indovinello.get('INPUT_CONFIRMATION', False):
            redirect_to_state(p, state_CONFIRM_MEDIA_INPUT)
        elif game.manual_validation(p):
            send_to_validator(p, game, current_indovinello, input_type)        
        else:
            approve_media_input_indovinello(p, approved=True, signature=None)
        p.put()

def send_to_validator(p, game, current_indovinello, input_type):
    assert input_type in ['PHOTO','VOICE'] # missing 'VIDEO'
    squadra_name = game.get_group_name(p)
    indovinello_number = game.completed_indovinello_number(p) + 1
    indovinello_name = current_indovinello['NOME']
    replies_dict = {
        'PHOTO': {
            'reply': p.ux().MSG_WAIT_SELFIE_APPROVAL,
            'caption': 'Selfie indovinello {} squadra {} per indovinello {}'.format(\
                indovinello_number, squadra_name, indovinello_name)
        },
        'VOICE': {
            'reply': p.ux().MSG_WAIT_VOICE_APPROVAL,
            'caption': 'Registrazione indovinello {} squadra {} per indovinello {}'.format(\
                indovinello_number, squadra_name, indovinello_name)
        }
    }
    # store a random password to make sure the approval is correct
    # (the team may have restarted the game in the meanwhile):
    approval_signature = utility.randomAlphaNumericString(5)
    current_indovinello['sign'] = approval_signature
    send_message(p, replies_dict[input_type]['reply'])
    kb_markup = telegram.InlineKeyboardMarkup(
        [
            [
                bot_ux.BUTTON_YES_CALLBACK(
                    json.dumps({'ok': True, 'uid':p.get_id(), 'sign': approval_signature})
                ),
                bot_ux.BUTTON_NO_CALLBACK(
                    json.dumps({'ok': False, 'uid': p.get_id(), 'sign': approval_signature})
                ),
            ]
        ]
    )
    file_id = current_indovinello['MEDIA_INPUT_ID_TYPE'][0]
    caption = replies_dict[input_type]['caption']
    logging.debug('Sending group input ({}) to validator'.format(input_type))
    if input_type == 'PHOTO':
        BOT.send_photo(game.get_validator_chat_id(p), photo=file_id, caption=caption, reply_markup=kb_markup)
    else: # input_type == 'VOICE':
        BOT.send_voice(game.get_validator_chat_id(p), voice=file_id, caption=caption, reply_markup=kb_markup)

def approve_media_input_indovinello(p, approved, signature):
    # need to double check if team is still waiting for approval
    # (e.g., could have restarted the game, or validator pressed approve twice in a row)
    current_indovinello = game.getCurrentIndovinello(p)
    if current_indovinello is None:
        return False
    file_id, input_type = current_indovinello['MEDIA_INPUT_ID_TYPE']
    assert input_type in ['PHOTO','VOICE']
    if game.manual_validation(p) and signature != current_indovinello.get('sign', signature):
        # if 'sign' is not in current_indovinello it means we are in INPUT_CONFIRMATION mode 
        return False
    if approved:
        game.set_end_mission_time(p)
        send_message(p, bot_ux.MSG_MEDIA_INPUT_MISSIONE_OK(p.language))        
        if game.send_notification_to_group(p):
            squadra_name = game.get_group_name(p)
            indovinello_number = game.completed_indovinello_number(p) + 1
            indovinello_name = current_indovinello['NOME']            
            if input_type=='PHOTO':
                caption = 'Selfie indovinello {} squadra {} per indovinello {}'.format(indovinello_number, squadra_name, indovinello_name)
                BOT.send_photo(game.HISTORIC_GROUP_id, photo=file_id, caption=caption)
            else: #elif input_type=='VOICE':
                caption = 'Registrazione indovinello {} squadra {} per indovinello {}'.format(indovinello_number, squadra_name, indovinello_name)
                BOT.send_voice(game.HISTORIC_GROUP_id, voice=file_id, caption=caption)
        game.append_group_media_input_file_id(p, file_id)        
        send_post_message(p, current_indovinello)
        redirect_to_state(p, state_COMPLETE_MISSION)
    else:
        if input_type=='PHOTO':
            send_message(p, p.ux().MSG_SELFIE_MISSIONE_WRONG)
        else: #input_type=='VOICE':
            send_message(p, p.ux().MSG_RECORDING_MISSIONE_WRONG)
    return True


# ================================
# CONFIRM MEDIA INPUT (photo, voice)
# ================================

def state_CONFIRM_MEDIA_INPUT(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    current_indovinello = game.getCurrentIndovinello(p)
    input_type = current_indovinello['REQUIRED_INPUT'] # PHOTO, VOICE
    if give_instruction:
        msg = p.ux().MSG_CONFIRM_PHOTO_INPUT if input_type == 'PHOTO' else p.ux().MSG_CONFIRM_RECORDING_INPUT
        kb = [[p.ux().BUTTON_YES, p.ux().BUTTON_NO]]
        send_message(p, msg, kb)
    else:
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input in utility.flatten(kb):
            if text_input == p.ux().BUTTON_YES:
                approve_media_input_indovinello(p, approved=True, signature=None)
            else: 
                assert text_input == p.ux().BUTTON_NO
                msg = p.ux().MSG_MEDIA_INPUT_ABORTED
                send_message(p, msg, remove_keyboard=True)
                send_typing_action(p, sleep_time=1)
                redirect_to_state(p, state_MEDIA_INPUT_MISSION)
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS)  

# ================================
# COMPLETE CURRENT MISSION
# ================================

def state_COMPLETE_MISSION(p, message_obj=None, **kwargs):
    give_instruction = message_obj is None        
    if give_instruction:
        game.setCurrentIndovinelloAsCompleted(p)
        survery_time = game.remainingIndovinelloNumber(p) == 0 or \
            JUMP_TO_SURVEY_AFTER and game.completed_indovinello_number(p) == JUMP_TO_SURVEY_AFTER
        game.set_mission_end_time(p)
        if survery_time:            
            game.set_game_end_time(p, completed=True)
            msg = p.ux().MSG_PRESS_FOR_ENDING
            kb = [[p.ux().BUTTON_END]]
            send_message(p, msg, kb)
        else:        
            msg = p.ux().MSG_PRESS_FOR_NEXT_MISSION
            kb = [[p.ux().BUTTON_NEXT_MISSION]]            
            send_message(p, msg, kb)
    else:
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input in utility.flatten(kb):
            if text_input == p.ux().BUTTON_NEXT_MISSION:
                redirect_to_state(p, state_MISSION_INTRO)
            elif text_input == p.ux().BUTTON_END:
                send_message(p, p.ux().MSG_TIME_STOP, remove_keyboard=True)
                send_typing_action(p, sleep_time=1)
                send_message(p, p.ux().MSG_CONGRATS_PRE_SURVEY)
                send_typing_action(p, sleep_time=1)
                send_message(p, p.ux().MSG_SURVEY_INTRO)
                send_typing_action(p, sleep_time=1)
                redirect_to_state(p, state_SURVEY)
            else:
                assert False
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS)        

# ================================
# Survey State
# ================================

def state_SURVEY(p, message_obj=None, **kwargs):
    give_instruction = message_obj is None
    if give_instruction:
        current_question = game.setNextQuestion(p)
        questions_number = game.completedQuestionsNumber(p) + 1
        total_questions = game.getTotalQuestions(p)
        msg = '*Domanda {}/{}*: {}'.format(questions_number, total_questions, current_question['DOMANDA'])
        risposte = [x.strip() for x in current_question['RISPOSTE'].split(',')]
        kb = [risposte]
        send_message(p, msg, kb)
    else:
        text_input = message_obj.text
        kb = p.get_keyboard()
        current_question = game.getCurrentQuestion(p)
        if current_question is None:
            return
            # when question has been set to complete and at the same time the user presses a button            
        question_type_open = current_question['TYPE'] == 'Open'
        if text_input:
            if text_input in utility.flatten(kb):
                answer = '' if question_type_open else text_input
                game.setCurrentQuestionAsCompleted(p, answer)
            elif question_type_open:
                game.setCurrentQuestionAsCompleted(p, text_input)
            else:
                send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS)
                return
            if game.remainingQuestionsNumber(p) == 0:
                redirect_to_state(p, state_EMAIL)
            else:
                p.put()
                repeat_state(p)
        else:
            if question_type_open:
                send_message(p, p.ux().MSG_WRONG_INPUT_INSERT_TEXT_OR_BUTTONS)
            else:
                send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS)

# ================================
# Survey State
# ================================

def state_EMAIL(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    if give_instruction:
        kb = [[p.ux().BUTTON_SKIP_EMAIL]]
        send_message(p, p.ux().MSG_EMAIL, kb)
    else:
        text_input = message_obj.text
        if text_input:
            if text_input == p.ux().BUTTON_SKIP_EMAIL:
                redirect_to_state(p, state_END)
            else: 
                if utility.check_email(text_input):                
                    game.setEmail(p, text_input)
                    redirect_to_state(p, state_END)
                else:
                    send_message(p, p.ux().MSG_EMAIL_WRONG)
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS)

# ================================
# Final State
# ================================

def state_END(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    if give_instruction:        
        penalty_hms, total_hms_game, ellapsed_hms_game, \
        total_hms_missions, ellapsed_hms_missions = game.set_elapsed_and_penalty_and_compute_total(p)
        msg = p.ux().MSG_END.format(penalty_hms, \
            total_hms_game, ellapsed_hms_game, total_hms_missions, ellapsed_hms_missions)        
        send_message(p, msg, remove_keyboard=True)
        if game.send_notification_to_group(p):
            msg_group = p.ux().MSG_END_NOTIFICATION.format(game.get_group_name(p), penalty_hms, \
                total_hms_game, ellapsed_hms_game, total_hms_missions, ellapsed_hms_missions)
            send_message(game.HISTORIC_GROUP, msg_group)                
        send_message(p, p.ux().MSG_GO_BACK_TO_START)     
        game.exit_game(p, save_data=True)   
        restart(p)
    else:
        pass


## +++++ END OF STATES +++++ ###

def deal_with_callback_query(callback_query):
    callback_query_data = json.loads(callback_query.data)
    approved = callback_query_data['ok']
    user_id = callback_query_data['uid']
    approval_signature = callback_query_data['sign']
    p = ndb_person.get_person_by_id(user_id)
    squadra_name = game.get_group_name(p)
    callback_query_id = callback_query.id
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id
    BOT.delete_message(chat_id, message_id)
    validation_success = approve_media_input_indovinello(p, approved, signature=approval_signature)
    if validation_success:
        if approved:
            answer = "Messaggio di conferma inviato alla squadra {}!".format(squadra_name)
        else:
            answer = "Inviato messsaggio di rifare il selfie alla squadra {}!".format(squadra_name)
    else:
        answer = "Problema di validazione. La squadra {} ha ricomnciato il gioco " \
                 "o l'approvazione è stata mandata più volte".format(squadra_name)
    BOT.answer_callback_query(callback_query_id, answer)

# ================================
# ADMIN COMMANDS
# ================================

def deal_with_admin_commands(p, message_obj):
    text_input = message_obj.text
    if p.is_admin():
        if text_input == '/debug':
            #send_message(p, game.debugTmpVariables(p), markdown=False)
            send_text_document(p, 'tmp_vars.json', game.debugTmpVariables(p))
            return True
        if text_input == '/testInlineKb':
            send_message(p, "Test inline keypboard", kb=[[p.ux().BUTTON_YES_CALLBACK('test'), p.ux().BUTTON_NO_CALLBACK('test')]], inline_keyboard=True)
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
            broadcast(p, msg)
            return True
        if text_input.startswith('/textUser '):
            p_id, text = text_input.split(' ', 2)[1]
            p = Person.get_by_id(p_id)
            if send_message(p, text, kb=p.get_keyboard()):
                msg_admin = 'Message sent successfully to {}'.format(p.get_first_last_username())
                tell_admin(msg_admin)
            else:
                msg_admin = 'Problems sending message to {}'.format(p.get_first_last_username())
                tell_admin(msg_admin)
            return True
        if text_input.startswith('/restartUser '):
            p_id = ' '.join(text_input.split(' ')[1:])
            p = Person.get_by_id(p_id)
            if p:
                if game.user_in_game(p):
                    game.exit_game(p, save_data=False)
                    send_message(p, p.ux().MSG_EXITED_FROM_GAME, remove_keyboard=True)
                restart(p)
                msg_admin = 'User restarted: {}'.format(p.get_first_last_username())
                tell_admin(msg_admin)                
            else:
                msg_admin = 'No user found: {}'.format(p_id)
                tell_admin(msg_admin)
            return True
        if text_input == '/remove_keyboard_from_notification_group':
            bot_telegram.remove_keyboard_from_notification_group()
            return True
        if text_input == '/reset_all_users':            
            reset_all_users(message=None) #message=p.ux().MSG_THANKS_FOR_PARTECIPATING
            return True
    return False

def deal_with_manager_commands(p, message_obj):
    text_input = message_obj.text
    # logging.debug("In deal_with_manager_commands with user:{} ismanager:{}".format(p.get_id(), p.is_manager()))
    if p.is_manager():
        if text_input == '/admin':
            msg = "Comandi disponibili:\n"
            msg += "- /info: info cacce al tesoro attive\n"
            msg += "- /update: refresh configuarzione cacce al tesoro\n"            
            msg += "- /stats: statistiche delle cacce al tesoro\n"
            msg += "- /terminate: termina una caccia al tesoro"
            send_message(p, msg, markdown=False)
            return True
        if text_input == '/info':
            info_cacce = '\n'.join(["- {} 🔐{}".format(v['Name'], k) for k,v in key.ACTIVE_HUNTS.items()])
            msg = "Cacce al tesoro attive:\n{}".format(info_cacce)
            send_message(p, msg, markdown=False)
            return True
        if text_input == '/update':
            bot_ux.reload_ux()
            key.reload_config()
            send_message(p, p.ux().MSG_RELOADED_CONFIG_TABLE)
            return True
        if text_input == '/stats':
            stats_list_str = '\n'.join(["/stats_{}".format(k) for k in key.ACTIVE_HUNTS.keys()])
            msg = "Statistiche disponibili:\n{}".format(stats_list_str)
            send_message(p, msg, markdown=False)
            return True
        if text_input.startswith('/stats_'):
            hunt_pw = text_input.split('_', 1)[1]
            if hunt_pw in key.ACTIVE_HUNTS:
                hunt_stats = ndb_person.get_people_on_hunt_stats(hunt_pw)
                if hunt_stats:
                    msg = 'Stats:\n\n{}'.format(hunt_stats)
                else:
                    msg = 'Nessuna squadra iscritta'
                send_message(p, msg, markdown=False)
            else:
                msg = 'Wrong stats command'
                send_message(p, msg, markdown=False)
            return True        
        if text_input == '/terminate':
            terminate_list_str = '\n'.join(["/terminate_{}".format(k) for k in key.ACTIVE_HUNTS.keys()])
            msg = "Available games to terminate:\n{}".format(terminate_list_str)
            send_message(p, msg, markdown=False)
            return True
        if text_input.startswith('/terminate_'):            
            hunt_pw = text_input.split('_', 1)[1]
            if hunt_pw in key.ACTIVE_HUNTS:
                qry = Person.query(Person.current_hunt==hunt_pw)
                remaining_people = qry.fetch()
                for u in remaining_people:                    
                    game.exit_game(u, save_data=True)
                    send_message(u, p.ux().MSG_HUNT_TERMINATED, remove_keyboard=True, sleep=True)
                    send_typing_action(p, sleep_time=4)
                    restart(p)
                send_message(p, "Mandato messagio di termine a {} squadre.".format(len(remaining_people)))
                return True
        return False


def deal_with_universal_command(p, message_obj):
    text_input = message_obj.text
    if text_input.startswith('/start'):
        if game.user_in_game(p):
            send_message(p, p.ux().MSG_YOU_ARE_IN_A_GAME_EXIT_FIRST)
        else:
            redirect_to_state(p, state_INITIAL, message_obj)
        return True
    if text_input.lower() == '/it':
        send_message(p, "🇮🇹 Linua settata per ITALIANO")
        p.set_language('IT', put=True)
        return True
    if text_input.lower() == '/en':
        send_message(p, "🇬🇧 Language set on ENGLISH")
        p.set_language('EN', put=True)
        return True
    if text_input == '/exit':
        if game.user_in_game(p):
            game.exit_game(p, save_data=False)
            send_message(p, p.ux().MSG_EXITED_FROM_GAME, remove_keyboard=True)
            restart(p)
        else:
            send_message(p, p.ux().MSG_NOT_IN_GAME)
        return True
    if text_input == '/state':
        state = p.get_state()
        msg = "You are in state {}".format(state)
        send_message(p, msg, markdown=False)
        return True
    if text_input == '/refresh':
        repeat_state(p)
        return True
    if text_input in ['/help', 'HELP', 'AIUTO']:
        pass
        return True
    if text_input in ['/stop']:
        p.set_enabled(False, put=True)
        msg = "🚫 Hai *disabilitato* il bot.\n" \
              "In qualsiasi momento puoi riattivarmi scrivendomi qualcosa."
        send_message(p, msg)
        return True
    return False

# ================================
# DEAL WITH REQUEST
# ================================
@client_context
def deal_with_request(request_json):
    # retrieve the message in JSON and then transform it to Telegram object
    update_obj = telegram.Update.de_json(request_json, BOT)
    if update_obj.callback_query:
        deal_with_callback_query(update_obj.callback_query)
        return 
    message_obj = update_obj.message    
    user_obj = message_obj.from_user
    chat_id = user_obj.id    
    username = user_obj.username
    last_name = user_obj.last_name if user_obj.last_name else ''
    name = (user_obj.first_name + ' ' + last_name).strip()
    # language = user_obj.language_code
    
    p = ndb_person.get_person_by_id_and_application(user_obj.id, 'telegram')

    if p == None:
        p = ndb_person.add_person(chat_id, name, last_name, username, 'telegram')
        report_master('New user: {}'.format(p.get_first_last_username()))
    else:
        _, was_disabled = p.update_info(name, last_name, username)
        if was_disabled:
            msg = "Bot riattivato!"
            send_message(p, msg)

    if message_obj.forward_from and not p.is_manager():
        send_message(p, p.ux().MSG_NO_FORWARDING_ALLOWED)
        return

    text = message_obj.text
    if text:
        text_input = message_obj.text        
        logging.debug('Message from @{} in state {} with text {}'.format(chat_id, p.state, text_input))
        if WORK_IN_PROGRESS and not p.is_manager():
            send_message(p, p.ux().MSG_WORK_IN_PROGRESS)    
            return
        if deal_with_admin_commands(p, message_obj):
            return
        if deal_with_universal_command(p, message_obj):
            return
        if deal_with_manager_commands(p, message_obj):
            return
    logging.debug("Sending {} to state {} with input message_obj {}".format(p.get_first_name(), p.state, message_obj))
    repeat_state(p, message_obj=message_obj)

possibles = globals().copy()
possibles.update(locals())