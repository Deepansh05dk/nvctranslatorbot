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

client = tweepy.Client(bearer_token=BEARER_TOKEN,
                       consumer_key=API_KEY,
                       consumer_secret=API_KEY_SECRET,
                       access_token=ACCESS_TOKEN,
                       access_token_secret=ACCESS_TOKEN_SECRET,
                       return_type=dict,
                       wait_on_rate_limit=True)


# Authenticate to Twitter
auth = tweepy.OAuthHandler(API_KEY, API_KEY_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)


def nvctranslator(tweet_text):
    new_text = tweet_text
    return new_text

# Define a class inheriting from StreamListener


class MentionListener(tweepy.StreamingClient):
    def on_tweet(self, tweet):
        try:
            # Check if the tweet is a mention
            if "@nvctranslator" in tweet.text.lower():
                username = tweet.author_id
                status_id = tweet.id
                user = api.get_user(user_id=username)
                response = f"@{user.screen_name} Thank you for your mention!"
                api.update_status(
                    status=response, in_reply_to_status_id=status_id)
                logger.info(f"Replied to @{user.screen_name}")
        except Exception as e:
            logger.error("Error on_tweet: %s", str(e))

    def on_error(self, status_code):
        if status_code == 420:
            # Returning False disconnects the stream
            logger.warning("Rate limited. Disconnecting the stream.")
            return False
        else:
            logger.error(f"Error: {status_code}")


def reply_to_tweet(tweet_id, reply_text):
    # create tweet with reply to specific tweet id
    logger.info('Replying to user')
    status = client.create_tweet(
        text=reply_text, in_reply_to_tweet_id=tweet_id)
    print(status)  # print created tweet


if __name__ == "__main__":
    # Create a Stream object with our authentication and listener
    logger.info("Twitterbot started")
    # Create a Stream object with our authentication and listener
    myStreamListener = MentionListener(bearer_token=os.getenv('BEARER_TOKEN'))

    # Start streaming, filter for mentions of the bot
    try:
        myStreamListener.add_rules(tweepy.StreamRule(value="@nvctranslator"))
        myStreamListener.filter()
    except KeyboardInterrupt:
        logger.info("Stream stopped by user.")
    except Exception as e:
        logger.error(f"Error in stream: {str(e)}")
