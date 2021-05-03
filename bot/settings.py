import os
from airtable import Airtable
from bot import ndb_envvar

APP_NAME = 'historictrentobot'
APP_VERSION = '0.1.1'

# PARAMS
NGROK = False # set to True for local testing
ENV_VERSION = os.environ.get('GAE_VERSION', 'test') # test or production
MAX_TEAM_NAME_LENGTH = 30
WORK_IN_PROGRESS = False
JUMP_TO_SURVEY_AFTER = False  # 2

if NGROK:
    # local version
    from bot import ngrok 
    APP_BASE_URL = ngrok.get_ngrok_base()
else:
    # cloud version
    APP_BASE_URL = 'https://{}-dot-{}.appspot.com'.format(ENV_VERSION, APP_NAME)

# ENVIRONMENT VARIABLES (SECRETS IN DB)
ENV_VARS = ndb_envvar.get_all(ENV_VERSION)
TELEGRAM_API_TOKEN = ENV_VARS.get("TELEGRAM_API_TOKEN")
AIRTABLE_API_KEY = ENV_VARS.get("AIRTABLE_API_KEY")
AIRTABLE_CONFIG_ID = ENV_VARS.get("AIRTABLE_CONFIG_ID")
HISTORIC_NOTIFICHE_GROUP_CHAT_ID = ENV_VARS.get("HISTORIC_NOTIFICHE_GROUP_CHAT_ID")
ADMIN_ID = ENV_VARS.get("ADMIN_ID")
DEPLOY_NOTIFICATION_WEBHOOK_URL_ROUTING = ENV_VARS.get("DEPLOY_NOTIFICATION_WEBHOOK_URL_ROUTING")
DEPLOY_NOTIFICATION_WEBHOOK_SECRET = ENV_VARS.get("DEPLOY_NOTIFICATION_WEBHOOK_SECRET")

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