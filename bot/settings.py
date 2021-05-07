import os
from airtable import Airtable
from bot import ndb_envvar

APP_NAME = 'historictrentobot'
APP_VERSION = '0.2.1'
CLOUD_ENVS = ['test', 'production']
GAE_SERVER = 'GAE_VERSION' in os.environ # check if we are on the cloud version
ROOT_DIR = os.path.dirname(os.path.dirname(__file__)) # base dir (works both in flask and gunicorn)

# PARAMS
MAX_TEAM_NAME_LENGTH = 30
WORK_IN_PROGRESS = False
JUMP_TO_SURVEY_AFTER = False  # 2

if GAE_SERVER:
    # cloud version
    ENV_VERSION = os.environ.get('GAE_VERSION') # test or production
    APP_BASE_URL = 'https://{}-dot-{}.appspot.com'.format(ENV_VERSION, APP_NAME)    
    ENV_VARS = ndb_envvar.get_all(ENV_VERSION)
else:
    # local version
    from bot import ngrok 
    # APP_BASE_URL = ngrok.get_ngrok_base()
    APP_BASE_URL = ngrok.start_pyngrok()    
    print(f'Running local version: {APP_BASE_URL}')

    # check local environments    
    LOCAL_ENV_FILES = [
        f for f in os.listdir(ROOT_DIR) 
        if (
            f.startswith('.env') and
            not any(f.endswith(x) for x in CLOUD_ENVS)
        )
    ]

    if LOCAL_ENV_FILES:
        # use settings in .env_
        from dotenv import dotenv_values
        LOCAL_ENV = os.path.join(ROOT_DIR, LOCAL_ENV_FILES[0])
        ENV_VERSION = LOCAL_ENV.split('.env_')[1] # what follows '.env_'
        print(f'Using settings specified in {LOCAL_ENV}')
        ENV_VARS = dotenv_values(LOCAL_ENV)
    else:
        ENV_VERSION = 'test'
        print(f'Using test bot')
        ENV_VARS = ndb_envvar.get_all(ENV_VERSION)


# ENVIRONMENT VARIABLES (SECRETS IN DB/.env_ file)
TELEGRAM_API_TOKEN = ENV_VARS.get("TELEGRAM_API_TOKEN")
AIRTABLE_API_KEY = ENV_VARS.get("AIRTABLE_API_KEY")
AIRTABLE_CONFIG_ID = ENV_VARS.get("AIRTABLE_CONFIG_ID")
HISTORIC_NOTIFICHE_GROUP_CHAT_ID = ENV_VARS.get("HISTORIC_NOTIFICHE_GROUP_CHAT_ID")
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

ADMIN_IDS = [
    row['fields']['ID']
    for row in MANAGERS_CONFIG_TABLE.get_all()
    if row['fields'].get('Admin', False) and not row['fields'].get('Disabled', False)
]