# Import of librairies
import tensorflow as tf
import mysql.connector as mariadb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import datetime
import math
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import StandardScaler
from tensorflow import keras
from tqdm import tqdm
from joblib import load
from timeloop import Timeloop
from datetime import timedelta
import time 

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
        cursor.execute("SET  time_zone = 'Europe/Paris'")
        cursor.execute(query)
        field_names = [i[0] for i in cursor.description]
        df = pd.DataFrame(cursor, columns=field_names)
        return df
    
# Transforming the input data in the proper format 


def measure_rmse(actual, predicted):
    return math.sqrt(mean_squared_error(actual, predicted))

def list_stations():
    request = sql_query("../../aws_mariadb_crendentials - write.csv")
    query = """
    SELECT DISTINCT station_id FROM velib_realtime
    """
    df= request(query)
    # Removing bad values
    df= df.drop(0)
    df = df.drop(1391)
    list_of_stations = list(df.station_id)
    return list_of_stations

def loading_models_unique(station_id, day_of_testing):

    try:
        LSTM_A = tf.keras.models.load_model('/home/exalis/Github/velib-prediction-v2/4. Models/Tensorflow Univariate - {} - {} - LSTM_A.h5'.format(day_of_testing, station_id))
        LSTM_B = tf.keras.models.load_model('/home/exalis/Github/velib-prediction-v2/4. Models/Tensorflow Univariate - {} - {} - LSTM_B.h5'.format(day_of_testing, station_id))
        std = load('/home/exalis/Github/velib-prediction-v2/4. Models/Tensorflow Univariate - {} - {} - std.joblib'.format(day_of_testing, station_id))
        return LSTM_A, LSTM_B, std
    
    except:
        print('impossible to load ', list_of_stations[i])


def create_result_df():
    # Extracting base for prediction 

    request = sql_query("../../aws_mariadb_crendentials - write.csv")

    query = """
    SELECT station_id, date_of_update, nb_total_free_bikes FROM db_velib.velib_realtime
    WHERE date_of_update >= DATE_SUB(NOW(), INTERVAL 185 Minute) AND MINUTE(date_of_update)%5 = 0
    ORDER BY station_id, date_of_update ASC;
    """
    df= request(query)
    df.index = df.date_of_update
    df = df[['station_id','nb_total_free_bikes']]
    df = df.pivot_table(df, index= 'station_id', columns=df.index)

    # Creating dataframe for proper predction

    df_prediction = pd.DataFrame(index=df.index, columns=['last_observations','model_A', 'model_B', 'date_of_prediction'])
    
    for i in df_prediction.index:
        df_prediction["last_observations"].loc[i] = np.array(df.loc[i])
    
    df_prediction['date_of_prediction'] = str(pd.Timestamp.now())[:16]
    return df_prediction


def predict_iteration_unique(list_of_stations, df_prediction, LSTM_A, LSTM_B, std):
    # Request for each minutes
    for station_id in tqdm(list_of_stations):
        try:
            input_data = std.transform(df_prediction[df_prediction.index == station_id]["last_observations"].iloc[0].reshape(-1, 1))[-36:]
            df_prediction.loc[station_id]['model_A'] = std.inverse_transform(LSTM_A.predict(input_data.reshape(1,past_history,1))[0])
      #      df_prediction.loc[station_id]['model_B'] = std.inverse_transform(LSTM_B.predict(input_data.reshape(1,past_history,1))[0])
            df_prediction
        except:
            print('error on ', station_id)
# Initialisation

# Variables
day_of_testing = '2020-05-19'

# Loading global model for al stations
station_id = 'global'
past_history = 36
future_target = 6
list_of_stations = list_stations()

# Loading the models only once
LSTM_A, LSTM_B, std = loading_models_unique(station_id, day_of_testing)

tl = Timeloop()

@tl.job(interval=timedelta(minutes=1))
def predicting_by_5_minutes():
    df_prediction = create_result_df()
    predict_iteration_unique(list_of_stations, df_prediction, LSTM_A, LSTM_B, std)
    df_prediction.to_csv('/home/exalis/Github/velib-prediction-v2/prediction - {}.csv'.format(str(pd.Timestamp.now())[:16]))

tl.start()

while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        tl.stop()
        break
