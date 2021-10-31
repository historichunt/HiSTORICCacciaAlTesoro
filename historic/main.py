from flask import Flask, request
from historic.config import settings


import logging
import google.cloud.logging
client = google.cloud.logging.Client()
# logging.debug #format='%(asctime)s  [%(levelname)s]: %(message)s'
client.setup_logging(log_level=logging.DEBUG)


# If `entrypoint` is not defined in app.yaml, App Engine will look for an app
# called `app` in `main.py`.
app = Flask(__name__)

# run once
with app.app_context():
    from historic.bot import bot_telegram_admin
    bot_telegram_admin.set_webhook()

@app.route('/')
def root():
    logging.debug("in root function")
    """Return a friendly HTTP greeting."""
    return "hiSTORIC!!", 200

@app.route(settings.DEPLOY_NOTIFICATION_WEBHOOK_URL_ROUTING, methods=['POST'])
def new_deploy():    
    from historic.bot.bot_telegram import report_admins
    from historic.config.settings import APP_VERSION, ENV_VERSION
    payload_json = request.get_json(force=True)
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
    msg = f'🛎️ New {ENV_VERSION} Version {APP_VERSION}' 
    if ENV_VERSION != 'production':
        msg += f' ({branch})' # issue #
    # msg += f'\n{payload_json_str}'
    report_admins(msg)
    return msg, 200

@app.errorhandler(404)
def page_not_found(e):
    logging.debug("page_not_found")
    # note that we set the 404 status explicitly
    return "url not found", 404

@app.errorhandler(500)
def internal_error(error):
    return "500 error: {}".format(error), 500

@app.route(settings.WEBHOOK_TELEGRAM_ROUTING, methods=['POST'])
def telegram_webhook_handler():
    from historic.bot.main_exception import run_new_thread_and_report_exception
    from historic.bot.bot_telegram_dialogue import deal_with_request    
    import json

    request_json = request.get_json(force=True)

    logging.debug("TELEGRAM POST REQUEST: {}".format(json.dumps(request_json)))

    run_new_thread_and_report_exception(deal_with_request, request_json)

    return '', 200
