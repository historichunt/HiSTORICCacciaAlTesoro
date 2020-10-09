import key
from airtable import Airtable
import airtable_utils
import re

def check_curly_bracket(s):
    return len(re.findall(r'\{\d*\}',s)) == s.count('{') == s.count('}')

def check_asterix(s):
    return s.count('*')%2==0

def check_underscores(s):
    return s.count('_')%2==0

def check_square_bracket(s):
    return s.count('[') == s.count(']')

def check_back_apostrophe(s):
    return s.count('`')==0


def check_ux():
    print('Checking UX')
    ux_table = Airtable(key.AIRTABLE_CONFIG_ID, 'UX', api_key=key.AIRTABLE_API_KEY)
    row_dict_list = airtable_utils.get_rows(ux_table)
    for row_dict in row_dict_list:
        for k,v in row_dict.items():
            assert check_curly_bracket(v), \
                'Error CURLY BRACKET in ux table in var "{}" column {}'.format(row_dict['VAR'], k)
            if k!='VAR':
                assert check_underscores(v), \
                    'Error UNDERSCORES in ux table in var "{}" column {}'.format(row_dict['VAR'], k)
            assert check_square_bracket(v), \
                'Error SQUARE BRACKET in ux table in var "{}" column {}'.format(row_dict['VAR'], k)
            assert check_back_apostrophe(v), \
                'Error BACK APOSTROPHE in ux table in var "{}" column {}'.format(row_dict['VAR'], k)

def check_hunts():
    from game import HUNTS
    for hunt_config_dict in HUNTS.values():
        hunt_name = hunt_config_dict['Name']        
        print('Checking {}'.format(hunt_name))
        game_id = hunt_config_dict['Airtable_Game_ID']
        hunt_missioni_table = Airtable(game_id, 'Missioni', api_key=key.AIRTABLE_API_KEY)
        missioni_row_dict_list = airtable_utils.get_rows(hunt_missioni_table)
        for row_dict in missioni_row_dict_list:
            for k,v in row_dict.items():
                if type(v) is not str:
                    continue
                assert check_curly_bracket(v), \
                    'Error CURLY BRACKET in missioni of hunt "{}" in mission name "{}" column {}'.format(
                        hunt_name, row_dict['NAME'], k)
                assert check_underscores(v), \
                    'Error UNDERSCORES in missioni of hunt "{}" in mission name "{}" column {}'.format(
                        hunt_name, row_dict['NAME'], k)
                assert check_square_bracket(v), \
                    'Error SQUARE BRACKET in missioni of hunt "{}" in mission name "{}" column {}'.format(
                        hunt_name, row_dict['NAME'], k)
                assert check_back_apostrophe(v), \
                    'Error BACK APOSTROPHE in missioni of hunt "{}" in mission name "{}" column {}'.format(
                        hunt_name, row_dict['NAME'], k)        

def check_consistencies():
    check_ux()
    check_hunts() 
    print('Success!!')

if __name__ == "__main__":
    check_consistencies()