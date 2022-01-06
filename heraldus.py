import logging
import sys
import imaplib
import email
import email.message
from email.header import decode_header
from datetime import datetime, date
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class UserMail:
    def __init__(self, user, password):
        self.user = user
        self.password = password


mail_boxes = {}


def get_mail_server(user_mail):
    try:
        mail = imaplib.IMAP4('localhost', 143)
        mail.login(user_mail.user, user_mail.password)
        mail.select('INBOX')
        return mail
    except imaplib.IMAP4.error:
        return None


def set_check_email(update: Update, context: CallbackContext):
    if not update.message:
        return

    user_mail = mail_boxes.get(update.message.chat.id)
    if len(context.args) != 2 or user_mail or not get_mail_server(UserMail(*context.args)):
        return

    logging.info(context.args)
    j = updater.job_queue
    j.run_repeating(check_email, interval=300, context={'chat': update.message.chat.id, 'args': context.args})
    mail_boxes[update.message.chat.id] = UserMail(*context.args)
    update.message.reply_text('done!')


def mark_msgs_as_read(update, context):
    user_mail = mail_boxes.get(update.message.chat.id)
    if user_mail:
        mail = get_mail_server(user_mail.user)
        type, data = mail.search(None, 'UNSEEN')
        for msg in data:
            mail.store(msg.replace(' ', ','), '+FLAGS', '\Seen')
        update.message.reply_text('clear!')


def echo(update: Update, context: CallbackContext) -> None:
    if update.message.chat.id not in mail_boxes:
        update.message.reply_text("You aren't subscribed to mail")
    else:
        update.message.reply_text('Great! You are subscribed to mail')


def get_header(header):
    decode_subject = decode_header(header)
    if decode_subject[0][1]:
        return decode_subject[0][0].decode(decode_subject[0][1])
    return decode_subject[0][0]


def check_email(context: CallbackContext):
    job = context.job
    user_mail = mail_boxes.get(job.context['chat'])
    if user_mail:
        mail = get_mail_server(user_mail)
        status, response = mail.search(None, 'UNSEEN')
        unread_msg_nums = response[0].split()
        response = ''
        for msg_num in unread_msg_nums:
            status, msg_data = mail.fetch(msg_num.decode('utf-8'), '(RFC822)')
            
            email_msg = email.message_from_bytes(msg_data[0][1], _class = email.message.EmailMessage)
            response += '{}. {} - {}\n'.format(msg_num.decode('utf-8'),
                    get_header(email_msg['From']),
                    get_header(email_msg['Subject']))

        if len(response):
            context.bot.send_message(job.context['chat'], text=response)


if __name__ == '__main__':
    updater = Updater(token='')
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('set_check_email', set_check_email))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    
    updater.start_polling()
    updater.idle()
