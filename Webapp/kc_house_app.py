import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import gridspec
import folium
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
import geopandas
import datetime as dt
import plotly.express as px
import glob
import numpy as np
from PIL import Image

print("")
sns.set_theme(style='darkgrid', font='Source Sans Pro')
st.set_page_config(layout="wide")


@st.cache(allow_output_mutation=True)

# Extract
def get_data(path):
    # Finds all the files with .csv extension
    all_files = glob.glob(path + '\*.csv')
    dataframes = [pd.read_csv(filename) for filename in all_files]
    
    return dataframes


def get_geofile(url):
    geo = geopandas.read_file(url)
    return geo


# Feature Engineering
def data_format(data):
    data['date'] = pd.to_datetime(data['date'])

    dim = ['sqft_living', 'sqft_lot', 'sqft_above', 'sqft_basement', 'sqft_living15', 'sqft_lot15']

    data[dim] = data[dim].apply(lambda x: round(x*0.092903, 2))

    for i in range(len(dim)):   
       data =  data.rename(columns={dim[i]: dim[i].replace('sqft', 'm²')})

    return data

def condition(x):

    if x <= 2:
        return 'low'
    elif ((x > 2) and (x <= 4)):
        return 'mid' 
    else:
        return 'high'

def set_feature(data):
        # Renovation
    data['renovated'] = data['yr_renovated'].apply(lambda x: 'yes' if x != 0 else 'no')

    # Construction
    data['construction'] = data['yr_built'].apply(lambda x: '<1965' if x < 1965 else '>1965')

    # 3_or more_bedrooms
    data['3_or_more_bedrooms'] = data['bedrooms'].apply(lambda x: '3+' if x >=3 else '<3')

    # Basement
    data['basement'] = data['m²_basement'].apply(lambda x: 'yes' if x != 0 else 'no')

    # Waterfront
    data['waterfront'] = data['waterfront'].apply(lambda x: 'no' if x == 0 else 'yes')

    # Condition

    data['condition_label'] = data['condition'].apply(condition)

    # Seasons

    # Summer
    data.loc[(data['date'].dt.strftime('%m-%d') >= '06-21') & (data['date'].dt.strftime('%m-%d') <= '09-22'), 'season'] = 'summer'

    # Autumn
    data.loc[(data['date'].dt.strftime('%m-%d') >= '09-23') & (data['date'].dt.strftime('%m-%d') <= '12-20'), 'season'] = 'autumn'

    # Winter
    mask_1 = (data['date'].dt.strftime('%m-%d') >= '12-21') & (data['date'].dt.strftime('%m-%d') <= '12-31')

    mask_2 = (data['date'].dt.strftime('%m-%d') >= '01-01') & (data['date'].dt.strftime('%m-%d') <= '03-20')

    data.loc[(mask_1 | mask_2) , 'season'] = 'winter'

    # Spring
    data.loc[(data['date'].dt.strftime('%m-%d') >= '03-21') & (data['date'].dt.strftime('%m-%d') <= '06-20'), 'season'] = 'spring'

    return data

# Cleaning
def duplicate_values(data):
    data = data.drop_duplicates(subset='id', keep='last')
    return data

def remove_outliers(data):
    data = data.loc[data['bedrooms'] != max(data['bedrooms'])]
    return data

### Insights ###
def plot_bar(data, cat, cat_2):
    
    plot_data = data[[cat, cat_2]].groupby(cat).mean().reset_index()
    plot_data_2 = data[[cat, cat_2]].groupby(cat).median().reset_index()
    ylim = np.max([plot_data[cat_2].max(), plot_data_2[cat_2].max()])
    ylim = 0.05*ylim + ylim
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    axes[0].bar(cat, cat_2, data=plot_data)
    axes[0].set_title(f'Average {cat_2.title()} per {cat.title()}')
    axes[0].ticklabel_format(style='plain', axis='y')
    axes[0].set_ylim(0, ylim)


    axes[1].bar(cat, cat_2, data=plot_data_2)
    axes[1].set_title(f'Median {cat_2.title()} per {cat.title()}')
    axes[1].ticklabel_format(style='plain', axis='y')
    axes[1].set_ylim(0, ylim)
    return fig

