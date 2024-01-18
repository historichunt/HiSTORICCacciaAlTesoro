import logging
import telegram
import json
import random
import asyncio
from historic.config import params, settings
from historic.bot import airtable_utils, utility, ndb_person, bot_ui, game, geo_utils
from historic.bot import date_time_util as dtu
from historic.bot.bot_telegram import BOT, delete_commands, get_commands, get_menu, remove_menu, send_message, send_location, send_typing_action, \
    report_admins, send_text_document, send_media_url, \
    broadcast, reset_all_users, report_location_admin, set_commands, set_menu, get_photo_url_from_telegram, send_sticker_data
from historic.config import params
from historic.bot.utility import flatten, get_str_param_boolean, make_2d_array
from historic.bot.ndb_person import Person
from historic.routing.api import api_google
from historic.bot.main_exception import exception_reporter

# ================================
# RESTART
# ================================
async def restart_multi(users, **kwargs):
    for u in users:
        await redirect_to_state(u, state_INITIAL, **kwargs)

async def restart(user, **kwargs):
    # user.reset_tmp_variables()    
    await redirect_to_state(user, state_INITIAL, **kwargs)

# ================================
# REDIRECT TO STATE
# ================================
async def redirect_to_state(user, new_function, message_obj=None, **kwargs):
    new_state = new_function.__name__
    if user.state != new_state:
        logging.debug("In redirect_to_state. current_state:{0}, new_state: {1}".format(str(user.state), str(new_state)))
        user.set_state(new_state)
    await repeat_state(user, message_obj, **kwargs)

async def redirect_to_state_multi(users, new_function, message_obj=None, **kwargs):
    reversed_users = list(reversed(users)) # so that game creator is last
    for u in reversed_users:
        await redirect_to_state(u, new_function, message_obj, **kwargs)


# ================================
# REPEAT STATE
# ================================
async def repeat_state(user, message_obj=None, **kwargs):
    state = user.state
    if state is None:
        await restart(user)
        return
    method = possibles.get(state)
    if not method:
        msg = "⚠️ User {} sent to unknown method state: {}".format(user.chat_id, state)
        await report_admins(msg)
        await restart(user)
    else:
        await method(user, message_obj, **kwargs)

# ================================
# Initial State
# ================================

async def state_INITIAL(p, message_obj=None, **kwargs):    
    if message_obj is None:
        kb = [
            [p.ui().BUTTON_START_HUNT],
            [p.ui().BUTTON_SWITCH_LANGUAGE],
            [p.ui().BUTTON_INFO]
        ]     
        if p.is_global_admin() or p.is_hunt_admin():
            kb[-1].append(p.ui().BUTTON_ADMIN)       
        await set_commands(p) # refresh commands in menu
        await send_message(p, p.ui().MSG_WELCOME, kb)
    else: 
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input:            
            if text_input in flatten(kb):
                if text_input == p.ui().BUTTON_START_HUNT:
                    await redirect_to_state(p, state_ASK_GPS_TO_LIST_HUNTS)
                elif text_input == p.ui().BUTTON_INFO:
                    await send_message(p, p.ui().MSG_HISTORIC_INFO, remove_keyboard=True)
                    await send_typing_action(p, sleep_time=5)
                    await repeat_state(p)
                elif text_input == p.ui().BUTTON_SWITCH_LANGUAGE:
                    await redirect_to_state(p, state_CHANGE_LANGUAGE)
                elif text_input == p.ui().BUTTON_ADMIN:
                    await redirect_to_state(p, state_ADMIN)
                return
            if text_input.lower() == '/start':
                await repeat_state(p)
                return
            if text_input.lower().startswith('/start '):
                hunt_password = text_input.lower().split()[1]
            else: 
                hunt_password = text_input.lower()
            correct_password = await access_hunt_via_password(p, hunt_password, send_msg_if_wrong_pw=False)
            if not correct_password:
                await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS, kb)    
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS, kb)


async def access_hunt_via_password(p, hunt_password, send_msg_if_wrong_pw):
    if hunt_password in game.HUNTS_PW:   
        if (
            game.HUNTS_PW[hunt_password].get('Active', False) 
            or game.is_person_hunt_admin(p, hunt_password)
        ):
            p.set_tmp_variable('HUNT_PW', hunt_password)
            check_location = game.HUNTS_PW[hunt_password].get('GPS', False)             
            if check_location == False:
                await redirect_to_state(p, state_CHECK_LANGUAGE_AND_START_HUNT)            
            else:
                await redirect_to_state(p, state_ASK_GPS_TO_START_HUNT)                
            return True
        else:
            if send_msg_if_wrong_pw:
                await send_message(p, p.ui().MSG_HUNT_DISABLED)
                await send_typing_action(p, 1)
                await repeat_state(p)
            return False
    else:
        if send_msg_if_wrong_pw:
            await send_message(p, p.ui().MSG_WRONG_PASSWORD)
            await send_typing_action(p, 1)
            await repeat_state(p)
        return False

# ================================
# Change Language State
# ================================

async def state_CHANGE_LANGUAGE(p, message_obj=None, **kwargs):    
    if message_obj is None:
        buttons_languages = [
            p.ui().get_var(f'BUTTON_SWITCH_{l}')
            for l in params.LANGUAGES
            if l != p.language
        ]
        kb = [[b] for b in  buttons_languages]
        kb.append([p.ui().BUTTON_BACK])
        await send_message(p, p.ui().MSG_CHANGE_LANGUAGE, kb)
    else: 
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input:            
            if text_input in flatten(kb):
                if text_input == p.ui().BUTTON_BACK:
                    await redirect_to_state(p, state_INITIAL)
                else:
                    for l in params.LANGUAGES:
                        if text_input == p.ui().get_var(f'BUTTON_SWITCH_{l}'):
                            p.set_language(l)
                            await send_message(p, p.ui().MSG_LANGUAGE_SWITCHED)
                            await send_typing_action(p, sleep_time=1)                    
                            await redirect_to_state(p, state_INITIAL)
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS, kb)

# ================================
# Admin State
# ================================

async def state_ADMIN(p, message_obj=None, **kwargs):    
    if message_obj is None:
        kb = [
            [p.ui().BUTTON_BACK]
        ]
        if p.is_global_admin():
            kb.extend([
                [p.ui().BUTTON_VERSION, p.ui().BUTTON_UPDATE_HUNTS_CONFIG],
            ])
        if p.is_hunt_admin():
            hunts_dict_list = game.get_hunts_that_person_admins(p)
            hunt_names_buttons = sorted([[d['Name']] for d in hunts_dict_list])
            kb.extend(hunt_names_buttons)
        if len(kb)>3:
            kb.append([p.ui().BUTTON_BACK])
        await send_message(p, p.ui().MSG_ADMIN, kb)
    else: 
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input:
            if text_input in flatten(kb):
                if text_input == p.ui().BUTTON_VERSION:
                    msg = p.ui().MSG_VERSION.format(settings.APP_VERSION)
                    await send_message(p, msg)
                elif text_input == p.ui().BUTTON_BACK:
                    await redirect_to_state(p, state_INITIAL)
                elif text_input == p.ui().BUTTON_UPDATE_HUNTS_CONFIG:
                    game.reload_config_hunt()
                    await send_message(p, p.ui().MSG_RELOADED_HUNTS_CONFIG)
                else:
                    hunt_pw = game.HUNTS_NAME[text_input]['Password']
                    p.set_tmp_variable('ADMIN_HUNT_NAME', text_input)
                    p.set_tmp_variable('ADMIN_HUNT_PW', hunt_pw)
                    await redirect_to_state(p, state_HUNT_ADMIN)
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS, kb)


# ================================
# Hunt Admin State
# ================================

