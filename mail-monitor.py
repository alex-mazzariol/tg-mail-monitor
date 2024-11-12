import imaplib
import email
import requests
import os
import time
import socket

# Get configuration from environment variables
IMAP_SERVER = os.getenv('IMAP_SERVER')
EMAIL_ACCOUNT = os.getenv('EMAIL_ACCOUNT')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Set up IMAP connection
mail = imaplib.IMAP4_SSL(IMAP_SERVER)
mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
mail.select('inbox')

def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    data = {'chat_id': CHAT_ID, 'text': message}
    requests.post(url, data=data)

def check_email():
    result, data = mail.search(None, 'UNSEEN')
    email_ids = data[0].split()
    for email_id in email_ids:
        result, msg_data = mail.fetch(email_id, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        subject = msg['subject']
        send_telegram_message(f'New email: {subject}')

# Check if the server supports IDLE
if 'IDLE' in mail.capabilities:
    print("Server supports IDLE. Waiting for new messages...")
    try:
        while True:
            tag = mail._new_tag()
            mail.send(f"{tag} IDLE\r\n".encode())
            response = mail.readline()

            if response.strip().startswith(b'+ idling'):
                mail.sock.settimeout(60)
                try:
                    response = mail.readline()
                    if response and b'EXISTS' in response:
                        check_email()
                except (socket.timeout, imaplib.IMAP4.abort):
                    pass
            else:
                break
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        mail.send(b'DONE\r\n')
        mail.close()
        mail.logout()
else:
    print("Server does not support IDLE. Exiting after initial check.")
    check_email()
    mail.close()
    mail.logout()