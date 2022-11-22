from pyairtable import Table
from pyairtable.metadata import get_base_schema
from pyairtable.api import Base
from historic.config import settings
import json
import requests

def test_metadata(airtable_game_id):
    url = f"https://api.airtable.com/v0/meta/bases/{airtable_game_id}/tables"

    # payload={}
    headers = {
        'Authorization': f'Bearer {settings.AIRTABLE_ACCESS_TOKEN}',
        # 'Cookie': 'brw=brwJKyttKj84lpEiz'
        }

    response = requests.request("GET", url, headers=headers) # data=payload

    json_data = json.loads(response.text)
    with open('hunt_schema/schema.json', 'w') as fout:
        json.dump(json_data, fout, ensure_ascii=False, indent=3)


    

if __name__ == "__main__":
    from historic.bot.utils_cli import get_hunt_from_password

    hunt_name, airtable_game_id = get_hunt_from_password()    
    test_metadata(airtable_game_id)