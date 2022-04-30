import ijson
import json
import multiprocessing
import sys
import couchdb
# Simple multithreading https://stackoverflow.com/questions/2846653/how-can-i-use-threading-in-python
from multiprocessing.pool import ThreadPool
from geopy.geocoders import Nominatim


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


def typeCrime(text: str):
    ## Derived from
    # https://www.crimestatistics.vic.gov.au/about-the-data/classifications-and-victorian-map-boundaries/offence-classification

    # crimeList = [
    #     "crime", "robb", "stabb", "drug", "assault",
    # ]
    # crimeMention = ""
    # text = text.lower()
    # for crime in crimeList:
    #     if crime in text:
    #         crimeMention += (crime + "|")
    #
    # if crimeMention == "":
    #     return None
    if "crime" in text.lower():
        return True
    return False


def tweetValidator(tweet: json) -> bool:
    text = tweet["text"]
    if text is None:
        return False
    if text.startswith("RT"):
        return False
    return True


def tweetFormatter(tweet: json) -> json:
    location = surburbGetter(tweet)
    crime = typeCrime(tweet["text"])
    council = location["municipality"] if "municipality" in location else ""
    postcode = location["postcode"] if "postcode" in location else ""
    suburb = location["suburb"] if "suburb" in location else ""

    sqlInsert = {
        "_id": tweet["_id"] or tweet["id"],
        "tweet": tweet["text"],
        "created_at": tweet["created_at"],
        "mentionCrime": crime,
        "council": council,
        "postcode": postcode,
        "suburb": suburb
    }
    return sqlInsert


def processTweet(listTweet, db):
    for row in listTweet:
        if row["geo"] and tweetValidator(row):  # Else ignore
            dbInsert = tweetFormatter(row)
            try:
                db.save(dbInsert)
            except NameError:
                print("Matching id found")
                continue


def main():
    # Supply twitter json as arg 1
    tweet_json_file = open(sys.argv[1], 'r', encoding="utf8")

    couch = couchdb.Server('http://admin:admin@172.26.134.187:5984/')
    db = couch['tweets']  # existing

    results = []
    # MultiProcessing (Load it up with a chunk because overhead is high)
    num_thread = int(multiprocessing.cpu_count())
    pool = ThreadPool(num_thread)
    result = pool.apply_async(processTweet, args=(ijson.items(tweet_json_file, 'rows.item.doc'), db))
    results.append(result)
    [result.wait() for result in results]


if __name__ == '__main__':
    # Start time

    main()