async def state_HUNT_ADMIN(p, message_obj=None, **kwargs):    
    hunt_name = p.get_tmp_variable('ADMIN_HUNT_NAME')
    hunt_pw = p.get_tmp_variable('ADMIN_HUNT_PW')
    if message_obj is None:
        kb = [            
            [p.ui().BUTTON_BACK],
            [p.ui().BUTTON_CHECK_BUGS_HUNT, p.ui().BUTTON_TEST_MISSION],
            [p.ui().BUTTON_STATS_ACTIVE, p.ui().BUTTON_TERMINATE],
            [p.ui().BUTTON_DOWNLOAD_MEDIA, p.ui().BUTTON_DOWNLOAD_ERRORS, p.ui().BUTTON_DOWNLOAD_REPORT],
            [p.ui().BUTTON_BACK]
        ]
        msg = p.ui().MSG_HUNT_ADMIN_SELECTED.format(hunt_name)
        await send_message(p, msg, kb)
    else: 
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input:
            if text_input in flatten(kb):
                if text_input == p.ui().BUTTON_BACK:
                    await redirect_to_state(p, state_ADMIN)
                elif text_input == p.ui().BUTTON_CHECK_BUGS_HUNT:
                    from historic.bot.airtable_check import check_hunt
                    error = check_hunt(hunt_pw)
                    if error:
                        await send_message(p, error, markdown=False)
                    else:
                        await send_message(p, p.ui().MSG_CHECK_HUNT_OK)
                elif text_input == p.ui().BUTTON_TEST_MISSION:
                    hunt_languages = game.get_hunt_languages(hunt_pw)
                    if p.language not in hunt_languages:
                        lang_commands_str = ', '.join([f'/{l}' for l in hunt_languages])
                        await send_message(p, f"Cambia lingua ({lang_commands_str}) e ripremi su {text_input}")    
                    else:
                        await send_message(p, p.ui().MSG_GAME_IS_LOADING, remove_keyboard=True)
                        game.load_game(p, hunt_pw, test_hunt_admin=True)
                        await game.build_missions(p, test_all=True)
                        await redirect_to_state(p, state_TEST_HUNT_MISSION_ADMIN)                    
                elif text_input == p.ui().BUTTON_STATS_ACTIVE:
                    hunt_stats = ndb_person.get_people_on_hunt_stats(hunt_pw)
                    if hunt_stats:
                        msg = 'Stats:\n\n{}'.format(hunt_stats)
                        if len(msg)>4000:
                            file_name_prefix = 'stats_' + hunt_name.replace(' ','_')[:30]
                            timestamp = dtu.timestamp_yyyymmdd()
                            await send_text_document(p, f'{file_name_prefix}_{timestamp}.txt', msg)      
                        else:
                            await send_message(p, msg, markdown=False)    
                    else:
                        msg = 'Nessuna squadra iscritta'
                        await send_message(p, msg, markdown=False)
                elif text_input == p.ui().BUTTON_TERMINATE:
                    await redirect_to_state(p, state_TERMINATE_HUNT_CONFIRM)
                elif text_input == p.ui().BUTTON_DOWNLOAD_MEDIA:
                    msg = "Preparazione del file, ti prego di attendere... "\
                        "(L'operazione potrebbe richiedere anche diversi minuti)"
                    await send_message(p, msg, markdown=False)
                    zip_content = airtable_utils.download_media_zip(hunt_pw)
                    if zip_content == 0:
                        msg = 'Nessun media trovato.'
                        await send_message(p, msg, markdown=False)
                    elif zip_content == 'MAX':
                        msg = 'I file sono più di 50 mega, fai girare lo script da linea di comando, per favore.'
                        await send_message(p, msg, markdown=False)
                    else:
                        timestamp = dtu.timestamp_yyyymmdd()
                        zip_file_name = 'media_' + hunt_name.replace(' ','_')[:30] + f"_{timestamp}.zip"
                        await send_text_document(p, zip_file_name, zip_content)      
                elif text_input == p.ui().BUTTON_DOWNLOAD_ERRORS:
                    mission_errors, errors_digested = airtable_utils.get_wrong_answers(hunt_pw)
                    file_name_prefix = 'errori_' + hunt_name.replace(' ','_')[:30]
                    timestamp = dtu.timestamp_yyyymmdd()
                    await send_text_document(p, f'{file_name_prefix}_{timestamp}.txt', mission_errors)      
                    await send_text_document(p, f'{file_name_prefix}_{timestamp}_digested.txt', errors_digested)      
                elif text_input == p.ui().BUTTON_DOWNLOAD_REPORT:
                    report_text = airtable_utils.get_report(hunt_pw)
                    file_name = 'report_' + hunt_name.replace(' ','_')[:30] + '.txt'
                    timestamp = dtu.timestamp_yyyymmdd()
                    await send_text_document(p, file_name, report_text)      
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS)     
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS, kb)

# ================================
# Test Hunt Mission Admin
# ================================

async def state_TEST_HUNT_MISSION_ADMIN(p, message_obj=None, **kwargs):    
    missions = p.tmp_variables['MISSIONI_INFO']['TODO']
    if message_obj is None:        
        kb = [
            [m['NOME']] 
            for m in missions
        ]
        kb.insert(0, [p.ui().BUTTON_BACK])
        kb.insert(len(kb), [p.ui().BUTTON_BACK])
        msg = "Seleziona una missione da testare."
        await send_message(p, msg, kb)
    else: 
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input:
            if text_input in flatten(kb):
                if text_input == p.ui().BUTTON_BACK:
                    await redirect_to_state(p, state_HUNT_ADMIN) 
                else:
                    selected_mission = next(
                        m for m in missions 
                        if m['NOME']==text_input
                    )
                    game.set_next_mission(p, selected_mission)        
                    await redirect_to_state(p, state_MISSION_INTRO)
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS)     
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS, kb)

# ================================
# Terminate Hunt Admin State
# ================================

async def state_TERMINATE_HUNT_CONFIRM(p, message_obj=None, **kwargs):    
    hunt_name = p.get_tmp_variable('ADMIN_HUNT_NAME')
    hunt_pw = p.get_tmp_variable('ADMIN_HUNT_PW')
    if message_obj is None:
        kb = [
            [p.ui().BUTTON_YES],
            [p.ui().BUTTON_ANNULLA],
        ]
        msg = p.ui().MSG_HUNT_TERMINATE_CONFIRM.format(hunt_name)
        await send_message(p, msg, kb)
    else: 
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input:
            if text_input in flatten(kb):
                if text_input == p.ui().BUTTON_ANNULLA:
                    await redirect_to_state(p, state_HUNT_ADMIN)
                elif text_input == p.ui().BUTTON_YES:
                    qry = Person.query(Person.current_hunt==hunt_pw)
                    remaining_people = qry.fetch()
                    if remaining_people:                                                        
                        for remaining_person in remaining_people:                     
                            teminate_hunt(remaining_person)
                    msg = "Mandato messaggio di termine a {} squadre.".format(len(remaining_people))
                    await send_message(p, msg, remove_keyboard=True)
                    await send_typing_action(p, sleep_time=1)
                    await restart(p)
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS)     
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS, kb)    

# ================================
# Terminate Person Confirm
# ================================

async def state_TERMINATE_USER_CONFIRM(p, message_obj=None, **kwargs):    
    user_id = p.get_tmp_variable('TERMINATE_USER_ID', None)
    prev_state_func = possibles.get(p.last_state)
    u = Person.get_by_id(user_id)
    if u is None:
        await send_message(p, 'Wrong user ID')
        await redirect_to_state(p, prev_state_func)
        return
    u_info = u.get_first_last_username()        
    if message_obj is None:
        if u:
            kb = [
                [p.ui().BUTTON_YES],
                [p.ui().BUTTON_ANNULLA],
            ]            
            msg = f'Sei sicuro di voler terminare la caccia per {u_info}'
            await send_message(p, msg, kb)
        else:
            await send_message(p, f'Utente {user_id} non valideo')
            await redirect_to_state(p, prev_state_func)
    else: 
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input:
            if text_input in flatten(kb):
                if text_input == p.ui().BUTTON_ANNULLA:
                    await redirect_to_state(p, prev_state_func)
                elif text_input == p.ui().BUTTON_YES:
                    if game.user_in_game(u):
                        teminate_hunt(u)
                        await send_message(p, f'Caccia terminata per {u_info}')
                    else:
                        await send_message(p, f'User id {user_id} non è in una caccia')
                    await send_typing_action(p, sleep_time=1)
                    await redirect_to_state(p, prev_state_func)
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS)     
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS, kb)   

async def teminate_hunt(p):    
    reset_hunt_after_completion = get_str_param_boolean(p.tmp_variables['SETTINGS'], 'RESET_HUNT_AFTER_COMPLETION')
    terminate_message_key = 'MSG_HUNT_TERMINATED_RESET_ON' if reset_hunt_after_completion else 'MSG_HUNT_TERMINATED_RESET_OFF'
    result = await send_message(p, p.ui().get_var(terminate_message_key), remove_keyboard=True, sleep=True)
    # await send_typing_action(p, sleep_time=1)
    if not p.tmp_variables.get('FINISHED', False):                   
        game.exit_game(p, save_data=True, reset_current_hunt=True)
        await restart(p)
    else:
        # people who have completed needs to be informed too
        # we already saved the data but current hunt wasn't reset
        p.reset_current_hunt()
    return result

# ================================
# ASK_GPS_TO_LIST_HUNTS (accessed via pw/qr code)
# ================================

async def state_ASK_GPS_TO_START_HUNT(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None

    if give_instruction:                        
        kb = [
            [bot_ui.BUTTON_LOCATION(p.language)],            
            [p.ui().BUTTON_BACK],            
        ] 
        await send_message(p, p.ui().MSG_GET_GPS_TO_SET_HUNT_START, kb)
    else:
        text_input = message_obj.text
        location = message_obj.location        
        kb = p.get_keyboard()
        if text_input:            
            if text_input in flatten(kb):
                if text_input == p.ui().BUTTON_BACK:
                    await restart(p)
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_LOCATION)
        elif location:            
            p.set_location(location['latitude'], location['longitude'])            
            await redirect_to_state(p, state_CHECK_LANGUAGE_AND_START_HUNT)
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_LOCATION)

# ================================
# ASK_GPS_TO_LIST_HUNTS
# ================================

async def state_ASK_GPS_TO_LIST_HUNTS(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    if give_instruction:                
        kb = [
            [bot_ui.BUTTON_LOCATION(p.language)],            
            [p.ui().BUTTON_BACK],            
        ] 
        await send_message(p, p.ui().MSG_LIST_HUNTS_FROM_GPS, kb)
    else:
        text_input = message_obj.text
        location = message_obj.location        
        kb = p.get_keyboard()
        if text_input:            
            if text_input in flatten(kb):
                if text_input == p.ui().BUTTON_BACK:
                    await restart(p)
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_LOCATION)
        elif location:            
            p.set_location(location['latitude'], location['longitude'], put=True)            
            await redirect_to_state(p, state_SHOW_AVAILABLE_HUNTS_NEARBY)
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_LOCATION)

# ================================
# SHOW_AVAILABLE_HUNTS_NEARBY
# ================================

