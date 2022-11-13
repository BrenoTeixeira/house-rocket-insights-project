import pandas as pd
import multiprocessing as mp
import os
from geo_location import geo_worker
import time

def locations(df):
    coords = df[['id', 'lat', 'long']].astype(str)

    # Formating the coordenates for the request.
    coords['coord'] = coords[['lat', 'long']].apply(lambda x: x['lat'] + ',' + x['long'], axis=1)
    get_data_df = coords[['id', 'coord']]

    p = mp.Pool(processes=mp.cpu_count() - 1)
    get_data_df[['road', 'house_number', 'neighbourhood', 'county']] = p.map(geo_worker, get_data_df.iterrows())

    return get_data_df


def save_data(df):
    df.drop(columns='coord', inplace=True)
    df.to_csv('data/address.csv', index=False)

if __name__ == '__main__':

    data = pd.read_csv('data/kc_house_data.csv', usecols=['id', 'lat', 'long'])
    data = data

    locations_df = locations(df=data)

    save_data(df=locations_df)
    
    


