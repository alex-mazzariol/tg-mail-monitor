import email
import requests
import os
import datetime
import re
from imapclient import IMAPClient
from bs4 import BeautifulSoup
from email.message import Message

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

def _decode_part(part: Message) -> str:
    """Decode a non-multipart part to unicode text, respecting charset."""
    # Try to get raw bytes (handles base64/quoted-printable automatically)
    payload = part.get_payload(decode=True)
    if payload is None:
        # Some libraries may give a str payload already
        payload = part.get_payload()
        return payload if isinstance(payload, str) else ""
    # Use declared charset if present; otherwise fall back
    charset = part.get_content_charset() or part.get_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        # Unknown codec — fall back to utf-8
        return payload.decode("utf-8", errors="replace")

def get_email_body(msg: Message) -> str:
    html_candidates = []
    text_candidates = []

    if msg.is_multipart():
        for part in msg.walk():
            # Skip container parts
            if part.is_multipart():
                continue

            ctype = (part.get_content_type() or "").lower()
            disp = (part.get("Content-Disposition") or "").lower()

            # Skip attachments/inline binaries
            if "attachment" in disp or part.get_filename() or ctype.startswith("image/"):
                continue

            if ctype == "text/html":
                html_candidates.append(_decode_part(part))
            elif ctype == "text/plain":
                text_candidates.append(_decode_part(part))
    else:
        ctype = (msg.get_content_type() or "").lower()
        if ctype == "text/html":
            html_candidates.append(_decode_part(msg))
        elif ctype == "text/plain":
            text_candidates.append(_decode_part(msg))

    # Prefer HTML → plain fallback. In multipart/alternative, the best version is usually last.
    if html_candidates:
        for html in reversed(html_candidates):
            text = html_to_text(html)  # your function
            cleaned = clean_all_whitespace(text)  # your function
            if cleaned.strip():
                return cleaned
        # If everything was empty whitespace, still return the last processed
        return clean_all_whitespace(html_to_text(html_candidates[-1]))

    if text_candidates:
        for plain in reversed(text_candidates):
            cleaned = clean_all_whitespace(plain)
            if cleaned.strip():
                return cleaned
        return clean_all_whitespace(text_candidates[-1])

    return ""

def html_to_text(html_content):
    # Simple HTML to text conversion
    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove all links
    for a in soup.find_all("a"):
        a.replace_with(a.get_text())

    return soup.get_text(separator=' ')

def escape_markdown(text):
    # Escape special characters for Markdown
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '=', '|', '{', '}']
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
