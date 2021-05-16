#!/bin/sh
#Generate a certificate that the bot can use to connect to mumble
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -nodes