async def state_SHOW_AVAILABLE_HUNTS_NEARBY(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    if give_instruction:                
        lat_lon = p.get_location()
        open_hunts = [
            hunt for hunt in game.HUNTS_NAME.values()
            if hunt.get('Active', False) and
            'GPS' in hunt and 
            geo_utils.distance_km(
                utility.get_lat_lon_from_string(hunt['GPS']), 
                lat_lon
            ) <= params.MAX_DISTANCE_KM_HUNT_GPS
        ]
        num_open_hunts = len(open_hunts)
        if num_open_hunts > 0:
            kb = [
                [hunt['Name']] for hunt in open_hunts           
            ]     
            kb.append(
                [p.ui().BUTTON_BACK]
            )
            await send_message(p, p.ui().MSG_HUNT_NEARBY_YES, kb)
        else:
            await send_message(p, p.ui().MSG_HUNT_NEARBY_NO)
            await send_typing_action(p, 1)
            await redirect_to_state(p, state_ASK_GPS_TO_LIST_HUNTS)        
        # notify admin with position
        p_name = p.get_first_last_username_id(escape_markdown=False)
        hunt_names_str = ', '.join([h['Name'] for h in open_hunts])
        admin_msg = f'{p_name} ha mandato GPS per inizio caccia - cacce aperte trovate {num_open_hunts}: ({hunt_names_str})'
        await report_admins(admin_msg)
        await report_location_admin(lat_lon[0], lat_lon[1])
    else:
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input in flatten(kb):
            if text_input == p.ui().BUTTON_BACK:
                await redirect_to_state(p, state_ASK_GPS_TO_LIST_HUNTS)
            else:
                hunt_password = game.HUNTS_NAME[text_input]['Password']
                p.set_tmp_variable('HUNT_PW', hunt_password)
                await redirect_to_state(p, state_CHECK_LANGUAGE_AND_START_HUNT)                
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS, kb)

# ================================
# Change Language Before Hunt Start
# ================================

async def state_CHECK_LANGUAGE_AND_START_HUNT(p, message_obj=None, **kwargs):    
    hunt_password = p.get_tmp_variable('HUNT_PW')
    if message_obj is None:        
        hunt_languages = game.get_hunt_languages(hunt_password)
        if p.language not in hunt_languages:            
            buttons_languages = [
                p.ui().get_var(f'BUTTON_SWITCH_{l}')
                for l in hunt_languages
            ]
            kb = [[b] for b in  buttons_languages]
            kb.append([p.ui().BUTTON_ANNULLA])
            await send_message(p, p.ui().MSG_HUNT_NOT_AVAILABLE_IN_YOUR_LANGUAGE, kb)
        else:
            await start_hunt(p, hunt_password)
    else: 
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input:            
            if text_input in flatten(kb):
                if text_input == p.ui().BUTTON_ANNULLA:
                    await redirect_to_state(p, state_INITIAL)
                else:
                    for l in params.LANGUAGES:
                        if text_input == p.ui().get_var(f'BUTTON_SWITCH_{l}'):
                            p.set_language(l)
                            await send_message(p, p.ui().MSG_LANGUAGE_SWITCHED)
                            await send_typing_action(p, sleep_time=1)     
                            await start_hunt(p, hunt_password)                                                   
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS, kb)

async def start_hunt(p, hunt_password): 
    await send_message(p, p.ui().MSG_GAME_IS_LOADING, remove_keyboard=True)
    game.load_game(p, hunt_password)
    notify_group_id = game.get_notify_group_id(p) 
    if notify_group_id:
        p_name = p.get_first_last_username_id()
        h_name = p.get_tmp_variable('HUNT_NAME')
        msg = f'{p_name} ha iniziato la caccia: {h_name}'
        await send_message(notify_group_id, msg)    
    skip_instructions = get_str_param_boolean(p.tmp_variables['SETTINGS'], 'SKIP_INSTRUCTIONS')
    await set_commands(p) # refresh commands in menu
    if skip_instructions:
        await redirect_to_state(p, state_CHECK_INITIAL_POSITION)        
    else:
        await redirect_to_state(p, state_INSTRUCTIONS)


# ================================
# Instructions
# ================================

async def state_INSTRUCTIONS(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    instructions = p.tmp_variables['INSTRUCTIONS']
    if kwargs.get('next_step', False):
        game.increase_intro_completed(p)
    completed = instructions['COMPLETED']
    steps = instructions['STEPS']
    if len(steps) == completed:
        # start the hunt
        await redirect_to_state(p, state_CHECK_INITIAL_POSITION)
        return
    current_step = steps[completed]
    input_type = current_step.get('Input_Type',[]) # list of buttons, special types (e.g., EMAIL)
    input_buttons = [x for x in input_type if x.startswith('BUTTON_')]
    first_input_button = input_buttons[0] if input_buttons else None
    all_inputs_are_buttons = len(input_buttons) == len(input_type)
    if give_instruction:                
        msg = current_step.get('Text','')
        media = current_step.get('Media', '')
        if input_buttons:
            # BUTTON_UNDERSTOOD, BUTTON_START_GAME
            # BUTTON_ROUTE_KIDS, BUTTON_ROUTE_ADULTS
            # BUTTON_ROUTE_FOOT, BUTTON_ROUTE_BICYCLE
            # BUTTON_ROUTE_CIRCULAR_YES, BUTTON_ROUTE_CIRCULAR_NO
            # BUTTON_X_MIN
            buttons = [p.ui()[b] for b in input_buttons]
            kb = make_2d_array(buttons, length=2)
            if media:
                media_dict = media[0]
                url_attachment = media_dict['url']
                type = media_dict['type']
                await send_media_url(p, url_attachment, type, kb, caption=msg)
            else:
                await send_message(p, msg, kb)
        else:
            if media:
                media_dict = media[0]
                url_attachment = media_dict['url']
                type = media_dict['type']
                await send_media_url(p, url_attachment, type, caption=msg, remove_keyboard=True)
            else:
                await send_message(p, msg, remove_keyboard=True)        
            if not input_type: 
                # no input, go to next instruction after 1 sec
                await send_typing_action(p, sleep_time=1)
                await repeat_state(p, next_step=True)        
    else:
        if len(input_type)==0:
            # this may happen if a person sends quickly an input while in a step with no input type
            return
        text_input = message_obj.text
        input_type = input_type[0] # take first element in the list
        if input_buttons:
            # BUTTON_UNDERSTOOD, BUTTON_START_GAME
            # BUTTON_ROUTE_KIDS, BUTTON_ROUTE_ADULTS
            # BUTTON_ROUTE_FOOT, BUTTON_ROUTE_BICYCLE
            # BUTTON_ROUTE_CIRCULAR_YES, BUTTON_ROUTE_CIRCULAR_NO
            # BUTTON_X_MIN
            kb = p.get_keyboard()
            if text_input in flatten(kb):
                if text_input == p.ui().BUTTON_EXIT:
                    game.exit_game(p, save_data=False, reset_current_hunt=True)
                    await send_message(p, p.ui().MSG_EXITED_FROM_GAME, remove_keyboard=True)
                    await restart(p)
                elif text_input in [p.ui().BUTTON_ROUTE_KIDS]:
                    p.set_tmp_variable('ROUTE_AGE_GROUP', 'KIDS', put=True)
                elif text_input in [p.ui().BUTTON_ROUTE_ADULTS]:
                    p.set_tmp_variable('ROUTE_AGE_GROUP', 'ADULTS', put=True)
                elif text_input in [p.ui().BUTTON_ROUTE_FOOT]:
                    p.set_tmp_variable('ROUTE_TRANSPORT', api_google.PROFILE_FOOT_WALKING, put=True)
                elif text_input in [p.ui().BUTTON_ROUTE_BICYCLE]:
                    p.set_tmp_variable('ROUTE_TRANSPORT', api_google.PROFILE_CYCLING_REGULAR, put=True)
                elif text_input in [p.ui().BUTTON_ROUTE_CIRCULAR_YES]:
                    p.set_tmp_variable('ROUTE_CIRCULAR', True, put=True)
                elif text_input in [p.ui().BUTTON_ROUTE_CIRCULAR_NO]:
                    p.set_tmp_variable('ROUTE_CIRCULAR', False, put=True)
                elif text_input in [p.ui().BUTTON_45_MIN, p.ui().BUTTON_60_MIN,
                                    p.ui().BUTTON_90_MIN, p.ui().BUTTON_120_MIN]:                    
                    duration_min = int(text_input.split()[1])
                    p.set_tmp_variable('ROUTE_DURATION_MIN', duration_min, put=True)
                else:
                    # BUTTON_CONTINUE, BUTTON_UNDERSTOOD, BUTTON_START_GAME: 
                    # do nothing except for repeating state                
                    pass                    
                await send_typing_action(p, sleep_time=1)
                await repeat_state(p, next_step=True)
                return
            elif all_inputs_are_buttons:            
                await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS)  
                return
        
        if input_type == 'EMAIL':
            if text_input:
                if utility.check_email(text_input):                
                    p.set_tmp_variable('EMAIL', text_input, put=True)
                    await send_typing_action(p, sleep_time=1)
                    await repeat_state(p, next_step=True)
                else:
                    await send_message(p, p.ui().MSG_EMAIL_WRONG)
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_INSERT_TEXT)
        elif input_type == 'CONTACT_PERSON_NAME':
            if text_input:
                p.set_tmp_variable('CONTACT_PERSON_NAME', text_input, put=True)
                await send_typing_action(p, sleep_time=1)
                await repeat_state(p, next_step=True)                    
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_INSERT_TEXT)
        elif input_type == 'CONTACT_PERSON_PHONE':
            if text_input:
                p.set_tmp_variable('CONTACT_PERSON_PHONE', text_input, put=True)
                await send_typing_action(p, sleep_time=1)
                await repeat_state(p, next_step=True)
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_INSERT_TEXT)
        elif input_type == 'TEAM_NAME':
            if text_input:
                if len(text_input) > params.MAX_TEAM_NAME_LENGTH:
                    await send_message(p, p.ui().MSG_GROUP_NAME_TOO_LONG.format(params.MAX_TEAM_NAME_LENGTH))
                    return
                if not utility.hasOnlyLettersAndSpaces(text_input):
                    await send_message(p, p.ui().MSG_GROUP_NAME_INVALID)
                    return
                game.set_group_name(p, text_input)
                notify_group_id = game.get_notify_group_id(p)
                if notify_group_id:
                    msg = '\n'.join([
                        f'Caccia {game.get_hunt_name(p)}:',
                        f'Nuova squadra registrata: {text_input}'
                    ])
                    await send_message(notify_group_id, msg)
                await send_typing_action(p, sleep_time=1)
                await repeat_state(p, next_step=True)
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_INSERT_TEXT)                
        elif input_type == 'GROUP_SIZE':
            if text_input: 
                if utility.is_int(text_input):
                    group_size = int(text_input)
                    p.set_tmp_variable('GROUP_SIZE', group_size, put=True)
                    await send_typing_action(p, sleep_time=1)
                    await repeat_state(p, next_step=True)
                else:
                    await send_message(p, p.ui().MSG_WRONG_NUMBER_OF_PEOPLE) 
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_INSERT_TEXT)
        elif input_type == 'TEST_POSITION':
            location = message_obj.location
            if location:            
                await send_typing_action(p, sleep_time=1)
                await repeat_state(p, next_step=True)
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_LOCATION)
        elif input_type == 'TEST_PHOTO':     
            photo = message_obj.photo       
            if photo is not None and len(photo)>0:
                photo_file_id = photo[-1]['file_id']
                game.append_group_media_input_file_id(p, photo_file_id)
                await send_typing_action(p, sleep_time=1)                            
                notify_group_id = game.get_notify_group_id(p)
                if notify_group_id:
                    msg = '\n'.join([
                        f'Caccia {game.get_hunt_name(p)}:',
                        f'Selfie iniziale {game.get_group_name(p)}'
                    ])
                    BOT.send_photo(notify_group_id, photo=photo_file_id, caption=msg)
                await send_typing_action(p, sleep_time=1)
                await repeat_state(p, next_step=True)
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_PHOTO)
        elif input_type == 'TEST_VOICE':
            voice = message_obj.voice
            if voice is not None:
                voice_file_id = voice['file_id']
                game.append_group_media_input_file_id(p, voice_file_id)
                await send_typing_action(p, sleep_time=1)
                await repeat_state(p, next_step=True)
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_VOICE)
        elif input_type == 'TEST_VIDEO':
            video = message_obj.video
            if video is not None:
                video_file_id = video['file_id']
                game.append_group_media_input_file_id(p, video_file_id)
                await send_typing_action(p, sleep_time=1)
                await repeat_state(p, next_step=True)
            else:
                if message_obj.video_note is not None:
                    await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_VIDEO_NO_VIDEO_NOTE)
                else:
                    await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_VIDEO)

