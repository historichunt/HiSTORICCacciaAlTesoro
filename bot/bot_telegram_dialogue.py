import logging
import telegram
import json
import random
from bot import bot_telegram, utility, ndb_person, bot_ux, game, geoUtils, params, settings
from bot import date_time_util as dtu
from bot.bot_telegram import BOT, send_message, send_location, send_typing_action, \
    report_admins, send_text_document, send_media_url, \
    broadcast, report_admins, reset_all_users
from bot import params
from bot.utility import flatten, get_str_param_boolean
from bot.ndb_person import Person
from bot.ndb_utils import client_context

# ================================
# RESTART
# ================================
def restart_multi(users, **kwargs):
    for u in users:
        redirect_to_state(u, state_INITIAL, **kwargs)

def restart(user, **kwargs):
    redirect_to_state(user, state_INITIAL, **kwargs)

# ================================
# REDIRECT TO STATE
# ================================
def redirect_to_state(user, new_function, message_obj=None, **kwargs):
    new_state = new_function.__name__
    if user.state != new_state:
        logging.debug("In redirect_to_state. current_state:{0}, new_state: {1}".format(str(user.state), str(new_state)))
        user.set_state(new_state)
    repeat_state(user, message_obj, **kwargs)

def redirect_to_state_multi(users, new_function, message_obj=None, **kwargs):
    reversed_users = list(reversed(users)) # so that game creator is last
    for u in reversed_users:
        redirect_to_state(u, new_function, message_obj, **kwargs)


# ================================
# REPEAT STATE
# ================================
def repeat_state(user, message_obj=None, **kwargs):
    state = user.state
    if state is None:
        restart(user)
        return
    method = possibles.get(state)
    if not method:
        msg = "⚠️ User {} sent to unknown method state: {}".format(user.chat_id, state)
        report_admins(msg)
        restart(user)
    else:
        method(user, message_obj, **kwargs)

# ================================
# Initial State
# ================================

def state_INITIAL(p, message_obj=None, silent=False, **kwargs):    
    if message_obj is None:
        if not silent:
            switch_language_button = p.ux().BUTTON_ENGLISH if p.language=='IT' else p.ux().BUTTON_ITALIAN
            kb = [
                [switch_language_button],
                [p.ux().BUTTON_INFO]
            ]     
            if p.is_global_admin() or p.is_hunt_admin():
                kb[-1].append(p.ux().BUTTON_ADMIN)       
            send_message(p, p.ux().MSG_WELCOME_START, kb)
    else: 
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input:            
            if text_input in flatten(kb):
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
                elif text_input == p.ux().BUTTON_ADMIN:
                    redirect_to_state(p, state_ADMIN)
                return
            if text_input.lower() == '/start':
                repeat_state(p)
                return
            if text_input.lower().startswith('/start '):
                hunt_password = text_input.lower().split()[1]
            else: 
                hunt_password = text_input.lower()
            if hunt_password in game.HUNTS_PW:   
                if (
                    game.HUNTS_PW[hunt_password].get('Active', False) 
                    or 
                    game.is_person_hunt_admin(p, hunt_password)
                ):
                    game.reset_game(p, hunt_password)
                    # game_name = game.HUNTS_PW[hunt_password]['Name']
                    # send_message(p, p.ux().MSG_WELCOME.format(game_name), remove_keyboard=True)
                    hunt_settings = p.tmp_variables['SETTINGS']
                    skip_instructions = get_str_param_boolean(hunt_settings, 'SKIP_INSTRUCTIONS')
                    if not skip_instructions:
                        redirect_to_state(p, state_INSTRUCTIONS)
                    else:
                        # start the hunt
                        redirect_to_state(p, state_MISSION_INTRO)
                else:
                    send_message(p, p.ux().MSG_HUNT_DISABLED)
            else:
                send_message(p, p.ux().MSG_WRONG_PASSWORD)
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS, kb)


# ================================
# Admin State
# ================================

