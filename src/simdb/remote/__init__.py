"""Remote module.

The remote module contains code for running a REST API which is used to provide a remote
endpoint to which simulations can be sent for staging and signing-off.
"""

# API versions supported by this client, as they appear in the server endpoint URLs.
# Update this when a new API version is added to simdb.remote.apis.
CLIENT_API_VERSIONS = ("v1.2",)


# API constants
class APIConstants:
    LIMIT_HEADER = "simdb-result-limit"
    PAGE_HEADER = "simdb-page"
    SORT_BY_HEADER = "simdb-sort-by"
    SORT_ASC_HEADER = "simdb-sort-asc"
