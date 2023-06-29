import telegram
import telegram.error
from telegram.error import (TelegramError, Unauthorized)
import logging
import time
from historic.bot.bot_ui import COMMANDS_LANG
from historic.config import settings
from historic.bot import game, utility
from historic.bot.ndb_person import Person
from io import BytesIO

BOT = telegram.Bot(token=settings.TELEGRAM_API_TOKEN)

def get_chat_id_from_str(s):
    if s.startswith('T_'): 
        return s[2:]
    return s # e.g., HISTORIC_GROUP for notification has id "-1001499..."

def make_kb_serializable(kb):
    new_kb = []
    for line in kb:
        new_kb.append(
            [
                b.text 
                if type(b)==telegram.KeyboardButton
                else b
                for b in line
            ]
        )
    return new_kb

def get_reply_markup(p, kb=None, remove_keyboard=None, inline_keyboard=False):
    is_person = isinstance(p, Person)
    if kb or remove_keyboard:
        if inline_keyboard:
            return {'inline_keyboard': kb}
        elif remove_keyboard:
            if is_person:
                p.set_keyboard(kb=[])            
            return telegram.ReplyKeyboardRemove()
        else:
            if is_person:
                saved_kb = make_kb_serializable(kb)
                p.set_keyboard(saved_kb)
            return telegram.ReplyKeyboardMarkup(kb, resize_keyboard=True)
    return None
'''
If kb==None keep last keyboard
'''
# @retry_on_network_error
def send_message(p, text, kb=None, markdown=True, remove_keyboard=False, \
    inline_keyboard=False, sleep=False, **kwargs):
    chat_id = p.chat_id if isinstance(p, Person) else get_chat_id_from_str(p)
    reply_markup = get_reply_markup(p, kb, remove_keyboard, inline_keyboard)
    try:
        BOT.send_message(
            chat_id = chat_id,
            text = text,
            parse_mode = telegram.ParseMode.MARKDOWN if markdown else None,
            reply_markup = reply_markup,
            disable_web_page_preview = True,
            **kwargs
        )
    except Unauthorized:
        logging.debug('User has blocked Bot: {}'.format(chat_id))
        return False
    except TelegramError as e:
        logging.debug('Exception in reaching user {}: {}'.format(chat_id, e))
        return False
    if sleep:
        time.sleep(0.1)
    return True

def send_location(p, lat, lon):
    chat_id = p.chat_id if isinstance(p, Person) else get_chat_id_from_str(p)
    loc = telegram.Location(lon,lat)
    BOT.send_location(chat_id, location = loc)

def send_typing_action(p, sleep_time=None):    
    chat_id = p.chat_id if isinstance(p, Person) else get_chat_id_from_str(p)
    BOT.sendChatAction(
        chat_id = chat_id,
        action = telegram.ChatAction.TYPING
    )
    if sleep_time:
        time.sleep(sleep_time)

def send_photo_data(p, img_content, kb=None, caption=None,
    remove_keyboard=False, inline_keyboard=False, markdown=True):
    
    rm = get_reply_markup(p, kb, remove_keyboard, inline_keyboard)      
    chat_id = p.chat_id if isinstance(p, Person) else get_chat_id_from_str(p)
    parse_mode = telegram.ParseMode.MARKDOWN if markdown else None 
    data = BytesIO(img_content)
    BOT.send_photo(
        chat_id, photo=data, caption=caption, 
        reply_markup=rm, parse_mode=parse_mode
    )

def send_media_url(p, url_attachment, type='image/png', kb=None, caption=None,
    remove_keyboard=False, inline_keyboard=False, markdown=True):
    chat_id = p.chat_id if isinstance(p, Person) else get_chat_id_from_str(p)
    # attach_type = url_attachment.rsplit('.',1)[1].lower()     
    # if '?' in attach_type:
    #     attach_type = attach_type.split('?')[0]
    attach_type = type.split('/')[1]    
    rm = get_reply_markup(p, kb, remove_keyboard, inline_keyboard)       
    parse_mode = telegram.ParseMode.MARKDOWN if markdown else None 
    if attach_type in ['jpg','png','jpeg']:
        try:
            BOT.send_photo(chat_id, photo=url_attachment, caption=caption, reply_markup=rm, parse_mode=parse_mode)
        except telegram.error.BadRequest:
            report_admins(f'Error on sending photo: {url_attachment}')
    elif attach_type in ['mp3']:
        BOT.send_audio(chat_id, audio=url_attachment, caption=caption, reply_markup=rm)
    elif attach_type in ['ogg']:
        BOT.send_voice(chat_id, voice=url_attachment, caption=caption, reply_markup=rm)       
    elif attach_type in ['gif']:        
        BOT.send_animation(chat_id, animation=url_attachment, caption=caption, reply_markup=rm)
    elif attach_type in ['mp4']:
        BOT.send_video(chat_id, video=url_attachment, caption=caption, reply_markup=rm)
    elif attach_type in ['tgs']:
        BOT.send_sticker(chat_id, sticker=url_attachment, reply_markup=rm)
    else:            
        error_msg = "Found attach_type: {}".format(attach_type)
        logging.error(error_msg)
        raise ValueError('Wrong attach type: {}'.format(error_msg))

