from egw.apiendpoint import ApiEndpoint


class SubnetEndpoint(ApiEndpoint):
    wsdl = "soapschemas/EGW/custSoapSubnets/custSoapSubnetsSimple.wsdl"
    location = "/custSoapSubnets/"

    def _check_response(self, response, message=None, success=True, fail=False):
        """Convenience function to check SOAP response and print/return message/data"""
        if response.status == "200":
            if message:
                print(message)
            return success
        print("\n".join(response.errorReturned))
        return fail

    def get(self, erl_id):
        """Retrieve all subnets for a given ERL from EGW database"""
        args = {
            "authentication": {**self.args},
            "subnetIdent": {"erl_id": erl_id},
        }
        response = self.client.service.qrySubnetRequest(args)
        if response.status == "404" and response.errorReturned[0].startswith(
            "Subnet not found"
        ):
            return False
        return self._check_response(response, success=response.subnetList[0])

    def set(self, entry):
        """Update subnets in EGW database for a given ERL"""
        if db := self.get(entry.subnetIdent):
            if self.compare(entry, db):
                return True
            if not self.delete(entry.subnetIdent):
                return False
        args = {
            "authentication": {**self.args},
            "subnet": {
                "subnetIdent": {"erl_id": entry.subnetIdent},
                "subnetMaskList": entry.subnetMaskList,
            },
        }
        return self._check_response(
            self.client.service.addOrUpdateSubnetRequest(args),
            message=f"updated {entry.subnetIdent}",
        )

    def delete(self, erl_id):
        """Delete all subnets for an ERL in the EGW database"""
        args = {
            "authentication": {**self.args},
            "subnetIdent": {"erl_id": erl_id},
        }
        return self._check_response(self.client.service.deleteSubnetRequest(args))

    def from_dict(self, data):
        entry = self.client.factory.create("ns0:subnet")
        entry.subnetIdent = data["erl_id"]
        for prefix in data["subnet"].split(","):
            subnet = self.client.factory.create("ns0:subnetMask")
            subnet.subnetMaskIP, subnet.subnetMaskNum = prefix.split("/")
            entry.subnetMaskList.append(subnet)
        return entry

    def compare(self, a, b):
        a = {e.subnetMaskIP + "/" + e.subnetMaskNum for e in a.subnetMaskList}
        b = {e.subnetMaskIP + "/" + e.subnetMaskNum for e in b.subnetMaskList}
        return a == b
