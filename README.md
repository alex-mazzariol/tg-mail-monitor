# TG Mail Monitor

## Description

This is a simple mail monitor that will check for new mails in a given folder and will send a notification using a Telegram bot.

This is to reduce the battery usage of K-9 Mail and other mail clients on smartphones, while still being able to get promptly notified of new mails.

## Principle of Operation

The script uses the IMAP IDLE command to check for new mails in a given folder. If a new mail is found, it will send a notification to a Telegram bot. If IMAP IDLE is not supported by the server, the script will fall back to a simple polling mechanism.

The polling mechanism is implemented by just checking for new mails and exiting. Systemd will restart the script every 60 seconds, so it will effectively check for new mails every minute.

## Installation

### Prerequisites

- A Telegram bot with a token and chat ID
- An e-mail account with a password-accessible IMAP server (i.e. no OAuth2 like Gmail)

### Setup

1. Clone this repository to your server
2. Create a new Telegram bot and get the bot token and chat ID
3. Create the configuration file in a secure location and adjust the directory paths in the systemd service file
4. Create the systemd service file for each instance of the script
5. Start the service

### Sample Setup

* Put all files in `/opt/mail-monitor`
* Create the configuration file in `/opt/mail-monitor/mail1.env`
* Create the systemd service file in `/etc/systemd/system/mail-monitor@.service`
* Start the service with `systemctl start mail-monitor@mail1`

## License

MIT License

Copyright (c) 2024 Alex Mazzariol

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.