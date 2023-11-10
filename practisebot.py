import tweepy
from dotenv import load_dotenv
import os
import requests
import logging
import time
load_dotenv()

# Create a logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s]   %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True)

# Config details of twitter API
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
API_KEY = os.getenv("CONSUMER_KEY")
API_KEY_SECRET = os.getenv("CONSUMER_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN_KEY")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")


# Authenticate to Twitter
auth = tweepy.OAuthHandler(API_KEY, API_KEY_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

client = tweepy.Client(bearer_token=BEARER_TOKEN,
                       consumer_key=API_KEY,
                       consumer_secret=API_KEY_SECRET,
                       access_token=ACCESS_TOKEN,
                       access_token_secret=ACCESS_TOKEN_SECRET,
                       return_type=dict,
                       wait_on_rate_limit=True)


def get_tweets_with_hastag():
    # Get tweets with specific hashtag
    logger.info("GETTING TWEETS FROM API CALL")
    try:
        url = "https://twitter154.p.rapidapi.com/hashtag/hashtag"
        headers = {
            'X-RapidAPI-Key': '789a5bf49cmsh785ce4d32f850bep1f2856jsn72b73dd1d0df',
            'X-RapidAPI-Host': 'twitter154.p.rapidapi.com'
        }

        # Set query parameters
        querystring = {"hashtag": "#nvctranslator",
                       "limit": "10", "section": "top"}

        # Make API call with query parameters
        response = requests.request(
            "GET", url, headers=headers, params=querystring)

        # Return JSON response
        return response.json()['results']
    except Exception as e:
        logging.error("Exception occurred in retrieveTweet")
        logging.error(str(e))
        return None


def reply_to_tweet(tweet_id, reply_text):
    # create tweet with reply to specific tweet id
    logger.info('Replying to user')
    status = client.create_tweet(
        text=reply_text, in_reply_to_tweet_id=tweet_id)
    print(status)  # print created tweet


def nvctranslator(tweet_text):
    logger.info('converting tweet into nvc language')
    new_text = tweet_text
    return new_text


if __name__ == "__main__":
    WAIT_TIME = 2  # min
    logger.info('Montioring tweets -Program started')
    already_replied = 0
    while 1:
        logger.info("Listining for tweets")
        time.sleep(WAIT_TIME*10)
        tweets = get_tweets_with_hastag()
        if (tweets):
            logger.info("Found Tweets")
            recent_tweets = tweets[:len(tweets)-already_replied]
            for tweet in recent_tweets:
                already_replied += 1
                try:
                    reply_to_tweet(str(tweet['tweet_id']), str(nvctranslator(f"Hello again {tweet['user']['name']}"
                                                                             )))
                    logger.info("Successfully replied")
                except Exception as e:
                    logger.error(e)
