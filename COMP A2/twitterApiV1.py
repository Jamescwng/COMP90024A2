import json
import os
import sys

import couchdb
from tweepy import API, HTTPException, TooManyRequests, OAuthHandler
from geopy.geocoders import Nominatim
import time

twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

if not twitter_bearer_token:
    raise RuntimeError("Not found bearer token")


def surburbGetter(tweet: json) -> str:
    area = ""
    # Get suburb by geographical location
    # Extract geocode
    if tweet.geo:
        locator = Nominatim(user_agent="cloud project")
        geo = tweet.geo["coordinates"]
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
    text = tweet.text
    if text is None:
        return False
    if text.startswith("RT"):
        return False
    return True


def tweetFormatter(tweet: json) -> json:
    location = surburbGetter(tweet)
    crime = typeCrime(tweet.text)
    council = location["municipality"] if "municipality" in location else ""
    postcode = location["postcode"] if "postcode" in location else ""
    suburb = location["suburb"] if "suburb" in location else ""
    coordinates = tweet.geo["coordinates"]
    coordinates[0] = str(coordinates[0])
    coordinates[1] = str(coordinates[1])

    sqlInsert = {
        "_id": tweet.id_str,
        "tweet": tweet.text,
        "created_at": tweet.created_at.strftime("%a %b %d %X +0000 %Y"),
        "mentionCrime": crime,
        "council": council,
        "postcode": postcode,
        "suburb": suburb,
        "geo": coordinates
    }
    return sqlInsert


def processTweet(tweet, db):
    if tweet.geo and tweetValidator(tweet):  # Else ignore
        dbInsert = tweetFormatter(tweet)
        try:
            if tweet.id_str in db:
                doc = db.get(tweet.id)
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
    with open(sys.argv[1], 'r', encoding="utf8") as f:
        query = f.read().rstrip()

    auth = OAuthHandler("ZHhedTWScKB6LwbEi5sNiV3YA", "d6hoBcuWKe4lriLTa53aCWeDmDLDpQlHAZop0SCtgQydN9H6Rn")

    auth.set_access_token("1480793806551191554-TJw4qDyY4VkEEq5sHD7IEIIXHHzlZS",
                          "q7r3iKRxiKmSIPqTzJTQnYQ8gSE9vyF8Z1SrMFwhcWKWJ")

    api = API(auth, wait_on_rate_limit=True)

    max_results = 10
    limit = 30
    counter = 0
    resp = None
    search_words = query
    date_since = "202001011200"

    # https://docs.tweepy.org/en/stable/client.html#search-tweets\
    while resp is None:
        try:

            resp = api.search_full_archive(label="dev", query=query, maxResults=max_results)
        except TooManyRequests:
            # timeout so wait 5 mins
            time.sleep(300)

    if "errors" in resp:
        raise RuntimeError(resp.errors)
    if resp:
        for tweet in resp:
            if tweetValidator(tweet):  # Else ignore
                processTweet(tweet, db)

    while "next_token" in resp.meta and counter < limit:
        try:
            resp = api.search_full_archive(label="dev", query=query, maxResults=max_results, next_token=resp.meta["next_token"])
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
