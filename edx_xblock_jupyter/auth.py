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

from middleware import CresponseMiddleware
from webob import Response
# Globals
log = logging.getLogger(__name__)

def needs_authorization_header(func):
    """
    Maybe put this into its own Auth class singleton
    Decorator to make sure API calls are authorized
    """
    def function_wrapper(token=None):
        auth = func(token)
        auth.update({"Authorization":"Bearer %s" % token})
        return auth
    return function_wrapper

@needs_authorization_header
def get_headers(sifu_token=None):
    headers = {
        'referer': "0.0.0.0:8000",
        'content-type': "application/json"
    }
    return headers

def get_auth_token(auth_grant, username, sifu_domain):
    """
    Gets the authentication token associated with this user through Sifu's
    calls to the edx oauth2 api.
    """
    payload = {
        "username":username,
        "auth_code":auth_grant,
        "grant_type":"edx_auth_code",
        "path": "create"
    }
    headers = get_headers()
    url = 'http://%s:3334/token' % sifu_domain
    try:
        resp = requests.post(url, data=json.dumps(payload), headers=headers)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print("HTTPError:", e.message)
            return None
        try:
            json_response = resp.json()
        except:
            return None
        else:
            CresponseMiddleware._auth_token = 'Bearer %s' % json_response["access_token"]
            return json_response["access_token"]
    except requests.exceptions.RequestException as e:
        log.debug(u'[JupyterNotebook Xblock] : RequestException occured in get_auth_token: {}'.format(e))
        return None

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

def destroy_sifu_token(sifu_token, sifu_domain):
    """
    Removes the login associated with this token
    """
    url = "http://%s:3334/revoke" % sifu_domain
    payload = {
        "token_type_hint":"access_token",
        "token":sifu_token,
    }
    headers = get_headers()
    try:
        response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
        return True
    except requests.exceptions.RequestException as e:
        log.debug(u'[JupyterNotebook Xblock] : RequestException occured in destroy_sifu_token: {}'.format(e))
        return False
