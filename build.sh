#!/bin/bash
pip install --upgrade pip
pip uninstall -y python-telegram-bot
pip install --no-cache-dir "python-telegram-bot==13.4"
pip install --no-cache-dir -r requirements.txt
