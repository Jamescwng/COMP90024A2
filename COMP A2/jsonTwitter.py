import ijson
import json
import multiprocessing
import sys
import couchdb
# Simple multithreading https://stackoverflow.com/questions/2846653/how-can-i-use-threading-in-python
from multiprocessing.pool import ThreadPool
from geopy.geocoders import Nominatim
import datetime as dt
import numpy as np

from scipy.special import softmax
from emot.emo_unicode import UNICODE_EMOJI
import re
import nltk

nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from transformers import AutoModelForSequenceClassification
from transformers import AutoTokenizer, AutoConfig

# Loading
tweet_json_file = open(sys.argv[1], 'r', encoding="utf8")

# Database
couch = couchdb.Server('http://admin:admin@172.26.134.187:5984/')
db = couch['twitter']

# Model
MODEL = f"cardiffnlp/twitter-roberta-base-sentiment-latest"
tokenizer = AutoTokenizer.from_pretrained(MODEL)
config = AutoConfig.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(MODEL)


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
    unParsedSent = generateSentiment(tweet["text"])
    sentiment = [str(unParsedSent[0]), str(unParsedSent[1])]

    sqlInsert = {
        "_id": tweet["_id"] or tweet["id"],
        "tweet": tweet["text"],
        "created_at": tweet["created_at"] if "created_at" in tweet else -1,
        "hourOfDay": hourOfDay,
        "dayOfWeek": dayOfWeek,
        "council": council,
        "postcode": postcode,
        "suburb": suburb,
        "geo": coordinates,
        "sentiment": sentiment
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
                    if not "sentiment" in doc:
                        unParsedSent = generateSentiment(doc["tweet"])
                        sentiment = [str(unParsedSent[0]), str(unParsedSent[1])]
                        doc["sentiment"] = sentiment
                    db.save(doc)
                else:
                    dbInsert = tweetFormatter(row)
                    db.save(dbInsert)
            except NameError:
                print("Matching id found")
                continue


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


# dfSentiment['sentiment'] = dfSentiment['new_tweet'].apply(lambda x: sentiment_score(x[:512]))


def main():
    # Supply twitter json as arg 1
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
