import logging
import ssl
from copy import copy
from copy import deepcopy
from dataclasses import dataclass
from urllib.parse import quote
from urllib.parse import quote_plus
from urllib.parse import unquote

from rich import print
from suds.client import Client


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


class SubnetEndpoint(Endpoint):
    wsdl = "soapschemas/EGW/custSoapSubnets/custSoapSubnetsSimple.wsdl"
    location = "/custSoapSubnets/"

    def get(self, erl_id, silent=False):
        args = {
            "authentication": {**self.args},
            "subnetIdent": {"erl_id": erl_id},
        }
        response = self.client.service.qrySubnetRequest(args)
        if response.status != 200:
            if not silent:
                print("\n".join(response.errorReturned))
            return []
        return response.subnetList

    def set(self):
        args = {
            "authentication": {**self.args},
            "subnetIdent": {"erl_id": erl_id},
        }

        pass

    def from_dict(self, data):
        entry = self.client.factory.create("ns0:subnet")
        entry.subnetIdent = data["erl_id"]
        for prefix in data["subnet"].split(","):
            subnet = self.client.factory.create("ns0:subnetMask")
            subnet.subnetMaskIP, subnet.subnetMaskNum = prefix.split("/")
            entry.subnetMaskList.append(subnet)

        return entry

    def compare(self, data):
        pass