def state_ADMIN(p, message_obj=None, **kwargs):    
    if message_obj is None:
        kb = [
            [p.ux().BUTTON_BACK]
        ]
        if p.is_global_admin():
            kb.extend([
                [p.ux().BUTTON_VERSION, p.ux().BUTTON_UPDATE_HUNTS_CONFIG],
            ])
        if p.is_hunt_admin():
            hunts_dict_list = game.get_hunts_that_person_admins(p)
            hunt_names_buttons = sorted([[d['Name']] for d in hunts_dict_list])
            kb.extend(hunt_names_buttons)
        kb.append([p.ux().BUTTON_BACK])
        send_message(p, p.ux().MSG_ADMIN, kb)
    else: 
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input:
            if text_input in flatten(kb):
                if text_input == p.ux().BUTTON_VERSION:
                    msg = p.ux().MSG_VERSION.format(settings.APP_VERSION)
                    send_message(p, msg)
                elif text_input == p.ux().BUTTON_BACK:
                    redirect_to_state(p, state_INITIAL)
                elif text_input == p.ux().BUTTON_UPDATE_HUNTS_CONFIG:
                    game.reload_config_hunt()
                    send_message(p, p.ux().MSG_RELOADED_HUNTS_CONFIG)
                else:
                    p.set_tmp_variable('ADMIN_HUNT_NAME', text_input)
                    redirect_to_state(p, state_HUNT_ADMIN)
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS, kb)


# ================================
# Hunt Admin State
# ================================

def state_HUNT_ADMIN(p, message_obj=None, **kwargs):    
    hunt_name = p.get_tmp_variable('ADMIN_HUNT_NAME')
    hunt_pw = game.HUNTS_NAME[hunt_name]['Password']
    if message_obj is None:
        kb = [
            [p.ux().BUTTON_STATS],
            [p.ux().BUTTON_TERMINATE],
            [p.ux().BUTTON_BACK]
        ]
        msg = p.ux().MSG_HUNT_ADMIN_SELECTED.format(hunt_name)
        send_message(p, msg, kb)
    else: 
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input:
            if text_input in flatten(kb):
                if text_input == p.ux().BUTTON_BACK:
                    redirect_to_state(p, state_ADMIN)
                elif text_input == p.ux().BUTTON_STATS:
                    hunt_stats = ndb_person.get_people_on_hunt_stats(hunt_pw)
                    if hunt_stats:
                        msg = 'Stats:\n\n{}'.format(hunt_stats)
                    else:
                        msg = 'Nessuna squadra iscritta'
                    send_message(p, msg, markdown=False)
                elif text_input == p.ux().BUTTON_TERMINATE:
                    redirect_to_state(p, state_TERMINATE_HUNT_CONFIRM)
            else:
                send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS)     
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS, kb)

# ================================
# Hunt Admin State
# ================================

def state_TERMINATE_HUNT_CONFIRM(p, message_obj=None, **kwargs):    
    hunt_name = p.get_tmp_variable('ADMIN_HUNT_NAME')
    hunt_pw = game.HUNTS_NAME[hunt_name]['Password']
    if message_obj is None:
        kb = [
            [p.ux().BUTTON_YES],
            [p.ux().BUTTON_ANNULLA],
        ]
        msg = p.ux().MSG_HUNT_TERMINATE_CONFIRM.format(hunt_name)
        send_message(p, msg, kb)
    else: 
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input:
            if text_input in flatten(kb):
                if text_input == p.ux().BUTTON_ANNULLA:
                    redirect_to_state(p, state_HUNT_ADMIN)
                elif text_input == p.ux().BUTTON_YES:
                    qry = Person.query(Person.current_hunt==hunt_pw)
                    remaining_people = qry.fetch()
                    if remaining_people:                                                            
                        for u in remaining_people:                     
                            if not p.tmp_variables.get('FINISHED', False):                   
                                game.exit_game(u, save_data=True, reset_current_hunt=True)
                                restart(u, silent=True)
                            else:
                                # people who have completed needs to be informed too
                                # we already saved the data but current hunt wasn't reset
                                u.reset_current_hunt()
                            reset_hunt_after_completion = get_str_param_boolean(u.tmp_variables['SETTINGS'], 'RESET_HUNT_AFTER_COMPLETION')
                            terminate_message_key = 'MSG_HUNT_TERMINATED_RESET_ON' if reset_hunt_after_completion else 'MSG_HUNT_TERMINATED_RESET_OFF'
                            send_message(u, p.ux().get_var(terminate_message_key), remove_keyboard=True, sleep=True)
                    msg = "Mandato messagio di termine a {} squadre.".format(len(remaining_people))
                    send_message(p, msg, remove_keyboard=True)
                    send_typing_action(p, sleep_time=1)
                    restart(p)
            else:
                send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS)     
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS, kb)    


