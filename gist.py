#!/usr/bin/env python
# coding=utf-8

__author__ = 'nogaems'
__copyright__ = None
__credits__ = ['nogaems']
__license__ = 'GPL'
__version__ = '0.0.1'
__maintainer__ = "nogaems"
__email__ = "nomad@ag.ru"
__status__ = "Dev"

import json
import argparse
import requests
import sys
import select
import logging as log
import getpass
import time
import datetime

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="""
GitHub Gist poster.

You should either redirect file/message to the stdin of this app or use specified flag to determine what you need to send into the GitHub Gist. If needed you may use your GitHub username and password. Also might be used the access-token. In case of you has been authorized with some way above, you might make up to 5000 requests per hour to GitHub, otherwise it's about 60 requests per hour.
""")

parser.add_argument('--file', '-f', action='store',
                    help='Path to the file you want to send.')
parser.add_argument('--user', '-u', action='store',
                    help='Username of the GitHub account')
parser.add_argument('--password', '-p', action='store',
                    help='Password of the GitHub account')
parser.add_argument('--token', '-t', action='store',
                    help='Access token to GitHub')
parser.add_argument('--verbose', '-v', action='store_true',
                    help='Verbose output') 

args = parser.parse_args()

if args.verbose:
    log.basicConfig(format="%(levelname)s: %(message)s", level=log.INFO)
    log.info('Verbose output.')
else:
    log.basicConfig(format="%(levelname)s: %(message)s")

content = ''

if select.select([sys.stdin,],[],[],0.0)[0]:
    log.info('Using stdin')
    for line in sys.stdin:
        content += line
else:
    if args.file:
        log.info('Trying to load file \'{}\''.format(args.file))
        try:
            content = open(args.file).read()
        except (FileNotFoundError, PermissionError) as e:
            log.error(e)
            exit(1)
        log.info('Done')
    else:
        log.error('Please specify the file which to be sended!')
        exit(1)
        
account = (None, None)

if args.user:
    if args.password:
        account = (args.user, args.password)
    else:
        try:
            account = (args.user,
                       getpass.getpass(prompt='Enter password for user \'{}\':'.format(args.user))
            )
        except (KeyboardInterrupt, EOFError) as e:
            log.error('\nPlease specify the password for user \'{}\'!'.format(args.user))

root_endpoint = 'https://api.github.com'

if account != (None, None):
    log.info('Account data validation')
    try:
        account_check = requests.get(root_endpoint, auth=account)
    except Exception as e:
        log.error('Some error has occured: {}'.format(e))
        exit(1)
    parsed = json.loads(account_check.text)    
    if account_check.status_code in (401, 402):
        log.error('Invalid account data!')
        exit(1)
    elif account_check.status_code != 200:
        log.error('Response status code:{}\nSome error has occured: {}'.format(
            account_check.status_code,
            json.loads(account_check.text)['message']
        ))
        exit(1)
    log.info('Correct')
        
rate_limit_url = 'https://api.github.com/rate_limit'

try:
    if account != (None, None):
        rate_limit = requests.get(rate_limit_url, auth=account)
    else:
        rate_limit = requests.get(rate_limit_url)
except Exception as e:
    log.error('Some error has occured: {}'.format(e))
    exit(1)
parsed = json.loads(rate_limit.text)
if parsed['rate']['remaining'] < 1:
    wait = int((int(parsed['rate']['reset']) - time.time)/60)
    log.error('You achieved access rate limit. Please wait for {} minute(-s) for the access rate counter reset.'.format(wait))
log.info('Access rate limit is not earned yet, {} time(s) left. Reset in {}'.format(
    parsed['rate']['remaining'],
    datetime.datetime.fromtimestamp(int(parsed['rate']['reset'])).strftime('%Y-%m-%d %H:%M:%S')))

gists_url = 'https://api.github.com/gists'
filename = args.file.split('/')[-1] if args.file else sys.stdin.name
headers = {
    'description':'Pasted from CLI',
    'public': False,
    'files': {
        filename: {
            'content': content
        }
    }
}

try:
    log.info('Tryind to upload data')
    response = requests.post(gists_url, json.dumps(headers))
except Exception as e:
    log.error('Some error has occured: {}'.format(e))
    exit(1)
parsed = json.loads(response.text)
if response.status_code == 201:
    log.info('Success!')
    print('HTML link: {}\nraw link: {}'.format(
        parsed['html_url'],
        parsed['files'][filename]['raw_url']))
    exit(0)
else:
    log.error('An error occured while sending a data: {} {}'.format(response.status_code,
                                                                    response.text))
    exit(1)
