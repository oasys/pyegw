import ssl

from egw.endpoints import AnalogEndpoint
from egw.locations import LocationEndpoint
from egw.subnets import SubnetEndpoint
from egw.switches import SwitchEndpoint


class Api(object):
    def __init__(
        self,
        host,
        user,
        password,
        ssl_verify=True,
        debug=False,
    ):
        self.user = user
        self.password = password
        self.url = "https://" + host + "/"
        self.debug = debug

        if not ssl_verify:
            ssl._create_default_https_context = ssl._create_unverified_context

        self.locations = LocationEndpoint(self)
        self.switches = SwitchEndpoint(self)
        self.subnets = SubnetEndpoint(self)
        self.endpoints = AnalogEndpoint(self)
