# -*- coding: utf-8 -*-

from main_exception import SafeRequestHandler
import webapp2

import json
import jsonUtil
import logging
from time import sleep
import key
from person import Person

import requests
from main_exception import report_exception


# ================================
# Telegram Send Request
# ================================
def sendRequest(p, url, data, debugInfo):
    from google.appengine.api import urlfetch
    urlfetch.set_default_fetch_deadline(20)
    from main import tell_admin
    try:
        resp = requests.post(url, data)
        logging.info('Response: {}'.format(resp.text))
        resp_json = json.loads(resp.text)
        success = resp_json['ok']
        if success:
            return True
        else:
            status_code = resp.status_code
            error_code = resp_json['error_code']
            description = resp_json['description']
            if error_code == 403:
                # Disabled user
                p.setEnabled(False, put=True)
                #logging.info('Disabled user: ' + p.getFirstNameLastNameUserName())
            elif error_code == 400 and description == "INPUT_USER_DEACTIVATED":
                p.setEnabled(False, put=True)
                debugMessage = '❗ Input user disactivated: ' + p.getFirstNameLastNameUserName()
                logging.debug(debugMessage)
                tell_admin(debugMessage)
            else:
                debugMessage = '❗ Raising unknown err ({}).' \
                               '\nStatus code: {}\nerror code: {}\ndescription: {}.'.format(
                    debugInfo, status_code, error_code, description)
                logging.error(debugMessage)
                # logging.debug('recipeint_chat_id: {}'.format(recipient_chat_id))
                logging.debug('Telling to {} who is in state {}'.format(p.chat_id, p.state))
                tell_admin(debugMessage)
    except:
        report_exception()

# ================================
# SEND MESSAGE
# ================================

def send_message(p, msg, kb=None, markdown=True, inline_keyboard=False, one_time_keyboard=False,
                 sleepDelay=False, force_reply=False, remove_keyboard=False,
                 disable_web_page_preview=False):
    # reply_markup: InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardHide or ForceReply
    if inline_keyboard:
        replyMarkup = {  # InlineKeyboardMarkup
            'inline_keyboard': kb
        }
    elif kb:
        p.setLastKeyboard(kb, put=True)
        replyMarkup = {  # ReplyKeyboardMarkup
            'keyboard': kb,
            'resize_keyboard': True,
            'one_time_keyboard': one_time_keyboard,
        }
    elif remove_keyboard:
        p.setLastKeyboard([], put=True)
        replyMarkup = {
            'remove_keyboard': remove_keyboard
        }
    elif force_reply:
        replyMarkup = {  # ForceReply
            'force_reply': force_reply
        }
    else:
        replyMarkup = {}

    data = {
        'chat_id': p.chat_id,
        'text': msg,
        'disable_web_page_preview': disable_web_page_preview,
        'parse_mode': 'Markdown' if markdown else '',
        'reply_markup': json.dumps(replyMarkup),
    }
    debugInfo = "tell function with msg={} and kb={}".format(msg, kb)
    success = sendRequest(p, key.TELEGRAM_API_URL + 'sendMessage', data, debugInfo)
    if success:
        if sleepDelay:
            sleep(0.1)
        return True

# ================================
# SEND LOCATION
# ================================

def sendLocation(chat_id, latitude, longitude, kb=None):
    try:
        data = {
            'chat_id': chat_id,
            'latitude': latitude,
            'longitude': longitude,
        }
        resp = requests.post(key.TELEGRAM_API_URL + 'sendLocation', data)
        logging.info('send location: {}'.format(resp.text))
        if resp.status_code == 403:
            p = Person.query(Person.chat_id == chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.getFirstNameLastNameUserName())
    except:
        report_exception()

# ================================
# SEND VOICE
# ================================

def sendVoice(chat_id, file_id):
    try:
        data = {
            'chat_id': chat_id,
            'voice': file_id,
        }
        resp = requests.post(key.TELEGRAM_API_URL + 'sendVoice', data)
        logging.info('Response: {}'.format(resp.text))
    except:
        report_exception()


# ================================
# SEND PHOTO
# ================================

def sendPhotoViaUrlOrId(chat_id, url_id, kb=None, caption=None, inline_keyboard=False):
    try:
        if kb:
            if inline_keyboard:
                replyMarkup = {  # InlineKeyboardMarkup
                    'inline_keyboard': kb
                }
            else:
                replyMarkup = {  # ReplyKeyboardMarkup
                    'keyboard': kb,
                    'resize_keyboard': True,
                }
        else:
            replyMarkup = {}
        data = {
            'chat_id': chat_id,
            'photo': url_id,
            'reply_markup': json.dumps(replyMarkup),
        }
        if caption:
            data['caption'] = caption
        resp = requests.post(key.TELEGRAM_API_URL + 'sendPhoto', data)
        check_telegram_response(resp)
    except:
        report_exception()

