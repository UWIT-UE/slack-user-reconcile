#!/usr/bin/env python3

import requests
import json
import sys
import urllib.parse
import configparser
import os

# Some logging systems like stackdriver distinguish between stdout and stderr
def loginfo(msg):
    sys.stdout.write('user-reconcile info: {0}\n'.format(msg))

def logerror(msg):
    sys.stderr.write('user-reconcile error: {0}\n'.format(msg))

CONFIG_FILE = '/config/user-reconcile.cfg'
if 'CONFIG_FILE' in os.environ:
    CONFIG_FILE = os.environ['CONFIG_FILE']

if not os.path.exists(CONFIG_FILE):
    logerror('config file not found {}'.format(CONFIG_FILE))
    sys.exit(1)

config = configparser.ConfigParser()
config.read(CONFIG_FILE)
cfgvals = config['common']

general_options = [ 'failsafe_count', 'permit_gws_group' ]
slack_options = [ 'slack_team', 'slack_token', 'slack_post_channel' ]
gws_options = [ 'gws_cert_file', 'gws_key_file', 'gws_ca_file' ]

for option in general_options + slack_options + gws_options:
    if option not in cfgvals.keys():
        logerror('missing [common] config option {}'.format(option))
        sys.exit(1)

for option in gws_options:
    if not os.path.exists(cfgvals[option]):
        logerror('certificate file not found {}'.format(cfgvals[option]))
        sys.exit(1)

# Not user servicable
gws_url = 'https://groups.uw.edu/group_sws/v3'
users_api_url = "https://{team_id}.slack.com/api/users.list?token={api_token}"
post_api_url = "https://{team_id}.slack.com/api/chat.postMessage?token={api_token}&channel={channel}&text={message}"
scim_api_url = "https://api.slack.com/scim/v1/Users/{user_id}"

def slack_get_users(team_id, api_token):
    url = users_api_url.format(team_id=team_id, api_token=api_token)
    r = requests.get(url)
    if not r.status_code == requests.codes.ok:
        logerror ('bad http response on get_users: {}'.format(r.status_code))
        return list()

    response_data = r.json()
    if not response_data.get('ok'):
        logerror ('bad status on get_users: {}'.format(response_data['error']))
        return list()

    if 'members' in response_data:
        return response_data['members']
    else:
        logerror ('no members provided by Slack')
        return list()

def slack_deactivate(team_id, api_token, user_id):
    # deactivate uses SCIM REST calling convention unlike the rest of Slack API
    # so this looks different than slack_get_users
    url = scim_api_url.format(team_id=team_id, user_id=user_id)
    r = requests.delete(url, headers={"Accept":"application/json", "Authorization":"Bearer {}".format(cfgvals['slack_token'])})
    if not r.status_code == requests.codes.ok:
        logerror ('bad http response on deactivate: {}'.format(r.status_code))
        return False
    else:
        return True

def slack_reactivate(team_id, api_token, user_id):
    # reactivate uses SCIM REST calling convention unlike the rest of Slack API
    # so this looks different than slack_get_users
    url = scim_api_url.format(team_id=team_id, user_id=user_id)
    payload = json.dumps({ "schemas": [ "urn:scim:schemas:core:1.0" ],
                           "id": user_id,
                           "active": "true",
                         })
    r = requests.patch(url, headers={"Accept":"application/json", "Authorization":"Bearer {}".format(cfgvals['slack_token'])}, data=payload)
    if not r.status_code == requests.codes.ok:
        logerror ('bad http response on reactivate: {}'.format(r.status_code))
        return False
    else:
        return True

def slack_post(team_id, api_token, channel, message):
    url = post_api_url.format(team_id=team_id, api_token=api_token, 
                              channel=urllib.parse.quote(channel), message=urllib.parse.quote(message))
    r = requests.put(url)
    if not r.status_code == requests.codes.ok:
        logerror('bad http response on get_users: {}'.format(r.status_code))
        return False

    response_data = r.json()
    if not response_data.get('ok'):
        logerror ('bad status on slack_post: {}'.format(response_data['error']))
        return False
    return True

## Everything loaded, lets work
loginfo('running')

## GWS fetch
query = "{}/group/{}/effective_member".format(gws_url, cfgvals['permit_gws_group'])

r = requests.get(query, cert=(cfgvals['gws_cert_file'], cfgvals['gws_key_file']), verify=cfgvals['gws_ca_file'])
if not r.status_code == requests.codes.ok:
    logerror('bad http response on gws_fetch: {}'.format(r.status_code))
    sys.exit(1)

permitGroupMembers = r.json()['data']

permitList = {}
for puser in permitGroupMembers:
    if puser['type'] == 'uwnetid':
        permitList[puser['id']] = 1    

if len(permitList.keys()) < int(cfgvals['failsafe_count']):
    logerror("membership of permit group ({}) is too small, abort".format(len(permitList.keys())))
    sys.exit(1)

## Process Slack users 
actionsTaken = { "reactivate": [], "deactivate": [] }
slackUsers = slack_get_users(cfgvals['slack_team'], cfgvals['slack_token'])
for user in slackUsers:

    if user['id'] == 'USLACKBOT':
        #loginfo('Skipping slackbot')
        continue

    if user['deleted']:
        if user['name'] in permitList:
            if slack_reactivate(cfgvals['slack_team'], cfgvals['slack_token'], user['id']):
                loginfo ('Reactivated  ' + user['name']) 
                actionsTaken['reactivate'].append(user['name'])
        continue

    if user['name'] not in permitList:
        if user['is_app_user'] or user['is_bot']:
            #loginfo('Skipping app/bot ' + user['name'])
            continue
        if user['is_admin'] or user['is_owner'] or user['is_primary_owner']:
            #loginfo('Skipping admin/owner ' + user['name'])
            slack_post(cfgvals['slack_team'], cfgvals['slack_token'], cfgvals['slack_post_channel'], 
                       ":exclamation: *Attention Human* :exclamation:\nUser {} is no longer eligible for Slack but is an owner or admin. Please manually process this one if its real.".format(user['name']))
            continue

        #loginfo('Want deactivate ' + user['name'])
        if slack_deactivate(cfgvals['slack_team'], cfgvals['slack_token'], user['id']):
            loginfo('Deactivated ' + user['name'])
            actionsTaken['deactivate'].append(user['name'])
            
## Summarize
if len(actionsTaken['deactivate']):
    slack_post(cfgvals['slack_team'], cfgvals['slack_token'], cfgvals['slack_post_channel'], "*Deactivated users*\n" + ", ".join(actionsTaken['deactivate']))
    loginfo('Deactivated users ' + ", ".join(actionsTaken['deactivate']))
if len(actionsTaken['reactivate']):
    slack_post(cfgvals['slack_team'], cfgvals['slack_token'], cfgvals['slack_post_channel'], "*Reactivated users*\n" + ", ".join(actionsTaken['reactivate']))
    loginfo('Reactivated users ' + ", ".join(actionsTaken['reactivate']))


