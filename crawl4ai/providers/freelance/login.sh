#!/bin/bash
# Login bei freelance.de und Cookie speichern

NODE_PATH=$(npm root -g) node login.js
 
# Hinweis: Das Cookie aus freelance_cookies.json muss in crawl4ai-config.yml übernommen werden. 