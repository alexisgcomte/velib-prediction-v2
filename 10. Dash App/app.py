import dash
import dash_html_components as html
import dash_core_components as dcc
import plotly.graph_objects as go
import pandas as pd
from dash.dependencies import Input, Output
import mysql.connector as mariadb
from datetime import timedelta
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

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
    
# Modify later query to have last value and df

def retrieve_results():

    request = sql_query("../../aws_mariadb_crendentials.csv")
    query = """
    SELECT * FROM 
    ((SELECT predicted_time, station_id, model_A FROM velib_pred
    WHERE date_of_update =
    (select max(date_of_update) FROM velib_pred))
    UNION
    (SELECT date_of_update, station_id, nb_total_free_bikes FROM velib_realtime
    WHERE date_of_update < (SELECT max(date_of_update) FROM velib_pred) AND date_of_update >= DATE_SUB((SELECT max(date_of_update) FROM velib_pred), INTERVAL 30 MINUTE)
    ORDER BY date_of_update DESC)
    ORDER BY predicted_time ASC) AS data1
    LEFT OUTER JOIN
    (SELECT station_id, concat(station_id, ' - ', station_name) station_name FROM db_velib.velib_stations) AS data2
    on data1.station_id = data2.station_id
    """
#    query = """
#    SELECT * FROM velib_pred
#    WHERE date_of_update =
#    (select max(date_of_update) FROM velib_pred)
#    """
    df = request(query)
    df.index = df.predicted_time
    df = df[['station_name','model_A']]

    return df

# Load data
#df = pd.read_csv('samplevelib.csv', index_col=0, parse_dates=True)

# Initialize the app
app = dash.Dash(__name__)
server = app.server
#app.config.suppress_callback_exceptions = True
#app.scripts.config.serve_locally = True
#app.css.config.serve_locally = True

df = retrieve_results()

def get_options(list_stocks):
    dict_list = []
    for i in list_stocks:
        dict_list.append({'label': i, 'value': i})

    return dict_list


app.layout = html.Div(
    children=[
        html.Div(className='row',
                 children=[
                    html.Div(className='three columns div-user-controls',
                             children=[
                                 html.H2('DASH - Velib Prediction'),
                                 html.P("Let's predict velib availiability ! ;)"),
                                 html.P('Pick one or more stations.'),
                                 html.Div(
                                     className='div-for-dropdown',
                                     children=[
                                         dcc.Dropdown(id='stockselector', options=get_options(df['station_name'].unique()),
                                                      multi= True, value=[df['station_name'].sort_values()[0]],
                                                      style={'backgroundColor': '#1E1E1E'},
                                                      className='stockselector'
                                                      ),
                                     ],
                                     style={'color': '#1E1E1E'})
                                ]
                             ),
                    html.Div(className='nine columns div-for-charts bg-grey',
                             children=[
                                 dcc.Graph(id='timeseries', config={'displayModeBar': False}, animate=True)
                             ])
                              ])
        ]

)


# Callback for timeseries price
@app.callback(Output('timeseries', 'figure'),
              [Input('stockselector', 'value')])
def update_graph(selected_dropdown_value):
    trace1 = []
#    df_sub = df
    df_sub = pd.read_csv('last_update.csv', index_col=0)
    for station_name in selected_dropdown_value:
        trace1.append(go.Scatter(x=df[df['station_name'] == station_name].index,
                                 y=df[df['station_name'] == station_name]['model_A'],
                                 mode='lines',
                                 opacity=0.7,
                                 name=station_name,
                                 textposition='bottom center'))
    traces = [trace1]
    data = [val for sublist in traces for val in sublist]
    figure = {'data': data,
              #data
              'layout': go.Layout(
                  colorway=["#5E0DAC", '#FF4F00', '#375CB1', '#FF7400', '#FFF400', '#FF0056'],
                  template='plotly_dark',
                  paper_bgcolor='rgba(0, 0, 0, 0)',
                  plot_bgcolor='rgba(0, 0, 0, 0)',
                  margin={'b': 15},
                  hovermode='x',
                  autosize=True,
                  title={'text': 'Availiability', 'font': {'color': 'white'}, 'x': 0.5},
                  xaxis={'range': [df_sub.index.min(), df_sub.index.max()]},
              ),

              }

    return figure

UPDADE_INTERVAL = 60

def get_new_data_every(period=UPDADE_INTERVAL):
    """Update the data every 'period' seconds"""
    while True:
        df = retrieve_results()
        df.to_csv('./last_update.csv')
        print("data updated")
        time.sleep(period)
        

def start_multi():
    executor = ProcessPoolExecutor(max_workers=1)
    executor.submit(get_new_data_every)
    


if __name__ == '__main__':
    
    start_multi()
    app.run_server()