# -*- coding: utf-8 -*-

from google.appengine.api import urlfetch
from main_exception import SafeRequestHandler

import jsonUtil
import logging
import key

import requests
import json

json_headers = {'Content-type': 'application/json'}

def setGetStartedButton():
    from main import tell_admin
    response_data = {
        "get_started": {
            "payload":"START"
        }
    }
    response_data_str = json.dumps(response_data)

    try:
        logging.info('sending menu with json: {}'.format(response_data))
        resp = requests.post(key.FACEBOOK_PROFILE_API_URL, data=response_data_str, headers=json_headers)
        logging.info('responding to request: {}'.format(resp.text))
        tell_admin('Response to GetStartedButton: {}'.format(resp.text))
        return resp.status_code == 200
    except:
        report_exception()

def setFB_Menu():
    setMenu(['INIZIO','IMPOSTAZIONI','AIUTO','STOP'])

def setMenu(menu_items):
    from main import tell_admin
    response_data = {
        "persistent_menu": [
            {
                "locale": "default",
                "composer_input_disabled": False, #Set to true to disable user input in the menu. This means users will only be able to interact with your bot via the menu, postbacks, buttons, and webviews.
                "call_to_actions": [
                    {
                        "title": "Opzioni",
                        "type": "nested",
                        "call_to_actions": [
                            {
                                "type": "postback",
                                "title": i,
                                "payload": i,
                            }
                            for i in menu_items
                        ]
                    },
                    {
                        "title": "Links",
                        "type": "nested",
                        "call_to_actions": [
                            {
                                "type": "web_url",
                                "title": "Telegram bot",
                                "url": "https://t.me/hiSTORIC_bot",
                                "webview_height_ratio": "tall"  # compact, tall, full
                            },
                            {
                                "type": "web_url",
                                "title": "Website",
                                "url": "http://pickmeup.trentino.it",
                                "webview_height_ratio": "tall"  # compact, tall, full
                            }

                        ]
                    },

                ]
            },
            #{
            #    "locale": "default",
            #    "composer_input_disabled": False #Set to true to disable user input in the menu. This means users will only be able to interact with your bot via the menu, postbacks, buttons, and webviews.
            #}
        ]
    }
    response_data_str = json.dumps(response_data)

    try:
        logging.info('sending menu with json: {}'.format(response_data))
        resp = requests.post(key.FACEBOOK_PROFILE_API_URL, data=response_data_str, headers=json_headers)
        logging.info('responding to request: {}'.format(resp.text))
        tell_admin('Response to set persisten menu: {}'.format(resp.text))
        return resp.status_code == 200
    except:
        report_exception()

def sendMsgRequest(p, request_data):
    request_data_str = json.dumps(request_data)
    try:
        logging.info('responding to request with message: {}'.format(request_data))
        resp = requests.post(key.FACEBOOK_MSG_API_URL, data=request_data_str, headers=json_headers)
        logging.info('responding to request: {}'.format(resp.text))
        logging.info('status code: {}'.format(resp.status_code))
        code = resp.status_code
        if code == 403:
            # Disabled user
            p.setEnabled(False, put=True)
            # logging.info('Disabled user: ' + p.getFirstNameLastNameUserName())
        return code == 200
    except:
        report_exception()


def sendMessage(p, msg):
    msg = msg.replace('*','')
    request_data = {
        "recipient": {
            "id": p.chat_id
        },
        "message": {
            "text": msg,
        }
    }
    logging.info('message request (simple): {}'.format(request_data))
    return sendMsgRequest(p, request_data)

# max 11 reply_items
def sendMessageWithQuickReplies(p, msg, reply_items):
    msg = msg.replace('*', '')
    request_data = {
        "recipient": {
            "id": p.chat_id
        },
        "message": {
            "text": msg,
            "quick_replies": [
                {
                    "content_type": "text",
                    "title": i,
                    "payload": i
                }
                for i in reply_items
            ]
        }
    }
    logging.info('message request with quick replies: {}'.format(request_data))
    return sendMsgRequest(p, request_data)

# max 3 button_items
def sendMessageWithButtons(p, msg, button_items):
    msg = msg.replace('*', '')
    request_data = {
        "recipient": {
            "id": p.chat_id
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": msg,
                    "buttons": [
                        {
                            "type": "postback",
                            "title": i,
                            "payload": i
                        }
                        for i in button_items
                    ]
                }
            }
        }
    }
    logging.info('message request with buttons: {}'.format(request_data))
    return sendMsgRequest(p, request_data)


