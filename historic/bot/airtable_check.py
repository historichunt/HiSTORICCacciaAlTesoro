import re
from airtable import Airtable
from historic.config import settings, airtable_utils

def check_curly_bracket(s):
    return s.count('{') == s.count('}')

def check_asterix(s):
    return s.count('*')%2==0

def check_underscores(s):
    return s.count('_')%2==0

def check_square_bracket(s):
    return s.count('[') == s.count(']')

def check_backtick(s):
    return s.count('`')==0


def check_ui():
    print('Checking UI')
    ui_table = Airtable(settings.AIRTABLE_CONFIG_ID, 'UI', api_key=settings.AIRTABLE_API_KEY)
    row_dict_list = airtable_utils.get_rows(ui_table)
    for row_dict in row_dict_list:
        for k,v in row_dict.items():
            assert check_curly_bracket(v), \
                'Error CURLY BRACKET in ui table in var "{}" column {}'.format(row_dict['VAR'], k)
            if k!='VAR':
                assert check_underscores(v), \
                    'Error UNDERSCORES in ui table in var "{}" column {}'.format(row_dict['VAR'], k)
            assert check_square_bracket(v), \
                'Error SQUARE BRACKET in ui table in var "{}" column {}'.format(row_dict['VAR'], k)
            assert check_backtick(v), \
                'Error BACK APOSTROPHE in ui table in var "{}" column {}'.format(row_dict['VAR'], k)

def check_hunt(hunt_pw):
    from historic.bot.game import HUNTS_PW
    hunt_config_dict = HUNTS_PW[hunt_pw]    
    # hunt_name = hunt_config_dict['Name']            
    game_id = hunt_config_dict['Airtable_Game_ID']
    hunt_missioni_table = Airtable(game_id, 'Missioni', api_key=settings.AIRTABLE_API_KEY)
    missioni_row_dict_list = airtable_utils.get_rows(hunt_missioni_table)
    for row_dict in missioni_row_dict_list:
        for k,v in row_dict.items():
            if type(v) is not str:
                continue
            mk_check = (
                ('PARENTESI GRAFFE', check_curly_bracket),
                ('PARENTESI QUADRE', check_square_bracket),
                ('UNDERSCORES', check_underscores),
                ('BACKTICK', check_backtick)
            )
            miss_name = row_dict['NOME']
            for err_type, check_func in mk_check:
                if not check_func(v):
                    return f'Errore {err_type} in tabella "Missioni": missione "{miss_name}", colonna {k}'

# def check_consistencies():
#     check_ui()
#     check_hunt() 
#     print('Success!!')

if __name__ == "__main__":
    import sys
    assert len(sys.argv)==2
    pw = sys.argv[1]
    check_hunt(pw)