# ================================
# Intro - Instructions
# ================================

def state_INSTRUCTIONS(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    instructions = p.tmp_variables['INSTRUCTIONS']
    if kwargs.get('next_step', False):
        game.increase_intro_completed(p)
    completed = instructions['COMPLETED']
    steps = instructions['STEPS']
    if len(steps) == completed:
        # start the hunt
        redirect_to_state(p, state_MISSION_INTRO)
        return
    current_step = steps[completed]
    input_type = current_step.get('Input_Type','')
    if give_instruction:                
        msg = current_step.get('Text','')
        media = current_step.get('Media', '')
        if input_type.startswith('BUTTON_'):
            kb = [[p.ux().BUTTON_UNDERSTOOD]] \
                if input_type == 'BUTTON_UNDERSTOOD' \
                else [[p.ux().BUTTON_START_GAME]]             
            if media:
                url_attachment = media[0]['url']
                send_media_url(p, url_attachment, kb, caption=msg)
            else:
                send_message(p, msg, kb)
        else:
            if media:
                url_attachment = media[0]['url']
                send_media_url(p, url_attachment, caption=msg, remove_keyboard=True)
            else:
                send_message(p, msg, remove_keyboard=True)        
            if input_type == '':
                send_typing_action(p, sleep_time=1)
                repeat_state(p, next_step=True)        
    else:
        text_input = message_obj.text                
        if input_type == 'EMAIL':
            if utility.check_email(text_input):                
                game.set_email(p, text_input)
                send_typing_action(p, sleep_time=1)
                repeat_state(p, next_step=True)
            else:
                send_message(p, p.ux().MSG_EMAIL_WRONG)
        elif input_type == 'TEAM_NAME':
            if text_input:
                if len(text_input) > params.MAX_TEAM_NAME_LENGTH:
                    send_message(p, p.ux().MSG_GROUP_NAME_TOO_LONG.format(params.MAX_TEAM_NAME_LENGTH))
                    return
                if not utility.hasOnlyLettersAndSpaces(text_input):
                    send_message(p, p.ux().MSG_GROUP_NAME_INVALID)
                    return
                game.set_group_name(p, text_input)
                # send_message(p, p.ux().MSG_GROUP_NAME_OK.format(text_input))
                if game.send_notification_to_group(p):
                    send_message(settings.HISTORIC_NOTIFICHE_GROUP_CHAT_ID, "Nuova squadra registrata: {}".format(text_input))
                send_typing_action(p, sleep_time=1)
                repeat_state(p, next_step=True)
            else:
                send_message(p, p.ux().MSG_WRONG_INPUT_INSERT_TEXT)
        elif input_type.startswith('BUTTON_'):
            # BUTTON_UNDERSTOOD, BUTTON_START_GAME
            kb = p.get_keyboard()
            if text_input in flatten(kb):
                send_typing_action(p, sleep_time=1)
                repeat_state(p, next_step=True)
            else:            
                send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS)                  
        elif input_type == 'TEST_POSITION':
            location = message_obj.location
            if location:            
                send_typing_action(p, sleep_time=1)
                repeat_state(p, next_step=True)
            else:
                send_message(p, p.ux().MSG_WRONG_INPUT_SEND_LOCATION)
        elif input_type == 'TEST_PHOTO':     
            photo = message_obj.photo       
            if photo is not None and len(photo)>0:
                photo_file_id = photo[-1]['file_id']
                game.append_group_media_input_file_id(p, photo_file_id)
                send_typing_action(p, sleep_time=1)                            
                if game.send_notification_to_group(p):
                    BOT.send_photo(settings.HISTORIC_NOTIFICHE_GROUP_CHAT_ID, photo=photo_file_id, caption='Selfie iniziale {}'.format(game.get_group_name(p)))
                send_typing_action(p, sleep_time=1)
                repeat_state(p, next_step=True)
            else:
                send_message(p, p.ux().MSG_WRONG_INPUT_SEND_PHOTO)
        elif input_type == 'TEST_VOICE':
            voice = message_obj.voice
            if voice is not None:
                voice_file_id = voice['file_id']
                game.append_group_media_input_file_id(p, voice_file_id)
                send_typing_action(p, sleep_time=1)
                repeat_state(p, next_step=True)
            else:
                send_message(p, p.ux().MSG_WRONG_INPUT_SEND_VOICE)

