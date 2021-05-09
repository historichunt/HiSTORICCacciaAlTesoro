import os

ROOT_DIR = os.path.dirname(os.path.dirname(__file__)) # base dir (works both in flask and gunicorn)

LANGUAGES = ['IT','EN']
MAX_TEAM_NAME_LENGTH = 30
WORK_IN_PROGRESS = False
JUMP_TO_SURVEY_AFTER = False  # 2
