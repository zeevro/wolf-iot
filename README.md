# Wolf IoT

A dead-simple stand-alone server for implementing a Google Home integration written with Flask on python 3.

It implements the most basic and simple OAuth 2.0 and is meant for running on your own computer inside your home network so it has no users, no log-ins and so needs no database.

## Installation

```pip install https://github.com/zeevro/wolf-iot/archive/master.zip```

## Prerequisites

- A DNS domain name pointing to your computer
- A valid SSL certificate for that domain name (see [Let's Encrypt](https://letsencrypt.org/) or [SSL For Free](https://www.sslforfree.com/))
- A configured Google Actions project

## Google Actions project setup

1. Go to the [Google Actions Console](https://console.actions.google.com/) and create a new project
2. In the *Actions* tab fill in the *Fulfillment URL* as `https://my.public.dns.hostname:port/api/fulfillment/`
3. In the *Account linking* tab fill in *Client ID*, *Client secret*, *Authorization URL* and *Token URL*:
   - *Client ID* and *Client secret* can be acquired by running ```wolf_iot_server -i```.
   - *Authorization URL*: `https://my.public.dns.hostname:port/oauth/authorize/`
   - *Token URL*: `https://my.public.dns.hostname:port/oauth/token/`
4. OPTIONAL: How to setup sync requests

## TODO

- [ ] Store known devices in some permanent storage (e.g. file/database/redis/etc.)
- [ ] Device discovery (and sync requests)
- [ ] Finish writing README :)

