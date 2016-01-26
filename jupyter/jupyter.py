"""This XBlock is intended to allow to play with Jupyter notebooks"""

import pkg_resources

from xblock.core import XBlock
from xblock.fragment import Fragment


class JupyterXBlock(XBlock):
    """
    XBlock displays JupyterHub page with notebook
    """

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def student_view(self, context=None):
        """
        The primary view of the JupyterXBlock, shown to students
        when viewing courses.
        """
        html = self.resource_string("static/html/jupyter.html")
        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/jupyter.css"))
        frag.add_javascript(self.resource_string("static/js/src/jupyter.js"))
        frag.initialize_js('JupyterXBlock')
        return frag

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("JupyterXBlock",
             """<jupyter/>
             """),
            ("Multiple JupyterXBlock",
             """<vertical_demo>
                <jupyter/>
                </vertical_demo>
             """),
        ]
