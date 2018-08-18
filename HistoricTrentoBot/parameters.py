# -*- coding: utf-8 -*-
import utility
import key

PARAMETRI_ORIGINAL = utility.import_url_csv_to_dict_list(key.PARAMETRI_URL)
# NOME, DESCRIZIONE, VALORE

PARAMS = {row['NOME']:int(row['VALORE']) for row in PARAMETRI_ORIGINAL}
