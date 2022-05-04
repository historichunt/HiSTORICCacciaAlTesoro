import os

# base dir (two levels up)
# (works both in flask and gunicorn)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) 

LANGUAGES = ['IT','EN', 'JA', 'DE']
MAX_TEAM_NAME_LENGTH = 30
JUMP_TO_SURVEY_AFTER = False  # 2
TERMINATE_HUNT_AFTER_DAYS = 3

MAX_SIZE_FILE_BYTES = 50 * 1024 * 1024

# max distance to hunt gps location (config table)
# in order to be able to access the hunt
MAX_DISTANCE_KM_HUNT_GPS = 10