import threading
import urllib

class CresponseMiddleware(object):

    _response = {}
    _auth_token = {}

    @classmethod
    def get_response(cls, default=None):
        """
        Retrieve request
        """
        return cls._response.get(threading.current_thread(), default)

    def process_response(self, request, response):
        """
        Retrieve request
        """
        response.set_cookie('sifu_authorization', urllib.quote_plus(self._auth_token))
        return response
