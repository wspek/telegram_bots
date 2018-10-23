"""9GAG Media Telegram Bot

This Telegram bot can be used to query the 9GAG website for media, such as JPEGs, GIFs and MP4 videos.

The bot can be added to Telegram by using the username '@gagmedia_bot'.
"""

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


@run_async
def start_callback(bot, update):
    """Gets called automatically when a user sends the command '/start', after which the bot replies with a message.

    Args:
        bot: The bot that received the command.
        update: The specific type of update that should be processed, which is a (start) command in this case.
    """

    update.message.reply_text(messages.start_message)


@run_async
def error_callback(bot, update, error):
    """Gets called automatically when a Telegram bot error occurs, after which the error is logged.

    Args:
        bot: The bot that received the command.
        update: The specific type of update that should be processed, which is an error in this case.
        error: The error message describing the error which occurred.
    """

    logging.error(error)


@run_async
def inline_posts_callback(bot, update):
    """Gets called automatically when an inline query is performed.

    Args:
        bot: The bot that received the command.
        update: The specific type of update that should be processed, which is a keyword query in this case.
    """

    # Retrieve GIFs on the basis of given keywords
    keywords = update.inline_query.query
    posts, next_cursor = get_posts(keywords, update.inline_query.offset)

    message = u"Starting query | USER: {} | QRYID: {} | UPDID: {} | BOTID: {} | KEYWORDS: {} | NXTCSR: {}".format(
        update.effective_user.id,
        update.inline_query.id,
        update.update_id,
        update.inline_query.bot.id,
        keywords,
        next_cursor)
    logging.info(message)

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
        else:
            result = None
            logging.error(u"Encountered a post type of neither video or image ({})".format(post[u'type']))

        results.append(result)

    # Let the bot answer with the results
    query_id = update.inline_query.id
    bot.answer_inline_query(query_id, results=results, is_personal=True, next_offset=next_cursor)


def get_posts(keywords, cursor):
    """Searches 9GAG for all media on the basis of the given keywords.

    Args:
        keywords (str): A string of keywords separated by spaces.
        cursor (str): The cursor, which is essentially a string combining the keywords with a results page number in the
            format 'query={keywords}&c={page_nr}'. The first time the function is called (page 0) the cursor will be the
            empty string.

    Returns:
        A tuple containing two elements: a list of dictionaries representing the media and a string representing the
        cursor necessary to retrieve the second page.
    """

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
    """Retrieves a web page.

    Args:
        url (str): The web page URL.

    Returns:
        A string containing the web page content.

    """

    response = requests.get(url)
    content = response.content

    return content


def main_loop(token):
    """Sets up the bot and starts the polling loop.

    Args:
        token: The bot's token given by the @BotFather.
    """

    # This class, which employs the telegram.ext.Dispatcher, provides a frontend to telegram.Bot to the programmer,
    # so they can focus on coding the bot. Its purpose is to receive the updates from Telegram and to deliver them to
    #  said dispatcher.
    updater = Updater(token=token, workers=4)
    dispatcher = updater.dispatcher

    # Initialize logging
    logging.basicConfig(filename=LOG_FILE,
                        format=u'%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

    # Plug in the function that gets called when the user enters /start. Commands are Telegram messages that start
    # with /, optionally followed by an @ and the bot's name and/or some additional text.
    start_handler = CommandHandler(u'start', start_callback)
    dispatcher.add_handler(start_handler)

    # Registers an error handler in the Dispatcher.
    dispatcher.add_error_handler(error_callback)

    # Handler class to handle Telegram inline queries. Optionally based on a regex.
    inline_query_handler = InlineQueryHandler(inline_posts_callback)
    dispatcher.add_handler(inline_query_handler)

    # Starts polling updates from Telegram.
    updater.start_polling()


if __name__ == u'__main__':
    main_loop(sys.argv[1])
