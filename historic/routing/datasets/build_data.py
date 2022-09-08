import pandas as pd
from airtable.airtable import Airtable
from historic.routing.api import api_google
from historic.routing.data_matrices import DataMatrices
from historic.bot import airtable_utils
from historic.routing.utils.render_map import render_map_with_coordinates
from historic.config import settings
from historic.routing.datasets.trento_hunt_params import TRENTO_BASE_KEY

def read_data_from_spreadsheet(spreadsheet_key, spreadsheet_gid, max_points=None):
    url = f'https://docs.google.com/spreadsheets/d/{spreadsheet_key}/export?gid={spreadsheet_gid}&format=csv'
    df = pd.read_csv(url)
    
    # each row becomes a dictionary where key is column name and value is the data in the cell
    records = df.to_dict('records') 
    if max_points is not None:
        records = records[:max_points]
    name_coordinates = {
        r['storia']: [r['long'],r['lat']]
        for r in records
        if not any(pd.isnull(r[c]) for c in ['storia','lat','long'])
    }
    return name_coordinates

def read_data_from_airtable(table_id, table_name, max_points=None):
    # TODO: this works only if there is a table 'Missioni_IT;
    table = Airtable(table_id, table_name, api_key=settings.AIRTABLE_API_KEY)
    data = airtable_utils.get_rows(table)
    if max_points is not None:
        data = data[:max_points]
    name_longlat = {
        r['NOME']: list(reversed([float(x) for x in r['GPS'].split(',')])) # latlong -> longlat
        for r in data
    }    
    return name_longlat

def build_data_from_spreadsheet(
    api, name, spreadsheet_key, spreadsheet_gid,
    update=True, max_points=None, max_linear_dst_km=None):        

    name_longlat = read_data_from_spreadsheet(spreadsheet_key, spreadsheet_gid, max_points)
    dm = DataMatrices(
        dataset_name = name,
        api = api
    )
    if update:
        dm.update_matrices(name_longlat)
    return dm

def build_data_from_airtable(
    api, table_id, table_name, 
    update=True, max_points=None, max_linear_dst_km=None):

    name_longlat = read_data_from_airtable(table_id, table_name, max_points)
    dm = DataMatrices(
        dataset_name = table_id,        
        api = api,
        max_linear_dst_km = max_linear_dst_km
    )      
    if update:  
        dm.update_matrices(name_longlat)
    return dm

def get_dm(api, name):
    return DataMatrices(
        dataset_name = name,
        api = api
    )        

def test_airtable_map(table_id, max_points=None):
    import numpy as np
    name_longlat = read_data_from_airtable(table_id, max_points)
    print('Read points: ', len(name_longlat))
    coordinates = np.array(list(name_longlat.values()))
    assert all(len(c)==2 for c in name_longlat.values())
    render_map_with_coordinates(coordinates)

if __name__ == "__main__":
    # test_airtable_map(TRENTO_BASE_KEY, 'Missioni_IT')
    build_data_from_airtable(
        api_google, 
        TRENTO_BASE_KEY,
        'Missioni_IT',
        max_linear_dst_km=2.5
        # max_points=3
    ) 
    