import requests
import uuid
import logging
import json
import sys
from telegram.ext import Updater, CommandHandler, InlineQueryHandler
from telegram import InlineQueryResultMpeg4Gif, InlineQueryResultPhoto

QUERY_URL = "https://9gag.com/v1/search-posts?"
LOG_FILE = '/var/log/9gag_bot.log'


# Callback function for when a user sends the message '/start'
def start_callback(bot, update):
    test = 0
    pass


# Callback function for when a Telegram bot exception occurs
def error_callback(bot, update, error):
    logging.error(error)


# Callback function for when an inline query occurs
def inline_posts_callback(bot, update):
    logging.info("Starting query.")

    logging.debug("Effective user ID: {}".format(update.effective_user.id))
    logging.debug("Query ID: {}".format(update.inline_query.id))
    logging.debug("Update ID: {}".format(update.update_id))
    logging.debug("Bot ID: {}".format(update.inline_query.bot.id))
    logging.debug("Effective user ID: {}".format(update.effective_user.id))

    # Retrieve GIFs on the basis of given keywords
    keywords = update.inline_query.query
    posts, next_cursor = get_posts(keywords, update.inline_query.offset)

    # Convert the results to the appropriate InlineQueryResult object
    results = []
    for post in posts:
        if post['type'] == 'video':
            result = InlineQueryResultMpeg4Gif(id=uuid.uuid4(), type='mpeg4_gif', mpeg4_url=post['url'],
                                               title=post['title'], thumb_url=post['thumbnail_url'])
        elif post['type'] == 'image':
            result = InlineQueryResultPhoto(id=uuid.uuid4(), type='photo', photo_url=post['url'],
                                            title=post['title'], thumb_url=post['thumbnail_url'])

        results.append(result)

    # Let the bot answer with the results
    query_id = update.inline_query.id
    bot.answer_inline_query(query_id, results=results, is_personal=True, next_offset=next_cursor)


def get_posts(keywords, cursor):
    # If the cursor is empty, it's the first page.
    if cursor == '':
        url_suffix = u'query={}&c={}'.format('%20'.join(keywords.split(' ')), 0)
    else:
        url_suffix = cursor.replace('amp;', '')

    # Get page in JSON format
    url = QUERY_URL + url_suffix
    page_source = get_page(url)
    page_dict = json.loads(page_source)

    try:
        # This may fail if the query is empty (no keywords).
        next_cursor = page_dict[u'data'][u'nextCursor']
    except Exception as e:
        return [], ''

    # For all the posts retrieved, get the media data
    media_urls = []
    for post in page_dict[u'data'][u'posts']:
        try:
            url = post[u'images'][u'image460sv'][u'url']
            media_type = u'video'
        except KeyError:
            # Entry does not exist. Probably not a video. Probably an image.
            url = post[u'images'][u'image460'][u'url']
            media_type = u'image'
        finally:
            title = post[u'title']
            thumbnail_url = post[u'images'][u'image460'][u'url']

            media_urls.append({
                'title': title,
                'type': media_type,
                'url': url,
                'thumbnail_url': thumbnail_url
            })

    return media_urls, next_cursor


def get_page(url):
    response = requests.get(url)
    content = response.content

    return content


def main_loop(token):
    updater = Updater(token=token)
    dispatcher = updater.dispatcher

    logging.basicConfig(filename=LOG_FILE,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

    # Plug in the function that gets called when the user enters /start
    start_handler = CommandHandler('start', start_callback)
    dispatcher.add_handler(start_handler)

    # Plug in the function that gets called when an error occurs
    dispatcher.add_error_handler(error_callback)

    # Plug in the function that gets called when the user does an inline query
    inline_query_handler = InlineQueryHandler(inline_posts_callback)
    dispatcher.add_handler(inline_query_handler)

    # Start polling for queries
    updater.start_polling()


if __name__ == '__main__':
    main_loop(sys.argv[1])
