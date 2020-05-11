# Import of librairies
import os
os.environ['NUMEXPR_MAX_THREADS'] = '16'
import mysql.connector as mariadb
import pandas as pd
from fbprophet import Prophet
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from tqdm import tqdm
from sklearn.metrics import mean_squared_error
from multiprocessing import Pool
from multiprocessing import freeze_support
import time
import math

# Defining classes and functions

class sql_query:
    def __init__(self, credentials_path):
        self.db_credentials = pd.read_csv(credentials_path, index_col="Field")
      
    
    def __call__(self, query):
        
        mariadb_connection = mariadb.connect(
            user=self.db_credentials.loc["user"][0],
            password=self.db_credentials.loc["password"][0],
            host=self.db_credentials.loc["host"][0],
            port=3306,
            db = "db_velib")
        
        self.cursor = mariadb_connection.cursor()
    
        cursor = self.cursor
        cursor.execute(query)
        field_names = [i[0] for i in cursor.description]
        df = pd.DataFrame(cursor, columns=field_names)
        return df
    
def prophet_prediction(hour, full_dataframe):
    df_instance = full_dataframe[full_dataframe["ds"] < hour]
    m = Prophet()
    m.fit(df_instance)
    future = m.make_future_dataframe(periods=30, freq='min')
    forecast = m.predict(future)
    predictions = forecast[forecast["ds"]>= hour]
    return list(predictions.yhat)

def measure_rmse(actual, predicted):
    return math.sqrt(mean_squared_error(actual, predicted))

def result_creating( station_id):
    day_of_testing = "2020-05-10"
    request = sql_query("../../aws_mariadb_crendentials.csv")

    query = """
    SELECT DISTINCT date_of_update, nb_total_free_bikes FROM velib_realtime
    WHERE station_id = {}
    AND date_of_update > DATE({})
    ORDER BY date_of_update ASC
    """.format(station_id, day_of_testing)

    df= request(query)
    df.columns = ['ds','y']

    # Setting max boundary
    df_data = df[df["ds"]< (pd.Timestamp(day_of_testing)+ pd.DateOffset(days=1))]

    # Creating dataframe for results
    df_results = pd.DataFrame(columns=['prediction', 'real_values', 'metrics'], index=pd.date_range(day_of_testing+' 06:00:00', periods=64, freq='15Min'))

    # Creating predictions

    for i in tqdm(df_results.index):
        df_results.loc[i]['prediction'] = prophet_prediction(i, df_data)
        df_results.loc[i]['real_values'] = list(df_data[df_data['ds'] >= i][0:30]['y'])
        df_results.loc[i]['metrics'] = measure_rmse(df_results.loc[i]["real_values"], df_results.loc[i]["prediction"])

    df_results.to_csv("/home/exalis/Github/velib-prediction-v2/3. Results/Facebook Prophet/Facebook Prophet Results - {} - {}.csv".format(day_of_testing, station_id))
    

def run_multiprocessing(func, i, n_processors):
    with Pool(processes=n_processors) as pool:
        return pool.map(func, i)

def main(list_of_stations):
    n_processors = 14
    out = run_multiprocessing(result_creating, list_of_stations , n_processors)


# Extracting the list of the stations

request = sql_query("../../aws_mariadb_crendentials.csv")
query = """
SELECT DISTINCT station_id FROM velib_realtime
"""
df= request(query)
# Removing bad values
df= df.drop(0)
df = df.drop(1391)

list_of_stations = list(df.station_id)

if __name__ == "__main__":
    freeze_support()   # required to use multiprocessing
    main(list_of_stations)
