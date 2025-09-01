import email
import requests
import os
import datetime
import re
from imapclient import IMAPClient
from bs4 import BeautifulSoup

# Get configuration from environment variables
IMAP_SERVER = os.getenv('IMAP_SERVER')
EMAIL_ACCOUNT = os.getenv('EMAIL_ACCOUNT')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

highest_uid = 0

def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    requests.post(url, data=data)

def clean_all_whitespace(text):
    """More aggressive cleaning - also handles spaces and tabs between newlines."""
    # Replace sequences of whitespace containing 3+ newlines with exactly 2 newlines
    return re.sub(r'[\t ]{2,}', ' ', re.sub(r'\n(?:\s*\n){2,}', '\n\n', text))

def get_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            # Skip attachments
            if "attachment" in content_disposition:
                continue
            # Get the email body
            if content_type == "text/plain":
                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                return clean_all_whitespace(body)
            elif content_type == "text/html":
                html_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                # Optionally, convert HTML to plain text
                body = html_to_text(html_body)
                return clean_all_whitespace(body)
    else:
        content_type = msg.get_content_type()
        if content_type == "text/plain":
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            return clean_all_whitespace(body)
        elif content_type == "text/html":
            html_body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            body = html_to_text(html_body)
            return clean_all_whitespace(body)
    return ""

def html_to_text(html_content):
    # Simple HTML to text conversion
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(separator=' ')
    return text

def escape_markdown(text):
    # Escape special characters for Markdown
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '=', '|', '{', '}', '.']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

def check_email(server):
    global highest_uid
    messages = server.search(['UNSEEN', 'UID', f'{highest_uid + 1}:*'])
    for uid, message_data in sorted(server.fetch(messages, ['BODY.PEEK[]', 'INTERNALDATE']).items()):
        try:
            # If the uid is still the highest, skip it
            if uid == highest_uid:
                continue
            
            # Get the INTERNALDATE
            internal_date = message_data[b'INTERNALDATE']

            # Ensure internal_date is timezone-aware
            if internal_date.tzinfo is None:
                # Assign UTC timezone to internal_date
                internal_date = internal_date.replace(tzinfo=datetime.timezone.utc)

            # Time window check
            time_difference = datetime.datetime.now(datetime.timezone.utc) - internal_date
            if time_difference > datetime.timedelta(hours=2):
                continue  # Skip messages older than 2 hours

            highest_uid = int(uid)

            print(f"You have new mail! With UID {uid}")

            msg = email.message_from_bytes(message_data[b'BODY[]'])
            subject = msg['subject']
            sender = msg['from']
            body = get_email_body(msg)
            body_preview = body[:350]
            # Escape Markdown special characters
            subject = escape_markdown(subject)
            body_preview = escape_markdown(body_preview)

            if len(body) > 350:
                #Here to avoid escaping the ellipsis
                body_preview += '...'

            message = f'*New email received for {EMAIL_ACCOUNT}*\n*From*: {sender}\n*Subject*: {subject}\n*Body Preview*: {body_preview}'
            send_telegram_message(message)
        except Exception as e:
            print(f"Error processing email: {e}")

with IMAPClient(IMAP_SERVER) as server:
    server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    server.select_folder('INBOX')

    if highest_uid == 0:
        # Get the maximum UID in the mailbox
        max_uid = max(server.search(['ALL']) or [0])
        highest_uid = max_uid

    print(f"Highest UID: {highest_uid}")
        
    check_email(server)
    if server.has_capability('IDLE'):
        print("Server supports IDLE. Waiting for new messages...")
        while True:
            is_idle = False
            try:
                server.idle()
                is_idle = True
                responses = server.idle_check(timeout=120)
                server.idle_done()
                is_idle = False
                if responses:
                    check_email(server)
            except:
                print("Exiting...")
                break
            finally:
                if is_idle:
                    server.idle_done()
    else:
        print("Server does not support IDLE. Exiting after initial check.")
    server.logout()