class SwitchEndpoint(Endpoint):
    wsdl = "soapschemas/EGW/custSoapSwitches/custSoapSwitches.wsdl"
    location = "/custSoapSwitches/"
    _all_entries = "UNINITIALIZED"

    def _load_all_entries(self):
        """Build local cache of all entries in EGW database"""
        if self._all_entries == "UNINITIALIZED":
            self._all_entries = self.get_all()

    def _check_response(self, response, field=None, silent=False):
        if response.Response.Status != "200":
            if not silent:
                print("\n".join(response.Response.ErrorMessage))
        if field:
            obj = response
            for each in field.split("."):
                try:
                    obj = getattr(obj, each)
                except AttributeError:
                    return []
            return obj
        else:
            return response.Response.Status == "200"

    def compare(self, data, remove_on_match=True):
        is_switch_entry = getattr(data, "port_entry", []) == []
        self._load_all_entries()
        match = None

        for switch in self._all_entries:
            if switch.switch_ip == data.switch_ip:
                if is_switch_entry:
                    match = all([switch[k] == v for k, v in data])
                    if match and remove_on_match:
                        self.remove_entry(switch.switch_ip)
                else:
                    port_name = data.port_entry.switch_port_name
                    for port in getattr(switch, "port_entry", []):
                        # CSV import in web GUI capitalizes all port names
                        if port_name.lower() == port.switch_port_name.lower():
                            match = all(
                                [
                                    port[k] == v
                                    for k, v in data.port_entry
                                    if k != "switch_port_name"
                                ]
                                + [
                                    port[k].lower() == v.lower()
                                    for k, v in data.port_entry
                                    if k == "switch_port_name"
                                ]
                            )
                            if match and remove_on_match:
                                self.remove_entry(switch.switch_ip, port_name)
        return match

    def remove_entry(self, switch_ip, port_name=None):
        """Remove port or switch entry from local cache"""
        self._load_all_entries()
        for switch in self._all_entries:
            if switch.switch_ip == switch_ip:
                if port_name:
                    for port in switch.port_entry:
                        if port_name.lower() == port.switch_port_name.lower():
                            switch.port_entry.remove(port)
                if len(switch.port_entry) == 0:
                    self._all_entries.remove(switch)

    def get_single(self, switch_ip, *args, **kwargs):
        """Return switch by exact match on switch IP address"""
        exact_match = [
            sw
            for sw in self.get(switch_ip, *args, **kwargs)
            if sw.switch_ip == switch_ip
        ]
        if len(exact_match) == 1:
            return exact_match[0]

    def get_all(self):
        """Retrieve all switches (and their ports) from EGW database"""
        return self.get("%")

    def get(self, switch_ip, silent=False):
        """Retrieve specific switch (and its ports) from EGW database"""
        switches = []
        args = {
            "Authentication": {k.capitalize(): v for k, v in self.args.items()},
            "QuerySwitchEntry": {
                "SwitchIpOrERLCombination": {"switch_ip": switch_ip},
            },
        }

        curr_switch_id = 0
        while True:  # handle paging
            args["QuerySwitchEntry"]["switch_id"] = curr_switch_id
            response = self.client.service.querySwitchRequest(args)
            if response.Response.Status != "200":
                if not silent:
                    print("\n".join(response.Response.ErrorMessage))
                return []
            switches += response.SwitchCollection.SwitchEntry
            curr_switch_id = response.SwitchStatistics.HighestSwitchIDReturned + 1
            stats = response.SwitchStatistics
            if stats.TotalNumberOfSwitches - stats.CountOfSwitchesReturned == 0:
                break

        return switches

    def set(self, data, remove_on_update=True):
        """Add or Update port/switch entry in EGW database"""
        is_switch_entry = getattr(data, "port_entry", []) == []
        is_new_switch = is_switch_entry and not self.get_single(
            data.switch_ip, silent=True
        )
        entry_type = "AddSwitchEntry" if is_new_switch else "UpdateSwitchEntry"
        args = {
            "Authentication": {k.capitalize(): v for k, v in self.args.items()},
            entry_type: {
                k: v
                for k, v in data
                if is_switch_entry or k in ("switch_ip", "port_entry")
            },
        }

        request = getattr(
            self.client.service,
            "addSwitchRequest" if is_new_switch else "updateSwitchRequest",
        )
        if result := self._check_response(request(args)) and remove_on_update:
            self.remove_entry(data)
        if result:
            print(f"switch {data.switch_ip} {'added' if is_new_switch else 'updated'}")
        return result

    def delete(
        self, switch_ip, port_name=None, remove_from_all_entries=True, force=False
    ):
        if port_name and not force:
            # only delete switch if it has no ports
            # TODO look up in cache instead
            if len(getattr(self.get_single(switch_ip), "port_entry", [])) == 0:
                return self.delete(switch_ip, force=True)
            # NOP if switch has ports (will be deleted when last port is deleted)
            return True

        port_criteria = {"switch_port_name": port_name} if port_name else {}
        args = {
            "Authentication": {k.capitalize(): v for k, v in self.args.items()},
            "DeleteSwitchEntry": {
                "switch_port_combination": {"switch_ip": switch_ip} | port_criteria
            },
        }
        if (
            result := self._check_response(
                self.client.service.deleteSwitchRequest(args)
            )
            and remove_from_all_entries
        ):
            self.remove_entry(switch_ip, port_name)
        if (
            port_name
            and len(getattr(self.get_single(switch_ip), "port_entry", [])) == 0
        ):
            # if we just deleted the last port, also delete the switch
            return result and self.delete(switch_ip, force=True)
        return result

    def delete_remaining(self):
        for switch in self._all_entries:
            if len(getattr(switch, "port_entry")) > 0:
                for port in getattr(switch, "port_entry", []):
                    if result := self.delete(switch.switch_ip, port.switch_port_name):
                        print(
                            f"deleted {port.switch_port_name} on switch {switch.switch_ip}"
                        )
            else:
                if result := self.delete(switch.switch_ip):
                    print(f"deleted switch {switch.switch_ip}")

    def from_dict(self, data):
        is_switch_entry = data.get("port_name") == "*"
        csv_field = {
            # API field name : CSV field name
            "log_level": "logging_level",
            "switch_port_name": "port_name",
            "switch_port_erl": "erl_id",
            "switch_erl": "erl_id",
            "switch_description": "description",
        }

        record = self.client.factory.create("ns0:SwitchAddUpdateEntry")
        for k, _ in self.client.items(record):
            field = csv_field.get(k, k)
            if field in data:
                if field == "switch_type":
                    record[k] = data[field].removesuffix(".js")
                else:
                    setattr(record, k, str(data[field]))
            else:
                delattr(record, k)

        if not is_switch_entry:
            record.port_entry = self.client.factory.create("ns0:PortEntry")
            record.port_entry.is_trunk_port = "no"  # set default
            for k, _ in self.client.items(record.port_entry):
                field = csv_field.get(k, k)
                if field in data:
                    setattr(record.port_entry, k, str(data[field]))

        return record


class LocationEndpoint(Endpoint):
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
            "erl_id": "ERL_ID",
            "security_desk_name": "SECURITY_DESK",
            "crisis_alert_email": "CRISIS_EMAIL",
            "url_data": "URL_DATA",
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
