from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from historic.bot.bot_telegram import report_admins
from historic.config import settings
import asyncio
import logging
import google.cloud.logging

client = google.cloud.logging.Client()
# logging.debug #format='%(asctime)s  [%(levelname)s]: %(message)s'
client.setup_logging(log_level=logging.DEBUG) # INFO

# If `entrypoint` is not defined in app.yaml, App Engine will look for an app
# called `app` in `main.py`.
app = FastAPI()

# add url for qr code app
# app.mount(
#     "/assets",
#     StaticFiles(directory="dist/assets"),
#     name="assets",
# )
# app.mount('/easy-qr-scan-bot', StaticFiles(directory='dist', html=True))

# @app.get("/easy-qr-scan-bot")
# def read_index():
#     return FileResponse("./dist/index.html")

@app.get('/set_webhook')
async def set_webhook(): 
    from historic.bot import bot_telegram_admin
    await bot_telegram_admin.set_webhook()

asyncio.gather((set_webhook()))

@app.get('/', status_code=201)
async def root():
    logging.debug("in root function")
    """Return a friendly HTTP greeting."""
    return "hiSTORIC!!"

@app.post(settings.DEPLOY_NOTIFICATION_WEBHOOK_URL_ROUTING, status_code=201)
async def new_deploy(req: Request):    
    from historic.bot.bot_telegram import report_admins
    from historic.config.settings import APP_VERSION, ENV_VERSION
    payload_json = await req.json()
    # payload has the following struture
    # {
    #     "event": "push",
    #     "repository": "kercos/HiSTORICCacciaAlTesoro",
    #     "commit": "5a94671388c5dc275aa194f811b5ba5214e27f4e",
    #     "ref": "refs/heads/refactoring",
    #     "head": "",
    #     "workflow": "deploy-app-to-gcp"
    # }
    branch = payload_json['ref'].split('/')[-1]
    # payload_json_str = json.dumps(payload_json, indent=3, ensure_ascii=False)
    msg = f'🛎️ New {ENV_VERSION} version {APP_VERSION}' 
    if ENV_VERSION != 'production':
        msg += f' ({branch})' # issue #
    # msg += f'\n{payload_json_str}'
    await report_admins(msg)

# ================================
# CRON TASKS
# ================================

@app.get('/dayly_check_terminate_hunt', status_code=201)
async def dayly_check_terminate_hunt(req: Request):
    headers = req.headers
    if not headers.get('X-Appengine-Cron', False):
        # Only requests from the Cron Service will contain the X-Appengine-Cron header
        return
        
    import time
    from historic.bot.date_time_util import now_utc_plus_delta_days
    from historic.config import params
    from historic.bot.ndb_person import Person
    from historic.bot.bot_telegram import send_message
    from historic.bot.bot_telegram_dialogue import teminate_hunt
    from historic.bot.ndb_utils import client

    with client.context():
        people_on_hunt = Person.query(Person.current_hunt!=None).fetch()    
        expiration_date = now_utc_plus_delta_days(-params.TERMINATE_HUNT_AFTER_DAYS)
        terminated_people_list = []
        for p in people_on_hunt:
            if p.last_mod < expiration_date:
                await send_message(p, p.ui().MSG_AUTO_QUIT)
                teminate_hunt(p)
                terminated_people_list.append(p)
                await asyncio.sleep(1)
        if terminated_people_list:
            msg_admin = "Caccia auto-terminata per:"
            for n,p in enumerate(terminated_people_list,1):
                msg_admin += f'\n {n}. {p.get_first_last_username(escape_markdown=False)}'
            await report_admins(msg_admin)

    
@app.post(settings.WEBHOOK_TELEGRAM_ROUTING, status_code=201)
async def telegram_webhook_handler(req: Request):
    from historic.bot.bot_telegram_dialogue import deal_with_request    
    from historic.bot.ndb_utils import client
    import traceback
    import json

    request_json = await req.json()

    logging.debug("TELEGRAM POST REQUEST: {}".format(json.dumps(request_json)))

    with client.context():        
        try:
            await deal_with_request(request_json)
        except Exception:            
            report_string = '❗️ Exception {}'.format(traceback.format_exc()) #.splitlines()
            logging.error(report_string) 
            try:  
                await report_admins(report_string)
            except Exception:
                report_string = '❗️ Exception {}'.format(traceback.format_exc())
                logging.error(report_string)    



    
