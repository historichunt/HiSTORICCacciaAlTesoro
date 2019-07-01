import logging
from bot_telegram import BOT, send_message, send_typing_action, \
    report_master, send_text_document, send_media_url, \
    broadcast, tell_admin, reset_all_users
import utility
import bot_ux as ux
import telegram
import ndb_person
from ndb_person import Person
from ndb_person import client_context
import game
import time
import params
import key
import geoUtils
import date_time_util as dtu
import json


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

def restart_user(user):
    redirect_to_state(user, state_INITIAL)

# ================================
# EXIT GAME
# ================================
def make_payer_exit_game(p, message=None):
    if game.exitGame(p):
        if message:
            send_message(p, message, remove_keyboard=True)
        redirect_to_state(p, state_INITIAL)

# ================================
# REDIRECT TO STATE
# ================================
def redirect_to_state_multi(users, new_function, message_obj=None):
    reversed_users = list(reversed(users)) # so that game creator is last
    for u in reversed_users:
        redirect_to_state(u, new_function, message_obj)

def redirect_to_state(user, new_function, message_obj=None):
    new_state = new_function.__name__
    if user.state != new_state:
        logging.debug("In redirect_to_state. current_state:{0}, new_state: {1}".format(str(user.state), str(new_state)))
        user.set_state(new_state)
    repeat_state(user, message_obj)


# ================================
# REPEAT STATE
# ================================
def repeat_state(user, message_obj=None):
    state = user.state
    if state is None:
        restart_user(user)
        return
    method = possibles.get(state)
    if not method:
        msg = "⚠️ User {} sent to unknown method state: {}".format(user.chat_id, state)
        report_master(msg)
    else:
        method(user, message_obj)

# ================================
# Initial State
# ================================

def state_INITIAL(p, message_obj=None, **kwargs):
    text_input = message_obj.text
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
                redirect_to_state(p, state_START)
            else:
                msg = '🙈 Non hai inserito la parola magica giusta per iniziare la caccia al tesoro.'
                send_message(p, msg)
        else:
            msg = "Ciao 😀\n" \
                  "C'è una caccia al tesoro in corso ma devi utilizzare il QR code per accedere.\n" \
                  "In alternativa digita /start seguito dalla *password* fornita dagli organizzatori."
            send_message(p, msg)

def state_START(p, message_obj=None, **kwargs):
    text_input = message_obj.text if message_obj else None
    giveInstruction = text_input is None
    if giveInstruction:
        kb = [[ux.BUTTON_START_GAME]]
        send_message(p, ux.MSG_PRESS_TO_START, kb)
    else:
        kb = p.get_keyboard()
        if text_input in utility.flatten(kb):
            if text_input == ux.BUTTON_START_GAME:
                send_message(p, ux.MSG_GO, remove_keyboard=True)
                send_typing_action(p, sleep_time=1)                
                redirect_to_state(p, state_NOME_GRUPPO)
        else:
            send_message(p, ux.MSG_WRONG_INPUT_USE_BUTTONS, kb)
            send_typing_action(p, sleep_time=1)
            repeat_state(p)

# ================================
# Nome Gruppo State
# ================================

def state_NOME_GRUPPO(p, message_obj=None, **kwargs):
    text_input = message_obj.text if message_obj else None
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
            redirect_to_state(p, state_SELFIE_INIZIALE)
        else:
            send_message(p, ux.MSG_WRONG_INPUT_INSERT_TEXT)
            send_typing_action(p, sleep_time=1)
            repeat_state(p)

# ================================
# Selfie Iniziale State
# ================================

def state_SELFIE_INIZIALE(p, message_obj=None, **kwargs):
    photo = message_obj.photo if message_obj else None
    giveInstruction = photo is None
    if giveInstruction:
        send_message(p, ux.MSG_SELFIE_INIZIALE)
    else:
        if photo:
            photo_file_id = photo[-1]['file_id']
            game.appendGroupSelfieFileId(p, photo_file_id)
            send_typing_action(p, sleep_time=1)
            send_message(p, ux.MSG_SELFIE_INIZIALE_OK)            
            if game.send_notification_to_group(p):
                BOT.send_photo(game.HISTORIC_GROUP, photo=photo_file_id, caption='Selfie iniziale {}'.format(game.getGroupName(p)))
            send_message(p, ux.MSG_START_TIME, sleepDelay=True, remove_keyboard=True)
            game.setStartTime(p)
            redirect_to_state(p, state_MISSION_INTRO)
        else:
            send_message(p, ux.MSG_WRONG_INPUT_SEND_PHOTO)
            send_typing_action(p, sleep_time=1)
            repeat_state(p)