def send_text_document(p, file_name, file_content, caption=None):
    import requests
    chat_id = p.chat_id if isinstance(p, Person) else get_chat_id_from_str(p)
    files = [('document', (file_name, file_content, 'text/plain'))]
    data = {'chat_id': chat_id}
    if caption:
        data['caption'] = caption
    resp = requests.post(settings.TELEGRAM_API_URL + 'sendDocument', data=data, files=files)
    logging.debug("Sent documnet. Response status code: {}".format(resp.status_code))

def get_photo_url_from_telegram(file_id):
    import requests    
    r = requests.post(settings.TELEGRAM_API_URL + 'getFile', data={'file_id': file_id})
    r_json = r.json()
    success = r_json['ok']
    if success:
        r_result = r_json['result']
        file_path = r_result['file_path']
        url = settings.TELEGRAM_BASE_URL_FILE + file_path
    else:
        url = 'https://via.placeholder.com/800x600?text=Image deleted'
    return url

def report_admins(message):
    logging.debug('Reporting to admin: {}'.format(message))
    max_length = 2000
    if len(message)>max_length:
        chunks = (message[0+i:max_length+i] for i in range(0, len(message), max_length))
        for m in chunks:
            for id in settings.ERROR_REPORTERS_IDS:
                send_message(id, m, markdown=False, sleep=True)
    else:
        for id in settings.ERROR_REPORTERS_IDS:
            send_message(id, message, markdown=False, sleep=True)

def report_location_admin(lat, lon):
    for id in settings.ERROR_REPORTERS_IDS:
        send_location(id, lat, lon)

# ---------
# MENU
# ---------

def get_menu(p):
    return BOT.get_chat_menu_button(
        chat_id=p.chat_id
    )

def set_menu(p):
    menu_button = telegram.MenuButtonCommands()
    return BOT.set_chat_menu_button(
        p.chat_id, 
        menu_button
    )

def remove_menu(p):
    return BOT.set_chat_menu_button(
        p.chat_id, 
        telegram.MenuButtonDefault()
    )

# ---------
# COMMANDS
# ---------

def get_commands(p):
    return  [
        (c.command, c.description) 
        for c in BOT.get_my_commands(
            scope=telegram.BotCommandScopeChat(p.chat_id)
        )
    ]

def delete_commands(p):
    return BOT.delete_my_commands(
        scope=telegram.BotCommandScopeChat(p.chat_id)
    )

def set_commands(p):
    lang = p.language
    return BOT.set_my_commands(
        commands=COMMANDS_LANG(lang),
        scope=telegram.BotCommandScopeChat(p.chat_id)
    )

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

def broadcast(sender, msg, qry = None, blackList_sender=False, sendNotification=True, test=False):

    if qry is None:
        qry = Person.query()
    qry = qry.order(Person._key) #_MultiQuery with cursors requires __key__ order

    more = True
    cursor = None
    total, enabledCount = 0, 0

    while more:
        users, cursor, more = qry.fetch_page(100, start_cursor=cursor)
        for p in users:
            if not p.enabled:
                continue
            if p.chat_id[0] == '-': # negative id for groups
                continue
            if test and not p.is_global_admin():
                continue
            if blackList_sender and sender and p.get_id() == sender.get_id():
                continue
            total += 1
            if send_message(p, msg, sleep=True): #p.enabled
                enabledCount += 1

    disabled = total - enabledCount
    msg_debug = BROADCAST_COUNT_REPORT.format(total, enabledCount, disabled)
    logging.debug(msg_debug)
    if sendNotification:
        send_message(sender, msg_debug)
    #return total, enabledCount, disabled

# ---------
# Restart All
# ---------

def reset_all_users(qry = None, message=None):
    from historic.bot.bot_telegram_dialogue import restart
    if qry is None:
        qry = Person.query()
    qry = qry.order(Person._key)  # _MultiQuery with cursors requires __key__ order

    more = True
    cursor = None
    total = 0

    while more:
        users, cursor, more = qry.fetch_page(100, start_cursor=cursor)
        for p in users:
            if p.state == 'state_INITIAL':
                continue
            if p.enabled:
                total += 1
                if game.user_in_game(p):
                    game.exit_game(p, save_data=False, reset_current_hunt=True)
                    # send_message(p, p.ui().MSG_EXITED_FROM_GAME, remove_keyboard=True)
                if message:
                    send_message(p, message, remove_keyboard=True)
                p.reset_tmp_variables()
                restart(p)
                time.sleep(0.2)

    msg_admin = 'Resetted {} users.'.format(total)
    report_admins(msg_admin)

def remove_keyboard_from_group(chat_id):
    send_message(chat_id, 'Removing Keyboard', remove_keyboard=True)

# ================================
# UTILIITY TELL FUNCTIONS
# ================================

def send_message_to_person(uid, msg, markdown=False):
    p = Person.get_by_id(uid)
    send_message(p, msg, markdown=markdown)
    if p and p.enabled:
        return True
    return False