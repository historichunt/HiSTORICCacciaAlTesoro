import pandas as pd
from airtable.airtable import Airtable
from historic.hunt_route import api_google
from historic.hunt_route.data_matrices import DataMatrices
from historic.bot import airtable_utils
from historic.hunt_route.render_map import render_map_with_coordinates
from historic.config import settings

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

def read_data_from_airtable(table_id, max_points=None):
    table = Airtable(table_id, 'Missioni', api_key=settings.AIRTABLE_API_KEY)
    data = airtable_utils.get_rows(table)
    if max_points is not None:
        data = data[:max_points]
    names_longlat = {
        r['NOME']: list(reversed([float(x) for x in r['GPS'].split(',')])) # latlong -> longlat
        for r in data
    }    
    return names_longlat

def build_data_from_spreadsheet(api, name, spreadsheet_key, spreadsheet_gid, max_points=None):        
    names_longlat = read_data_from_spreadsheet(spreadsheet_key, spreadsheet_gid, max_points)
    return DataMatrices(
        dataset_name = name,
        points_name_coordinate = names_longlat,
        api = api
    )        

def build_data_from_airtable(api, table_id, max_points=None):
    names_longlat = read_data_from_airtable(table_id, max_points)
    return DataMatrices(
        dataset_name = table_id,
        points_name_coordinate = names_longlat,
        api = api
    )        

def get_dm(api, name):
    return DataMatrices(
        dataset_name = name,
        api = api
    )        

def test_airtable_map(table_id, max_points=None):
    import numpy as np
    names_longlat = read_data_from_airtable(table_id, max_points)
    print('Read points: ', len(names_longlat))
    coordinates = np.array(list(names_longlat.values()))
    assert all(len(c)==2 for c in names_longlat.values())
    render_map_with_coordinates(coordinates)

if __name__ == "__main__":
    # test_airtable_map('apph7gGu4AAOgcbdA', 4)
    build_data_from_airtable(api_google, 'apph7gGu4AAOgcbdA', max_points=3)
    