# ================================
# Check Initial Position
# ================================

async def state_CHECK_INITIAL_POSITION(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    goal_position = p.get_tmp_variable('HUNT_START_GPS')
    # CHECK_LOCATION = p.tmp_variables['SETTINGS'].get('CHECK_INITIAL_LOCATION', True)
    if goal_position is None:
        await load_missions(p)
        return
    # START_LOCATION = p.tmp_variables['SETTINGS'].get('START_LOCATION', 'PROXIMITY')
    GPS_TOLERANCE_METERS = int(p.tmp_variables['SETTINGS']['GPS_TOLERANCE_METERS'])
    if give_instruction:
        current_position = p.get_location()
        distance = geo_utils.distance_meters(goal_position, current_position)        
        if distance <= GPS_TOLERANCE_METERS:            
            await load_missions(p)
        else:
            msg = p.ui().MSG_GO_TO_START_LOCATION
            kb = [[bot_ui.BUTTON_LOCATION(p.language)]]
            await send_message(p, msg, kb)
            await send_location(p, goal_position[0], goal_position[1])
    else:
        location = message_obj.location
        if location:          
            lat, lon = location['latitude'], location['longitude']
            p.set_location(location['latitude'], location['longitude'])
            given_position = [lat, lon]
            distance = geo_utils.distance_meters(goal_position, given_position)
            if distance <= GPS_TOLERANCE_METERS:
                await send_message(p, p.ui().MSG_GPS_OK, remove_keyboard=True)
                await send_typing_action(p, sleep_time=1)
                await load_missions(p)
            else:
                msg = p.ui().MSG_TOO_FAR.format(distance)
                await send_message(p, msg)
                await send_typing_action(p, sleep_time=1)
                await repeat_state(p)
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_LOCATION)    

# ================================
# LOAD MISSIONS
# ================================

async def load_missions(p):        
    success = await game.build_missions(p)    
    if not success:
        await send_message(p, p.ui().MSG_ERROR_ROUTING)
        await send_typing_action(p, sleep_time=1)
        await restart(p)
        msg_admin = f"Problema percorso per {p.get_first_last_username_id()}"
        await send_text_document(p, 'tmp_vars.json', game.debug_tmp_vars(p), caption=msg_admin)
        await report_admins(msg_admin)
    else:
        WAIT_QR_MODE = p.tmp_variables['SETTINGS'].get('WAIT_QR_MODE', False)                
        await send_message(p, p.ui().MSG_GO)
        if WAIT_QR_MODE:            
            await redirect_to_state(p, state_WAIT_FOR_QR)
        else:
            await redirect_to_state(p, state_MISSION_INTRO)

# ================================
# MISSION WAIT QR
# ================================

async def state_WAIT_FOR_QR(p, message_obj=None, **kwargs):    
    first_call = kwargs.get('first_call', True)
    qr_code = kwargs.get('qr_code', False)
    give_instruction = qr_code==False and message_obj is None    
    if give_instruction:
        if first_call:
            await check_if_first_mission_and_start_time(p)
        send_msg_mission_number(p)
        msg = p.ui().MSG_SCAN_QR_CODE    
        kb = [
                [
                    telegram.KeyboardButton(
                        "Scan QR Code", # TODO: localize
                        web_app=telegram.WebAppInfo(settings.WEB_APP_QR_URL)
                    )                    
                ],
                [
                    p.ui().BUTTON_EXIT
                ]
            ]
        await send_message(p, msg, kb=kb)
    else:
        text_input = message_obj.text if message_obj else qr_code if qr_code else None
        photo = message_obj.photo if message_obj else None
        testing = p.get_tmp_variable('TEST_HUNT_MISSION_ADMIN', False)   
        kb = p.get_keyboard()        
        if text_input:
            if text_input in flatten(kb):
                assert text_input == p.ui().BUTTON_EXIT
                await redirect_to_state(p, state_EXIT_CONFIRMATION)
                return
            else:
                qr_code = text_input
        elif photo is None or len(photo)==0:            
            await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_PHOTO)
            return
        else:            
            file_id = photo[-1]['file_id']
            qr_url = await get_photo_url_from_telegram(file_id)
            qr_code = utility.read_qr_from_url(qr_url)
        current_mission = game.get_current_mission(p) if testing else game.get_mission_matching_qr(p, qr_code)
        if current_mission:
            game.set_next_mission(p, current_mission, remove_from_todo=True)
            await send_message(p, p.ui().MSG_QR_OK, remove_keyboard=True)                
            if not send_post_message(p, current_mission, after_loc=True):
                await send_typing_action(p, sleep_time=1)                    
            await redirect_to_state(p, state_DOMANDA)
        else:
            msg = p.ui().MSG_QR_ERROR
            await send_message(p, msg)
            await send_typing_action(p, sleep_time=1)
            await repeat_state(p, first_call=False)
        
# ================================
#  EXIT CONFIRMATION
# ================================

async def state_EXIT_CONFIRMATION(p, message_obj=None,  **kwargs):            
    give_instruction = message_obj is None
    if give_instruction:
        kb = [
            [p.ui().BUTTON_YES, p.ui().BUTTON_NO]
        ]
        msg = p.ui().MSG_EXIT_FROM_GAME_CONFIRM
        await send_message(p, msg, kb)
    else:
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input in flatten(kb):
            if text_input == p.ui().BUTTON_YES:
                game.exit_game(p, save_data=True, reset_current_hunt=True)
                await send_message(p, p.ui().MSG_EXITED_FROM_GAME, remove_keyboard=True)
                await restart(p)
            else: 
                assert text_input == p.ui().BUTTON_NO
                prev_state_func = possibles.get(p.last_state)
                await redirect_to_state(p, prev_state_func)
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS)  


# ================================
# MISSION INTRO
# ================================

async def state_MISSION_INTRO(p, message_obj=None, **kwargs):            
    give_instruction = message_obj is None
    if give_instruction:
        testing = p.get_tmp_variable('TEST_HUNT_MISSION_ADMIN', False)
        # if testing next mission is already set up
        current_mission = game.get_current_mission(p) if testing else game.set_next_mission(p)        
        if not testing:
            await check_if_first_mission_and_start_time(p)            
            send_msg_mission_number(p)            
        if 'INTRODUZIONE_LOCATION' not in current_mission:
            await redirect_to_state(p, state_MISSION_GPS)
            return
        if 'INTRO_MEDIA' in current_mission:
            caption = current_mission.get('INTRO_MEDIA_CAPTION',None)
            media_dict = current_mission['INTRO_MEDIA'][0]
            url_attachment = media_dict['url']
            type = media_dict['type']
            await send_media_url(p, url_attachment, type, caption=caption)
            await send_typing_action(p, sleep_time=1)
        msg = current_mission['INTRODUZIONE_LOCATION'] # '*Introduzione*: ' + 
        kb = [[random.choice(bot_ui.BUTTON_CONTINUE_MULTI(p.language))]]
        await send_message(p, msg, kb)
        p.put()
    else:
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input in flatten(kb):
            if text_input in bot_ui.BUTTON_CONTINUE_MULTI(p.language):
                current_mission = game.get_current_mission(p)
                await redirect_to_state(p, state_VERIFY_LOCATION)
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS)            