# ================================
# INTRO
# ================================

def state_MISSION_INTRO(p, message_obj=None, **kwargs):
    text_input = message_obj.text if message_obj else None
    giveInstruction = text_input is None
    if giveInstruction:
        current_indovinello = game.setNextIndovinello(p)
        indovinello_number = game.completedIndovinelloNumber(p) + 1
        total_indovinelli = game.getTotalIndovinelli(p)
        msg = '*🎳 Missione {}/{}*'.format(indovinello_number, total_indovinelli)
        send_message(p, msg)
        send_typing_action(p, sleep_time=1)
        if 'INTRO_MEDIA' in current_indovinello:
            caption = current_indovinello.get('INTRO_MEDIA_CAPTION',None)
            url_attachment = current_indovinello['INTRO_MEDIA'][0]['url']
            send_media_url(p, url_attachment, caption=caption)
            send_typing_action(p, sleep_time=3)
        msg = current_indovinello['INTRODUZIONE_LOCATION'] # '*Introduzione*: ' + 
        kb = [[ux.BUTTON_CONTINUE]]
        send_message(p, msg, kb)
        p.put()
    else:
        kb = p.get_keyboard()
        if text_input in utility.flatten(kb):
            if text_input == ux.BUTTON_CONTINUE:
                current_indovinello = game.getCurrentIndovinello(p)
                if 'GPS' in current_indovinello:
                    redirect_to_state(p, state_GPS)
                else:
                    redirect_to_state(p, state_INDOVINELLO)
            else:
                assert False
        else:
            send_message(p, ux.MSG_WRONG_INPUT_USE_BUTTONS)            

# ================================
# GPS state
# ================================

def state_GPS(p, message_obj=None, **kwargs):
    location = message_obj.location if message_obj else None
    giveInstruction = location is None
    current_indovinello = game.getCurrentIndovinello(p)
    if giveInstruction:
        goal_position = [float(x) for x in current_indovinello['GPS'].split(',')]
        msg = ux.MSG_GO_TO_PLACE
        kb = [[ux.BUTTON_LOCATION]]
        send_message(p, msg, kb)
        BOT.send_location(p.chat_id, goal_position[0], goal_position[1])
    else:
        if location:            
            goal_position = [float(x) for x in current_indovinello['GPS'].split(',')]
            lat, lon = location['latitude'], location['longitude']
            p.set_location(lat, lon)
            given_position = [lat, lon]
            distance = geoUtils.distance_meters(goal_position, given_position)
            if distance <= params.GPS_TOLERANCE_METERS:
                send_message(p, ux.MSG_GPS_OK, remove_keyboard=True)
                send_typing_action(p, sleep_time=1)
                redirect_to_state(p, state_INDOVINELLO)
            else:
                msg = ux.MSG_TOO_FAR.format(distance)
                send_message(p, msg)
        else:
            send_message(p, ux.MSG_WRONG_INPUT_SEND_LOCATION)

# ================================
# INDOVINELLO state
# ================================
def state_INDOVINELLO(p, message_obj=None, **kwargs):
    text_input = message_obj.text if message_obj else None
    giveInstruction = text_input is None
    current_indovinello = game.getCurrentIndovinello(p)
    if giveInstruction:
        game.set_mission_start_time(p)
        current_indovinello['start_time'] = dtu.nowUtcIsoFormat()
        current_indovinello['wrong_answers'] = []       
        msg = current_indovinello['INDOVINELLO'] 
        if current_indovinello.get('INDIZIO_1',False):
            kb = [['💡 PRIMO INDIZIO']]
            send_message(p, msg, kb)
        else:
            send_message(p, msg, remove_keyboard=True)
        p.put()
    else:
        if text_input:            
            kb = p.get_keyboard()
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
                #correct_answers_upper_word_set = set(utility.flatten([x.split() for x in correct_answers_upper]))
                if text_input.upper() in correct_answers_upper:
                    current_indovinello['end_time'] = dtu.nowUtcIsoFormat()
                    send_message(p, ux.MSG_ANSWER_OK)
                    if 'POST_MESSAGE' in current_indovinello:
                        redirect_to_state(p, state_POST_INDOVINELLO)
                    elif 'GPS' in current_indovinello and not current_indovinello.get('SKIP_SELFIE', False):
                        # only indovinelli with GPS require selfies
                        redirect_to_state(p, state_SELFIE_INDOVINELLO)
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

