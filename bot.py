import re
import tweepy
from dotenv import load_dotenv
import os
import logging
import time
from datetime import datetime, timedelta
import asyncio
import aiohttp


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


def show_time(text):
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)
    print(text, current_time)


def chunks(lst, chunk_size):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


async def nvctranslator(tweet_text):
    """ Convert tweet text to nvc language """
    if len(tweet_text) > 0:
        try:
            url = "https://nvctranslator.com/post"
            payload = {"text": tweet_text}
            headers = {"Content-Type": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()  # Assuming the response is in JSON format
                        translatedText = data[0].get('translation', '')
                        matches = re.findall(
                            r'rephrased_txt: "(.*?)"', translatedText)
                        return ' '.join(matches).strip()
                    else:
                        logger.error(
                            f"Error with status code: {response.status}")
                        return None
        except Exception as e:  # Catching a more general exception
            logger.error(f"Error occurred in nvctranslator: {e}")
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


async def handle_each_tweet(param, index):
    try:
        show_time(f"start tweet {index}")
        # Get tweet details
        tweet_id = param['tweet']['id']
        tweet_created_at = param['tweet']['created_at']

        # Update the newest tweet time
        created_time = (datetime.strptime(
            tweet_created_at, '%Y-%m-%dT%H:%M:%S.%fZ')+timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Save the time of the most recent tweet processed
        if (index == 0):
            set_last_processed_time(created_time)

        tweet_author_id = param['tweet']['author_id']
        in_reply_to_tweet_id = None
        if ('referenced_tweets' in param['tweet']):
            in_reply_to_tweet_id = next(
                (ref_tweet['id'] for ref_tweet in param['tweet']['referenced_tweets'] if ref_tweet['type'] == 'replied_to'), None)
        if (in_reply_to_tweet_id):
            # Get user details
            in_reply_to_user_id = param['tweet']['in_reply_to_user_id']
            in_reply_to_user_tweet_details = next(
                (one_tweet for one_tweet in param['mentions']['includes']['tweets'] if one_tweet['id'] == in_reply_to_tweet_id), None)
            if (in_reply_to_user_tweet_details):
                in_reply_to_user_text = in_reply_to_user_tweet_details['text']
            userdetails_to_reply = next(
                (user for user in param['mentions']['includes']['users'] if user['id'] == in_reply_to_user_id), None)
            username_to_reply = None
            if (userdetails_to_reply):
                username_to_reply = userdetails_to_reply['username']
            userdetails_who_posted = next(
                (user for user in param['mentions']['includes']['users'] if user['id'] == tweet_author_id), None)
            username_who_posted = None
            if (userdetails_who_posted):
                username_who_posted = userdetails_who_posted['username']

            # Your code to reply to the tweet
            translated_text = await nvctranslator(
                tweet_text=str(in_reply_to_user_text.replace('\n\n', ' ')))

            if (username_who_posted == username_to_reply and translated_text == None and len(translated_text) == 0):
                return
            reply_text = f"Here is @{username_to_reply}’s message in a form of non-violent communication: {translated_text}"
            await asyncio.to_thread(reply_to_tweet(tweet_id=tweet_id,
                                                   reply_text=str(reply_text.strip())))
        else:
            logger.warning('This tweet is not a reply')

        show_time(f"end tweet {index}")

    except Exception as e:
        logger.error(e)


async def twitter_bot():
    global last_processed_time
    try:
        logger.info("Twitter bot started")

        # Initialize Tweepy Client
        client = tweepy.Client(bearer_token=BEARER_TOKEN, return_type=dict,
                               wait_on_rate_limit=True)

        # Fetch mentions since the last processed tweet
        logger.info("Fetching latest mentions tweets")
        show_time("api start")
        mentions = client.get_users_mentions(
            id='1640149719447109633',
            start_time=last_processed_time,
            tweet_fields=["created_at", "author_id", "conversation_id"],
            expansions=["in_reply_to_user_id", "referenced_tweets.id",
                        'author_id', 'edit_history_tweet_ids'],
            user_fields=["username"]
        )
        show_time("api end")
        if 'data' in mentions:
            for batch in chunks(mentions['data'], 30):
                show_time("api end")
                show_time(f"start tweets")
                handle_tweets = [handle_each_tweet(
                    param={'tweet': tweet, 'mentions': mentions}, index=index) for index, tweet in enumerate(batch)]
                await asyncio.gather(*handle_tweets)
                print("new time -", str(last_processed_time))
                show_time(f"end tweets ")
        else:
            logger.warning('No mentions found')

    except Exception as e:
        logger.error(f"error in twitter bot function :-{e}")


async def main():
    WAIT_TIME = 1.01  # min
    show_time('main start')
    await asyncio.gather(twitter_bot(), asyncio.sleep(WAIT_TIME*60))
    show_time('main end')


if __name__ == "__main__":
    while 1:
        asyncio.run(main())
