import json, urllib, requests, yaml, os
import pkg_resources

from django.template import Template, Context, RequestContext

from crequest.middleware import CrequestMiddleware
from urlparse import urlparse, parse_qs

from xblock.core import XBlock
from xblock.exceptions import JsonHandlerError
from xblock.fields import Scope, String, Integer, Float, Boolean, List, DateTime, JSONField
from xblock.fragment import Fragment
from xblock.validation import Validation
from xblockutils.studio_editable import StudioEditableXBlockMixin, FutureFields
from xmodule.x_module import XModuleMixin

from django.utils.encoding import iri_to_uri
from django.utils.translation import ugettext
from django.http import HttpResponse
from django.middleware import csrf
from django.contrib.sessions.models import Session
from django.conf import settings

from provider.oauth2.models import Client

import logging

from auth import get_headers, get_auth_token, parse_auth_code, get_sifu_id, get_authorization_grant, destroy_sifu_token

# Globals
log = logging.getLogger(__name__)

@XBlock.needs('user')
class JupyterNotebookXBlock(StudioEditableXBlockMixin, XBlock):

    display_name = String(
        display_name="Display Name",
        help="Display name for this module",
        default="JupyterNotebook",
        scope=Scope.settings,
    )

    url_resource = String(
        scope=Scope.settings
    )

    file_noteBook = String(
        display_name="Upload file noteBook",
        scope=Scope.settings,
        resettable_editor=False
    )

    course_unit = String(
        display_name="Course Unit",
        scope=Scope.settings,
        resettable_editor=False
    )

    editable_fields = ('display_name', 'file_noteBook', 'course_unit')

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def studio_view(self, context, request=None):
        """
        Render a form for editing this XBlock
        """
        fragment = Fragment()
        context = {'fields': [],
                   'courseKey': self.location.course_key}
        # Build a list of all the fields that can be edited:
        for field_name in self.editable_fields:
            field = self.fields[field_name]
            assert field.scope in (Scope.content, Scope.settings), (
                "Only Scope.content or Scope.settings fields can be used with "
                "StudioEditableXBlockMixin. Other scopes are for user-specific data and are "
                "not generally created/configured by content authors in Studio."
            )
            field_info = self._make_field_info(field_name, field)
            if field_info is not None:
                context["fields"].append(field_info)
        fragment.content = self.render_template('static/html/studio_edit.html', context)
        fragment.add_css(self.resource_string("static/css/jupyternotebook_xblock.css"))
        fragment.add_javascript(self.resource_string("static/js/src/studio_edit.js"))
        fragment.initialize_js('JupyternotebookStudioEditableXBlock')
        return fragment

    def get_config(self, key):
        os.chdir(os.path.dirname(__file__))
        config = yaml.safe_load(open("%s/config.yml" % os.getcwd(), 'r'))
        return config[key]

    def student_view(self, context=None, request=None):
        if not self.runtime.user_is_staff:
            user_service = self.runtime.service(self, 'user')
            xb_user = user_service.get_current_user()
            username = xb_user.opt_attrs.get('edx-platform.username')
            if username is None:
                log.debug(u'[JupyterNotebook Xblock] : User not found in student_view')

            # get the course details
            course_unit_name = str(self.course_unit)
            resource = str(self.file_noteBook)

            cr = CrequestMiddleware.get_request()
            token = csrf.get_token(cr)
            sessionid = cr.session.session_key

            cookie_data_string = cr.COOKIES.get(settings.SESSION_COOKIE_NAME)
            host = cr.META['HTTP_HOST']

            authorization_grant = get_authorization_grant(token, sessionid, host)

            # Get a token from Sifu
            sifu_domain = self.get_config('sifu_domain')
            sifu_token = None
            # it looks like these might be single use tokens
            #cr.session['sifu_token'] = None
            try:
                sifu_token = cr.session['sifu_token']
            except:
                cr.session['sifu_token'] = None

            if sifu_token is None:
                sifu_token = get_auth_token(authorization_grant, username, sifu_domain)
                cr.session['sifu_token'] = sifu_token

            #check if user notebook & base notebook exists
            if not self.user_notebook_exists(username, course_unit_name, resource, sifu_token, sifu_domain):
                log.debug(u'[JupyterNotebook Xblock] : User notebook does not exist.')
                # check the base file exists
                if not self.base_file_exists(course_unit_name, resource, sifu_token, sifu_domain):
                    log.debug(u'[JupyterNotebook Xblock] : The course unit base notebook does not exist.')
                    # create the base file
                    self.create_base_file(course_unit_name, resource, sifu_token, sifu_domain, host)
                # create user notebook assuming the base file exists
                if not self.create_user_notebook(username, course_unit_name, resource, sifu_token, sifu_domain):
                    log.debug(u'[JupyterNotebook Xblock] : Could create {}\'s notebook'.format(username))

            context = {
                'self': self,
                'user_is_staff': self.runtime.user_is_staff,
                'current_url_resource': self.get_current_url_resource(username, course_unit_name, resource, sifu_token, sifu_domain, host),
            }
        else:
            context = {
                'self': self,
                'user_is_staff': self.runtime.user_is_staff,
                'current_url_resource': None,
            }
        template = self.render_template("static/html/jupyternotebook_xblock.html", context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/jupyternotebook_xblock.css"))
        frag.add_javascript(self.resource_string("static/js/src/jupyternotebook_xblock.js"))
        frag.initialize_js('JupyternotebookXBlock')
        return frag

    def user_notebook_exists(self, username, course_unit_name, resource, sifu_token, sifu_domain):
        """
        Tests to see if user notebook exists
        """
        headers = get_headers(sifu_token)
        url = 'http://%s:3334/v1/api/notebooks/users/courses/files' % sifu_domain
        payload = {"notey_notey":{"username":username,"course":course_unit_name,"file":resource}}

        try:
            resp = requests.request("GET", url, data=json.dumps(payload), headers=headers)
            resp.raise_for_status()

            resp = resp.json()
            return resp["result"]
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            log.debug(u'[JupyterNotebook Xblock] : RequestException occured in user_notebook_exists: {}'.format(e))
            return False

    def get_xblock_notebook(self, host):
        """
        Gets the uploaded notebook from studio
        NB!!! (requires that studio be running) NB!! <----- LOOK HERE
        """
        url = "http://%s/%s" % (host, self.file_noteBook)
        print(url)
        try:
            resp = requests.request("GET", url)
            return resp.content
        except requests.exceptions.RequestException as e:
            print(e)
            return False

    def base_file_exists(self, course_unit_name, resource, sifu_token, sifu_domain):
        base_url = "http://%s:3334/%s"
        headers = get_headers(sifu_token)
        api_endpoint = "v1/api/notebooks/courses/files/"
        response = None
        url = base_url % (sifu_domain, api_endpoint)
        payload = {"notey_notey":{"course":course_unit_name,"file":resource}}

        try:
            # TODO check for auth-403 alreadystarted-400 doesntexist-404
            resp = requests.request("GET", url, data=json.dumps(payload), headers=headers)
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print("HTTPError:", e.message)
                return False
            resp = resp.json()
            return resp["result"]
        except requests.exceptions.RequestException as e:
            print("[edx_xblock_jupyter] ERROR : %s " % e)
            return False

    def create_base_file(self, course_unit_name, resource, sifu_token, sifu_domain, host):
        base_url = "http://%s:3334/%s"
        headers = get_headers(sifu_token)
        api_endpoint = "v1/api/notebooks/courses/files/"
        response = None
        url = base_url % (sifu_domain, api_endpoint)
        loaded_file = self.get_xblock_notebook(host)
        payload = {"notey_notey":{"course":course_unit_name,"file":resource,"data":loaded_file}}

        try:
            # TODO check for auth-403 alreadystarted-400 doesntexist-404
            response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
            return True
        except requests.exceptions.RequestException as e:
            print("[edx_xblock_jupyter] ERROR : %s " % e)
            return False

    def create_user_notebook(self, username, course_unit_name, resource, sifu_token, sifu_domain):
        base_url = "http://%s:3334/%s"
        headers = get_headers(sifu_token)
        api_endpoint = "v1/api/notebooks/users/courses/files/"
        response = None
        url = base_url % (sifu_domain, api_endpoint)
        payload = {"notey_notey":{"username":username,"course":course_unit_name,"file":resource}}
        try:
            # TODO check for auth-403 alreadystarted-400 doesntexist-404
            resp = requests.request("POST", url, data=json.dumps(payload), headers=headers)
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print("HTTPError:", e.message)
                return False
            return True
        except requests.exceptions.RequestException as e:
            print("[edx_xblock_jupyter] ERROR : %s " % e)
            return False

    def get_current_url_resource(self, username, course, filename, sifu_token, sifu_domain, host):
        """
        Returns the url for the API call to fetch a notebook
        """
        params = ('0.0.0.0', urllib.quote(username), urllib.quote(course), urllib.quote(filename), sifu_token)
        url = "http://%s:3334/v1/api/notebooks/users/%s/courses/%s/files/%s?Authorization=Bearer %s" % params
        return url

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

    def _make_field_info(self, field_name, field):
        info = super(JupyternotebookXBlock, self)._make_field_info(field_name, field)
        if field_name == 'file_noteBook':
            info['type'] = 'file_uploader'
        return info

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("JupyternotebookXBlock",
             """<vertical_demo>
                <jupyternotebook_xblock/>
                </vertical_demo>
             """),
        ]
