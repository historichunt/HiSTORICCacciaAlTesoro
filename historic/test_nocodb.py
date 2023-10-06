from nocodb.nocodb import NocoDBProject, APIToken, JWTAuthToken
# from nocodb.filters import LikeFilter, EqFilter, And
from nocodb.infra.requests_client import NocoDBRequestsClient

def test():

    # Usage with API Token
    client = NocoDBRequestsClient(
            # Your API Token retrieved from NocoDB conf
            APIToken("9ZIQs45jUCEJnO1JbyWUnEcYKApan08pp5LMl-6W"),
            # Your nocodb root path
            "http://localhost:8080"
    )

    # Be very carefull with org, project_name and table names
    # weird errors from nocodb can arrive if they are wrong
    # example: id is not defined...
    # probably they will fix that in a future release.
    project = NocoDBProject(
            "noco", # org name. noco by default
            "Getting Started" # project name. Case sensitive!!
    )

    table_name = "test"

    # Retrieve a page of rows from a table
    table_rows = client.table_row_list(project, table_name)

    print(table_rows)



if __name__ == "__main__":
    test()