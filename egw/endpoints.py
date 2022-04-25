from egw.apiendpoint import ApiEndpoint


class AnalogEndpoint(ApiEndpoint):
    wsdl = "soapschemas/EGW/custSoapEndpointsV2/custSoapEndpoints.wsdl"
    location = "/custSoapEndpointsV2/"

    def _check_response(self, response, message=None, success=True, fail=False):
        """Convenience function to check SOAP response and print/return message/data"""
        if response.status == 0:
            if message:
                print(message)
            return success
        return fail

    def get(self, endpoint, pbx):
        """Retrieve endpoints for a given PBX extension from EGW database"""
        args = self.args | {
            "ip_pbx_name": pbx,
            "endpoint": endpoint,
        }
        response = self.client.service.qryEndpointRequest(args)
        if response.status == -1 and response.errorReturned in (
            "endpoint_or_mac_doesnt_exist",
            "ip_pbx_not_found",
        ):
            return False
        return self._check_response(response, success=response.EndpointInfo[0])

    def set(self, entry):
        """Update single endpoint in the EGW database"""
        entry.username = self.args["username"]
        entry.password = self.args["password"]
        return self._check_response(
            self.client.service.addOrUpdateEndpointRequest(entry),
            message=f"updated {entry.ip_pbx_name} extension {entry.endpoint}",
        )

    def delete(self, entry):
        """Delete single endpoint in the EGW database"""
        entry.username = self.args["username"]
        entry.password = self.args["password"]
        return self._check_response(
            self.client.service.deleteEndpointRequest(entry),
            message=f"deleted {entry.ip_pbx_name} extension {entry.endpoint}",
        )

    def from_dict(self, data):
        entry = self.client.factory.create("ns0:EndpointProvisioning")
        entry.endpoint = data["endpoint"]
        entry.ip_pbx_name = data["pbx_name"]
        entry.erl_id = data["erl_id"]
        entry.display_name = data["description"]
        return entry

    def compare(self, a, b):
        def upper_if_str(val):
            return val.upper() if isinstance(val, str) else val

        fields = (
            "ip_pbx_name",
            "endpoint",
            "mac_address",
            "erl_id",
            "ip_address",
            "display_name",
        )
        return all(
            upper_if_str(getattr(a, field)) == upper_if_str(getattr(b, field, None))
            for field in fields
        )