async def check_if_first_mission_and_start_time(p):
    if p.get_tmp_variable('TIME_STARTED', init_value=False):
        return False
    mission_number = game.get_num_compleded_missions(p) + 1        
    if mission_number == 1:
        # first one
        await send_message(p, p.ui().MSG_START_TIME, remove_keyboard=True)            
        game.set_game_start_time(p)
        p.set_tmp_variable('TIME_STARTED', True)        
        await send_typing_action(p, sleep_time=1)                
        return True

async def send_msg_mission_number(p):
    mission_number = game.get_num_compleded_missions(p) + 1        
    total_missioni = game.get_total_missions(p)
    msg = p.ui().MSG_MISSION_N_TOT.format(mission_number, total_missioni)
    await send_message(p, msg, remove_keyboard=True)
    await send_typing_action(p, sleep_time=1)        

# ================================
# VERIFY_LOCATION state
# ================================  

async def state_VERIFY_LOCATION(p, message_obj=None, **kwargs):        
    current_mission = game.get_current_mission(p)
    if 'GPS' in current_mission:
        await redirect_to_state(p, state_MISSION_GPS)
        return
    elif 'QR'in current_mission:
        await redirect_to_state(p, state_MISSION_QR)
        return
    else:
        await redirect_to_state(p, state_DOMANDA)
        return

# ================================
# GPS state
# ================================  

async def state_MISSION_GPS(p, message_obj=None, **kwargs):        
    give_instruction = message_obj is None
    current_mission = game.get_current_mission(p)
    goal_position = utility.get_lat_lon_from_string(current_mission['GPS'])
    if goal_position == p.get_tmp_variable('HUNT_START_GPS'):
        await redirect_to_state(p, state_DOMANDA)
        return
    if give_instruction:        
        # skip GPS if already there (only for first mission and ROUTING driven hunt)
        testing = p.get_tmp_variable('TEST_HUNT_MISSION_ADMIN', False)
        routing_mode = p.get_tmp_variable('TEST_HUNT_MISSION_ADMIN') == 'ROUTING'
        mission_number = game.get_num_compleded_missions(p) + 1
        first_mission = mission_number == 1
        if not testing and first_mission and routing_mode:
            current_position = p.get_location()
            distance = geo_utils.distance_meters(goal_position, current_position)
            GPS_TOLERANCE_METERS = int(p.tmp_variables['SETTINGS']['GPS_TOLERANCE_METERS'])
            if distance <= GPS_TOLERANCE_METERS:
                await redirect_to_state(p, state_DOMANDA)
                return
        msg = p.ui().MSG_GO_TO_PLACE
        kb = [[bot_ui.BUTTON_LOCATION(p.language)]]
        await send_message(p, msg, kb)
        await send_location(p, goal_position[0], goal_position[1])
    else:
        location = message_obj.location
        if location:            
            lat, lon = location['latitude'], location['longitude']
            p.set_location(lat, lon)
            given_position = [lat, lon]
            distance = geo_utils.distance_meters(goal_position, given_position)
            GPS_TOLERANCE_METERS = int(p.tmp_variables['SETTINGS']['GPS_TOLERANCE_METERS'])
            if distance <= GPS_TOLERANCE_METERS:
                await send_message(p, p.ui().MSG_GPS_OK, remove_keyboard=True)
                if not send_post_message(p, current_mission, after_loc=True):
                    await send_typing_action(p, sleep_time=1)                    
                await redirect_to_state(p, state_DOMANDA)
            else:
                msg = p.ui().MSG_TOO_FAR.format(distance)
                await send_message(p, msg)
                await send_typing_action(p, sleep_time=1)
                await repeat_state(p)
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_LOCATION)


# ================================
# GPS state
# ================================  

async def state_MISSION_QR(p, message_obj=None, **kwargs):            
    give_instruction = message_obj is None
    current_mission = game.get_current_mission(p)
    goal_qr_code = current_mission['QR']
    if give_instruction:                
        msg = p.ui().MSG_GO_TO_QR
        await send_message(p, msg, remove_keyboard=True)
    else:
        photo = message_obj.photo        
        if photo is None or len(photo)==0:            
            await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_PHOTO)
            return
        else:
            file_id = photo[-1]['file_id']
            qr_url = await get_photo_url_from_telegram(file_id)
            qr_code = utility.read_qr_from_url(qr_url)
            if utility.qr_matches(goal_qr_code, qr_code):
                await send_message(p, p.ui().MSG_QR_OK, remove_keyboard=True)
                if not send_post_message(p, current_mission, after_loc=True):
                    await send_typing_action(p, sleep_time=1)                    
                await redirect_to_state(p, state_DOMANDA)
            else:
                msg = p.ui().MSG_QR_ERROR
                await send_message(p, msg)
                await send_typing_action(p, sleep_time=1)
                await repeat_state(p)
        



# ================================
# DOMANDA state
# ================================
async def state_DOMANDA(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    current_mission = game.get_current_mission(p)
    if give_instruction:
        if 'DOMANDA_MEDIA' in current_mission:
            caption = current_mission.get('DOMANDA_MEDIA_CAPTION',None)
            media_dict = current_mission['DOMANDA_MEDIA'][0]
            type = media_dict['type'] # e.g., image/png
            url_attachment = media_dict['url']
            await send_media_url(p, url_attachment, type, caption=caption)
            await send_typing_action(p, sleep_time=1)                
        msg = current_mission['DOMANDA'] 
        if current_mission.get('INDIZIO_1',False):
            kb = [[p.ui().BUTTON_FIRST_HINT]]
            await send_message(p, msg, kb)
        else:
            await send_message(p, msg, remove_keyboard=True)
        game.start_mission(p) # set start time of the mission
        p.put()
        
        # SOLUZIONI must be present, below old code when it was optional
        # if 'SOLUZIONI' not in current_mission:
        #     # if there is no solution required go to required_input (photo or voice)
        #     assert all(x in current_mission for x in ['INPUT_INSTRUCTIONS', 'INPUT_TYPE'])
        #     await redirect_to_state(p, state_MEDIA_INPUT_MISSION)
    else:
        text_input = message_obj.text
        if text_input:            
            kb = p.get_keyboard()
            if text_input in flatten(kb):
                now_string = dtu.now_utc_iso_format()
                MIN_SEC_INDIZIO_1 = int(p.tmp_variables['SETTINGS']['MIN_SEC_INDIZIO_1'])
                MIN_SEC_INDIZIO_2 = int(p.tmp_variables['SETTINGS']['MIN_SEC_INDIZIO_2'])
                if text_input == p.ui().BUTTON_FIRST_HINT:
                    before_string = current_mission['start_time']
                    ellapsed = dtu.delta_seconds_iso(before_string, now_string)
                    if ellapsed > MIN_SEC_INDIZIO_1 and current_mission.get('INDIZIO_1',False):
                        msg = '💡 *Indizio 1*: {}'.format(current_mission['INDIZIO_1'])
                        if current_mission.get('INDIZIO_2',False):
                            kb = [[p.ui().BUTTON_SECOND_HINT]]
                            current_mission['indizio1_time'] = now_string
                            await send_message(p, msg, kb)
                        else:
                            await send_message(p, msg, remove_keyboard=True)
                    else:
                        remaining = MIN_SEC_INDIZIO_1 - ellapsed
                        await send_message(p, p.ui().MSG_TOO_EARLY.format(remaining))
                elif text_input == p.ui().BUTTON_SECOND_HINT and current_mission.get('INDIZIO_2',False):
                    before_string = current_mission['indizio1_time']
                    ellapsed = dtu.delta_seconds_iso(before_string, now_string)
                    if ellapsed > MIN_SEC_INDIZIO_2 and current_mission.get('INDIZIO_2',False):
                        msg = '💡 *Indizio 2*: {}'.format(current_mission['INDIZIO_2'])                    
                        current_mission['indizio2_time'] = now_string
                        await send_message(p, msg, remove_keyboard=True)
                    else:
                        remaining = MIN_SEC_INDIZIO_2 - ellapsed
                        await send_message(p, p.ui().MSG_TOO_EARLY.format(remaining))
            else:
                import functools, regex
                soluzioni_list = [
                    x.strip() for x in 
                    regex.split(r"(?<!\\)(?:\\{2})*\K,", current_mission['SOLUZIONI'])
                ] # split on comma but not on /, (when comma is used in regex)
                correct_answers_upper = [x.upper() for x in soluzioni_list if not regex.match(r'^/.*/$', x)]
                correct_answers_regex = [x[1:-1].replace('\\,',',') for x in soluzioni_list if regex.match(r'^/.*/$', x)]
                for r in correct_answers_regex:
                    try: regex.compile(r)
                    except regex.error: correct_answers_regex.remove(r)
                #correct_answers_upper_word_set = set(flatten([x.split() for x in correct_answers_upper]))
                if text_input.upper() in correct_answers_upper or functools.reduce(lambda a, r: a or regex.match(r, text_input, regex.I), correct_answers_regex, False):
                    await game.set_mission_end_time(p) # set time of ending the mission (after solution)
                    if not send_post_message(p, current_mission):
                        await send_message(p, bot_ui.MSG_ANSWER_OK(p.language), remove_keyboard=True)
                        await send_typing_action(p, sleep_time=1)                    
                    if 'INPUT_INSTRUCTIONS' in current_mission:
                        # only missioni with GPS require selfies
                        await redirect_to_state(p, state_MEDIA_INPUT_MISSION)
                    else:
                        await redirect_to_state(p, state_COMPLETE_MISSION)
                # elif utility.answer_is_almost_correct(text_input.upper(), correct_answers_upper_word_set):
                #     await send_message(p, p.ui().MSG_ANSWER_ALMOST)
                else:
                    give_penalty = current_mission.get('PENALTY',False)
                    game.increase_wrong_answers_current_indovinello(p, text_input, give_penalty)
                    if give_penalty:
                        penalties, penalty_sec = game.get_total_penalty(p)
                        msg = p.ui().MSG_ANSWER_WRONG_SG if penalties==1 else p.ui().MSG_ANSWER_WRONG_PL
                        await send_message(p, msg.format(penalties, penalty_sec))
                    else:
                        await send_message(p, bot_ui.MSG_ANSWER_WRONG_NO_PENALTY(p.language))
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_INSERT_TEXT)

