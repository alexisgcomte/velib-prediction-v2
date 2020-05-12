# Import of librairies
import tensorflow as tf
import mysql.connector as mariadb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from sklearn.preprocessing import StandardScaler
from tensorflow import keras
import datetime
import math
from sklearn.metrics import mean_squared_error
from tqdm import tqdm

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
    
# Transforming the input data in the proper format 

def data_preparation(dataset, target, start_index, end_index, history_size,
                      target_size, step, single_step=False):
    data = []
    labels = []

    start_index = start_index + history_size
    if end_index is None:
        end_index = len(dataset) - target_size

    for i in range(start_index, end_index):
        indices = range(i-history_size, i, step)
        data.append(dataset[indices])

        if single_step:
            labels.append(target[i+target_size])
        else:
            labels.append(target[i:i+target_size])

    return np.array(data), np.array(labels)


def measure_rmse(actual, predicted):
    return math.sqrt(mean_squared_error(actual, predicted))


def model_training(station_id, day_of_testing, past_history, future_target):


    tf.random.set_seed(13)
    past_history = 180
    future_target = 30
    STEP = 1
    BATCH_SIZE = 32
    BUFFER_SIZE = 100000
    EPOCHS = 15
    EVALUATION_INTERVAL = 200

    request = sql_query("../../aws_mariadb_crendentials.csv")

    # Taking data from  station 9034 - Madeleine
    query = """
    SELECT DISTINCT date_of_update, nb_total_free_bikes FROM velib_realtime
    WHERE station_id = {}
    AND date_of_update > DATE('2020-05-05')
    AND date_of_update <= DATE_ADD(DATE('{}'), INTERVAL 1 DAY)
    ORDER BY date_of_update ASC
    """.format(station_id, day_of_testing)

    df = request(query)
    df.index = df['date_of_update']
    df = df.nb_total_free_bikes
    
    TRAIN_SPLIT = round(df.shape[0]*0.7)

    # StandardScaler transformation of the dataset

    std = StandardScaler()
    std.fit(df[:TRAIN_SPLIT].values.reshape(-1,1))
    df = std.transform(df.values.reshape(-1,1))

    # Creating proper format data

    x_train, y_train = data_preparation(df, df[1:], 0, TRAIN_SPLIT,
                                               past_history,
                                               future_target, STEP)
    x_val, y_val = data_preparation(df, df[1:], TRAIN_SPLIT, None,
                                           past_history,
                                           future_target, STEP)

    # Creating format for NN intput

    x_train = x_train.reshape(x_train.shape[0], x_train.shape[1], 1)
    x_val = x_val.reshape(x_val.shape[0], x_val.shape[1], 1)

    # Creating batches for tensorflow use

    train_data = tf.data.Dataset.from_tensor_slices((x_train, y_train))
    train_data = train_data.cache().shuffle(BUFFER_SIZE).batch(BATCH_SIZE).repeat()

    val_data = tf.data.Dataset.from_tensor_slices((x_val, y_val))
    val_data = val_data.batch(BATCH_SIZE).repeat()

    # Modeling A
    
    LSTM_model_A = tf.keras.models.Sequential([
        tf.keras.layers.LSTM(32, input_shape=x_train.shape[-2:]),
        tf.keras.layers.Dense(future_target)
    ])

    LSTM_model_A.compile(optimizer='adam', loss='mean_squared_error')

    LSTM_model_A_history = LSTM_model_A.fit(train_data, epochs=EPOCHS,
                                                steps_per_epoch=EVALUATION_INTERVAL,
                                                validation_data=val_data,
                                                validation_steps=200)
    
    # Modeling B
    
    LSTM_model_B = keras.Sequential()
    LSTM_model_B.add(
      keras.layers.Bidirectional(
        keras.layers.LSTM(
          units=64,
          input_shape=(x_train.shape[-2:])
        )
      )
    )
    LSTM_model_B.add(keras.layers.Dropout(rate=0.2))
    LSTM_model_B.add(keras.layers.Dense(units=30))
    LSTM_model_B.compile(loss='mean_squared_error', optimizer='adam')
    
    LSTM_model_B_history = LSTM_model_B.fit(train_data, epochs=EPOCHS,
                                            steps_per_epoch=EVALUATION_INTERVAL,
                                            validation_data=val_data,
                                            validation_steps=200)
    
    
    
    return LSTM_model_A, LSTM_model_A_history, LSTM_model_B, LSTM_model_B_history, std

def results_filling(df_results):

    for i in df_results.index:
        try:
            # interval // Taking the last 180 values
            past_for_prediction = df[(i - datetime.timedelta(minutes=past_history+100)):i][-180:].values
            past_for_prediction_encoded = std.transform(past_for_prediction.reshape(-1, 1))

            # Prediction of A
            results_A = LSTM_model_A.predict(past_for_prediction_encoded.reshape(1,past_history,1))[0]
            results_A = std.inverse_transform(results_A)

            # Prediction of B
            results_B = LSTM_model_B.predict(past_for_prediction_encoded.reshape(1,past_history,1))[0]
            results_B = std.inverse_transform(results_B)

            df_results.prediction_A[i] = results_A
            df_results.prediction_B[i] = results_B
            df_results.real_values[i] = df[i: i + datetime.timedelta(minutes=60)][0:30].values

            df_results.loc[i].metrics_A = measure_rmse(df_results.loc[i].real_values, df_results.loc[i].prediction_A)
            df_results.loc[i].metrics_B = measure_rmse(df_results.loc[i].real_values, df_results.loc[i].prediction_B)
        except:
            print('error at', i)
            
            df_results.loc[i].metrics_A = None
            df_results.loc[i].metrics_B = None

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
print(list_of_stations[0:5])

#Variables

day_of_testing = '2020-05-11'
past_history = 180
future_target = 30

# Request for database

for station_id in tqdm(list_of_stations):

    request = sql_query("../../aws_mariadb_crendentials.csv")

    query = """
    SELECT DISTINCT date_of_update, nb_total_free_bikes FROM velib_realtime
    WHERE station_id = {}
    AND date_of_update > DATE('2020-05-05')
    AND date_of_update <= DATE_ADD(DATE('{}'), INTERVAL 1 DAY)
    ORDER BY date_of_update ASC
    """.format(station_id, day_of_testing)

    df = request(query)
    df.index = df['date_of_update']
    df = df.nb_total_free_bikes

    df_results = pd.DataFrame(columns=['prediction_A', 'prediction_B', 'real_values', 'metrics_A', 'metrics_B'], index=pd.date_range(day_of_testing+' 06:00:00', periods=64, freq='15Min'))

    # Training

    LSTM_model_A, LSTM_model_A_history, LSTM_model_B, LSTM_model_B_history, std = model_training(station_id, day_of_testing, past_history, future_target)

    # importing results
    results_filling(df_results)

    df_results.to_csv("/home/exalis/Github/velib-prediction-v2/3. Results/2. Tensorflow Univariate/Tensorflow Univariate Results - {} - {}.csv".format(day_of_testing, station_id))

    print('finished ', station_id)