# ================================
# MISSION INSTRUCTIONS
# ================================

def state_MISSION_INTRO(p, message_obj=None, **kwargs):        
    give_instruction = message_obj is None
    if give_instruction:
        current_indovinello = game.setNextIndovinello(p)        
        indovinello_number = game.completed_indovinello_number(p) + 1
        if indovinello_number==1:
            # first one
            send_message(p, p.ux().MSG_START_TIME, remove_keyboard=True)            
            game.set_game_start_time(p)
            send_typing_action(p, sleep_time=1)        
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
        if text_input in flatten(kb):
            if text_input in bot_ux.BUTTON_CONTINUE_MULTI(p.language):
                current_indovinello = game.getCurrentIndovinello(p)
                redirect_to_state(p, state_GPS)
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
            # if there is no solution required go to required_input (photo or voice)
            assert all(x in current_indovinello for x in ['INPUT_INSTRUCTIONS', 'INPUT_TYPE'])
            redirect_to_state(p, state_MEDIA_INPUT_MISSION)
    else:
        text_input = message_obj.text
        if text_input:            
            kb = p.get_keyboard()
            if text_input in flatten(kb):
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
                correct_answers_upper = [x.strip() for x in current_indovinello['SOLUZIONI'].upper().split(',')]
                #correct_answers_upper_word_set = set(flatten([x.split() for x in correct_answers_upper]))
                if text_input.upper() in correct_answers_upper:
                    game.set_end_mission_time(p)
                    if not send_post_message(p, current_indovinello):
                        send_message(p, bot_ux.MSG_ANSWER_OK(p.language), remove_keyboard=True)
                        send_typing_action(p, sleep_time=1)                    
                    if 'INPUT_INSTRUCTIONS' in current_indovinello:
                        # only missioni with GPS require selfies
                        redirect_to_state(p, state_MEDIA_INPUT_MISSION)
                    else:
                        redirect_to_state(p, state_COMPLETE_MISSION)
                # elif utility.answer_is_almost_correct(text_input.upper(), correct_answers_upper_word_set):
                #     send_message(p, p.ux().MSG_ANSWER_ALMOST)
                else:
                    give_penalty = current_indovinello.get('PENALTY',False)
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
    input_type = current_indovinello['INPUT_TYPE'] # PHOTO, VOICE
    assert input_type in ['PHOTO','VOICE'] # missing video
    if give_instruction:
        msg = current_indovinello['INPUT_INSTRUCTIONS']
        send_message(p, msg, remove_keyboard=True)
    else:
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
                BOT.send_photo(settings.HISTORIC_NOTIFICHE_GROUP_CHAT_ID, photo=file_id, caption=caption)
            else: #elif input_type=='VOICE':
                caption = 'Registrazione indovinello {} squadra {} per indovinello {}'.format(indovinello_number, squadra_name, indovinello_name)
                BOT.send_voice(settings.HISTORIC_NOTIFICHE_GROUP_CHAT_ID, voice=file_id, caption=caption)
        game.append_group_media_input_file_id(p, file_id)        
        if 'POST_INPUT' in current_indovinello:                        
            msg = current_indovinello['POST_INPUT']
            send_message(p, msg, remove_keyboard=True)
            send_typing_action(p, sleep_time=1)
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
    input_type = current_indovinello['INPUT_TYPE'] # PHOTO, VOICE
    if give_instruction:
        msg = p.ux().MSG_CONFIRM_PHOTO_INPUT if input_type == 'PHOTO' else p.ux().MSG_CONFIRM_RECORDING_INPUT
        kb = [[p.ux().BUTTON_YES, p.ux().BUTTON_NO]]
        send_message(p, msg, kb)
    else:
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input in flatten(kb):
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
        survery_time = (
            game.remainingIndovinelloNumber(p) == 0 or (
                params.JUMP_TO_SURVEY_AFTER and
                game.completed_indovinello_number(p) == params.JUMP_TO_SURVEY_AFTER
            )
        )
        game.set_mission_end_time(p)
        if survery_time:            
            game.set_game_end_time(p, finished=True)
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
        if text_input in flatten(kb):
            if text_input == p.ux().BUTTON_NEXT_MISSION:
                redirect_to_state(p, state_MISSION_INTRO)
            elif text_input == p.ux().BUTTON_END:
                send_message(p, p.ux().MSG_TIME_STOP, remove_keyboard=True)
                send_typing_action(p, sleep_time=1)
                send_message(p, p.ux().MSG_CONGRATS_PRE_SURVEY)
                send_typing_action(p, sleep_time=1)                
                settings = p.tmp_variables['SETTINGS']
                skip_survey = get_str_param_boolean(settings, 'SKIP_SURVEY')
                # saving data in airtable
                game.set_elapsed_and_penalty_and_compute_total(p)
                game.save_game_data_in_airtable(p)
                if not skip_survey:
                    redirect_to_state(p, state_SURVEY)
                else:
                    # end game
                    redirect_to_state(p, state_END)
        else:
            send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS)        

