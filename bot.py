import re
import tweepy
from dotenv import load_dotenv
import os
import requests
import logging
import time
from datetime import datetime, timedelta
import json


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

last_processed_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def get_last_processed_time():
    global last_processed_time
    return last_processed_time


def set_last_processed_time(tweet_time):
    global last_processed_time
    last_processed_time = tweet_time


def nvctranslator(tweet_text):
    """ Convert tweet text to nvc language """

    if (len(tweet_text) > 0):
        logger.info('Converting tweet text into nvc language')
        try:
            url = "https://nvctranslator.com/post"
            # data to be sent in the POST request
            payload = {"text": tweet_text}
            headers = {"Content-Type": "application/json"}
            response = requests.request(
                "POST", url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Error occurred in nvctranslator: {e}")
            return None

        if (response.json()[1] == 201):
            logger.info("Text succesfully translated")
            translatedText = response.json()[0]['translation']

            matches = re.findall(r'rephrased_txt: "(.*?)"', translatedText)
            translatedText = ' '.join(matches)
            return translatedText.strip()
        else:
            logger.error("unable to complete API Post request")
            return None
    else:
        logger.warning("No text provided to translate")
        return None


def reply_to_tweet(tweet_id, reply_text):
    # create tweet with reply to specific tweet id
    try:
        # Create a tweet in reply to the specified tweet ID
        logger.info('Replying to user')
        client = tweepy.Client(bearer_token=BEARER_TOKEN,
                               consumer_key=API_KEY, consumer_secret=API_KEY_SECRET, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)
        status = client.create_tweet(text=str(
            reply_text), in_reply_to_tweet_id=tweet_id)
        logger.info(status)
        logger.info("Successfully replied")

    except Exception as e:
        # Handle any exceptions that might occur during the tweet creation
        logger.error(f"Error replying to tweet {tweet_id}: {e}")


def main():

    try:
        logger.info("Twitter bot started")

        # Initialize Tweepy Client
        client = tweepy.Client(bearer_token=BEARER_TOKEN, return_type=dict,
                               wait_on_rate_limit=True)

        # Fetch mentions since the last processed tweet
        logger.info("Fetching latest mentions tweets")

        mentions = client.get_users_mentions(
            id='1640149719447109633',
            start_time=last_processed_time,
            tweet_fields=["created_at", "author_id", "conversation_id"],
            expansions=["in_reply_to_user_id", "referenced_tweets.id",
                        'author_id', 'edit_history_tweet_ids'],
            user_fields=["username"]
        )

        newest_time = get_last_processed_time()

        if 'data' in mentions:
            for tweet in mentions['data']:
                try:
                    # Get tweet details
                    tweet_id = tweet['id']
                    tweet_created_at = tweet['created_at']

                    # Update the newest tweet time
                    created_time = (datetime.strptime(
                        tweet_created_at, '%Y-%m-%dT%H:%M:%S.%fZ')+timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

                    if (datetime.strptime(newest_time, '%Y-%m-%dT%H:%M:%SZ') < datetime.strptime(created_time, '%Y-%m-%dT%H:%M:%SZ')):
                        newest_time = created_time

                    tweet_author_id = tweet['author_id']
                    in_reply_to_tweet_id = None
                    if ('referenced_tweets' in tweet):
                        in_reply_to_tweet_id = next(
                            (ref_tweet['id'] for ref_tweet in tweet['referenced_tweets'] if ref_tweet['type'] == 'replied_to'), None)
                    if (in_reply_to_tweet_id):
                        # Get user details
                        in_reply_to_user_id = tweet['in_reply_to_user_id']
                        in_reply_to_user_tweet_details = next(
                            (one_tweet for one_tweet in mentions['includes']['tweets'] if one_tweet['id'] == in_reply_to_tweet_id), None)
                        if (in_reply_to_user_tweet_details):
                            in_reply_to_user_text = in_reply_to_user_tweet_details['text']
                        userdetails_to_reply = next(
                            (user for user in mentions['includes']['users'] if user['id'] == in_reply_to_user_id), None)
                        username_to_reply = None
                        if (userdetails_to_reply):
                            username_to_reply = userdetails_to_reply['username']
                        userdetails_who_posted = next(
                            (user for user in mentions['includes']['users'] if user['id'] == tweet_author_id), None)
                        username_who_posted = None
                        if (userdetails_who_posted):
                            username_who_posted = userdetails_who_posted['username']

                        # Your code to reply to the tweet
                        translated_text = nvctranslator(
                            tweet_text=str(in_reply_to_user_text.replace('\n\n', ' ')))

                        if (username_who_posted != username_to_reply):
                            reply_text = f"Here is @{username_to_reply}’s message in a form of non-violent communication: {translated_text}"
                            reply_to_tweet(tweet_id=tweet_id,
                                           reply_text=str(reply_text.strip()))
                    else:
                        logger.warning('This tweet is not a reply')

                except Exception as e:
                    logger.error(e)
        # set the last processed time to latest processed tweet time
            if newest_time is not None and newest_time != last_processed_time:
                set_last_processed_time(newest_time)
        else:
            logger.warning('No mentions found')
    except Exception as e:
        logger.error(f"error in main function :-{e}")
        # Save the time of the most recent tweet processed


if __name__ == "__main__":
    WAIT_TIME = 1.01  # min
    while 1:
        main()
        time.sleep(WAIT_TIME*60)