async def send_post_message(p, current_mission, after_loc=False, after_input=False):
    assert not (after_loc and after_input) # can't be both True
    prefix = 'POST_LOC' if after_loc else 'POST_INPUT' if after_input else 'POST'
    post_msg_present = f'{prefix}_MESSAGE' in current_mission # POST_MESSAGE, POST_LOC_MESSAGE, POST_INPUT_MESSAGE
    post_media_present = f'{prefix}_MEDIA' in current_mission # POST_MEDIA, POST_LOC_MEDIA, POST_INPUT_MEDIA
    if post_msg_present or post_media_present:
        if post_media_present:
            caption = current_mission.get(f'{prefix}_MEDIA_CAPTION',None) # POST_MEDIA_CAPTION, POST_LOC_MEDIA_CAPTION, POST_INPUT_MEDIA_CAPTION
            media_dict = current_mission[f'{prefix}_MEDIA'][0] # POST_MEDIA, POST_LOC_MEDIA, POST_INPUT_MEDIA
            url_attachment = media_dict['url']
            type = media_dict['type']
            await send_media_url(p, url_attachment, type, caption=caption)
            await send_typing_action(p, sleep_time=1)
        if post_msg_present:
            msg = current_mission[f'{prefix}_MESSAGE'] # POST_MESSAGE, POST_LOC_MESSAGE, POST_INPUT_MESSAGE
            await send_message(p, msg, remove_keyboard=True)
            await send_typing_action(p, sleep_time=1)
        return True
    return False


# ================================
# MEDIA INPUT (photo, voice)
# ================================

async def state_MEDIA_INPUT_MISSION(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    current_mission = game.get_current_mission(p)
    input_type = current_mission['INPUT_TYPE'] # PHOTO, VOICE
    assert input_type in ['PHOTO','VOICE','VIDEO']
    if give_instruction:
        msg = current_mission['INPUT_INSTRUCTIONS']
        await send_message(p, msg, remove_keyboard=True)
    else:
        photo = message_obj.photo
        voice = message_obj.voice
        video = message_obj.video
        if input_type == 'PHOTO': 
            if photo is None or len(photo)==0:            
                await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_PHOTO)
                return
            file_id = photo[-1]['file_id']
        if input_type == 'VOICE':          
            if voice is None:
                await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_VOICE)
                return                    
            file_id = voice['file_id']
        if input_type == 'VIDEO':          
            if video is None:
                if message_obj.video_note is not None:
                    await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_VIDEO_NO_VIDEO_NOTE)
                else:
                    await send_message(p, p.ui().MSG_WRONG_INPUT_SEND_VIDEO)
                return 
            file_id = video['file_id']
        current_mission['MEDIA_INPUT_ID_TYPE'] = [file_id, input_type]
        if current_mission.get('INPUT_CONFIRMATION', False):
            await redirect_to_state(p, state_CONFIRM_MEDIA_INPUT)
        elif game.manual_validation(p):
            send_to_validator(p, game, current_mission, input_type)        
        else:
            await approve_media_input_indovinello(p, approved=True, signature=None)
        p.put()

async def send_to_validator(p, game, current_mission, input_type):
    assert input_type in ['PHOTO','VOICE', 'VIDEO']
    squadra_name = game.get_group_name(p)
    mission_number = game.get_num_compleded_missions(p) + 1
    indovinello_name = current_mission['NOME']
    replies_dict = {
        'PHOTO': {
            'reply': p.ui().MSG_WAIT_SELFIE_APPROVAL,
            'caption': 'Selfie indovinello {} squadra {} per indovinello {}'.format(\
                mission_number, squadra_name, indovinello_name)
        },
        'VOICE': {
            'reply': p.ui().MSG_WAIT_VOICE_APPROVAL,
            'caption': 'Registrazione indovinello {} squadra {} per indovinello {}'.format(\
                mission_number, squadra_name, indovinello_name)
        },
        'VIDEO': {
            'reply': p.ui().MSG_WAIT_VIDEO_APPROVAL,
            'caption': 'Video indovinello {} squadra {} per indovinello {}'.format(\
                mission_number, squadra_name, indovinello_name)
        }
    }
    # store a random password to make sure the approval is correct
    # (the team may have restarted the game in the meanwhile):
    approval_signature = utility.randomAlphaNumericString(5)
    current_mission['sign'] = approval_signature
    await send_message(p, replies_dict[input_type]['reply'])
    kb_markup = telegram.InlineKeyboardMarkup(
        [
            [
                bot_ui.BUTTON_YES_CALLBACK(
                    json.dumps({'ok': True, 'uid':p.get_id(), 'sign': approval_signature})
                ),
                bot_ui.BUTTON_NO_CALLBACK(
                    json.dumps({'ok': False, 'uid': p.get_id(), 'sign': approval_signature})
                ),
            ]
        ]
    )
    file_id = current_mission['MEDIA_INPUT_ID_TYPE'][0]
    caption = replies_dict[input_type]['caption']
    logging.debug('Sending group input ({}) to validator'.format(input_type))
    if input_type == 'PHOTO':
        BOT.send_photo(game.get_validator_chat_id(p), photo=file_id, caption=caption, reply_markup=kb_markup)
    elif input_type == 'VOICE':
        BOT.send_voice(game.get_validator_chat_id(p), voice=file_id, caption=caption, reply_markup=kb_markup)
    else: # input_type == 'VIDEO':
        BOT.send_video(game.get_validator_chat_id(p), video=file_id, caption=caption, reply_markup=kb_markup)

async def approve_media_input_indovinello(p, approved, signature):
    # need to double check if team is still waiting for approval
    # (e.g., could have restarted the game, or validator pressed approve twice in a row)
    current_mission = game.get_current_mission(p)
    if current_mission is None:
        return False
    file_id, input_type = current_mission['MEDIA_INPUT_ID_TYPE']
    assert input_type in ['PHOTO','VOICE', 'VIDEO']
    if game.manual_validation(p) and signature != current_mission.get('sign', signature):
        # if 'sign' is not in current_mission it means we are in INPUT_CONFIRMATION mode 
        return False
    if approved:        
        if not send_post_message(p, current_mission, after_input=True):
            await send_message(p, bot_ui.MSG_MEDIA_INPUT_MISSIONE_OK(p.language))        
            await send_typing_action(p, sleep_time=1)
        notify_group_id = game.get_notify_group_id(p)
        if notify_group_id:
            squadra_name = game.get_group_name(p)
            mission_number = game.get_num_compleded_missions(p) + 1
            indovinello_name = current_mission['NOME']     
            msg_type_str = {'PHOTO':'Selfie', 'VOICE': 'Registrazione', 'VIDEO': 'Video'}
            msg = '\n'.join([
                f'Caccia {game.get_hunt_name(p)}:',
                f'{msg_type_str[input_type]} indovinello {mission_number} ({indovinello_name}) squadra {squadra_name}'
            ])
            if input_type=='PHOTO':                
                BOT.send_photo(notify_group_id, photo=file_id, caption=msg)
            elif input_type=='VOICE':
                BOT.send_voice(notify_group_id, voice=file_id, caption=msg)
            else: # input_type=='VIDEO':
                BOT.send_video(notify_group_id, video=file_id, caption=msg)
        game.append_group_media_input_file_id(p, file_id)        
        await redirect_to_state(p, state_COMPLETE_MISSION)
    else:
        if input_type=='PHOTO':
            await send_message(p, p.ui().MSG_SELFIE_MISSIONE_WRONG)
        elif input_type=='VOICE':
            await send_message(p, p.ui().MSG_RECORDING_MISSIONE_WRONG)
        else: # input_type=='VIDEO'
            await send_message(p, p.ui().MSG_VIDEO_MISSIONE_WRONG)
    return True


# ================================
# CONFIRM MEDIA INPUT (photo, voice)
# ================================

async def state_CONFIRM_MEDIA_INPUT(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    current_mission = game.get_current_mission(p)
    input_type = current_mission['INPUT_TYPE'] # PHOTO, VOICE
    if give_instruction:
        msg = p.ui().MSG_CONFIRM_PHOTO_INPUT if input_type == 'PHOTO' else p.ui().MSG_CONFIRM_RECORDING_INPUT
        kb = [[p.ui().BUTTON_YES, p.ui().BUTTON_NO]]
        await send_message(p, msg, kb)
    else:
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input in flatten(kb):
            if text_input == p.ui().BUTTON_YES:
                await approve_media_input_indovinello(p, approved=True, signature=None)
            else: 
                assert text_input == p.ui().BUTTON_NO
                msg = p.ui().MSG_MEDIA_INPUT_ABORTED
                await send_message(p, msg, remove_keyboard=True)
                await send_typing_action(p, sleep_time=1)
                await redirect_to_state(p, state_MEDIA_INPUT_MISSION)
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS)  

