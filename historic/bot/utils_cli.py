from historic.bot import game

def get_hunt_from_password(verbose=True):
    while True:
        password = input('\nInserisci password caccia al tesoro: ').lower()
        if password in game.HUNTS_PW:
            break
        print('\nPasswrod non valida.\n')

    hunt_name = game.HUNTS_PW[password]['Name']
    airtable_game_id = game.HUNTS_PW[password]['Airtable_Game_ID']
    
    if verbose:
        print(f'\nTrovata caccia: {hunt_name}\n')

    return hunt_name, password, airtable_game_id

