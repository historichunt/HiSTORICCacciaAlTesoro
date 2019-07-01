import telegram
import telegram.error
from telegram.error import TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError
# from main_exception import retry_on_network_error
import key
import logging
import traceback
import bot_ux
import time
import ndb_person
from ndb_person import Person
from ndb_utils import client_context


BOT = telegram.Bot(token=key.TELEGRAM_TOKEN)

'''
If kb==None keep last keyboard
'''
# @retry_on_network_error
def send_message(p, text, kb=None, markdown=True, remove_keyboard=False, \
    inline_keyboard=False, sleep=False, **kwargs):
    #sendMessage(chat_id, text, parse_mode=None, disable_web_page_preview=None, disable_notification=False,
    # reply_to_message_id=None, reply_markup=None, timeout=None, **kwargs)
    if kb or remove_keyboard:
        if inline_keyboard:
            reply_markup = {  
                'inline_keyboard': kb
            }
        elif remove_keyboard:
            p.set_keyboard(kb=[])            
            reply_markup = telegram.ReplyKeyboardRemove()
        else:
            p.set_keyboard(kb)
            reply_markup = telegram.ReplyKeyboardMarkup(kb, resize_keyboard=True)
        BOT.sendMessage(
            chat_id = p.chat_id,
            text = text,
            parse_mode = telegram.ParseMode.MARKDOWN if markdown else None,
            reply_markup = reply_markup,
            **kwargs
        )
    else:
        try:
            BOT.sendMessage(
                chat_id = p.chat_id,
                text = text,
                parse_mode = telegram.ParseMode.MARKDOWN if markdown else None,
                **kwargs
            )
        except Unauthorized:
            logging.debug('User has blocked Bot: {}'.format(p))
            p.switch_notifications()
    if sleep:
        time.sleep(0.1)

def send_typing_action(p, sleep_time=None):    
    BOT.sendChatAction(
        chat_id = p.chat_id,
        action = telegram.ChatAction.TYPING
    )
    if sleep_time:
        time.sleep(sleep_time)


def send_media_url(p, url_attachment, kb=None, caption=None):
    attach_type = url_attachment.split('.')[-1].lower()            
    if attach_type in ['jpg','png','jpeg']:
        BOT.send_photo(p.chat_id, photo=url_attachment, caption=caption)
    elif attach_type in ['mp3']:
        BOT.send_audio(p.chat_id, audio=url_attachment, caption=caption)
    elif attach_type in ['gif']:
        BOT.send_animation(p.chat_id, animation=url_attachment, caption=caption)
    elif attach_type in ['mp4']:
        BOT.send_audio(p.chat_id, audio=url_attachment, caption=caption)
    else:            
        error_msg = "Found attach_type: {}".format(attach_type)
        logging.error(error_msg)
        raise ValueError('Wrong attach type: {}'.format(error_msg))

def send_text_document(p, file_name, file_content):
    import requests
    files = [('document', (file_name, file_content, 'text/plain'))]
    data = {'chat_id': p.chat_id}
    resp = requests.post(key.TELEGRAM_API_URL + 'sendDocument', data=data, files=files)
    logging.debug("Sent documnet. Response status code: {}".format(resp.status_code))

def get_photo_url_from_telegram(file_id):
    import requests
    r = requests.post(key.TELEGRAM_API_URL + 'getFile', data={'file_id': file_id})
    r_json = r.json()
    r_result = r_json['result']
    file_path = r_result['file_path']
    url = key.TELEGRAM_BASE_URL_FILE + file_path
    return url

bot_telegram_MASTER = None

@client_context
def report_master(message):
    global bot_telegram_MASTER
    if bot_telegram_MASTER is None:
        bot_telegram_MASTER = ndb_person.get_person_by_id(key.ADMIN_IDS[0])
    max_length = 2000
    if len(message)>max_length:
        chunks = (message[0+i:max_length+i] for i in range(0, len(message), max_length))
        for m in chunks:
            send_message(bot_telegram_MASTER, m, markdown=False)    
    else:
        send_message(bot_telegram_MASTER, message, markdown=False)

import utility

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

    from bot_telegram_dialogue import make_payer_exit_game
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
            if test and not p.is_tester():
                continue
            if blackList_sender and sender and p.get_id() == sender.get_id():
                continue
            total += 1
            if send_message(p, msg, sleepDelay=True): #p.enabled
                enabledCount += 1
                if exit_game:
                    make_payer_exit_game(p)

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
    from bot_telegram_dialogue import make_payer_exit_game

    if qry is None:
        qry = Person.query()
    qry = qry.order(Person._key)  # _MultiQuery with cursors requires __key__ order

    more = True
    cursor = None
    total = 0

    while more:
        users, cursor, more = qry.fetch_page(100, start_cursor=cursor)
        for p in users:
            if p.enabled:
                #if p.state == INITIAL_STATE:
                #    continue
                #logging.debug('Restarting {}'.format(p.chat_id))
                total += 1
                make_payer_exit_game(p, message)
            time.sleep(0.1)

    msg_admin = 'Resetted {} users.'.format(total)
    tell_admin(msg_admin)

# ================================
# UTILIITY TELL FUNCTIONS
# ================================

@client_context
def tell_admin(msg):
    logging.debug(msg)
    for uid in key.ADMIN_IDS:
        p = ndb_person.get_person_by_id(uid)
        send_message(p, msg, markdown=False)

def send_message_to_person(uid, msg, markdown=False):
    p = Person.get_by_id(uid)
    send_message(p, msg, markdown=markdown)
    if p and p.enabled:
        return True
    return False