# ================================
# COMPLETE CURRENT MISSION
# ================================

async def state_COMPLETE_MISSION(p, message_obj=None, **kwargs):
    give_instruction = message_obj is None        
    if give_instruction:
        if p.get_tmp_variable('TEST_HUNT_MISSION_ADMIN', False):
            await redirect_to_state(p, state_TEST_HUNT_MISSION_ADMIN)
            return
        game.set_current_mission_as_completed(p)
        survery_time = (
            game.get_num_remaining_missions(p) == 0 or (
                params.JUMP_TO_SURVEY_AFTER and
                game.get_num_compleded_missions(p) == params.JUMP_TO_SURVEY_AFTER
            )
        )
        if survery_time:            
            game.set_game_end_time(p, finished=True)
            msg = p.ui().MSG_PRESS_FOR_ENDING
            kb = [[p.ui().BUTTON_END]]
            await send_message(p, msg, kb)
        else:                    
            msg = p.ui().MSG_PRESS_FOR_NEXT_MISSION
            kb = [[p.ui().BUTTON_NEXT_MISSION]]            
            await send_message(p, msg, kb)            
    else:
        text_input = message_obj.text
        kb = p.get_keyboard()
        if text_input in flatten(kb):
            if text_input == p.ui().BUTTON_NEXT_MISSION:
                if p.tmp_variables['SETTINGS'].get('WAIT_QR_MODE', False):
                    await redirect_to_state(p, state_WAIT_FOR_QR)                
                else:
                    await redirect_to_state(p, state_MISSION_INTRO)
            elif text_input == p.ui().BUTTON_END:
                await send_message(p, p.ui().MSG_TIME_STOP, remove_keyboard=True)
                await send_typing_action(p, sleep_time=1)
                await send_message(p, p.ui().MSG_CONGRATS_PRE_SURVEY)
                await send_typing_action(p, sleep_time=1)                
                settings = p.tmp_variables['SETTINGS']
                skip_survey = get_str_param_boolean(settings, 'SKIP_SURVEY')
                # saving data in airtable                
                await game.save_game_data_in_airtable(p, compute_times=True)
                if not skip_survey:
                    await redirect_to_state(p, state_SURVEY)
                else:
                    # end game
                    await redirect_to_state(p, state_END)
        else:
            await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS)        

# ================================
# Survey State
# ================================

async def state_SURVEY(p, message_obj=None, **kwargs):
    give_instruction = message_obj is None
    if give_instruction:        
        current_question = game.set_next_survey_question(p)
        questions_number = game.get_num_completed_survey_questions(p) + 1
        if questions_number == 1:
            await send_message(p, p.ui().MSG_SURVEY_INTRO)
            await send_typing_action(p, sleep_time=1)
        total_questions = game.get_tot_survey_questions(p)
        msg = '*Domanda {}/{}*: {}'.format(questions_number, total_questions, current_question['DOMANDA'])
        if 'RISPOSTE' in current_question:
            risposte = [x.strip() for x in current_question['RISPOSTE'].split(',')]
            kb = [risposte]
            await send_message(p, msg, kb)
        else:
            # no buttons -> no skip
            await send_message(p, msg, remove_keyboard=True)
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
                await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS)
                return
            if game.get_remaing_survey_questions_number(p) == 0:
                # end survey -> save survey data in airtable
                game.save_survey_data_in_airtable(p)
                await redirect_to_state(p, state_END)
            else:
                p.put()
                await repeat_state(p)
        else:
            if question_type_open:
                await send_message(p, p.ui().MSG_WRONG_INPUT_INSERT_TEXT_OR_BUTTONS)
            else:
                await send_message(p, p.ui().MSG_WRONG_INPUT_USE_BUTTONS)

# ================================
# Final State
# ================================

async def state_END(p, message_obj=None, **kwargs):    
    give_instruction = message_obj is None
    hunt_settings = p.tmp_variables['SETTINGS']
    reset_hunt_after_completion = get_str_param_boolean(hunt_settings, 'RESET_HUNT_AFTER_COMPLETION')
    if give_instruction:        
        penalty_hms, total_hms_game, ellapsed_hms_game, \
            total_hms_missions, ellapsed_hms_missions = game.get_elapsed_and_penalty_and_total_hms(p)
        penalty_sec = p.get_tmp_variable('penalty_sec')
        if penalty_sec > 0:
            msg = p.ui().MSG_END.format(penalty_hms, \
                total_hms_game, ellapsed_hms_game, total_hms_missions, ellapsed_hms_missions)        
        else:
            msg = p.ui().MSG_END_NO_PENALTY.format(\
                total_hms_game, total_hms_missions)        
        await send_message(p, msg, remove_keyboard=True)
        notify_group_id = game.get_notify_group_id(p)
        if notify_group_id:
            msg_game_penalty = f' ({ellapsed_hms_game} tempo + {penalty_hms} penalità)' if penalty_sec > 0 else ''
            msg_missioni_penalty = f' ({ellapsed_hms_missions} tempo + {penalty_hms} penalità)' if penalty_sec > 0 else ''
            msg_group = '\n'.join([
                f'Caccia {game.get_hunt_name(p)}:',
                f'🏁 La squadra *{game.get_group_name(p)}* ha completato la caccia al tesoro in *{total_hms_game}*{msg_game_penalty}',
                f'Ha completato le missioni in *{total_hms_missions}*{msg_missioni_penalty}'
            ])
            await send_message(notify_group_id, msg_group)                        
        final_message_key = 'MSG_FINAL_RESET_ON' if reset_hunt_after_completion else 'MSG_FINAL_RESET_OFF'
        await send_message(p, p.ui().get_var(final_message_key))     
        game.exit_game(p, save_data=True, reset_current_hunt=reset_hunt_after_completion)   
        if reset_hunt_after_completion:
            await restart(p)        
    else:
        # thisi only happens if RESET_HUNT_AFTER_COMPLETION is False:
        # checking reset_hunt flag to prevent msg to be shown 
        # in case of double click on button on previous state
        if not reset_hunt_after_completion:        
            # we need to tell them that we will let them know when the games is over
            msg = p.ui().MSG_HUNT_NOT_TERMINATED
            await send_message(p, msg)        
        


## +++++ END OF STATES +++++ ###

async def deal_with_callback_query(callback_query):
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
        validation_success = await approve_media_input_indovinello(p, approved, signature=approval_signature)
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