# ================================
# Survey State
# ================================

def state_SURVEY(p, message_obj=None, **kwargs):
    give_instruction = message_obj is None
    if give_instruction:        
        current_question = game.set_next_survey_question(p)
        questions_number = game.get_num_completed_survey_questions(p) + 1
        if questions_number == 1:
            send_message(p, p.ux().MSG_SURVEY_INTRO)
            send_typing_action(p, sleep_time=1)
        total_questions = game.get_tot_survey_questions(p)
        msg = '*Domanda {}/{}*: {}'.format(questions_number, total_questions, current_question['DOMANDA'])
        risposte = [x.strip() for x in current_question['RISPOSTE'].split(',')]
        kb = [risposte]
        send_message(p, msg, kb)
    else:
        text_input = message_obj.text
        kb = p.get_keyboard()
        current_question = game.get_current_survey_question(p)
        if current_question is None:
            return
            # when question has been set to complete 
            # and at the same time the user presses a button            
        question_type_open = current_question['TYPE'] == 'Open'
        if text_input:
            if text_input in flatten(kb):
                answer = '' if question_type_open else text_input
                game.set_current_survey_question_as_completed(p, answer)
            elif question_type_open:
                game.set_current_survey_question_as_completed(p, text_input)
            else:
                send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS)
                return
            if game.get_remaing_survey_questions_number(p) == 0:
                # end survey -> save survey data in airtable
                game.save_survey_data_in_airtable(p)
                redirect_to_state(p, state_END)
            else:
                p.put()
                repeat_state(p)
        else:
            if question_type_open:
                send_message(p, p.ux().MSG_WRONG_INPUT_INSERT_TEXT_OR_BUTTONS)
            else:
                send_message(p, p.ux().MSG_WRONG_INPUT_USE_BUTTONS)

# ================================
# Final State
# ================================

