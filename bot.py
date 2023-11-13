import sqlite3
import tweepy
from dotenv import load_dotenv
import os
import requests
import logging
import time
import urllib.parse
from datetime import datetime, timezone, timedelta


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


def create_connection(db_file):
    """ Create a database connection to the SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        logger.info("Database successfully connected")
    except Exception as e:
        logger.error(e)
    return conn


def get_last_processed_time(conn):
    """ Get the last processed tweet time from the database """

    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS tweets (tweet_time TEXT PRIMARY KEY)")
    cur.execute("SELECT tweet_time FROM tweets ORDER BY tweet_time DESC LIMIT 1")
    last_time_row = cur.fetchone()
    return last_time_row[0] if last_time_row else None


def set_last_processed_time(conn, tweet_time):
    logger.info('Setting the last processed tweet time')
    """ Update the last processed tweet time in the database """
    cur = conn.cursor()
    cur.execute("INSERT INTO tweets (tweet_time) VALUES (?)", (tweet_time,))
    conn.commit()


def nvctranslator(tweet_text):
    """ Convert tweet text to nvc language """
    tweet_text = tweet_text.replace(
        '@nvctranslator', '').replace('\n', '').strip()
    if (len(tweet_text) > 0):
        logger.info('Converting tweet text into nvc language')
        try:
            url = f"https://nvctranslator.com/translate?text={urllib.parse.quote(tweet_text)}"
            response = requests.request(
                "GET", url)
        except Exception as e:
            logging.error("Exception occurred in retrieveTweet")
            logging.error(str(e))
            return None
        if (response.json()[1] == 200):
            logger.info("Text succesfully translated")
            translatedText = response.json()[0]['translation'].split('\n')[
                1].split(': ')[1][1:-1]
            return translatedText.strip()
        else:
            logger.error("unable to complete API get request")
            return None
    else:
        logger.info("No text provided to translate")
        return None


def reply_to_tweet(tweet_id, reply_text, client):
    # create tweet with reply to specific tweet id
    try:
        # Create a tweet in reply to the specified tweet ID
        logger.info('Replying to user')
        status = client.create_tweet(
            text=str(reply_text), in_reply_to_tweet_id=str(tweet_id))
        logger.info(status)
        logger.info("Successfully replied")

    except Exception as e:
        # Handle any exceptions that might occur during the tweet creation
        logger.error(f"Error replying to tweet {tweet_id}: {e}")


def main():
    logger.info("Twitter bot started")
    # Database connection
    db_file = 'tweets.db'
    conn = create_connection(db_file)

    # Load the last processed tweet's time
    if (get_last_processed_time(conn) == None):
        start_time = datetime.utcnow()
        start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        set_last_processed_time(conn, start_time_str)
    logger.info('Getting the last processed tweet time')
    last_processed_time = get_last_processed_time(conn)
    print(last_processed_time)

    # Initialize Tweepy Client
    client = tweepy.Client(bearer_token=BEARER_TOKEN,
                           consumer_key=API_KEY,
                           consumer_secret=API_KEY_SECRET,
                           access_token=ACCESS_TOKEN,
                           access_token_secret=ACCESS_TOKEN_SECRET,
                           return_type=dict,
                           wait_on_rate_limit=True)

    # Fetch mentions since the last processed tweet
    logger.info("Fetching latest mentions tweets")
    mentions = client.get_users_mentions(
        id='1640149719447109633',
        start_time=last_processed_time,
        tweet_fields=["created_at", "text", "author_id"],
        expansions=["author_id"],
        user_fields=["username"]
    )
    newest_time = None

    if 'data' in mentions:
        for tweet in mentions['data']:
            try:
                # Get tweet details
                tweet_id = tweet['id']
                tweet_text = tweet['text']
                tweet_created_at = tweet['created_at']

                # Get user details
                # 'includes' contains additional information like user details
                author_id = tweet['author_id']
                author_details = next(
                    (user for user in mentions['includes']['users'] if user['id'] == author_id), None)
                if author_details:
                    username = author_details['username']
                logger.info(
                    f"Tweet ID: {tweet_id}, Created at: {tweet_created_at}, Username: {username}, Text: {tweet_text}")

                # Your code to reply to the tweet
                translated_text = nvctranslator(tweet_text=tweet_text)
                reply_text = f"Here is @{username}’s message in a form of non-violent communication: {translated_text}"
                reply_to_tweet(tweet_id=tweet_id, reply_text=str(
                    reply_text.strip()), client=client)

                # Update the newest tweet time
                newest_time = (datetime.strptime(
                    tweet_created_at, '%Y-%m-%dT%H:%M:%S.%fZ')+timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

                if (datetime.strptime(newest_time, '%Y-%m-%dT%H:%M:%SZ') < datetime.strptime(last_processed_time, '%Y-%m-%dT%H:%M:%SZ')):
                    newest_time = last_processed_time

            except Exception as e:
                logger.error(e)

        # Save the time of the most recent tweet processed
        if newest_time is not None and newest_time != last_processed_time:
            set_last_processed_time(conn, newest_time)
    else:
        logger.warning('No mentions found')
    conn.close()


if __name__ == "__main__":
    WAIT_TIME = 2  # min
    while 1:
        main()
        time.sleep(WAIT_TIME*10)
