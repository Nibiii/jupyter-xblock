"""
Helper functions for the Xblock
"""

import json
from django.template import Template, Context, RequestContext
from crequest.middleware import CrequestMiddleware
from urlparse import urlparse, parse_qs
from django.utils.encoding import iri_to_uri
from django.http import HttpResponse
from django.middleware import csrf
import urllib
import requests
import yaml
import os
from django.contrib.sessions.models import Session
from provider.oauth2.models import Client
from django.conf import settings
import logging

# Globals
log = logging.getLogger(__name__)

def get_authorization_grant(token, sessionid, host):
    """
    Get the authorization code for this user, for use in allowing edx to be
    an oauth2 provider to sifu.
    """
    cr = CrequestMiddleware.get_request()
    headers = {
         "Host":host, # Get base url from env variable
         "X-CSRFToken":token,
         "Connection": 'keep-alive',
         "Referer":"http://%s" % host,
         "Cookie": cr.META['HTTP_COOKIE']
    }
    sifu_id = get_sifu_id()
    if sifu_id is None:
        return None

    # will need to update sifu with the secret details somehow
    state = "3835662" # randomly generate this
    base_url = "http://%s" % host
    location = "%s/oauth2/authorize/?client_id=%s&state=%s&redirect_uri=%s&response_type=code" % (base_url,sifu_id,state,base_url)
    authorization_grant = None
    try:
        while location is not None:
            resp = requests.request("GET", location, headers=headers, allow_redirects=False)
            resp.raise_for_status()
            try:
                location = resp.headers['location']
                authorization_grant = parse_auth_code(resp.headers['location']) if authorization_grant is None else authorization_grant
            except KeyError, e:
                print(e)
                # client might not be trusted
                # session id might be incorrect
                location = None
        # "GET /oauth2/authorize/confirm"
        # "GET /oauth2/redirect ""
        #"GET /?state=3835662&code=48dbd69c8028c61d35df319d04f9d827cfe4c51c HTTP/1.1" 302 0 "
        return authorization_grant

        # to delete post http://0.0.0.0:8000/admin/oauth2/grant/
        # csrfmiddlewaretoken=dZXgCmUiBMTwfjwFZ702h8pg5O0ZkktA&_selected_action=32&action=delete_selected&post=yes
        # as form data
    except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
        log.debug(u'[JupyterNotebook Xblock] : RequestException occured in get_authorization_grant: {}'.format(e))
        return None

def parse_auth_code(redirect_url):
    qs = urlparse(redirect_url).query
    qs = parse_qs(qs)
    return qs['code'].pop(0) if not len(qs) == 0 else None

def get_sifu_id():
    client = Client.objects.filter(name='sifu').values().first()
    if client is None:
        log.debug(u'[JupyterNotebook Xblock] : Oauth2 client is not set up in the Admin backend.')
        return client
    return client['client_id']
