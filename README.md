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
- Endpoints

The Endpoints API only implements identifying endpoints by IP PBX
extension, not via MAC or IP address.  The other services, Layer2 3rd
Party and WLAN, are currently not implemented.

## Common methods

Each SOAP API endpoint is mapped to a python API class attribute:

- `api.locations`
- `api.switches`
- `api.subnets`
- `api.endpoints`

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

See the [EGW System Guide](docs/EGW%205.6%20System%20Guide.pdf) for field definitions.

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

Field names for endpoints:

```csv
operation;pbx_name;endpoint;mac;erl_id;ip;description
```

Note that, unlike the others, the batch import format for endpoints on
the EGW (and for `pyegw`) is a semicolon-delimited `.txt` file.

Example import:

```python
from egw import api
from csv import DictReader

egw = api("egw-a.example.com", "user", "pass")

with open("switches.csv") as f:
    entries = [egw.switches.from_dict(record) for record in DictReader(f)]
```

### compare()

Test if two objects are identical or differ.  Useful to determine if
updates to the EGW are required.

## Endpoint-specific methods

### locations

#### get_single()

`locations.get(ERL)` is a substring match on ERL_IDs. `get_single(ERL)`
will search for an exact match.

### switches

#### get_all()

`switches.get(IP)` typically matches only a single entry in the
database, but the actual backend query is an SQL LIKE expression.
This is a convenience method to call `get("%")`, returning all entries.

#### get_single()

`locations.get(IP)` is a substring match on switch IP. `get_single(IP)`
will search for an exact match.

#### delete_remaining()

The `get/set/compare/delete` methods, by default, maintain a local
cache of EGW objects.  This method will delete from the EGW any entries
remaining in the cache.

**NOTE** this deletes data.  Please ensure that all objects have been
either `compare`d, `delete`d, or `set` before calling this method.
