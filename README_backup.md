# velib-prediction-v2

You can find the app related to this project here!
https://prediction-velib.herokuapp.com/

## Introduction

As a Jedha datascience bootcamp student, my team made a proof of concept of the possibility to predict the station availiability of Velib', Paris bike sharing service. The results were very interesting, but two weeks were not enough to make it "realtime" and to go deeper into the analysis. The idea of the project is to do the complement: **predicting the number of availaible velib, but this time for all Paris and in realtime!**

The objective to go deeper in different fields:
- Modeling:
    - Using new librairies like Facebook Prophet or other Deep Learning Models
    - Making a good assessment of different model on large scale
- Data Engineering:
    - Creating a realtime scrapping Bash machine in AWS
    - Creating a SQL databae for easier query, updated every minute by the scrapping device
- Data Visualization:
    - Creating a clean visualization of the predictions with Plotly
    - Using Dash for interactive selection of the stations and update of lines
- Production:
    - Making predictions every 5 minutes and uploading results in an SQL database
    - Creating a device responsive Heroku app to make the project accessible!

## I. Creating auto-scrapping, SQL database
### 1. SQL database (alias **db_velib**)
#### a. Creating the RDS MariaDB SQL database
#### b. Creating realtime update table (alias **db_velib.velib_realtime**)
#### c. Creating the station name table (alias **db_velib.stations**)
#### d. Creating the prediction table (alias **db_velib.results**)

### 2. Scrapping and Predicting Machine (alias **ubuntu_scrapping**)
#### a. Creating the AWS Linux instance
#### b. Making the auto-scrapping script
#### C. Making the auto-predict script

## II. Model research - Univariate
### 1. Models for benchmark : Facebook Prophet vs Tensorflow (LSTM)
### 2. First Benchmark : one model by station
### 3. Second Benchmark: global model vs one model by station

## III. Creating an interactive app
### 1. Creating a nice Dash app
### 2. Uploading the Dash app to Heroku

## Conclusion and next steps