# ================================
# SEND PHOTO
# ================================

def sendAnimationViaUrlOrId(chat_id, url_id, kb=None, caption=None, inline_keyboard=False):
    try:
        if kb:
            if inline_keyboard:
                replyMarkup = {  # InlineKeyboardMarkup
                    'inline_keyboard': kb
                }
            else:
                replyMarkup = {  # ReplyKeyboardMarkup
                    'keyboard': kb,
                    'resize_keyboard': True,
                }
        else:
            replyMarkup = {}
        data = {
            'chat_id': chat_id,
            'animation': url_id,
            'reply_markup': json.dumps(replyMarkup),
        }
        if caption:
            data['caption'] = caption
        resp = requests.post(key.TELEGRAM_API_URL + 'sendAnimation', data)
        check_telegram_response(resp)
    except:
        report_exception()

# ================================
# SEND PHOTO
# ================================

def sendVideoViaUrlOrId(chat_id, url_id, kb=None, caption=None, inline_keyboard=False):
    try:
        if kb:
            if inline_keyboard:
                replyMarkup = {  # InlineKeyboardMarkup
                    'inline_keyboard': kb
                }
            else:
                replyMarkup = {  # ReplyKeyboardMarkup
                    'keyboard': kb,
                    'resize_keyboard': True,
                }
        else:
            replyMarkup = {}
        data = {
            'chat_id': chat_id,
            'video': url_id,
            'reply_markup': json.dumps(replyMarkup),
        }
        if caption:
            data['caption'] = caption
        resp = requests.post(key.TELEGRAM_API_URL + 'sendVideo', data)
        check_telegram_response(resp)
    except:
        report_exception()

def sendPhotoFromPngImage(chat_id, img_data, filename='image.png'):
    try:
        img = [('photo', (filename, img_data, 'image/png'))]
        data = {
            'chat_id': chat_id,
        }
        resp = requests.post(key.TELEGRAM_API_URL + 'sendPhoto', data=data, files=img)
        check_telegram_response(resp)
    except:
        report_exception()

# ================================
# SEND AUDIO
# ================================

def sendAudioViaUrlOrId(chat_id, url_id, kb=None, caption=None, inline_keyboard=False):
    try:
        if kb:
            if inline_keyboard:
                replyMarkup = {  # InlineKeyboardMarkup
                    'inline_keyboard': kb
                }
            else:
                replyMarkup = {  # ReplyKeyboardMarkup
                    'keyboard': kb,
                    'resize_keyboard': True,
                }
        else:
            replyMarkup = {}
        data = {
            'chat_id': chat_id,
            'audio': url_id,
            'reply_markup': json.dumps(replyMarkup),
        }
        if caption:
            data['caption'] = caption
        resp = requests.post(key.TELEGRAM_API_URL + 'sendAudio', data)
        check_telegram_response(resp)
    except:
        report_exception()


# ================================
# Callback Query
# ================================

def answerCallbackQuery(callback_query_id, text):
    try:
        data = {
            'callback_query_id': callback_query_id,
            'text': text,
            'show_alert': True
        }
        resp = requests.post(key.TELEGRAM_API_URL + 'answerCallbackQuery', data)
        check_telegram_response(resp)
    except:
        report_exception()


def deleteMessage(chat_id, message_id):
    try:
        data = {
            'chat_id': chat_id,
            'message_id': message_id
        }
        resp = requests.post(key.TELEGRAM_API_URL + 'deleteMessage', data)
        logging.info('Response: {}'.format(resp.text))
    except:
        report_exception()


# ================================
# SEND DOCUMENT
# ================================

def sendDocument(chat_id, file_id):
    try:
        data = {
            'chat_id': chat_id,
            'document': file_id,
        }
        resp = requests.post(key.TELEGRAM_API_URL + 'sendDocument', data)
        check_telegram_response(resp)
    except:
        report_exception()

def sendExcelDocument(chat_id, sheet_tables, filename='file'):
    import utility
    try:
        xlsData = utility.convert_data_to_spreadsheet(sheet_tables)
        files = [('document', ('{}.xls'.format(filename), xlsData, 'application/vnd.ms-excel'))]
        data = {
            'chat_id': chat_id,
        }
        resp = requests.post(key.TELEGRAM_API_URL + 'sendDocument', data=data, files=files)
        check_telegram_response(resp)
    except:
        report_exception()

