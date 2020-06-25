# velib-prediction-v2

You can find the app related to this project here!
https://prediction-velib.herokuapp.com/

Table of Contents
=================

   * [velib-prediction-v2](#velib-prediction-v2)
      * [Introduction](#introduction)
      * [I. Creating auto-scrapping, SQL database](#i-creating-auto-scrapping-sql-database)
         * [1. SQL database (alias <strong>db_velib</strong>)](#1-sql-database-alias-db_velib)
            * [a. Creating the RDS MariaDB SQL database](#a-creating-the-rds-mariadb-sql-database)
            * [b. Creating realtime update table (alias <strong>db_velib.velib_realtime</strong>)](#b-creating-realtime-update-table-alias-db_velibvelib_realtime)
            * [c. Creating the station name table (alias <strong>db_velib.stations</strong>)](#c-creating-the-station-name-table-alias-db_velibstations)
            * [d. Creating the prediction table (alias <strong>db_velib.results</strong>)](#d-creating-the-prediction-table-alias-db_velibpred)
         * [2. Scrapping and Predicting Machine (alias <strong>ubuntu_scrapping</strong>)](#2-scrapping-and-predicting-machine-alias-ubuntu_scrapping)
            * [a. Creating the AWS Linux instance](#a-creating-the-aws-linux-instance)
            * [b. Making the auto-scrapping script](#b-making-the-auto-scrapping-script)
            * [C. Making the auto-predict script](#c-making-the-auto-predict-script)
      * [II. Model research - Univariate](#ii-model-research---univariate)
         * [1. Models for benchmark : Facebook Prophet vs Tensorflow (LSTM)](#1-models-for-benchmark--facebook-prophet-vs-tensorflow-lstm)
         * [2. First Benchmark : one model by station](#2-first-benchmark--one-model-by-station)
         * [3. Second Benchmark: global model vs one model by station](#3-second-benchmark-global-model-vs-one-model-by-station)
      * [III. Creating an interactive app](#iii-creating-an-interactive-app)
         * [1. Creating a nice Dash app](#1-creating-a-nice-dash-app)
         * [2. Uploading the Dash app to Heroku](#2-uploading-the-dash-app-to-heroku)
      * [Conclusion and next steps](#conclusion-and-next-steps)

Created by [gh-md-toc](https://github.com/ekalinin/github-markdown-toc)

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

For the purpose of deployment and conveniance, I have used an amazon RDS server running MariaDB. It is of course possible to use an other SQL application and to run in local. We will deal here only of the SQL aspects, not server creation.

Everycode for SQL will be done in the SQL console.

Creation of the database:
```
CREATE DATABASE db_velib;
```

#### b. Creating realtime update table (alias **db_velib.velib_realtime**)

The purpose of the table is to scrap the database of the velib numbers.

Creation of the table :
```
CREATE TABLE velib_realtime (
station_id SMALLINT UNSIGNED,
operational_station VARCHAR(3),
nb_free_docks TINYINT UNSIGNED,
nb_total_free_bikes TINYINT UNSIGNED,
nb_free_mechanical_bikes TINYINT UNSIGNED,
nb_free_electrical_bikes TINYINT UNSIGNED,
payment_totem VARCHAR(3),
bike_return_possible VARCHAR(3),
data_actualisation DATETIME, # in minutes
date_of_update DATETIME,
PRIMARY KEY (station_id, date_of_update)
) 
ENGINE=INNODB;
```

Adding Index for station_id and date_of_update for later use :
```
ALTER TABLE db_velib.velib_realtime 
ADD INDEX idx_velib_realtime_station_id (station_id);
```
```
ALTER TABLE db_velib.velib_realtime 
ADD INDEX idx_velib_realtime_date_of_update (date_of_update);
```

#### c. Creating the station name table (alias **db_velib.stations**)

The purpose of the table is to scrap the database of the stations information.

Creating table :
```
CREATE TABLE velib_stations (
station_id int(10) unsigned NOT NULL AUTO_INCREMENT,
station_name varchar(45) DEFAULT NULL,
station_capacity tinyint(3) DEFAULT NULL,
geo_coordinates varchar(50) DEFAULT NULL,
latitude varchar(30) DEFAULT NULL,
longitude varchar(30) DEFAULT NULL,
geo_point point DEFAULT NULL,
city varchar(30) DEFAULT NULL,
PRIMARY KEY (station_id)
) ENGINE=InnoDB ;
```

Creating indexes :
```
ALTER TABLE db_velib.velib_stations 
ADD INDEX idx_velib_station_station_id (station_id);
```


#### d. Creating the prediction table (alias **db_velib.pred**)

The purpose of the table is to store the predictions to make visualization and later benchmarking.

Creation of the table :
```
CREATE TABLE velib_pred (
station_id SMALLINT UNSIGNED,  
predicted_time DATETIME,
model_A TINYINT UNSIGNED,
model_B TINYINT UNSIGNED,
date_of_update DATETIME,
PRIMARY KEY (station_id, predicted_time, date_of_update)
) 
ENGINE=INNODB;
ALTER TABLE velib_pred ADD KEY index_velib_pred_update  (date_of_update);
```

Creating indexes :
```
ALTER TABLE db_velib.velib_realtime 
ADD INDEX index_date_of_update (date_of_update);
```

### 2. Scrapping and Predicting Machine (alias **ubuntu_scrapping**)

#### a. Creating the AWS Linux instance

This Linux instance has for purpose to do the scrapping work every minute, predicting every 5 minutes and updating the SQL databases. Even though this could have been done in Python application, Linux offers better monitoring and flexibility. 

The name of the machine will be here **ubuntu_scrapping**, with user name **ubuntu**.

Inside the ubuntu user folder, we will make two files for easier underestanding:
- **Scripts** to store all scripts, which will be launched via crontab jobs
- **temp_data** to store temporary the downloaded files of scrapping and prediction. Even if it would be possible not to store the files to improve performance, it makes debugging and code structuration much easier.

The structure can be found in the Ubuntu_AWS folder, as well as spec-file.txt for installing the conda environment.

The first step is to install anaconda and then creating an environment with all the needed libraries. The environment name will be **tensorflowenv**:
```
conda create --name tesnroflowenv --file spec-file.txt
```

For the next lines of code, aliases will be:

| Nature      |     Alias  | 
| ------------- | ------------- |
| Host     |   host             |
| User        |        user        |
| Password      |        password        |
| Database      |        db_velib        |

#### b. Making the auto-scrapping script

Creating the script to upload the database of velib count every minute.

Creating the file : 
```
cd /home/ubuntu/Scripts
touch update_realtime.sh
chmod +x update_realtime.sh
```

Code to insert in the script update_realtime.sh:
```
# Download the file to load
wget -N "https://opendata.paris.fr/explore/dataset/velib-disponibilite-en-temps-reel/download/?format=csv&timezone=Europe/Berlin&lang=fr&use_labels_for_header=true&csv_separator=%3B" -O /home/ubuntu/temp_data/velib_dispo.csv

# Connexion to mysql, create a temporary table with new data, look for last city data from velib scrapping to update city, update all table

mysql -h host -P 3306 -u user -ppassword -D db_velib <<EOF
SET time_zone = 'Europe/Paris';
CREATE TEMPORARY TABLE temp_velib_scrapping LIKE temp_velib_scrapping_update;
CREATE TEMPORARY TABLE temp_velib_realtime LIKE velib_realtime;

LOAD DATA LOCAL INFILE '/home/ubuntu/temp_data/velib_dispo.csv'
INTO TABLE temp_velib_scrapping FIELDS TERMINATED BY ';' ENCLOSED BY '' LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(station_id, station_name, operational_station, station_capacity, nb_free_docks, nb_total_free_bikes,
nb_free_mechanical_bikes, nb_free_electrical_bikes, payment_totem, bike_return_possible,
data_actualisation, geo_coordinates, city, insee_code);


INSERT INTO velib_realtime
(
SELECT
station_id,
operational_station,
nb_free_docks,
nb_total_free_bikes,
nb_free_mechanical_bikes,
nb_free_electrical_bikes,
payment_totem,
bike_return_possible,

CONVERT(LEFT(data_actualisation, CHAR_LENGTH(data_actualisation)-6), DATETIME) data_act,
CONVERT(LEFT(NOW(), CHAR_LENGTH(NOW())-3), DATETIME) update_time
FROM temp_velib_scrapping)
ON DUPLICATE KEY UPDATE

operational_station = VALUES(operational_station),
nb_free_docks = VALUES(nb_free_docks),
nb_total_free_bikes = VALUES(nb_total_free_bikes),
nb_free_mechanical_bikes = VALUES(nb_free_mechanical_bikes),
nb_free_electrical_bikes = VALUES(nb_free_electrical_bikes),
payment_totem = VALUES(payment_totem),
bike_return_possible = VALUES(bike_return_possible),
data_actualisation = VALUES(data_actualisation),
date_of_update = VALUES(date_of_update);

DROP TABLE temp_velib_scrapping;
DROP TABLE temp_velib_realtime;

EOF
```

Updating crontab for doing scrapping every minute :
```
crontab -e
```

Adding line to crontab list: 
```
* * * * * /home/ubuntu/Scripts/update_realtime.sh
```

#### C. Making the station information update script

Creating the file : 
```
cd /home/ubuntu/Scripts
touch update_stations_hourly.sh
chmod +x update_stations_hourly.sh
```

*(optional)* Making the first load (in order to input city)
```
mysql -h host -P 3306 -u user -ppassword -D db_velib <<EOF
LOAD DATA LOCAL INFILE '/home/ubuntu/temp_data/update_stations_first_load.csv' 
INTO TABLE tvelib_stations
FIELDS TERMINATED BY ';' ENCLOSED BY '' LINES TERMINATED BY '\n' IGNORE 1 ROWS  
(station_id, station_name, station_capacity, geo_coordinates, latitude, longitude,geo_point, city);

EOF
```

Updating update_stations_hourly.sh:
```
# Download the file to load
wget -N "https://opendata.paris.fr/explore/dataset/velib-emplacement-des-stations/download/?format=csv&timezone=Europe/Berlin&lang=fr&use_labels_for_header=true&csv_separator=%3B" -O /home/ubuntu/temp_data/update_stations.csv

# Connexion to mysql, create a temporary table with new data, look for last city data from velib scrapping to update city, update all table

mysql -h host -P 3306 -u user -ppassword -D db_velib <<EOF

CREATE TEMPORARY TABLE temp_velib_stations LIKE velib_stations;

LOAD DATA LOCAL INFILE '/home/ubuntu/temp_data/update_stations.csv' 
INTO TABLE temp_velib_stations
FIELDS TERMINATED BY ';' ENCLOSED BY '' LINES TERMINATED BY '\n' IGNORE 1 ROWS  
(station_id, station_name, station_capacity, geo_coordinates);

INSERT INTO velib_stations

SELECT * FROM
(SELECT t1.station_id, t1.station_name, t1.station_capacity, t1.geo_coordinates, t2.latitude, t2.longitude, t2.geo_point, t2.city  FROM
(SELECT station_id, station_name, station_capacity, geo_coordinates FROM db_velib.temp_velib_stations) t1
INNER JOIN
(SELECT * FROM db_velib.velib_stations) t2
on t1.station_id = t2.station_id) t3

ON DUPLICATE KEY UPDATE 
station_name = VALUES(station_name),
station_capacity = VALUES(station_capacity),
geo_coordinates = VALUES(geo_coordinates),
city= VALUES(city);
DROP TEMPORARY TABLE temp_velib_stations;

UPDATE velib_stations SET latitude = LEFT(geo_coordinates,LOCATE(",", geo_coordinates)-2);
UPDATE velib_stations SET latitude = RIGHT(geo_coordinates,char_length(geo_coordinates)-LOCATE(",", geo_coordinates)) ;
UPDATE velib_stations SET geo_point = POINT(latitude, longitude);

EOF

```

#### D. Making the auto-predict script

Creating the script to upload the database of velib count every minute. Python file **predict_5_min.py** can be found in AWS_scrapping folder.

Creating files : 
```
cd /home/ubuntu/Scripts
touch predict_5_min_and_load.sh
touch loading_predictions.sh
chmod +x predict_5_min_and_load.sh
chmod +x loading_predictions.sh
```

The purpose of predict_5_min_and_load.sh is to activate the environnement to run the prediction script, to make prediction and to start loading_predictions.sh to load the predictions into the database. 

Code to insert in the script predict_5_min_and_load.sh :
```
#!/bin/bash
source /home/ubuntu/anaconda3/bin/activate tensorflowenv
cd /home/ubuntu/Scripts/
python predict_5_min.py
source /home/ubuntu/anaconda3/bin/deactivate
./loading_predictions.sh
```

Code to insert in the script loading_predictions.sh :
```
# Connexion to mysql, create a temporary table with new data, look for last city data from velib scrapping to update city, update all table
mysql -h host -P 3306 -u user -ppassword -D db_velib <<EOF
CREATE TEMPORARY TABLE temp_velib_pred LIKE velib_pred;

LOAD DATA LOCAL INFILE '/home/ubuntu/temp_data/5min_predictions_global.csv'
INTO TABLE velib_pred FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(station_id, predicted_time, model_A, model_B, date_of_update);

INSERT INTO velib_pred

(SELECT * 
FROM temp_velib_pred)

ON DUPLICATE KEY UPDATE

station_id = VALUES(station_id),
predicted_time = VALUES(predicted_time),
model_A = VALUES(model_A),
model_B = VALUES(model_B),
date_of_update = VALUES(date_of_update);

DROP TABLE temp_velib_pred;

EOF

```

Updating crontab for doing scrapping every minute :
```
crontab -e
```

Adding line to crontab list: 
```
*/5 * * * * /home/ubuntu/Scripts/predict_5_min_and_load.sh
```

## II. Model research - Univariate
### 1. Models for benchmark : Facebook Prophet vs Tensorflow (LSTM)
### 2. First Benchmark : one model by station

All producted models can be found here (1390 models, 585 Mo)
https://drive.google.com/file/d/1JkA1gcXXTAI7HNik-GAbiq_ZHWBwXhep/view?usp=sharing

### 3. Second Benchmark: global model vs one model by station

## III. Creating an interactive app
### 1. Creating a nice Dash app
### 2. Deploying the Dash app to Heroku

## Conclusion and next steps