async def deal_with_admin_commands(p, message_obj):
    text_input = message_obj.text
    if p.is_error_reporter():
        if text_input == '/get_menu':
            menu = await get_menu(p)
            await send_message(p, menu.type)
            return True            
        if text_input == '/set_menu':
            assert set_menu(p)
            return True
        if text_input == '/del_menu':
            assert await remove_menu(p)
            return True
        if text_input == '/get_cmd':
            cmds = await get_commands(p)      
            await send_message(p, json.dumps(cmds, indent=3, ensure_ascii=False))
            return True            
        if text_input == '/set_cmd':
            assert await set_commands(p)            
            return True
        if text_input == '/del_cmd':
            assert await delete_commands(p)            
            return True            
        if text_input == '/debug':
            #await send_message(p, game.debug_tmp_vars(p), markdown=False)
            await send_text_document(p, 'tmp_vars.json', game.debug_tmp_vars(p))
            return True
        if text_input.startswith('/debug_'):
            user_id = text_input.split('_',1)[1]
            u = Person.get_by_id(user_id)
            if u:
                #await send_message(p, game.debug_tmp_vars(p), markdown=False)
                await send_text_document(p, 'tmp_vars.json', game.debug_tmp_vars(u))
            else:
                await send_message(p, f'User id {user_id} non valido')
            return True
        if text_input.startswith('/update_airtable_urls'):
            cmd_user_id = text_input.split()
            if len(cmd_user_id)==2:
                user_id = cmd_user_id[1]
                u = Person.get_by_id(user_id)    
            else:
                u = p
            if game.user_in_game(p):
                await send_message(p, 'Updating airtable urls... please wait...')
                updated_missions, updated_urls = game.update_airtable_urls_missions(u)
                await send_message(p, f'Done! Updated {updated_missions} missions and a total of {updated_urls} urls')
            else:
                await send_message(p, p.ui().MSG_NOT_IN_GAME)
            return True
        if text_input.startswith('/refresh_'):
            user_id = text_input.split('_',1)[1]
            u = Person.get_by_id(user_id)
            if u:
                await repeat_state(u)
                await send_message(p, f'User {user_id} refreshed!')
            else:
                await send_message(p, f'User id {user_id} non valido')
            return True
        if text_input.startswith('/terminate_'):
            user_id = text_input.split('_',1)[1]
            p.set_tmp_variable('TERMINATE_USER_ID', user_id)
            await redirect_to_state(p, state_TERMINATE_USER_CONFIRM)
            return True
        if text_input.startswith('/save_'):
            user_id = text_input.split('_',1)[1]
            u = Person.get_by_id(user_id)
            if u:   
                if game.user_in_game(u):
                    await game.save_game_data_in_airtable(u, compute_times=True)
                    await send_message(p, f'Dati salvati in airtable per {u.get_first_last_username()}')
                else:
                    await send_message(p, f'User id {user_id} non è in una caccia')
            else:
                await send_message(p, f'User id {user_id} non valido')
            return True
        if text_input.startswith('/restart_'):
            u_id = text_input.split('_',1)[1]
            u = Person.get_by_id(u_id)
            if u:
                if game.user_in_game(u):
                    game.exit_game(u, save_data=True, reset_current_hunt=True)
                    await send_message(u, p.ui().MSG_EXITED_FROM_GAME, remove_keyboard=True)
                await restart(u)
                msg_admin = 'User restarted: {}'.format(p.get_first_last_username())
                await send_message(p, msg_admin)
            else:
                msg_admin = 'No user found: {}'.format(u_id)
                await send_message(p, msg_admin)
            return True
        if text_input == '/version':
            msg = f'{settings.ENV_VERSION} {settings.APP_VERSION}'
            await send_message(p, msg)
            return True        
        if text_input.startswith('/test_zip'):
            pw = text_input.split()[1]
            zip_content = airtable_utils.download_media_zip(pw)
            if zip_content is None:
                await send_message(p, 'No media found')
            else:
                await send_text_document(p, 'media.zip', zip_content)      
            return True
        if text_input.startswith('/create_qrt'):
            code = text_input.split()[1]
            img_bytes = utility.create_qr(code, transparent=True)
            await send_sticker_data(p, img_bytes)
            return True
        if text_input.startswith('/create_qr'):
            code = text_input.split()[1]
            img_bytes = utility.create_qr(code, transparent=False)
            await send_sticker_data(p, img_bytes)
            return True
        if text_input == '/qr':
            # this doesn't seem to work:
            '''
            keyboard = [
                [telegram.InlineKeyboardButton("Scan QR codes", web_app=telegram.WebAppInfo(url=settings.WEB_APP_QR_URL))],
            ]            
            reply_markup = telegram.InlineKeyboardMarkup(keyboard)
            await send_message(p, 'Press button below to launch QR scanner', reply_markup=reply_markup)
            '''
            
            # display web-app
            kb = [
                [telegram.KeyboardButton(
                    "Scan QR Code",
                    web_app=telegram.WebAppInfo(settings.WEB_APP_QR_URL)
                )]
            ]
            await send_message(p, 'Press button below to launch QR scanner', kb=kb)
            return True 
        if text_input == '/features':
            # display web-app
            kb = [
                [telegram.KeyboardButton(
                    "MINIAPP FEATURES",
                    web_app=telegram.WebAppInfo(settings.APP_BASE_URL+'/miniapp_features')
                )]
            ]
            await send_message(p, 'Press button below to launch miniapp with features', kb=kb)
            return True 
        if text_input == '/sliders':
            # display web-app
            kb = [
                [telegram.KeyboardButton(
                    "MINIAPP SLIDERS",
                    web_app=telegram.WebAppInfo(settings.APP_BASE_URL+'/miniapp_sliders')
                )]
            ]
            await send_message(p, 'Press button below to launch miniapp with slider', kb=kb)
            return True 
        if text_input=='/botname':
            await send_message(p, settings.TELEGRAM_BOT_USERNAME)
            return True
        if text_input == '/test_inline_kb':
            await send_message(p, "Test inline keypboard", kb=[[p.ui().BUTTON_YES_CALLBACK('test'), p.ui().BUTTON_NO_CALLBACK('test')]], inline_keyboard=True)
            return True
        if text_input == '/random':
            from random import shuffle
            numbers = ['1','2','3','4','5']
            shuffle(numbers)
            numbers_str = ', '.join(numbers)
            await send_message(p, numbers_str)
            return True
        if text_input == '/exception':
            1/0
            return True
        if text_input == '/wait':
            for i in range(5):
                await send_message(p, str(i+1))
                await asyncio.sleep(i+1)
            await send_message(p, "end")
            return True
        if text_input.startswith('/echo '):
            text = text_input.split(' ', 1)[1]
            msg = '🔔 *Messaggio da hiSTORIC* 🔔\n\n' + text
            logging.debug("Test broadcast " + msg)
            await send_message(p, msg)
            return True
        if text_input.startswith('/broadcast '):
            text = text_input.split(' ', 1)[1]
            msg = '🔔 *Messaggio da hiSTORIC* 🔔\n\n' + text
            logging.debug("Starting to broadcast " + msg)
            await broadcast(p, msg)
            return True
        if text_input.startswith('/text '):
            u_id, text = text_input.split(' ',2)[1:]
            u = Person.get_by_id(u_id)
            if u is None:
                msg = 'ID not valid. Maybe you forgot T_?'
            elif await send_message(p, text, kb=p.get_keyboard()):
                msg = 'Message successfully sent to {}'.format(u.get_first_last_username())
            else:
                msg = 'Problems sending message to {}'.format(u.get_first_last_username())
            await send_message(p, msg, markdown=False)
            return True
        if text_input == '/reset_all_users':            
            await reset_all_users(message=None) #message=p.ui().MSG_THANKS_FOR_PARTECIPATING
            return True
    return False


async def deal_with_universal_command(p, message_obj):
    text_input = message_obj.text
    if not text_input.startswith('/'):
        return False
    if text_input.startswith('/start'):
        text_input_split = text_input.split()
        if game.user_in_game(p):
            if len(text_input_split)>1 and text_input_split[1].startswith('QR_'):
                qr_code = text_input_split[1].rsplit('_',1)[1] # code after last underscore
                if p.state == 'state_WAIT_FOR_QR':
                    await redirect_to_state(p, state_WAIT_FOR_QR, qr_code=qr_code)
                else:
                    await send_message(p, p.ui().MSG_WRONG_INPUT)
            else:
                await send_message(p, p.ui().MSG_YOU_ARE_IN_A_GAME_EXIT_FIRST)
        else:
            await redirect_to_state(p, state_INITIAL, message_obj)
        return True
    # change language (/it /en /de /ja)    
    if len(text_input)==3: 
        l = text_input[-2:].upper()
        if l in params.LANGUAGES:
            if game.user_in_game(p):
                await send_message(p, p.ui().MSG_NO_CHANGE_LANG_IN_HUNT, remove_keyboard=False)    
                return True
            else:
                p.set_language(l, put=True)
                await send_message(p, p.ui().MSG_LANGUAGE_SWITCHED)
                await send_typing_action(p, sleep_time=1)                    
                await repeat_state(p)
                return True
    if text_input == '/exit':        
        if game.user_in_game(p):
            await redirect_to_state(p, state_EXIT_CONFIRMATION)
            # msg = p.ui().MSG_EXIT_FROM_GAME_CONFIRM_COMMAND.format(escape_markdown('/exit_for_real'))
            # await send_message(p, msg)            
        else:
            await send_message(p, p.ui().MSG_NOT_IN_GAME)
        return True
    # if text_input == '/exit_for_real':
    #     if game.user_in_game(p):
    #         game.exit_game(p, save_data=False, reset_current_hunt=True)
    #         await send_message(p, p.ui().MSG_EXITED_FROM_GAME, remove_keyboard=True)
    #         await restart(p)
    #     else:
    #         await send_message(p, p.ui().MSG_NOT_IN_GAME)
    #     return True
    if text_input == '/state':
        state = p.get_state()
        msg = "You are in state {}".format(state)
        await send_message(p, msg, markdown=False)
        return True
    if text_input == '/refresh':
        await repeat_state(p)
        return True
    if text_input in ['/help', 'HELP', 'AIUTO']:
        await send_message(p, p.ui().MSG_SUPPORT)
        return True
    if text_input in ['/stop']:
        p.set_enabled(False, put=True)
        msg = "🚫 Hai *disabilitato* il bot.\n" \
              "In qualsiasi momento puoi riattivarmi scrivendomi qualcosa."
        await send_message(p, msg)
        return True
    return False

# ================================
# DEAL WITH REQUEST
# ================================
async def deal_with_request(request_json):
    # retrieve the message in JSON and then transform it to Telegram object
    update_obj = telegram.Update.de_json(request_json, BOT)
    if update_obj.callback_query:
        deal_with_callback_query(update_obj.callback_query)
        return 
    
    message_obj = update_obj.message
    
    if message_obj.chat.type == 'group':
        # ignore commands from group
        return
    
    user_obj = message_obj.from_user    
    
    chat_id = user_obj.id    
    username = user_obj.username
    last_name = user_obj.last_name if user_obj.last_name else ''
    name = user_obj.first_name
    lang = user_obj.language_code
    
    p = ndb_person.get_person_by_id_and_application(user_obj.id, 'telegram')

    if p == None:
        p = ndb_person.add_person(chat_id, name, last_name, username, lang, 'telegram')
        await report_admins('New user: {}'.format(p.get_first_last_username(escape_markdown=False)))
    else:
        _, was_disabled = p.update_info(name, last_name, username)
        if was_disabled:
            msg = "Bot riattivato!"
            await send_message(p, msg)

    if message_obj.forward_from and not p.is_admin_current_hunt():
        await send_message(p, p.ui().MSG_NO_FORWARDING_ALLOWED)
        return

    if message_obj.web_app_data:
        # got data from webapp
        # data = json.loads(message_obj.web_app_data.data)        
        # await send_message(p, f'data:{json.dumps(data, indent=3)}', remove_keyboard=True)
        datastring = message_obj.web_app_data.data
        if p.state == 'state_WAIT_FOR_QR':
             await redirect_to_state(p, state_WAIT_FOR_QR, qr_code=datastring)
        else:
            await send_message(p, f'data: {datastring}', markdown=False, remove_keyboard=True)
    else:
        text = message_obj.text
        if text:
            # got a message from use        
            text_input = message_obj.text        
            logging.debug('Message from @{} in state {} with text {}'.format(chat_id, p.state, text_input))
            if await deal_with_admin_commands(p, message_obj):
                return
            if await deal_with_universal_command(p, message_obj):
                return    
        logging.debug("Sending {} to state {} with input message_obj {}".format(p.get_first_name(), p.state, message_obj))
        await repeat_state(p, message_obj=message_obj)

possibles = globals().copy()
possibles.update(locals())
