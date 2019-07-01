import bot_telegram
from bot_telegram import BOT
import key 

def get_ngrok_base():
    import requests
    r = requests.get('http://localhost:4040/api/tunnels')
    remote_base = next(t['public_url'] for t in r.json()['tunnels'] if t["proto"]=="https")
    return remote_base


def set_webhook():
    from params import USE_NGROK
    base_url = get_ngrok_base() if USE_NGROK else key.GAE_SERVER_URL
    webhook_url = '{}{}'.format(base_url, key.TELEGRAM_WEBHOOK_PATH)
    s = BOT.setWebhook(webhook_url, allowed_updates=['message','callback_query'])
    if s:
        print("webhook setup ok: {}".format(webhook_url))
    else:
        return("webhook setup failed")


def delete_webhook():
    BOT.deleteWebhook()


def get_webhook_info():
    print(BOT.get_webhook_info())


if __name__ == "__main__":    
    set_webhook()