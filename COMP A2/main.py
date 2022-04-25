import json
import os

from tweepy import Client
from geopy.geocoders import Nominatim

twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

if not twitter_bearer_token:
    raise RuntimeError("Not found bearer token")

client = Client(twitter_bearer_token)


def surburbGetter(tweet: json) -> str:
    suburb = None
    # Get suburb by geographical location
    # Extract geocode
    if tweet["geo"]:
        locator = Nominatim(user_agent="cloud project")
        geo = tweet["geo"]["coordinates"]["coordinates"]
        # Twitter is long/lat, nominatim is lat/long
        coordinates = (geo[0], geo[1])
        location = locator.reverse(coordinates)

        suburb = location.raw["address"]["suburb"]

    return suburb


def typeCrime(text: str):
    ## Derived from
    # https://www.crimestatistics.vic.gov.au/about-the-data/classifications-and-victorian-map-boundaries/offence-classification

    crimeList = [
        "arson", "hoon", "drug", "assault", "scam", "theft", "steal", "murder", "homicide", "sexual offense", "stalk",
        "harass", "abduct", "robbery", "blackmail", "burgl", "disorderly",
    ]
    crimeMention = ""
    text = text.lower()
    for crime in crimeList:
        if crime in text:
            crimeMention += (crime + " ")

    if crimeMention == "":
        return None
    return crimeMention


def tweetValidator(tweet: json) -> bool:
    text = tweet["text"]
    if text is None:
        return False

    return True


def tweetFormatter(tweet: json) -> json:
    suburb = surburbGetter(tweet)
    crime = typeCrime(tweet["text"])

    sqlInsert = {
        "id": tweet["id"],
        "tweet": tweet["text"],
        "crimeType": crime,
        "suburb": suburb,
    }
    return sqlInsert


if __name__ == "__main__":
    """
     - Save it in a secure location
     - Treat it like a password or a set of keys
     - If security has been compromised, regenerate it
     - DO NOT store it in public places or shared docs
    """

    # https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query
    query = 'from:VictoriaPolice -is:retweet'

    max_results = 10
    limit = 30
    counter = 0

    # https://docs.tweepy.org/en/stable/client.html#search-tweets
    # TODO SOME STUFF TO DETERMINE HOW TO NOT PULL THE SAME TWEET
    resp = client.search_recent_tweets(query, max_results=max_results)
    if resp.errors:
        raise RuntimeError(resp.errors)
    if resp.data:
        for tweet in resp.data:
            if tweetValidator(tweet):  # Else ignore
                dbInsert = tweetFormatter(tweet)

                # Write this to couchDB
                sqlInsert = {
                    "id": tweet["id"],
                    "tweet": tweet["text"]
                }

    while resp.meta["next_token"] and counter < limit:
        resp = client.search_recent_tweets(query, max_results=max_results, next_token=resp.meta["next_token"])
        if resp.errors:
            raise RuntimeError(resp.errors)
        if resp.data:
            for tweet in resp.data:
                dbInsert = tweetFormatter(tweet)

                # Write this to couchDB
                sqlInsert = {
                    "id": tweet["id"],
                    "tweet": tweet["text"]
                }

# API KEY yHuHB7gB4J4npxCRM8PHLJEmL
# API SECRET PPc15NKLjPKlUV2SHJzKxJUEbpgHEKyPRggyRoaHfIgAvCeQSJ DONT CHECK IN
# BEARER TOKEN
# AAAAAAAAAAAAAAAAAAAAAFIObwEAAAAAm%2BkVcGvN3leXCC1B85puJEY6Yhc%3D0s9PQRynu9vaMVsUKpGtaQTpiN0TloMti6e7UhQTBkp2tttrsc
