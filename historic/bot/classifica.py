from matplotlib import pyplot as plt
import csv
from datetime import timedelta
import pandas as pd
import json

# TODO dividere per chi va in bici e chi va a piedi!

csv_filename = "classifica_trento_piedi.csv"

def convert_seconds_into_hours(sec):
    if sec < 0:
        sec = abs(sec)
        conversion = timedelta(seconds=int(sec))
        converted_time = str(conversion)
        converted_time = "-"+converted_time
    else:
        conversion = timedelta(seconds=int(sec))
        converted_time = str(conversion)
    return converted_time

def script():
    df = pd.read_csv('Results-Grid view.csv')  

    df['json_values'] = df['GAME VARS'].apply(lambda x: pd.json_normalize(json.loads(x)))
    df['START_TIME'] = pd.to_datetime(df['START_TIME'],format='%d/%m/%Y %H:%M')

    # solo quelli che hanno completato la caccia
    finished_df = df.loc[df['FINISHED'] == 'checked'] # pylint: disable = unsubscriptable-object

    with open(csv_filename, mode='w') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(['Nome Squadra','Settimana (giorno di inizio)','Tempo in più rispetto al previsto','Tempo medio per indovinelli'])

        # raggruppa per settimane (a partire dal lunedi')
        groups = finished_df.groupby([pd.Grouper(key='START_TIME', freq='W-MON')])
        for name, group in groups:
            if len(group) > 0: # per questa settimana, ci deve essere almeno una squadra che ha completato
                # nella tabella riportiamo il lunedi' di inizio della settimana in cui la squadra ha iniziato a giocare
                start_weekday = (name - timedelta(days=7)).strftime('%Y/%m/%d')

                # qui sotto ci sono 3 cicli su un dataframe, pessimo! ;)
                # forse potrei creare nel dataframe di questo gruppo le nuove colonne tipo group['secondi_in_piu_rispetto_a_quanto_richiesto']
                # e poi usare dei min idxmin in realta' su queste colonne per cambiare il valore e mettere <span class=highlight ...
                # ma la vedo incasinata e 3 cicli funzionano quindi ok cosi' ;)

                # primo ciclo: trovo la squadra che ci ha messo di meno a completare tutta la caccia
                # assumo che due squadre non abbiano lo stesso nome e non abbiano iniziato esattamente nello stesso secondo (anche se sarebbe teoricamente possibile)
                min_secondi_in_piu_rispetto_a_quanto_richiesto = float('inf')
                min_totale_group_name = None

                for index, row in group.iterrows():
                    group_name = row['GROUP_NAME']
                    start_time = pd.to_datetime(row['START_TIME'])
                    quanto_ci_han_messo_in_secondi = row['json_values']['ELAPSED GAME'][0]
                    quanto_volevano_giocare_in_minuti = row['json_values']['ROUTE_DURATION_MIN'][0]
                    quanto_volevano_giocare_in_secondi = quanto_volevano_giocare_in_minuti * 60
                    secondi_in_piu_rispetto_a_quanto_richiesto = quanto_ci_han_messo_in_secondi - quanto_volevano_giocare_in_secondi

                    if secondi_in_piu_rispetto_a_quanto_richiesto < min_secondi_in_piu_rispetto_a_quanto_richiesto:
                        (min_secondi_in_piu_rispetto_a_quanto_richiesto, min_totale_start_time, min_totale_group_name) = (secondi_in_piu_rispetto_a_quanto_richiesto, start_time, group_name)

                # secondo ciclo: escludo la squadra che ci ha messo di meno a completare tutta la caccia e tra le altre cerco quella che ci ha messo di meno per gli indovinelli
                min_secondi_medi_per_missione = float('inf')
                min_missioni_group_name = None

                for index, row in group.iterrows():
                    group_name = row['GROUP_NAME']
                    if group_name == min_totale_group_name:
                        continue
                    start_time = pd.to_datetime(row['START_TIME'])
                    total_time_missions = row['json_values']['TOTAL TIME MISSIONS'][0]
                    nr_missions = row['json_values']['MISSIONI_INFO.TOTAL'][0]
                    secondi_medi_per_missione = total_time_missions/nr_missions

                    if secondi_medi_per_missione < min_secondi_medi_per_missione:
                        (min_secondi_medi_per_missione, min_missioni_start_time, min_missioni_group_name) = (secondi_medi_per_missione, start_time, group_name)

                # terzo ciclo:  aggiungo il testo <premio> ai due gruppi che han vinto i 2 premi
                for index, row in group.iterrows():
                    group_name = row['GROUP_NAME']
                    win_totale_testo_prima = ''
                    win_totale_testo_dopo = ''
                    if group_name == min_totale_group_name:
                        win_totale_testo_prima = '<span class="premio_totale">'
                        win_totale_testo_dopo = ' (PREMIO!)</span>'
                    win_missioni_testo_prima = ''
                    win_missioni_testo_dopo = ''
                    if group_name == min_missioni_group_name:
                        win_missioni_testo_prima = '<span class="premio_missioni">'
                        win_missioni_testo_dopo = ' (PREMIO!)</span>'

                    start_time = pd.to_datetime(row['START_TIME'])
                    quanto_ci_han_messo_in_secondi = row['json_values']['ELAPSED GAME'][0]
                    quanto_volevano_giocare_in_minuti = row['json_values']['ROUTE_DURATION_MIN'][0]
                    quanto_volevano_giocare_in_secondi = quanto_volevano_giocare_in_minuti * 60
                    secondi_in_piu_rispetto_a_quanto_richiesto = quanto_ci_han_messo_in_secondi - quanto_volevano_giocare_in_secondi
                    total_time_missions = row['json_values']['TOTAL TIME MISSIONS'][0]
                    nr_missions = row['json_values']['MISSIONI_INFO.TOTAL'][0]
                    secondi_medi_per_missione = total_time_missions/nr_missions

                    # print(f'Group={group_name} / secondi in piu = {secondi_in_piu_rispetto_a_quanto_richiesto}  messo={quanto_ci_han_messo_in_secondi}-quantovolevano={quanto_volevano_giocare_in_secondi} /')
                    # print(f'Group={group_name} / secondi medi per missione = {total_time_missions/nr_missions}  total time missions={total_time_missions} / missions={nr_missions} /')
                    # print(f'Group={group_name} start_time={start_time} | start_weekday={start_weekday} \n secondi in piu = {secondi_in_piu_rispetto_a_quanto_richiesto} \n secondi medi per missione = {total_time_missions/nr_missions}')
                    # print(f'{group_name},{start_weekday},{win_totale_testo_prima}{secondi_in_piu_rispetto_a_quanto_richiesto}{win_totale_testo_dopo},{win_missioni_testo_prima}{secondi_medi_per_missione}{win_missioni_testo_dopo}')

                    # print(f'secondi{secondi_in_piu_rispetto_a_quanto_richiesto} / minuti={convert_seconds_into_hours(secondi_in_piu_rispetto_a_quanto_richiesto)}')
                    csv_writer.writerow(
                        [f'{group_name}', 
                        f'{start_weekday}', 
                        f'{win_totale_testo_prima}{convert_seconds_into_hours(secondi_in_piu_rispetto_a_quanto_richiesto)}{win_totale_testo_dopo}',
                        f'{win_missioni_testo_prima}{convert_seconds_into_hours(secondi_medi_per_missione)}{win_missioni_testo_dopo}'])

                # TODO: verificare cosa succede se una squadra ha una virgola nel nome squadra, rompe il CSV generato? mette i campi tra virgolette?
                # Credo funzioni perche' uso write_csv che ha dell'escaping di suo

    # load the csv and user row 0 as headers
    df = pd.read_csv(csv_filename, header = 0)
    # reverse the data per settimana cosi' le ultime settimane compaiono in alto
    df = df.sort_values(by='Settimana (giorno di inizio)', ascending=False)
    # df = df.iloc[::-1]
    df.to_csv(csv_filename,index=False)

if __name__ == "__main__":
    script()