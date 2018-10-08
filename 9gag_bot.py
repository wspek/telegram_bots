import requests
import uuid
import logging
import ujson
import sys
from telegram import InlineQueryResultMpeg4Gif, InlineQueryResultPhoto
from telegram.ext import Updater, CommandHandler, InlineQueryHandler
from telegram.ext.dispatcher import run_async
import messages

QUERY_URL = u"https://9gag.com/v1/search-posts?"
LOG_FILE = u'/var/log/9gag_bot.log'


# Callback function for when a user sends the message '/start'
@run_async
def start_callback(bot, update):
    update.message.reply_text(messages.start_message)


# Callback function for when a Telegram bot exception occurs
@run_async
def error_callback(bot, update, error):
    logging.error(error)


# Callback function for when an inline query occurs
@run_async
def inline_posts_callback(bot, update):
    logging.info(u"Starting query.")
    logging.debug(u"Effective user ID: {}".format(update.effective_user.id))
    logging.debug(u"Query ID: {}".format(update.inline_query.id))
    logging.debug(u"Update ID: {}".format(update.update_id))
    logging.debug(u"Bot ID: {}".format(update.inline_query.bot.id))
    logging.debug(u"Effective user ID: {}".format(update.effective_user.id))

    # Retrieve GIFs on the basis of given keywords
    keywords = update.inline_query.query
    posts, next_cursor = get_posts(keywords, update.inline_query.offset)

    # Convert the results to the appropriate InlineQueryResult object
    results = []
    for post in posts:
        if post[u'type'] == u'video':
            result = InlineQueryResultMpeg4Gif(id=uuid.uuid4(), type=u'mpeg4_gif', mpeg4_url=post[u'url'],
                                               mpeg4_width=post[u'width'], mpeg4_height=post[u'height'],
                                               title=post[u'title'], thumb_url=post[u'thumbnail_url'])
        elif post[u'type'] == u'image':
            result = InlineQueryResultPhoto(id=uuid.uuid4(), type=u'photo', photo_url=post[u'url'],
                                            photo_width=post[u'width'], photo_height=post[u'height'],
                                            title=post[u'title'], thumb_url=post[u'thumbnail_url'])

        results.append(result)

    # Let the bot answer with the results
    query_id = update.inline_query.id
    bot.answer_inline_query(query_id, results=results, is_personal=True, next_offset=next_cursor)


def get_posts(keywords, cursor):
    # If the cursor is empty, it's the first page.
    if cursor == '':
        url_suffix = u'query={}&c={}'.format(u'%20'.join(keywords.split(' ')), 0)
    else:
        url_suffix = cursor.replace(u'amp;', u'')

    # Get page in JSON format
    url = QUERY_URL + url_suffix
    page_source = get_page(url)
    page_dict = ujson.loads(page_source)

    try:
        # This may fail if the query is empty (no keywords).
        next_cursor = page_dict[u'data'][u'nextCursor']
    except KeyError:
        return [], ''

    # For all the posts retrieved, get the media data
    media_urls = []
    for post in page_dict[u'data'][u'posts']:
        try:
            media = post[u'images'][u'image460sv']
            url = media[u'url']
            media_type = u'video'
        except KeyError:
            # Entry does not exist. Probably not a video. Probably an image.
            media = post[u'images'][u'image460']
            url = media[u'url']
            media_type = u'image'
        finally:
            title = post[u'title']
            width = media[u'width']
            height = media[u'height']
            thumbnail_url = post[u'images'][u'image460'][u'url']

            media_urls.append({
                u'title': title,
                u'type': media_type,
                u'width': width,
                u'height': height,
                u'url': url,
                u'thumbnail_url': thumbnail_url
            })

    return media_urls, next_cursor


def get_page(url):
    response = requests.get(url)
    content = response.content

    return content


def main_loop(token):
    updater = Updater(token=token, workers=4)
    dispatcher = updater.dispatcher

    logging.basicConfig(filename=LOG_FILE,
                        format=u'%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

    # Plug in the function that gets called when the user enters /start
    start_handler = CommandHandler(u'start', start_callback)
    dispatcher.add_handler(start_handler)

    # Plug in the function that gets called when an error occurs
    dispatcher.add_error_handler(error_callback)

    # Plug in the function that gets called when the user does an inline query
    inline_query_handler = InlineQueryHandler(inline_posts_callback)
    dispatcher.add_handler(inline_query_handler)

    # Start polling for queries
    updater.start_polling()


if __name__ == u'__main__':
    main_loop(sys.argv[1])