def line_p(data, date, target_col, filter_col, threshold):

    df_h = data[[date, target_col, filter_col]].query(f'{filter_col} >= {threshold}')
    aux = df_h.groupby(df_h[date].dt.strftime('%Y-%m')).mean(numeric_only=True)

    fig = plt.figure(figsize=(12, 6))

    plt.plot(aux.index, aux[target_col])
    plt.title(f'Average {target_col} of properties with {threshold}+ {filter_col} over time', loc='center')
    plt.ylim([300000, max(aux.price) + 50000])
    
    return fig

def header(img_path):
    
    image = Image.open(img_path + r'\residential.png')
    st.title('INSIGHT PROJECT - HOUSE ROCKET')
    st.image(image=image, use_column_width=True, output_format='JPEG')

def data_overview(data, zipcode_filter):
    #################
    # Data Overview##
    #################
    
    f_attributes = st.sidebar.multiselect('Enter Columns', list(data.columns))
    

    st.header('Table with the suggested properties to buy')
    
    if zipcode_filter != [] and f_attributes != []:
        df_0 = data.loc[data['zipcode'].isin(zipcode_filter)][f_attributes]
    elif zipcode_filter != [] and f_attributes == []:
        df_0 = data.loc[data['zipcode'].isin(zipcode_filter)]
    elif zipcode_filter == [] and f_attributes != []:
        df_0 = data[f_attributes]
    else:
        df_0 = data.copy()

    st.write(df_0)
    st.write(df_0.shape)
   
    return None


# Recommended Properties
def portfolio_density(data, filter, zipcode_filter):

       
    if zipcode_filter != []:

        data = data.loc[(data['id'].isin(filter)) & (data['zipcode'].isin(zipcode_filter))]
    else:

        data = data.loc[(data['id'].isin(filter))]

    # Base Map Folium
    st.header('Suggested Properties')
    
    df_1 = data.copy()

    density_map = folium.Map(location=[df_1['lat'].mean(), df_1['long'].mean()], default_zoom=15)

    marker_cluster = MarkerCluster().add_to(density_map)
    for name, row in df_1.iterrows():
        folium.Marker([row['lat'], row['long']],
                      popup=f"Price R${row['price']} on: {row['date']}. "
                            f"Features: \nLiving Area:{row['m²_living']}m².\n {row['bedrooms']} "
                            f"bedrooms.\n {row['bathrooms']} bathrooms.\n year built: {row['yr_built']}").add_to(
            marker_cluster)

    folium_static(density_map)

def sell_overview(data):

  
    st.sidebar.header('Sell Table Filters')
    f_attributes = st.sidebar.multiselect('Enter Columns', list(data.columns), key='features')

    f_id = st.sidebar.multiselect('Enter ID', list(data['id'].unique()))
    
    min_ = min(data['total_expected_cost'])
    max_ = max(data['total_expected_cost'])

    f_cost = st.sidebar.slider('Price', min_value=min_, max_value=max_, value=min_, step=1.0)

    f_profit = st.sidebar.slider('Profit', min_value=min(data['profit']), max_value=max(data['profit']), value=min(data['profit']), step=1.0)

    st.header('Properties with the price to sell and the expected profit')
    
    if f_id != [] and f_attributes != []:
        df_0 = data.loc[data['id'].isin(f_id)][f_attributes]
    elif f_id != [] and f_attributes == []:
        df_0 = data.loc[data['id'].isin(f_id)]
    elif f_id == [] and f_attributes != []:
        df_0 = data[f_attributes]
    else:
        df_0 = data.copy()
    df_0 = df_0.loc[(df_0['total_expected_cost'] >= f_cost) & (df_0['total_expected_cost'] >= f_profit)]
    st.write(df_0)
    st.write(df_0.shape)
   
    return None


