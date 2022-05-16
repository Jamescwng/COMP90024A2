#COMP90024

## Interactive Frontend

to run:

`cd` into `app` folder
run `python main.py`

will launch application at http://127.0.0.1:8080

## classification directory

Classifies tweets according to sentiment: Positive, Neutral, Negative



# Matteo's Branch

## Interactive Frontend

to run:

`cd` into `app` folder
run `python main.py`

will launch application at http://127.0.0.1:8080

## classification directory

Classifies tweets according to sentiment: Positive, Neutral, Negative

dependencies:
folium
flask
waitress
pandas
numpy
shapely
geopandas
couchdb
flask_wtf
wtforms

curl -X GET 'http://admin:admin@172.26.134.187:5984/twitter/_all_docs?include_docs=true' | jq '{"docs": [.rows[].doc]}' | jq 'del(.docs[]._rev)' > twitter.json