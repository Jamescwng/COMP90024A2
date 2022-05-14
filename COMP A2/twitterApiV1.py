import datetime as dt
import json
import os
import re
import sys
import time
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
import couchdb
import nltk
# Simple multithreading https://stackoverflow.com/questions/2846653/how-can-i-use-threading-in-python
from emot import UNICODE_EMOJI
from geopy.geocoders import Nominatim
from nltk import RegexpTokenizer
from nltk.corpus import stopwords
from tweepy import API, TooManyRequests, OAuthHandler
from scipy.special import softmax
import numpy as np

nltk.download('stopwords')
from transformers import AutoModelForSequenceClassification
from transformers import AutoTokenizer, AutoConfig


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


def tweetValidator(tweet: json) -> bool:
    text = tweet.text
    if text is None:
        return False
    if text.startswith("RT"):
        return False
    return True


def tweetFormatter(tweet: json) -> json:
    location = surburbGetter(tweet)
    council = location["municipality"] if "municipality" in location else ""
    postcode = location["postcode"] if "postcode" in location else ""
    suburb = location["suburb"] if "suburb" in location else ""
    coordinates = tweet.geo["coordinates"]
    coordinates[0] = str(coordinates[0])
    coordinates[1] = str(coordinates[1])

    #  day-of-week as an integer from 0 to 6 representing Monday to Sunday
    unParsedSent = generateSentiment(tweet.text)
    sentiment = [str(unParsedSent[0]), str(unParsedSent[1])]

    sqlInsert = {
        "_id": tweet.id_str,
        "tweet": tweet.text,
        "created_at": tweet.created_at.strftime("%a %b %d %X +0000 %Y"),
        "hourOfDay": tweet.created_at.hour,
        "dayOfWeek": tweet.created_at.weekday(),
        "council": council,
        "postcode": postcode,
        "suburb": suburb,
        "geo": coordinates,
        "sentiment": sentiment
    }
    return sqlInsert


def processTweet(tweet, db):
    if tweet.geo and tweetValidator(tweet):  # Else ignore
        try:
            if tweet.id_str not in db:
                dbInsert = tweetFormatter(tweet)
                db.save(dbInsert)
        except NameError:
            print("Matching id found")


def generateSentiment(tweet):
    # translate emoji
    def emoji(text):
        for emot in UNICODE_EMOJI:
            if text == None:
                text = text
            else:
                text = text.replace(emot, "_".join(UNICODE_EMOJI[emot].replace(",", "").replace(":", "").split()))
            return text

    # remove links
    def remove_links(text):
        '''Takes a string and removes web links from it'''
        text = re.sub(r'http\S+', '', text)  # remove http links
        text = re.sub(r'bit.ly/\S+', '', text)  # remove bitly links
        text = text.strip('[link]')  # remove [links]
        return text

    def clean_html(text):
        html = re.compile('<.*?>')  # regex
        return html.sub(r'', text)

    # remove non ascii character
    def non_ascii(s):
        return "".join(i for i in s if ord(i) < 128)

    def punct(text):
        token = RegexpTokenizer(r'\w+')  # regex
        text = token.tokenize(text)
        text = " ".join(text)
        return text

    # remove stopwords
    def removeStopWords(text):
        # select english stopwords
        cachedStopWords = set(stopwords.words("english"))
        # add custom words
        cachedStopWords.update(
            ('and', 'I', 'A', 'http', 'And', 'So', 'arnt', 'This', 'When', 'It', 'many', 'Many', 'so',
             'cant', 'Yes', 'yes', 'No', 'no', 'These', 'these', 'mailto', 'regards', 'ayanna', 'like',
             'email'))
        # remove stop words
        new_text = ' '.join([word for word in text.split() if word not in cachedStopWords])
        return new_text

    # special characters removal
    def remove_(text):
        text = re.sub('([_]+)', "", text)
        return text

    def sentiment_score(review):
        tokens = tokenizer.encode(review, return_tensors='pt')
        result = model(tokens)
        scores = result[0][0].detach().numpy()
        scores = softmax(scores)
        ranking = np.argsort(scores)
        ranking = ranking[::-1]

        return config.id2label[ranking[0]], scores[ranking[0]]

    cleanTweet = tweet
    cleanTweet = emoji(cleanTweet)
    cleanTweet = clean_html(cleanTweet)
    cleanTweet = remove_links(cleanTweet)
    cleanTweet = non_ascii(cleanTweet)
    cleanTweet = cleanTweet.lower()
    cleanTweet = removeStopWords(cleanTweet)
    cleanTweet = clean_html(cleanTweet)
    cleanTweet = punct(cleanTweet)
    cleanTweet = remove_(cleanTweet)
    try:
        return sentiment_score(cleanTweet)
    except:
        return ['Neutral', '0']


if __name__ == "__main__":
    """
     - Save it in a secure location
     - Treat it like a password or a set of keys
     - If security has been compromised, regenerate it
     - DO NOT store it in public places or shared docs
    """

    # Database
    couch = couchdb.Server('http://admin:admin@172.26.134.187:5984/')
    db = couch['twitter']

    # # Model
    MODEL = f"cardiffnlp/twitter-roberta-base-sentiment-latest"
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    config = AutoConfig.from_pretrained(MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL)

    # https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query
    with open(sys.argv[1], 'r', encoding="utf8") as f:
        query = f.read().rstrip()

    auth = OAuthHandler("ZHhedTWScKB6LwbEi5sNiV3YA", "d6hoBcuWKe4lriLTa53aCWeDmDLDpQlHAZop0SCtgQydN9H6Rn")

    auth.set_access_token("1480793806551191554-TJw4qDyY4VkEEq5sHD7IEIIXHHzlZS",
                          "q7r3iKRxiKmSIPqTzJTQnYQ8gSE9vyF8Z1SrMFwhcWKWJ")

    api = API(auth, wait_on_rate_limit=True)

    max_results = 100
    resp = None
    oldTimeDate = dt.now() - relativedelta(days=30)
    date_since = oldTimeDate.strftime('%Y%m%d%H%M')

    search_words = query

    # https://docs.tweepy.org/en/stable/client.html#search-tweets\
    while resp is None:
        try:

            resp = api.search_30_day(label="dev", query=search_words, maxResults=max_results, fromDate=date_since)
        except TooManyRequests:
            # timeout so wait 5 mins
            time.sleep(300)

    if "errors" in resp:
        raise RuntimeError(resp.errors)
    if resp:
        for tweet in resp:
            if tweetValidator(tweet):  # Else ignore
                processTweet(tweet, db)

    while resp:
        try:
            oldTimeDate = resp[-1].created_at + relativedelta(minute=1)
            date_since = oldTimeDate.strftime('%Y%m%d%H%M')
            resp = api.search_30_day(label="dev", query=query, maxResults=max_results, fromDate=date_since)
        except TooManyRequests:
            # timeout so wait 5 mins
            time.sleep(300)
            continue
        if "errors" in resp:
            raise RuntimeError(resp.errors)
        if resp:
            for tweet in resp:
                if tweetValidator(tweet):  # Else ignore
                    processTweet(tweet, db)

# BEARER TOKEN
# AAAAAAAAAAAAAAAAAAAAAFIObwEAAAAAm%2BkVcGvN3leXCC1B85puJEY6Yhc%3D0s9PQRynu9vaMVsUKpGtaQTpiN0TloMti6e7UhQTBkp2tttrsc
