import folium
from folium import Choropleth
from flask import Flask, render_template
from waitress import serve
import pandas as pd
import numpy as np
import geopandas as gpd

suburbs = pd.read_pickle("./suburbs.pkl")
suburbData = pd.read_pickle("./suburbData.pkl")
counts = pd.read_pickle("./counts.pkl")

######################################################################################################################

import couchdb
from flask_wtf import FlaskForm
from wtforms.fields import DateField
from wtforms.validators import DataRequired
from wtforms import validators, SubmitField

from datetime import datetime

user = "admin"
password = "admin"
couchserver = couchdb.Server("http://%s:%s@172.26.134.187:5984/" % (user, password))
db = couchserver['twitter']

def get_data(start, end):
    data = {}

    for suburb in suburbs['geometry'].index.tolist():
        pos = 0
        total = 0

        for item in db.view('_design/Data/_view/Date', reduce=False, startkey=[suburb, start], endkey=[suburb, end]):
            if item.value == 1:
                pos += 1
            total += 1
        
        if total > 0:
            data[suburb] = [round(pos / (total * 1.0), 2) * 100, total, suburb]
    
    return pd.DataFrame.from_dict(data, orient='index', columns=['%', 'counts', 'suburb'])

class DateForm(FlaskForm):
    start = DateField('Start Date', format='%Y-%m-%d', validators=(validators.DataRequired(),))
    end = DateField('End Date', format='%Y-%m-%d', validators=(validators.DataRequired(),))
    submit = SubmitField('Update')

######################################################################################################################

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

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret'

@app.route("/", methods=['GET','POST'])
def index():
    form = DateForm()
    if form.validate_on_submit():
        return render_template("index.html", form=form, map=get_map(form.start.data, form.end.data))
    return render_template("index.html", form=form, map=get_map())

if __name__ == "__main__":
    serve(app, host="127.0.0.1", port=8080) # use serve for production development
    #app.run(host="127.0.0.1", port=8080, debug=True)

#https://stackoverflow.com/questions/51025893/flask-at-first-run-do-not-use-the-development-server-in-a-production-environmen