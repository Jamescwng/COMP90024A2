#pip install transformers[torch] to install PyTorch and Transformers
#pip install emoji

import couchdb
import random
from transformers import pipeline

user = "admin"
password = "admin"
couchserver = couchdb.Server("http://%s:%s@172.26.134.187:5984/" % (user, password))

db = couchserver['twitter']

rows = db.view('_design/CrimeInfo/_view/TweetData')

data = [row['value'] for row in rows]
random.seed(0)
random.shuffle(data)

model1 = "finiteautomata/bertweet-base-sentiment-analysis"
model2 = "cardiffnlp/twitter-roberta-base-sentiment-latest"
model = model2
#sentiment_pipeline = pipeline(model=model)
sentiment_pipeline = pipeline(model=model)
#data = ["I love you", "I hate you"] #example data used for testing
data = data[:50]
sentiment = sentiment_pipeline(data) #returns positive, negative, neutral for each tweet (with probability score)

# tweet classification results
with open("model2-classification-results" + ".txt", 'w') as f:
    for i in range(len(data)):
        f.write(data[i] + "\n")
        f.write(str(sentiment[i]) + "\n")
        f.write("\n")

