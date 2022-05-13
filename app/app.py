from copy import deepcopy
from datetime import datetime

import couchdb
import folium
import geopandas as gpd
import numpy as np
import pandas as pd
from flask import Flask, render_template
from flask_wtf import FlaskForm
from folium import Choropleth
from waitress import serve
from wtforms import SubmitField, validators
from wtforms.fields import DateField
from wtforms.validators import DataRequired
from shapely.geometry import Polygon, Point

# Form to update twitter data timeframe
class DateForm(FlaskForm):
    start = DateField('Start Date', format='%Y-%m-%d', validators=(validators.DataRequired(),))
    end = DateField('End Date', format='%Y-%m-%d', validators=(validators.DataRequired(),))
    submit = SubmitField('Update')

# Suburb polygons
suburbs = gpd.read_file('./localities/vic.shp')
suburbs = suburbs.drop(columns=['LC_PLY_PID', 'LOC_PID', "DT_CREATE", "LOC_CLASS", "STATE"])
suburbs = suburbs[["LOC_NAME", "geometry"]].set_index("LOC_NAME")
suburbsToKeep = pd.read_csv("suburbs.txt", header=None)
suburbs = suburbs.loc[suburbsToKeep[0]]
# suburbs = pd.read_pickle("./suburbs.pkl")

# Couchdb access
user = "admin"
password = "admin"
couchserver = couchdb.Server("http://%s:%s@172.26.134.187:5984/" % (user, password))

###########################################################################################################################################

# Get twitter data within timeframe
def get_data(start, end):
    db = couchserver['twitter']
    data = {}

    for suburb in suburbs['geometry'].index.tolist():
        pos = 0
        total = 0

        for item in db.view('_design/Data/_view/Data', reduce=False, startkey=[suburb, start], endkey=[suburb, end]):
            if item.value == 1:
                pos += 1
            total += 1
        
        if total > 0:
            data[suburb] = [round(pos / (total * 1.0), 2) * 100, total, suburb]
    
    return pd.DataFrame.from_dict(data, orient='index', columns=['%', 'counts', 'suburb'])

def get_pollution_data():
    db = couchserver['pollutant']
    rows = db.view('_design/Pollution/_view/Data')

    suburbs_copy = suburbs.copy(deep=True)

    points = []

    for row in rows:
        points.append((row['value']['geo'][0], row['value']['geo'][1], row['value']['reports']))

    points = pd.DataFrame(points)
    points[0] = points[0].apply(float)
    points[1] = points[1].apply(float)
    points['coords'] = list(zip(points[0],points[1]))
    points['coords'] = points['coords'].apply(Point)

    points = gpd.GeoDataFrame(points, geometry='coords', crs=suburbs.crs)

    pointInPolys = gpd.sjoin(points, suburbs)
    counts = pointInPolys.groupby('index_right')[2].sum()

    suburbs_copy["counts"] = counts
    suburbs_copy['counts'] = suburbs_copy['counts'].fillna(0)
    suburbs_copy["suburb"] = suburbs_copy.index

    return suburbs_copy

# Get map with twitter data within timeframe
def get_map(start=datetime.min.date(), end=datetime.max.date()):
    epoch = datetime.utcfromtimestamp(0)
    startdatetime = datetime.combine(start, datetime.min.time())
    enddatetime = datetime.combine(end, datetime.min.time())

    starttime = (startdatetime - epoch).total_seconds() * 1000.0
    endtime = (enddatetime - epoch).total_seconds() * 1000.0

    data = get_data(starttime, endtime)
    data.index.name = 'LOC_NAME'

    data_bins = data.iloc[:,0]

    bins = np.histogram(data_bins, bins=7)[1]

    # Create a base map
    m = folium.Map(location=[-37.810612, 144.963954], tiles='cartodbpositron', zoom_start=11)

    # Add a choropleth map to the base map
    Choropleth(geo_data=suburbs.__geo_interface__, 
            data=data_bins, 
            key_on="feature.id", 
            fill_color='RdYlBu', line_opacity=0.9,
            threshold_scale = bins,
            legend_name='Percentage of Positive Tweets Per Suburb - Each Suburb Has 50+ Tweets'
            ).add_to(m)

    mymap = m

    style_function = lambda x: {'fillColor': '#ffffff', 
                                'color':'#000000', 
                                'fillOpacity': 0.1, 
                                'weight': 0.1}
    highlight_function = lambda x: {'fillColor': '#000000', 
                                    'color':'#000000', 
                                    'fillOpacity': 0.50, 
                                    'weight': 0.1}

    NIL = folium.features.GeoJson(
        gpd.GeoDataFrame(suburbs.merge(data, on='LOC_NAME', how='left')),
        style_function=style_function, 
        control=False,
        highlight_function=highlight_function, 
        tooltip=folium.features.GeoJsonTooltip(
            fields=['suburb','counts','%'],
            aliases=['Suburb: ','Number of Tweets: ', 'Tweets With Positive Sentiment (%): '],
            style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;") 
        )
    )
    mymap.add_child(NIL)
    mymap.keep_in_front(NIL)
    folium.LayerControl().add_to(mymap)

    return mymap._repr_html_()

def get_pollution_map(data):
    counts = data.loc[:,'counts']

    bins = np.histogram(counts, bins=8)[1]
    bins = np.insert(bins, 1, 5)

    m = folium.Map(location=[-37.810612, 144.963954], tiles='cartodbpositron', zoom_start=10)

    # Add a choropleth map to the base map
    Choropleth(geo_data=suburbs.__geo_interface__, 
            data=counts, 
            key_on="feature.id", 
            fill_color='RdYlBu_r', line_opacity=0.9,
            threshold_scale = bins,
            legend_name='Number of Pollutant Reports per Suburb'
            ).add_to(m)

    mymap = m

    style_function = lambda x: {'fillColor': '#ffffff', 
                                'color':'#000000', 
                                'fillOpacity': 0.1, 
                                'weight': 0.1}
    highlight_function = lambda x: {'fillColor': '#000000', 
                                    'color':'#000000', 
                                    'fillOpacity': 0.50, 
                                    'weight': 0.1}

    NIL = folium.features.GeoJson(
        data,
        style_function=style_function, 
        control=False,
        highlight_function=highlight_function, 
        tooltip=folium.features.GeoJsonTooltip(
            fields=['suburb','counts'],
            aliases=['Suburb: ','Number of Pollutant Complaints: '],
            style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;") 
        )
    )
    mymap.add_child(NIL)
    mymap.keep_in_front(NIL)
    folium.LayerControl().add_to(mymap)

    return mymap._repr_html_()

###########################################################################################################################################

pollution_map = get_pollution_map(get_pollution_data())

# Run frontend
app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret'

@app.route("/", methods=['GET','POST'])
def index():
    form = DateForm()
    # Update map on submit
    if form.validate_on_submit():
        return render_template(
            "index.html", 
            form=form, 
            map=get_map(form.start.data, form.end.data),
            pollution_map=pollution_map
        )
    return render_template(
        "index.html", 
        form=form, 
        map=get_map(), 
        pollution_map=pollution_map
    )

if __name__ == "__main__":
    serve(app, host="127.0.0.1", port=8080) # use serve for production development
    #app.run(host="127.0.0.1", port=8080, debug=True)

#https://stackoverflow.com/questions/51025893/flask-at-first-run-do-not-use-the-development-server-in-a-production-environmen