def state_POST_INDOVINELLO(p, message_obj=None, **kwargs):
    text_input = message_obj.text if message_obj else None
    giveInstruction = text_input is None
    current_indovinello = game.getCurrentIndovinello(p)
    if giveInstruction:
        if 'POST_MEDIA' in current_indovinello:
            caption = current_indovinello.get('POST_MEDIA_CAPTION',None)
            url_attachment = current_indovinello['POST_MEDIA'][0]['url']
            send_media_url(p, url_attachment, caption=caption)
            send_typing_action(p, sleep_time=3)
        msg = current_indovinello['POST_MESSAGE']
        kb = [[ux.BUTTON_CONTINUE]]
        send_message(p, msg, kb)
    else:
        kb = p.get_keyboard()
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

def state_SELFIE_INDOVINELLO(p, message_obj=None, **kwargs):
    photo = message_obj.photo if message_obj else None
    giveInstruction = photo is None
    if giveInstruction:
        send_message(p, ux.MSG_SELFIE_INDOVINELLO, remove_keyboard=True)
    else:
        if photo:
            photo_file_id = photo[-1]['file_id']
            current_indovinello = game.getCurrentIndovinello(p)
            current_indovinello['SELFIE'] = photo_file_id
            if game.manual_validation(p):
                squadra_name = game.getGroupName(p)
                indovinello_number = game.completedIndovinelloNumber(p) + 1
                indovinello_name = current_indovinello['NOME']
                # store a random password to make sure the approval is correct
                # (the team may have restarted the game in the meanwhile):
                approval_signature = utility.randomAlphaNumericString(5)
                current_indovinello['sign'] = approval_signature
                send_message(p, ux.MSG_WAIT_SELFIE_APPROVAL)
                kb_markup = telegram.InlineKeyboardMarkup(
                    [
                        [
                            ux.BUTTON_SI_CALLBACK(json.dumps({'ok': True, 'uid':p.get_id(), 'sign': approval_signature})),
                            ux.BUTTON_NO_CALLBACK(json.dumps({'ok': False, 'uid': p.get_id(), 'sign': approval_signature})),
                        ]
                    ]
                )
                caption = 'Selfie indovinello {} squadra {} per indovinello {}'.format(indovinello_number, squadra_name, indovinello_name)
                logging.debug('Sending photo to validator')
                BOT.send_photo(game.get_validator_chat_id(p), photo=photo_file_id, caption=caption, reply_markup=kb_markup)
            else:
                approve_selfie_indovinello(p, approved=True, signature=None)
            p.put()
        else:
            send_message(p, ux.MSG_WRONG_INPUT_SEND_PHOTO)

def approve_selfie_indovinello(p, approved, signature):
    # need to double check if team is still waiting for approval
    # (e.g., could have restarted the game, or validator pressed approve twice in a row)
    current_indovinello = game.getCurrentIndovinello(p)
    if current_indovinello is None or (game.manual_validation(p) and signature != current_indovinello['sign']):
        return False
    if approved:
        send_message(p, ux.MSG_SELFIE_INDOVINELLO_OK)
        photo_file_id = current_indovinello['SELFIE']
        if game.send_notification_to_group(p):
            squadra_name = game.getGroupName(p)
            indovinello_number = game.completedIndovinelloNumber(p) + 1
            indovinello_name = current_indovinello['NOME']
            caption = 'Selfie indovinello {} squadra {} per indovinello {}'.format(indovinello_number, squadra_name, indovinello_name)
            BOT.send_photo(game.HISTORIC_GROUP, photo=photo_file_id, caption=caption)
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
        send_typing_action(p, sleep_time=1)
        send_message(p, ux.MSG_CONGRATS_PRE_SURVEY)
        send_typing_action(p, sleep_time=1)
        send_message(p, ux.MSG_SURVEY_INTRO)
        send_typing_action(p, sleep_time=1)
        redirect_to_state(p, state_SURVEY)
    else:        
        game.set_mission_end_time(p)
        redirect_to_state(p, state_MISSION_INTRO)


# ================================
# Survey State
# ================================

def state_SURVEY(p, message_obj=None, **kwargs):
    text_input = message_obj.text if message_obj else None
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
        kb = p.get_keyboard()
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
                redirect_to_state(p, state_EMAIL)
            else:
                p.put()
                repeat_state(p)
        else:
            if question_type_open:
                send_message(p, ux.MSG_WRONG_INPUT_INSERT_TEXT_OR_BUTTONS)
            else:
                send_message(p, ux.MSG_WRONG_INPUT_USE_BUTTONS)

# ================================
# Survey State
# ================================

