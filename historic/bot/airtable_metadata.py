from pyairtable import Table
from pyairtable.metadata import get_base_schema
from pyairtable.api import Base
from historic.config import settings
import json

def test_metadata():
    base_id =  '<enter base id>'
    # table_name = 'Settings'
    # table = Table(settings.AIRTABLE_API_KEY, base_id, table_name)
    # table_json = table.all()
    base = Base(settings.AIRTABLE_API_KEY, base_id)
    table_schema = get_base_schema(base)    
    with open('airtable_meta_test.json', 'w') as fout:        
        json.dump(table_schema, fout, indent=3, ensure_ascii=False)
    

if __name__ == "__main__":
    test_metadata()