import ijson
import json
import multiprocessing
import sys
import couchdb
# Simple multithreading https://stackoverflow.com/questions/2846653/how-can-i-use-threading-in-python
from multiprocessing.pool import ThreadPool
from geopy.geocoders import Nominatim
import datetime as dt

def surburbGetter(tweet: json) -> str:
    area = ""
    # Get suburb by geographical location
    # Extract geocode
    if tweet["geo"]:
        locator = Nominatim(user_agent="cloud project")
        geo = tweet["geo"]["coordinates"]
        # Twitter is long/lat, nominatim is lat/long
        coordinates = (geo[0], geo[1])
        location = locator.reverse(coordinates)
        if location and location.raw and location.raw["address"]:
            area = location.raw["address"]
    return area


def tweetValidator(tweet: json) -> bool:
    text = tweet["text"]
    if text is None:
        return False
    if text.startswith("RT"):
        return False
    return True


def tweetFormatter(tweet: json) -> json:
    # Location Data
    location = surburbGetter(tweet)
    council = location["municipality"] if "municipality" in location else ""
    postcode = location["postcode"] if "postcode" in location else ""
    suburb = location["suburb"] if "suburb" in location else ""
    coordinates = tweet["geo"]["coordinates"]
    coordinates[0] = str(coordinates[0])
    coordinates[1] = str(coordinates[1])
    # DateObj Data
    dateObj = dt.datetime.strptime(tweet["created_at"], "%a %b %d %X +0000 %Y") if "created_at" in tweet else -1
    hourOfDay = dateObj.hour if dateObj != -1 in tweet else -1
    #  day-of-week as an integer from 0 to 6 representing Monday to Sunday
    dayOfWeek = dateObj.weekday() if dateObj != -1 in tweet else -1


    sqlInsert = {
        "_id": tweet["_id"] or tweet["id"],
        "tweet": tweet["text"],
        "created_at": tweet["created_at"] if "created_at" in tweet else -1,
        "hourOfDay" : hourOfDay,
        "dayOfWeek": dayOfWeek,
        "council": council,
        "postcode": postcode,
        "suburb": suburb,
        "geo": coordinates
    }
    return sqlInsert


def processTweet(listTweet, db):
    for row in listTweet:
        if row["geo"] and tweetValidator(row):  # Else ignore
            try:
                if row["_id"] in db:
                    doc = db.get(row["_id"])
                    if not "geo" in doc:
                        dbInsert = tweetFormatter(row)
                        doc["geo"] = dbInsert["geo"]
                    if not "dayOfWeek" in doc and "created_at" in doc:
                        dateObj = dt.datetime.strptime(doc["created_at"], "%a %b %d %X +0000 %Y")
                        doc["hourOfDay"] = dateObj.hour
                        #  day-of-week as an integer from 0 to 6 representing Monday to Sunday
                        doc["dayOfWeek"] = dateObj.weekday()
                    db.save(doc)
                else:
                    dbInsert = tweetFormatter(row)
                    db.save(dbInsert)
            except NameError:
                print("Matching id found")
                continue


def main():
    # Supply twitter json as arg 1
    tweet_json_file = open(sys.argv[1], 'r', encoding="utf8")

    couch = couchdb.Server('http://admin:admin@172.26.134.187:5984/')
    db = couch['twitter']  # existing

    results = []
    # MultiProcessing (Load it up with a chunk because overhead is high)
    num_thread = int(multiprocessing.cpu_count())
    pool = ThreadPool(num_thread)
    result = pool.apply(processTweet, args=(ijson.items(tweet_json_file, 'rows.item.doc'), db))
    results.append(result)
    [result.wait() for result in results]


if __name__ == '__main__':
    # Start time
    main()