def state_EMAIL(p, message_obj=None, **kwargs):
    text_input = message_obj.text if message_obj else None
    giveInstruction = text_input is None
    if giveInstruction:
        kb = [[ux.BUTTON_SKIP_EMAIL]]
        send_message(p, ux.MSG_EMAIL, kb)
    else:
        if text_input:
            if text_input == ux.BUTTON_SKIP_EMAIL:
                redirect_to_state(p, state_END)
            else: 
                if utility.check_email(text_input):                
                    game.setEmail(p, text_input)
                    redirect_to_state(p, state_END)
                else:
                    send_message(p, ux.MSG_EMAIL_WRONG)
        else:
            send_message(p, ux.MSG_WRONG_INPUT_USE_BUTTONS)

# ================================
# Final State
# ================================

def state_END(p, message_obj=None, **kwargs):
    text_input = message_obj.text if message_obj else None
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

def deal_with_callback_query(callback_query):
    callback_query_data = json.loads(callback_query.data)
    approved = callback_query_data['ok']
    user_id = callback_query_data['uid']
    approval_signature = callback_query_data['sign']
    p = ndb_person.get_person_by_id(user_id)
    squadra_name = game.getGroupName(p)
    callback_query_id = callback_query.id
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id
    BOT.delete_message(chat_id, message_id)
    validation_success = approve_selfie_indovinello(p, approved, signature=approval_signature)
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
        if text_input == '/update':
            key.reload_config()
            send_message(p, "Reloaded config table")
            return True
        if text_input == '/debug':
            #send_message(p, game.debugTmpVariables(p), markdown=False)
            send_text_document(p, 'tmp_vars.json', game.debugTmpVariables(p))
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
            broadcast(p, msg)
            return True
        if text_input.startswith('/testBroadcast '):
            text = text_input.split(' ', 1)[1]
            msg = '🔔 *Messaggio da hiSTORIC* 🔔\n\n' + text                            
            broadcast(p, msg, exit_game=True, test=True)
            return True        
        if text_input.startswith('/resetBroadcast '):
            text = text_input.split(' ', 1)[1]
            msg = '🔔 *Messaggio da hiSTORIC* 🔔\n\n' + text
            logging.debug("Starting to broadcast and reset players" + msg)
            broadcast(p, msg, exit_game=True)
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
        if text_input.startswith('/resetUser '):
            p_id = ' '.join(text_input.split(' ')[1:])
            p = Person.get_by_id(p_id)
            if p:
                make_payer_exit_game(p, message='Reset')
                msg_admin = 'User resetted: {}'.format(p.get_first_last_username())
                tell_admin(msg_admin)                
            else:
                msg_admin = 'No user found: {}'.format(p_id)
                tell_admin(msg_admin)
            return True
        if text_input == '/reset_all_users':
            reset_all_users()
            return True
    return False

def deal_with_tester_commands(p, message_obj):
    text_input = message_obj.text
    # logging.debug("In deal_with_tester_commands with user:{} istester:{}".format(p.get_id(), p.is_tester()))
    if p.is_tester():
        if text_input == '/stats':
            stats_list_str = '\n'.join(["/stats_{}".format(k) for k in key.HUNTS.keys()])
            msg = "Available stats:\n{}".format(stats_list_str)
            send_message(p, msg, markdown=False)
            return True
        if text_input.startswith('/stats_'):
            hung_pw = text_input.split('_', 1)[1]
            if hung_pw in key.HUNTS:
                msg = 'Stats:\n\n{}'.format(ndb_person.get_people_on_hunt_stats(hung_pw))
                send_message(p, msg, markdown=False)
            else:
                msg = 'Wrong stats command'
                send_message(p, msg, markdown=False)
            return True
        return False


def deal_with_universal_command(p, message_obj):
    text_input = message_obj.text
    if text_input.startswith('/start'):
        state_INITIAL(p, message_obj)
        return True
    if text_input == '/exit':
        make_payer_exit_game(p, ux.MSG_EXITED_FROM_GAME)
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

    text = message_obj.text
    if text:
        text_input = message_obj.text        
        logging.debug('Message from @{} in state {} with text {}'.format(chat_id, p.state, text_input))
        if WORK_IN_PROGRESS and not p.is_tester():
            send_message(p, ux.MSG_WORK_IN_PROGRESS)    
            return
        if deal_with_admin_commands(p, message_obj):
            return
        if deal_with_universal_command(p, message_obj):
            return
        if deal_with_tester_commands(p, message_obj):
            return
    logging.debug("Sending {} to state {} with input message_obj {}".format(p.get_first_name(), p.state, message_obj))
    repeat_state(p, message_obj=message_obj)

possibles = globals().copy()
possibles.update(locals())