def insights(data):


    st.title('Insights')
    
    # Filters
    st.write('H1: Properties with low conditions <=2 are 45% cheaper.')
    cond_plot = plot_bar(data, cat='condition_label', cat_2='price')
    st.plotly_chart(cond_plot, use_container_width=True)
    st.write('Properties with low conditions are, on average, 44.30% cheaper than properties with high conditions; and 36.21% cheaper than properties with average conditions.')

    st.write('H2: The price of the properties with 3 or more bedrooms is increasing.')
    bed_plot = line_p(data, date='date', target_col='price', filter_col='bedrooms', threshold=3)
    st.plotly_chart(bed_plot, use_container_width=True)
    st.write('On average, The buildings with 3 or more bedrooms are 34.63% more expensive than the other buildings.')

    st.write('H3: Houses put on sale in the winter are cheaper.')
    seas_plot = plot_bar(data, cat='season', cat_2='price')
    st.plotly_chart(seas_plot, use_container_width=True)
    st.write('True: The average price of the properties put on sale during the winter is lower.')

    st.write('H4: Properties that weren\'t renovated are 25% cheaper.')
    ren_plot = plot_bar(data, cat='renovated', cat_2='price')
    st.plotly_chart(ren_plot, use_container_width=True)
    st.write('The average price of properties that weren\'t renovated is 30.17% lower than the average price of properties that were renovated.')

    st.write('H5: Properties with waterfront are, on average, 20% more expensive.')
    wa_plot = plot_bar(data, cat='waterfront', cat_2='price')
    st.plotly_chart(wa_plot, use_container_width=True)
    st.write('The average price of properties with waterfront is 211,80% higher than the average price of properties without waterfront.')
    return None


def financial_results(data):

    st.sidebar.header('Finacial Results Filters')
    f_zipcode = st.sidebar.multiselect('Region', list(data['zipcode'].unique()))
    
    if f_zipcode != []:
        data = data.loc[data['zipcode'].isin(f_zipcode)]

    fin_resu = pd.pivot_table(data, values=['profit', 'total_expected_cost'], index=['id', 'zipcode'], aggfunc='sum', margins=True, margins_name='Total')
    fin_resu_df = fin_resu.reset_index()
    fin_resu_df[['id', 'zipcode']] = fin_resu_df[['id', 'zipcode']].astype('str')
    
    results = data[['price_to_sell', 'total_expected_cost', 'profit']].sum()

    total_profit = results.profit
    total_costs = results.total_expected_cost
    total_revenue = results.price_to_sell
    roi = total_profit/total_costs*100

    summary_res = pd.DataFrame({'Investment': total_costs, 'Total Revenue': total_revenue, 'Total Profit': total_profit, 'ROI': roi}, index=[0]).T.rename(columns={0: 'Financial Result'})

    c1, c2 = st.columns((1, 1))
    
    c1.header('Finacial Results')
    c1.write(pd.DataFrame(fin_resu_df), width=500, height=600)

    c2.header('Summary of Financial Results')
    c2.write(summary_res, width=700, height=600)

    return None


if __name__ == '__main__':

    # Get Data
    raw_data_path = r'..\data'
    path = r'..\outputs'
    img_path = r'..\img'
    
    ur = 'https://opendata.arcgis.com/datasets/83fc2e72903343aabff6de8cb445b81c_2.geojson'
    
    
    df = get_data(raw_data_path)[0]
    suggestions = get_data(path)[1]
    sell_data = get_data(path)[0]
    geofile = get_geofile(ur)

    ##### Transformation #####
    # New Features
    df_1 = data_format(df)
    df_2 = remove_outliers(df_1)
    df_3 = duplicate_values(df_2)
    df_4 = set_feature(df_3)
    
    # Filters
    st.sidebar.header('Suggestions Filters')
    f_zipcode = st.sidebar.multiselect('Enter Region', list(suggestions['zipcode'].unique()))

    # Header
    header(img_path)

    # Data Overview
    data_overview(suggestions, f_zipcode)
    
    # Map plot
    portfolio_density(data=df_4, filter=suggestions['id'], zipcode_filter=f_zipcode)

    sell_overview(sell_data)

    # Commercial Attributes
    insights(df_4)

    # Financial Results
    financial_results(sell_data)