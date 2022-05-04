import couchdb
import folium
from folium.plugins import HeatMap
from folium.plugins import MarkerCluster
import random
from flask import Flask, render_template

user = "admin"
password = "admin"
couchserver = couchdb.Server("http://%s:%s@172.26.134.187:5984/" % (user, password))

db = couchserver['twitter']

rows = db.view('_design/CrimeInfo/_view/GeoData')

data = [row['value'] for row in rows]
random.seed(0)
random.shuffle(data)

MELB_COORDINATES = (-37.810612, 144.963954)

_map = folium.Map(location=MELB_COORDINATES, zoom_start=13)

HeatMap(data[:1500]).add_to(_map)

mCluster = MarkerCluster(name="Markers Demo").add_to(_map)

for each in data[:1500]:
    folium.Marker(location=[each[0], each[1]], 
                 popup="Latitude: {0}, Longitude: {1}".format(each[0], each[1])).add_to(mCluster)

folium.LayerControl().add_to(_map)

html_map = _map._repr_html_()

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", map = html_map)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)

#https://stackoverflow.com/questions/51025893/flask-at-first-run-do-not-use-the-development-server-in-a-production-environmen