def sendMessageWithList(p, msg, button_items):
    from main import tell_admin
    msg = msg.replace('*', '')
    request_data = {
        "recipient": {
            "id": p.chat_id
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "list",
                    "top_element_style": "compact", # large, compact
                    "elements": [
                        {
                            "title": i,
                            "subtitle": i,
                            "default_action": {
                                "type": "postback",
                                "payload": i
                            }
                        }
                        for i in button_items
                    ]
                }
            }
        }
    }
    logging.info('message request with list: {}'.format(request_data))
    request_data_str = json.dumps(request_data)
    try:
        logging.info('responding to request with message: {}'.format(request_data))
        resp = requests.post(key.FACEBOOK_MSG_API_URL, data=request_data_str, headers=json_headers)
        tell_admin('response to request with list: {}'.format(resp.text))
        logging.info('status code: {}'.format(resp.status_code))
        code = resp.status_code
        if code == 403:
            # Disabled user
            p.setEnabled(False, put=True)
            # logging.info('Disabled user: ' + p.getFirstNameLastNameUserName())
        return code == 200
    except:
        report_exception()

def sendPhotoUrl(p, url):
    request_data = {
        "recipient": {
            "id": p.chat_id
        },
        "message": {
            "attachment": {
                "type": "file",
                "payload": {
                    "url": url
                }
            }
        }
    }
    logging.info('send photo (url) request: {}'.format(request_data))
    return sendMsgRequest(p, request_data)

def sendPhotoData(p, file_data, filename):
    request_data = {
        "recipient": json.dumps(
            {
                "id": p.chat_id
            }
        ),
        "message": json.dumps(
            {
                "attachment": {
                    "type": "image",
                    "payload": {}
                }
            }
        )
    }

    files = {
        "filedata": (filename, file_data, 'image/png')
    }

    try:
        logging.info('sending photo data: {}'.format(request_data))
        resp = requests.post(key.FACEBOOK_MSG_API_URL, data=request_data, files=files)
        logging.info('responding to photo request: {}'.format(resp.text))
        return resp.status_code == 200
    except:
        report_exception()


def getUserInfo(user_id):
    url = key.FACEBOOK_BASE_API + \
          '/{}?fields=first_name,last_name,profile_pic,locale,timezone,gender' \
          '&access_token={}'.format(user_id, key.FACEBOOK_PAGE_ACCESS_TOKEN)
    logging.debug('Sending user info request: {}'.format(url))
    r = requests.get(url)
    json = r.json()
    first_name = json.get('first_name', None)
    last_name = json.get('last_name', None)
    logging.debug('Getting first name = {} and last name = {}'.format(first_name, last_name))
    return first_name, last_name

class WebhookHandler(SafeRequestHandler):

    # to confirm the webhook url
    def get(self):
        #urlfetch.set_default_fetch_deadline(60)
        logging.info('verification request: {}'.format(self.request.body))
        verify_token = self.request.get('hub.verify_token')
        if verify_token == key.FACEBOOK_VERIFY_TOKEN:
            challenge = self.request.get('hub.challenge')
            self.response.write(challenge)
        else:
            self.response.http_status_message(403)

    # to handle user interaction
    def post(self):
        from main import dealWithUserInteraction
        #urlfetch.set_default_fetch_deadline(60)
        body = jsonUtil.json_loads_byteified(self.request.body)
        logging.info('request body: {}'.format(body))
        messaging = body['entry'][0]['messaging'][0]
        chat_id = messaging['sender']['id']
        text = messaging.get('message', {}).get('text', '')
        if text=='':
            text = messaging.get('postback', {}).get('payload', '')
        #attachment = messaging.get('message', {}).get('attachments', [{}])[0]
        #voice_url = attachment.get('payload',{}).get('url',None) if attachment.get('type',None)=='audio' else None
        location = messaging.get('message', {}).get('attachments', [{}])[0].get('payload', {}).get('coordinates', None)
        # {"lat": 46.0, "long": 11.1}
        if location:
            location = {'latitude': location['lat'], 'longitude': location['long'] }

        # we need this as fb is send all sort of notification when user is active without sending any message
        if text=='' and location is None:
            return

        name, last_name = getUserInfo(chat_id)

        dealWithUserInteraction(chat_id, name=name, last_name=last_name, username=None,
                                application='messenger', text=text,
                                location=location, contact=None, photo=None, document=None, voice=None)



def report_exception():
    from main import tell_admin
    import traceback
    msg = "❗ Detected Exception: " + traceback.format_exc()
    tell_admin(msg)
    logging.error(msg)
