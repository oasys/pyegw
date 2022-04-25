from copy import copy
from copy import deepcopy

from egw.apiendpoint import ApiEndpoint


class LocationEndpoint(ApiEndpoint):
    wsdl = "soapschemas/EGW/custSoapLocationsV2/custSoapLocations.wsdl"
    location = "/custSoapLocationsV2/"

    def get(self, erl_id="*"):
        args = self.args | dict(QueryLocationEntry=dict(erl_id=erl_id))
        response = self.client.service.qryLocationByMatchingERLIDRequest(args)
        if response.status != 1:
            return []
        for location in response.LocationCollection.LocationEntry:
            if location.civicAddress.STS:
                location.civicAddress.RD += " " + location.civicAddress.STS
                location.civicAddress.STS = None
            yield location

    def get_single(self, erl_id):
        exact_match = [l for l in self.get(erl_id=erl_id) if l.erl_id == erl_id]
        if len(exact_match) == 1:
            return exact_match[0]

    def set(self, data):
        args = self.args.copy()
        del data.location_id
        del data.location_last_updated
        for field, _ in data:
            if field == "civicAddress":
                civic_address = {}
                for field, _ in data.civicAddress:
                    civic_address |= {field: data.civicAddress[field]}
                args |= dict(civicAddress=civic_address)
            elif field == "crisis_alert_email":
                args |= {"crisis_email_list": data[field]}
            else:
                args |= {field: data[field]}
        response = self.client.service.addOrUpdateLocationRequest(args)
        if response.status:
            print(response.errorReturned)
        return not response.status

    def delete(self, erl_id):
        args = self.args.copy()
        args |= dict(erl_id=erl_id)
        response = self.client.service.deleteLocationRequest(args)
        if response.status:
            print(response.errorReturned)
        return not response.status

    def from_dict(self, data):
        csv_field = {
            # API field name : CSV field name
            "security_desk_name": "security_desk",
            "crisis_alert_email": "crisis_email",
        }

        location = self.client.factory.create("ns0:LocationInfo")

        # defaults
        location.local_gateway_enabled = "0"
        location.direct_call_delivery = "0"
        location.wireless_locator_enabled = "0"
        del location.security_desk_phone
        del location.elins

        for k, _ in self.client.items(location):
            field = csv_field.get(k, k)
            if field in data:
                setattr(location, k, str(data[field]))

        location.civicAddress = self.client.factory.create("ns0:civicAddress")
        for k, _ in self.client.items(location.civicAddress):
            field = csv_field.get(k, k)
            if field in data:
                setattr(location.civicAddress, k, str(data[field]))

        return location

    def compare(self, a, b):
        if a is None or b is None:
            return False

        # elide fields we don't want to compare
        a, b = deepcopy(a), deepcopy(b)
        a.location_id = None
        b.location_id = None
        a.location_last_updated = None
        b.location_last_updated = None

        return self._deep_compare(a, b)
