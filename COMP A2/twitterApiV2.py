import json
import os
import sys

import couchdb
from tweepy import Client, HTTPException, TooManyRequests
from geopy.geocoders import Nominatim
import time

twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

if not twitter_bearer_token:
    raise RuntimeError("Not found bearer token")

client = Client(twitter_bearer_token)


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
    coordinates = tweet["geo"]["coordinates"]
    coordinates[0] = str(coordinates[0])
    coordinates[1] = str(coordinates[1])

    sqlInsert = {
        "_id": tweet["_id"] or tweet["id"],
        "tweet": tweet["text"],
        "created_at": tweet["created_at"],
        "mentionCrime": crime,
        "council": council,
        "postcode": postcode,
        "suburb": suburb,
        "geo": coordinates
    }
    return sqlInsert


def processTweet(tweet, db):
    if tweet["geo"] and tweetValidator(tweet):  # Else ignore
        dbInsert = tweetFormatter(tweet)
        try:
            if tweet["_id"] in db:
                doc = db.get(tweet["_id"])
                doc["geo"] = dbInsert["geo"]
                db.save(doc)
            else:
                db.save(dbInsert)
        except NameError:
            print("Matching id found")


if __name__ == "__main__":
    """
     - Save it in a secure location
     - Treat it like a password or a set of keys
     - If security has been compromised, regenerate it
     - DO NOT store it in public places or shared docs
    """

    couch = couchdb.Server('http://admin:admin@172.26.134.187:5984/')
    db = couch['twitter']  # existing

    # https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query
    with open('query.txt', 'r', encoding="utf8") as f:
        query = f.read().rstrip()

    max_results = 10
    limit = 30
    counter = 0
    resp = None

    # https://docs.tweepy.org/en/stable/client.html#search-tweets\
    while resp is None:
        try:
            resp = client.search_recent_tweets(query, max_results=max_results)
        except TooManyRequests:
            # timeout so wait 5 mins
            time.sleep(300)

    if resp.errors:
        raise RuntimeError(resp.errors)
    if resp.data:
        for tweet in resp.data:
            if tweetValidator(tweet):  # Else ignore
                processTweet(tweet, db)

    while "next_token" in resp.meta and counter < limit:
        try:
            resp = client.search_recent_tweets(query, max_results=max_results, next_token=resp.meta["next_token"])
        except TooManyRequests:
            # timeout so wait 5 mins
            time.sleep(300)
            continue
        if resp.errors:
            raise RuntimeError(resp.errors)
        if resp.data:
            for tweet in resp.data:
                if tweetValidator(tweet):  # Else ignore
                    processTweet(tweet, db)

# BEARER TOKEN
# AAAAAAAAAAAAAAAAAAAAAFIObwEAAAAAm%2BkVcGvN3leXCC1B85puJEY6Yhc%3D0s9PQRynu9vaMVsUKpGtaQTpiN0TloMti6e7UhQTBkp2tttrsc
