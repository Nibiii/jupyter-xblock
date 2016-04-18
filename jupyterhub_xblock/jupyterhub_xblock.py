import json
from django.utils.translation import ugettext
import pkg_resources

from django.template import Template, Context

from xblock.core import XBlock
from xblock.exceptions import JsonHandlerError
from xblock.fields import Scope, String, Integer, Float, Boolean, List, DateTime, JSONField
from xblock.fragment import Fragment
from xblock.validation import Validation
from xblockutils.studio_editable import StudioEditableXBlockMixin, FutureFields
from xmodule.x_module import XModuleMixin

import requests

#@Auth.needs_auth_token
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

    editable_fields = ('display_name', 'file_noteBook')

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

    def studio_view(self, context):
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

    def create_jupyterhub_user(self, username):
        base_url = "http://10.0.2.2:8081/%s"
        headers = self.get_headers()
        api_endpoint = "hub/api/users"
        response = None
        url = base_url % api_endpoint
        payload = {"admin":False,"usernames":[username]}
        try:
            # TODO check for auth-403 alreadystarted-400 doesntexist-404
            response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
            return True
        except requests.exceptions.RequestException as e:
            print("[edx_xblock_jupyter] ERROR : %s " % e)
            return False

    def student_view(self, context=None):
        # X block user details
        user_service = self.runtime.service(self, 'user')
        xb_user = user_service.get_current_user()
        username = xb_user.opt_attrs.get('edx-platform.username')

        if username is None:
            print("HTTP ERROR 404 User not found")

        # create user
        if not self.create_jupyterhub_user(username):
            print("Throw an error here")
        # Start the user server if not started
        self.start_user_server(username)
        # try and upload the course unit ipynb if it doesn't exist

        user_cookie = self.access_user_server(username)
        if user_cookie is None:
            print("Throw an error here")
        # NB TODO log user in - how a session maintained? Perhaps use Oauth
        # Check the user exists - and create if not

        context = {
            'self': self,
            'user_is_staff': self.runtime.user_is_staff,
            'current_url_resource': self.get_current_url_resource(username)
        }
        template = self.render_template("static/html/jupyterhub_xblock.html", context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/jupyterhub_xblock.css"))
        frag.add_javascript(self.resource_string("static/js/src/jupyterhub_xblock.js"))
        frag.initialize_js('JupyterhubXBlock')
        return frag

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
            return {'Cookie':response.headers.pop('set-cookie')}
        except requests.exceptions.RequestException as e:
            print("[edx_xblock_jupyter] ERROR : %s " % e)
            return None

    def get_unit_notebook(self):
        """
        Returns the Notebook file associated with this unit for upload to the
        user's Notebook server.
        """
        return "Welcome%20to%20Python.ipynb"

    def get_current_url_resource(self, username):
        notebook = self.get_unit_notebook()
        url = "http://127.0.0.1:8880/user/%s/notebooks/%s" % (username, notebook)
        return url

    @needs_authorization_header
    def get_headers(self):
        headers = {
            'referer': "0.0.0.0:8081/hub/",
            'content-type': "application/json"
            }
        return headers

    def start_user_server(self, username):
        """
        Starts the user server for handling Notebooks
        TODO set base url correctly.
        """
        base_url = "http://10.0.2.2:8081/%s"
        headers = self.get_headers()
        api_endpoint = "hub/api/users/%s/server" % username
        response = None
        url = base_url % api_endpoint
        try:
            # TODO check for auth-403 alreadystarted-400 doesntexist-404
            response = requests.request("POST", url, headers=headers)
            return True
        except requests.exceptions.RequestException as e:
            print("[edx_xblock_jupyter] ERROR : %s " % e)
            return False


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
