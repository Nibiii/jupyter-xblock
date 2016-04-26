import json
from django.utils.translation import ugettext
import pkg_resources

from django.template import Template, Context, RequestContext

#from django.core.context_processors import request
#from xblock.django.request import DjangoWebobRequest
from crequest.middleware import CrequestMiddleware

from xblock.core import XBlock
from xblock.exceptions import JsonHandlerError
from xblock.fields import Scope, String, Integer, Float, Boolean, List, DateTime, JSONField
from xblock.fragment import Fragment
from xblock.validation import Validation
from xblockutils.studio_editable import StudioEditableXBlockMixin, FutureFields
from xmodule.x_module import XModuleMixin

from django.utils.encoding import iri_to_uri
from django.http import HttpResponse

from django.middleware import csrf

import urllib

import requests

@XBlock.needs('request')
@XBlock.needs('user')
class JupyterhubXBlock(StudioEditableXBlockMixin, XBlock):

    display_name = String(
        display_name="Display Name",
        help="Display name for this module",
        default="Jupyterhub",
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

    def needs_authorization_header(func):
        """
        Maybe put this into its own Auth class singleton
        Decorator to make sure API calls are authorized
        """
        def function_wrapper(self):
            auth = func(self)
            auth.update({"Authorization":"token 73295e78f9d24677a80bf72edfe071b2"})
            return auth
        return function_wrapper

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
        fragment.add_css(self.resource_string("static/css/jupyterhub_xblock.css"))
        fragment.add_javascript(self.resource_string("static/js/src/studio_edit.js"))
        fragment.initialize_js('JupyterhubStudioEditableXBlock')
        return fragment

    def student_view(self, context=None, request=None):
        if not self.runtime.user_is_staff:
            user_service = self.runtime.service(self, 'user')
            xb_user = user_service.get_current_user()
            username = xb_user.opt_attrs.get('edx-platform.username')
            if username is None:
                print("HTTP ERROR 404 User not found")

            # get the course details
            course_unit_name = str(self.course_unit)
            resource = str(self.file_noteBook)

            cr = CrequestMiddleware.get_request()
            token = csrf.get_token(cr)
            sessionid = cr.session.session_key

            # make api to get grant
            headers = {
                 "Host":"0.0.0.0:8000",
                 "X-CSRFToken":token,
                 "Referer":"http://0.0.0.0:8000",
                 "Cookie": "djdt=hide; edxloggedin=true; csrftoken=%s; sessionid=%s" % (token, sessionid)
            }
            sifu_id = "cab1f254be91128c28a0"
            state = "3835662"
            base_url = "http://0.0.0.0:8000"
            url = "%s/oauth2/authorize/?client_id=%s&state=%s&redirect_uri=http://0.0.0.0:8000&response_type=code" % (base_url,sifu_id,state)
            auth_grant = None
            print(url)
            try:
                resp = requests.request("GET", url, headers=headers, allow_redirects=False)
                print(resp.headers)
                resp = requests.request("GET", resp.headers['location'],headers=headers, allow_redirects=False)
                print(resp.headers)
                resp = requests.request("GET", resp.headers['location'],headers=headers, allow_redirects=False)
                print(resp.headers)
                resp = requests.request("GET", resp.headers['location'],headers=headers, allow_redirects=False)
                print(resp.headers)
                # to delete post http://0.0.0.0:8000/admin/oauth2/grant/
                # csrfmiddlewaretoken=dZXgCmUiBMTwfjwFZ702h8pg5O0ZkktA&_selected_action=32&action=delete_selected&post=yes
                # as form data
            except requests.exceptions.RequestException as e:
                print(e)
            #check of user notebook & base notebook exists
            if not self.user_notebook_exists(username, course_unit_name, resource):
                print("User notebook does not exist")
                # check the base file exists
                if not self.base_file_exists(course_unit_name, resource):
                    print("Base file definitely does not exist")
                    # create the base file
                    self.create_base_file(course_unit_name, resource)
                # create user notebook assuming the base file exists
                if not self.create_user_notebook(username, course_unit_name, resource):
                    print("Throw an error here")


            context = {
                'self': self,
                'user_is_staff': self.runtime.user_is_staff,
                'current_url_resource': self.get_current_url_resource(username, course_unit_name, resource),
            }
        else:
            context = {
                'self': self,
                'user_is_staff': self.runtime.user_is_staff,
                'current_url_resource': None,
            }
        template = self.render_template("static/html/jupyterhub_xblock.html", context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/jupyterhub_xblock.css"))
        frag.add_javascript(self.resource_string("static/js/src/jupyterhub_xblock.js"))
        frag.initialize_js('JupyterhubXBlock')
        return frag

    def user_notebook_exists(self, username, course_unit_name, resource):
        """
        Tests to see if user notebook exists
        """
        headers = self.get_headers()
        payload = {"notey_notey":{"username":username,"course":course_unit_name,"file":resource}}
        try:
            resp = requests.request("GET", "http://10.0.2.2:3334/v1/api/notebooks/users/courses/files", data=json.dumps(payload), headers=headers)
            resp = resp.json()
            return resp["result"]
        except requests.exceptions.RequestException as e:
            print(e)
            return False

    def get_xblock_notebook(self):
        """
        Gets the uploaded notebook from studio
        """
        try:
            resp = requests.request("GET", "http://0.0.0.0:8001/%s" % self.file_noteBook)
            return resp.content
        except requests.exceptions.RequestException as e:
            print(e)
            return False

    def base_file_exists(self, course_unit_name, resource):
        base_url = "http://10.0.2.2:3334/%s"
        headers = self.get_headers()
        api_endpoint = "v1/api/notebooks/courses/files/"
        response = None
        url = base_url % api_endpoint
        payload = {"notey_notey":{"course":course_unit_name,"file":resource}}
        try:
            # TODO check for auth-403 alreadystarted-400 doesntexist-404
            resp = requests.request("GET", url, data=json.dumps(payload), headers=headers)
            resp = resp.json()
            return resp["result"]
        except requests.exceptions.RequestException as e:
            print("[edx_xblock_jupyter] ERROR : %s " % e)
            return False

    def create_base_file(self, course_unit_name, resource):
        base_url = "http://10.0.2.2:3334/%s"
        headers = self.get_headers()
        api_endpoint = "v1/api/notebooks/courses/files/"
        response = None
        url = base_url % api_endpoint
        loaded_file = self.get_xblock_notebook()
        payload = {"notey_notey":{"course":course_unit_name,"file":resource,"data":loaded_file}}
        try:
            # TODO check for auth-403 alreadystarted-400 doesntexist-404
            response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
            return True
        except requests.exceptions.RequestException as e:
            print("[edx_xblock_jupyter] ERROR : %s " % e)
            return False

    def create_user_notebook(self, username, course_unit_name, resource):
        base_url = "http://10.0.2.2:3334/%s"
        headers = self.get_headers()
        api_endpoint = "v1/api/notebooks/users/courses/files/"
        response = None
        url = base_url % api_endpoint
        payload = {"notey_notey":{"username":username,"course":course_unit_name,"file":resource}}
        try:
            # TODO check for auth-403 alreadystarted-400 doesntexist-404
            response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
            return True
        except requests.exceptions.RequestException as e:
            print("[edx_xblock_jupyter] ERROR : %s " % e)
            return False

    def access_user_server(self, username):
        """
        Return an authentication cookie associated with the user
        """
        base_url = "http://10.0.2.2:8081/%s"
        headers = self.get_headers()
        api_endpoint = "hub/api/users/%s/admin-access" % username
        response = None
        url = base_url % api_endpoint
        try:
            # TODO check for
            response = requests.request("POST", url, headers=headers)
            return response.headers.pop('set-cookie')
        except requests.exceptions.RequestException as e:
            print("[edx_xblock_jupyter] ERROR : %s " % e)
            return None

    def get_current_url_resource(self, username, course, filename):
        """
        Returns the url for the API call to fetch a notebook
        """
        params = (urllib.quote(username), urllib.quote(course), urllib.quote(filename))
        url = "http://0.0.0.0:3334/v1/api/notebooks/users/%s/courses/%s/files/%s" % params
        return url

    @needs_authorization_header
    def get_headers(self):
        headers = {
            'referer': "0.0.0.0:8081/hub/",
            'content-type': "application/json"
            }
        return headers

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

    def _make_field_info(self, field_name, field):
        info = super(JupyterhubXBlock, self)._make_field_info(field_name, field)
        if field_name == 'file_noteBook':
            info['type'] = 'file_uploader'
        return info

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("JupyterhubXBlock",
             """<vertical_demo>
                <jupyterhub_xblock/>
                </vertical_demo>
             """),
        ]
