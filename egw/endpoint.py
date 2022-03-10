import logging
from urllib.parse import quote_plus
from urllib.parse import unquote

from suds.client import Client


class Endpoint(object):
    def __init__(self, api):
        self.api = api
        self.args = dict(username=self.api.user, password=self.api.password)
        self.client = Client(
            self.api.url + self.wsdl,
            location=self.api.url + self.location,
        )
        if self.api.debug:
            logging.basicConfig(level=logging.INFO)
            logging.getLogger("suds.client").setLevel(logging.DEBUG)

    def _deep_compare(self, a, b):
        def normalize(data):
            if hasattr(data, "startswith"):  # is string-like object
                if data.startswith("http"):
                    return quote_plus(unquote(data))  # idempotent url encoding
                return data.lower()
            return data

        return not set(self.client.dict(a)) ^ set(self.client.dict(b)) and all(
            self._deep_compare(v, b[k])
            if hasattr(v, "__keylist__") and hasattr(b[k], "__keylist__")
            else normalize(v) == normalize(b[k])
            for k, v in self.client.items(a)
        )