def sendTextDocument(chat_id, text, filename='file'):
    try:
        files = [('document', ('{}'.format(filename), text, 'text/plain'))]
        data = {
            'chat_id': chat_id,
        }
        resp = requests.post(key.TELEGRAM_API_URL + 'sendDocument', data=data, files=files)
        check_telegram_response(resp)
    except:
        report_exception()


# ================================
# SEND WAITING ACTION
# ================================

def sendWaitingAction(chat_id, action_tipo='typing', sleep_time=None):
    try:
        data = {
            'chat_id': chat_id,
            'action': action_tipo,
        }
        resp = requests.post(key.TELEGRAM_API_URL + 'sendChatAction', data)
        logging.info('send waiting action: {}'.format(resp.text))
        if resp.status_code==403:
            p = Person.query(Person.chat_id == chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.getFirstNameLastNameUserName())
        elif sleep_time:
            sleep(sleep_time)
    except:
        report_exception()

# ================================
# HANDLERS
# ================================

class MeHandler(webapp2.RequestHandler):
    def get(self):
        json_response = requests.get(key.TELEGRAM_API_URL + 'getMe').json()
        self.response.write(json.dumps(json_response))
        # self.response.write(json.dumps(json.load(urllib2.urlopen(key.TELEGRAM_API_URL + 'getMe'))))

class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        allowed_updates = ["message", "edited_message", "inline_query", "chosen_inline_result", "callback_query"]
        data = {
            'url': key.TELEGRAM_WEBHOOK_URL,
            'allowed_updates': json.dumps(allowed_updates),
        }
        resp = requests.post(key.TELEGRAM_API_URL + 'setWebhook', data)
        logging.info('SetWebhook Response: {}'.format(resp.text))
        self.response.write(resp.text)

class GetWebhookInfo(webapp2.RequestHandler):
    def get(self):
        resp = requests.post(key.TELEGRAM_API_URL + 'getWebhookInfo')
        logging.info('GetWebhookInfo Response: {}'.format(resp.text))
        self.response.write(resp.text)

class DeleteWebhook(webapp2.RequestHandler):
    def get(self):
        resp = requests.post(key.TELEGRAM_API_URL + 'deleteWebhook')
        logging.info('DeleteWebhook Response: {}'.format(resp.text))
        self.response.write(resp.text)

# ================================
# WEBHOOK HANDLER
# ================================
class WebhookHandler(SafeRequestHandler):

    def post(self):
        from main import dealWithUserInteraction, dealWithCallbackQuery
        from main_exception import deferredSafeHandleException
        from google.appengine.ext import deferred
        from google.appengine.api import urlfetch
        urlfetch.set_default_fetch_deadline(20)
        body = jsonUtil.json_loads_byteified(self.request.body)
        logging.info('request body: {}'.format(body))
        # self.response.write(json.dumps(body))

        # update_id = body['update_id']
        if 'callback_query' in body:
            dealWithCallbackQuery(body['callback_query'])
            return

        if 'message' not in body:
            return
        message = body['message']
        if 'chat' not in message:
            return

        chat = message['chat']
        chat_id = str(chat['id'])
        if 'first_name' not in chat:
            return
        text = message.get('text') if 'text' in message else ''
        name = chat['first_name']
        last_name = chat['last_name'] if 'last_name' in chat else None
        username = chat['username'] if 'username' in chat else None
        location = message['location'] if 'location' in message else ''
        contact = message['contact'] if 'contact' in message else ''
        photo = message.get('photo') if 'photo' in message else ''
        document = message.get('document') if 'document' in message else ''
        voice = message.get('voice') if 'voice' in message else ''

        deferredSafeHandleException(dealWithUserInteraction,
            chat_id, name, last_name, username,
            application='telegram', text=text,
            location=location, contact=contact,
            photo=photo, document=document, voice=voice
        )

        # dealWithUserInteraction(
        #     chat_id, name, last_name, username,
        #     application='telegram', text=text,
        #     location=location, contact=contact,
        #     photo=photo, document=document, voice=voice
        # )

def check_telegram_response(resp):
    from main import tell_admin
    import inspect
    previous_method =  inspect.stack()[1][3]
    response = resp.text.encode('utf-8')
    logging.info('Response: {}'.format(response))
    resp_json = json.loads(resp.text)
    success = resp_json['ok']
    if not success:
        msg = "❗ Response problem from {}: {}".format(previous_method, response)
        tell_admin(msg)