def state_END(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    hunt_settings = p.tmp_variables['SETTINGS']
    reset_hunt_after_completion = get_str_param_boolean(hunt_settings, 'RESET_HUNT_AFTER_COMPLETION')
    if give_instruction:        
        penalty_hms, total_hms_game, ellapsed_hms_game, \
            total_hms_missions, ellapsed_hms_missions = game.get_elapsed_and_penalty_and_total_hms(p)
        msg = p.ux().MSG_END.format(penalty_hms, \
            total_hms_game, ellapsed_hms_game, total_hms_missions, ellapsed_hms_missions)        
        send_message(p, msg, remove_keyboard=True)
        if game.send_notification_to_group(p):
            msg_group = p.ux().MSG_END_NOTIFICATION.format(game.get_group_name(p), penalty_hms, \
                total_hms_game, ellapsed_hms_game, total_hms_missions, ellapsed_hms_missions)
            send_message(settings.HISTORIC_NOTIFICHE_GROUP_CHAT_ID, msg_group)                        
        final_message_key = 'MSG_FINAL_RESET_ON' if reset_hunt_after_completion else 'MSG_FINAL_RESET_OFF'
        send_message(p, p.ux().get_var(final_message_key))     
        game.exit_game(p, save_data=True, reset_current_hunt=reset_hunt_after_completion)   
        if reset_hunt_after_completion:
            restart(p, silent=True)        
    else:
        # thisi only happens if RESET_HUNT_AFTER_COMPLETION is False:
        # checking reset_hunt flag to prevent msg to be shown 
        # in case of double click on button on previous state
        if not reset_hunt_after_completion:        
            # we need to tell them that we will let them know when the games is over
            msg = p.ux().MSG_HUNT_NOT_TERMINATED
            send_message(p, msg)        
        


## +++++ END OF STATES +++++ ###

def deal_with_callback_query(callback_query):
    callback_query_data = json.loads(callback_query.data)
    approved = callback_query_data['ok']
    user_id = callback_query_data['uid']
    approval_signature = callback_query_data['sign']
    p = ndb_person.get_person_by_id(user_id)
    squadra_name = game.get_group_name(p)
    callback_query_id = callback_query.id
    if squadra_name is None:
        validation_success = False
    else:        
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
        answer = "Problema di validazione. La squadra {} ha ricomnciato o terminato il gioco " \
                 "o l'approvazione è stata mandata più volte".format(squadra_name)
    BOT.answer_callback_query(callback_query_id, answer)

# ================================
# ADMIN COMMANDS
# ================================

def deal_with_admin_commands(p, message_obj):
    text_input = message_obj.text
    if p.is_error_reporter():
        if text_input == '/debug':
            #send_message(p, game.debug_tmp_vars(p), markdown=False)
            send_text_document(p, 'tmp_vars.json', game.debug_tmp_vars(p))
            return True
        if text_input == '/version':
            msg = f'{settings.ENV_VERSION} {settings.APP_VERSION}'
            send_message(p, msg)
            return True
        if text_input == '/test_inline_kb':
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
                report_admins(msg_admin)
            else:
                msg_admin = 'Problems sending message to {}'.format(p.get_first_last_username())
                report_admins(msg_admin)
            return True
        if text_input.startswith('/restartUser '):
            p_id = ' '.join(text_input.split(' ')[1:])
            p = Person.get_by_id(p_id)
            if p:
                if game.user_in_game(p):
                    game.exit_game(p, save_data=False, reset_current_hunt=True)
                    send_message(p, p.ux().MSG_EXITED_FROM_GAME, remove_keyboard=True)
                restart(p)
                msg_admin = 'User restarted: {}'.format(p.get_first_last_username())
                report_admins(msg_admin)                
            else:
                msg_admin = 'No user found: {}'.format(p_id)
                report_admins(msg_admin)
            return True
        if text_input == '/remove_keyboard_from_notification_group':
            bot_telegram.remove_keyboard_from_notification_group()
            return True
        if text_input == '/reset_all_users':            
            reset_all_users(message=None) #message=p.ux().MSG_THANKS_FOR_PARTECIPATING
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
            game.exit_game(p, save_data=False, reset_current_hunt=True)
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
        send_message(p, p.ux().MSG_SUPPORT)
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
        report_admins('New user: {}'.format(p.get_first_last_username()))
    else:
        _, was_disabled = p.update_info(name, last_name, username)
        if was_disabled:
            msg = "Bot riattivato!"
            send_message(p, msg)

    if message_obj.forward_from and not p.is_admin_current_hunt():
        send_message(p, p.ux().MSG_NO_FORWARDING_ALLOWED)
        return

    text = message_obj.text
    if text:
        text_input = message_obj.text        
        logging.debug('Message from @{} in state {} with text {}'.format(chat_id, p.state, text_input))
        if deal_with_admin_commands(p, message_obj):
            return
        if deal_with_universal_command(p, message_obj):
            return
    logging.debug("Sending {} to state {} with input message_obj {}".format(p.get_first_name(), p.state, message_obj))
    repeat_state(p, message_obj=message_obj)

possibles = globals().copy()
possibles.update(locals())