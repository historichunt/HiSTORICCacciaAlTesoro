import os
from airtable import Airtable
from historic.bot import ndb_envvar
from historic.config.params import ROOT_DIR

APP_NAME = 'historictrentobot'
APP_VERSION = '0.9.27'
CLOUD_ENVS = ['test', 'production']
GAE_SERVER = 'GAE_VERSION' in os.environ # check if we are on the cloud version

if GAE_SERVER:
    # cloud version
    ENV_VERSION = os.environ.get('GAE_VERSION') # test or production
    APP_BASE_URL = 'https://{}-dot-{}.appspot.com'.format(ENV_VERSION, APP_NAME)    
    ENV_VARS = ndb_envvar.get_all(ENV_VERSION)
    LOCAL_ENV_FILES = None
else:
    # local version
    from historic.bot import ngrok 
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
        ENV_VARS = dotenv_values(LOCAL_ENV)
    else:
        ENV_VERSION = 'test'
        print(f'Using test bot')
        ENV_VARS = ndb_envvar.get_all(ENV_VERSION)
    print(f'Using settings: {ENV_VERSION}')


# ENVIRONMENT VARIABLES (SECRETS IN DB/.env_ file)
TELEGRAM_API_TOKEN = ENV_VARS.get("TELEGRAM_API_TOKEN")
AIRTABLE_API_KEY = ENV_VARS.get("AIRTABLE_API_KEY")
AIRTABLE_CONFIG_ID = ENV_VARS.get("AIRTABLE_CONFIG_ID")
DEPLOY_NOTIFICATION_WEBHOOK_URL_ROUTING = ENV_VARS.get("DEPLOY_NOTIFICATION_WEBHOOK_URL_ROUTING")
DEPLOY_NOTIFICATION_WEBHOOK_SECRET = ENV_VARS.get("DEPLOY_NOTIFICATION_WEBHOOK_SECRET")
UI_SPREADSHEET_KEY = ENV_VARS.get("UI_SPREADSHEET_KEY")

WEBHOOK_TELEGRAM_ROUTING = '/webhook_{}'.format(TELEGRAM_API_TOKEN)
WEBHOOK_TELEGRAM_BASE = APP_BASE_URL + WEBHOOK_TELEGRAM_ROUTING
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/'
TELEGRAM_BASE_URL_FILE = f'https://api.telegram.org/file/bot{TELEGRAM_API_TOKEN}/'

PEOPLE_TABLE = Airtable(
    AIRTABLE_CONFIG_ID, 
    'People', 
    api_key=AIRTABLE_API_KEY
)

GLOBAL_ADMIN_IDS = [
    row['fields']['ID']
    for row in PEOPLE_TABLE.get_all()
    if (
        row['fields'].get('Global Admin', False)
        and
        not row['fields'].get('Disabled', False)
    )
]

HUNT_ADMIN_IDS = set([
    row['fields']['ID']
    for row in PEOPLE_TABLE.get_all()
    if (
        len(row['fields'].get('Admin of Hunts', [])) > 0
        and
        not row['fields'].get('Disabled', False)
    )
])

if LOCAL_ENV_FILES:
    ERROR_REPORTERS_IDS = [ENV_VARS['ERROR_REPORTERS_ID']]
else:    
    ERROR_REPORTERS_IDS = [
        row['fields']['ID']
        for row in PEOPLE_TABLE.get_all()
        if (
            row['fields'].get('Report Errors', False) 
            and 
            not row['fields'].get('Disabled', False)
        )
    ]