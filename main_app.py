import sys
import os
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardHide, KeyboardButton, ParseMode)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler)
from api import botan
from geopy.geocoders import Nominatim
import random
from flask import Flask
import logging
app = flask.Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_KEY = sys.argv[1]
BOTAN_TOKEN = sys.argv[2]
MAIN, LOCATION = range(2)
UBER_URL = "http://blopa.github.io/uber.html?"  # TODO use "uber://?" or "https://m.uber.com/ul/?" ?
CMDS = ["/setpickup", "/setdropoff", "/setpickanddrop", "/applycoupon"]
SCMDS = ["/start", "/about", "/help"]
CMD = {}
PICK = {}
UBER_PROMO = "uberKoehUsaMeuCodigo"


def main():
    updater = Updater(TELEGRAM_KEY)
    dispatcher = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.command, start)],
        states={
            MAIN: [MessageHandler(Filters.command, mainmenu)],
            LOCATION: [MessageHandler(Filters.location, getlocation)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dispatcher.add_handler(conv_handler)
    updater.start_polling()


def start(bot, update):
    msg = update.message.text
    if str(msg).startswith(SCMDS[0]):
        update.message.reply_text("Hello, I'm a bot that helps you order a Uber. You can {}, {}, {} or {}.".format(*CMDS))
    elif str(msg).startswith(SCMDS[1]):
        update.message.reply_text("This bot will help you setting up a pickup and/or dropoff location for Uber.\n\nDon't have Uber? Install it now: https://uber.com/invite/uberKoehUsaMeuCodigo. \n\nThis bot was made by @PabloMontenegro and it is in development, you can check the source code at https://github.com/blopa/uber-telegram-bot.\n\nPull requests are welcome.")  # TODO
    elif str(msg).startswith(SCMDS[2]):
        update.message.reply_text("I'm a bot that helps you order a Uber. Try using {}, {}, {} or {}.".format(*CMDS))
    else:
        return mainmenu(bot, update)
    return MAIN


def mainmenu(bot, update):
    usr = update.message.from_user
    msg = update.message.text
    reply = ReplyKeyboardMarkup([[KeyboardButton(text="Current Location", request_location=True)]], one_time_keyboard=True)
    reply_msg = "Alright, send me the {}. You can either select send me the location now or simply select 'Current Location' from the menu. Or /cancel to cancel."
    if str(msg).startswith(CMDS[0]):  # /setpickup
        CMD[usr.id] = CMDS[0]
        update.message.reply_text(reply_msg.format('pickup location'), reply_markup=reply)
        return LOCATION
    elif str(msg).startswith(CMDS[1]):  # /setdropoff
        CMD[usr.id] = CMDS[1]
        update.message.reply_text(reply_msg.format('drop off location'), reply_markup=reply)
        return LOCATION
    elif str(msg).startswith(CMDS[2]):  # /setpickanddrop
        CMD[usr.id] = CMDS[2]
        update.message.reply_text(reply_msg.format('pickup location first'), reply_markup=reply)
        return LOCATION
    elif str(msg).startswith(CMDS[3]):  # /applycoupon
        link = UBER_URL + "c=" + UBER_PROMO
        update.message.reply_text('Awesome. Just click <a href="{}">HERE</a> to open the Uber app'.format(link), parse_mode=ParseMode.HTML)
        return MAIN

    if str(msg) in SCMDS:
        return start(bot, update)

    update.message.reply_text("Sorry, I didn't undestanded that. Try sending {}.".format(random.choice(CMDS)))
    return MAIN


def getlocation(bot, update):
    usr = update.message.from_user
    location = update.message.location
    if usr.id in CMD:
        geolocator = Nominatim()
        latiLong = str(location.latitude) + "," + str(location.longitude)
        try:
            loc = geolocator.reverse(latiLong).address
        except Exception:
            loc = ""
        reply_msg = "The {} location set to:\n"
        uber_msg = 'All set! Just click <a href="{}">HERE</a> to open the Uber app.'
        if CMD[usr.id] == CMDS[0]:  # /setpickup
            link = UBER_URL + "p={}".format(str(location.latitude) + "," + str(location.longitude))
            update.message.reply_text(uber_msg.format(link), parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardHide())
            if loc:
                update.message.reply_text(reply_msg.format('pickup') + loc)
            try:
                botan.track(BOTAN_TOKEN, update.message.from_user.id, {0: 'set pickup'}, 'set pickup')
            except Exception as e:
                logger.exception(e)
        elif CMD[usr.id] == CMDS[1]:  # /setdropoff
            link = UBER_URL + "d={}".format(str(location.latitude) + "," + str(location.longitude))
            update.message.reply_text(uber_msg.format(link), parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardHide())
            if loc:
                update.message.reply_text(reply_msg.format('dropoff') + loc)
            try:
                botan.track(BOTAN_TOKEN, update.message.from_user.id, {0: 'set dropoff'}, 'set dropoff')
            except Exception as e:
                logger.exception(e)
        elif CMD[usr.id] == CMDS[2]:  # /setpickanddrop
            if usr.id in PICK:
                try:
                    loc2 = geolocator.reverse(PICK[usr.id]).address
                except Exception:
                    loc2 = ""
                link = UBER_URL + "p={}&d={}".format(PICK[usr.id], str(location.latitude) + "," + str(location.longitude))
                del PICK[usr.id]
                update.message.reply_text(uber_msg.format(link), parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardHide())
                if loc and loc2:
                    update.message.reply_text(reply_msg.format('pickup') + loc2 + "\n\nAnd dropoff location set to:\n" + loc)
                try:
                    botan.track(BOTAN_TOKEN, update.message.from_user.id, {0: 'set pickup and dropoff'}, 'set pickup and dropoff')
                except Exception as e:
                    logger.exception(e)
            else:
                PICK[usr.id] = latiLong
                if loc:
                    update.message.reply_text(reply_msg.format('pickup') + loc)
                update.message.reply_text("Now send me the dropoff location or simply select 'Current Location' from the menu. Or /cancel to cancel.")
                return LOCATION
        else:
            update.message.reply_text("Something went wrong, please try again.")
    else:
        update.message.reply_text("Something went wrong, please try again.")

    return MAIN


def cancel(bot, update):
    update.message.reply_text("Ok, canceled.", reply_markup=ReplyKeyboardHide())
    return MAIN


if __name__ == '__main__':
    main()
