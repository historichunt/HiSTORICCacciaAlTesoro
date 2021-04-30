import os 
from airtable import Airtable
from dotenv import load_dotenv

APP_NAME = 'historictrentobot'
APP_VERSION = '0.1.0'

# PARAMS
NGROK = False # set to True for local testing
ENV_VERSION = 'test' # test or production
MAX_TEAM_NAME_LENGTH = 30
WORK_IN_PROGRESS = False
JUMP_TO_SURVEY_AFTER = False  # 2

# on cloud env file does not exists and this will be ignored
env_file = f'.env_{ENV_VERSION}' 
dotenv_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 
    env_file
)
load_dotenv(dotenv_path)

if NGROK:
    # local version
    from bot import ngrok 
    APP_BASE_URL = ngrok.get_ngrok_base()
else:
    # cloud version
    APP_BASE_URL = 'https://{}-dot-{}.appspot.com'.format(ENV_VERSION, APP_NAME)

TELEGRAM_API_TOKEN = os.environ.get("TELEGRAM_API_TOKEN")
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME")
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_CONFIG_ID = os.environ.get("AIRTABLE_CONFIG_ID")
HISTORIC_NOTIFICHE_GROUP_CHAT_ID = os.environ.get("HISTORIC_NOTIFICHE_GROUP_CHAT_ID")
ADMIN_ID = os.environ.get("ADMIN_ID")

WEBHOOK_TELEGRAM_ROUTING = '/webhook_{}'.format(TELEGRAM_API_TOKEN)
WEBHOOK_TELEGRAM_BASE = APP_BASE_URL + WEBHOOK_TELEGRAM_ROUTING
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/'
TELEGRAM_BASE_URL_FILE = f'https://api.telegram.org/file/bot{TELEGRAM_API_TOKEN}/'

MANAGERS_CONFIG_TABLE = Airtable(
    AIRTABLE_CONFIG_ID, 
    'Managers', 
    api_key=AIRTABLE_API_KEY
)

MANAGER_IDS = [
    row['fields']['ID']
    for row in MANAGERS_CONFIG_TABLE.get_all()
    if not row['fields'].get('Disabled', False)
]