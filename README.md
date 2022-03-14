# pyegw

Python API client library for the [Intrado][intrado] [Emergency Gateway][egw].

Provides a native python interface for interacting with the EGW's
SOAP API endpoints to enable automatic updating/synchronizing network
topology information.

[intrado]: https://www.intrado.com/
[egw]: https://www.intrado.com/en/safety-services/public-safety/e911-large-enterprise

## Features

- Locations / ERLs
- Switches and Ports
- Subnets

The other services, Endpoints (Analog and PBX), Layer2 3rd Party, and
WLAN), are currently not implemented.

## Common methods

Each SOAP API endpoint is mapped to a python API class attribute:

- `api.locations`
- `api.switches`
- `api.subnets`

For consistency, these have a set of common methods.

### get()

Retrieves one (or multiple) records from the EGW database that match the
calling criteria.

### set()

Adds or updates a single entry in the EGW database.

### delete()

Deletes a matching entry in the EGW database.

### from_dict()

Creates a local object corresponding to its endpoint subclass, assigning
values from a provided dictionary.  The mapping of dictionary keys to object
attributes is compatible with the native EGW CSV import/export file format.

Field names for ERLs/Locations:

```csv
operation,erl_id,HNO,RD,LOC,A3,A1,country,PC,NAM,security_desk,crisis_email,url_data
```

Field names for switches/ports:

```csv
switch_ip,snmp_community,description,erl_id,port_name,is_scan,switch_type
```

Field names for subnets:

```csv
operation,erl_id,subnet
```

Example import:

```python
from egw import api
from csv import DictReader

egw = api("egw-a.example.com", "user", "pass")

with open("switches.csv") as f:
    entries = [egw.switches.from_dict(record) for record in DictReader(f)]
```
