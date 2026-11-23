import graph_ql_interactions.github_request_functions as gql_queries

proj_list_query = gql_queries.open_graph_ql_query_file("findProjects.txt")
sprint_list_id_query = gql_queries.open_graph_ql_query_file("findProjectSprints.txt")


def get_projects(org_name: str = ""):
    return gql_queries.run_query(proj_list_query.replace("<ORG_NAME>", org_name))["data"][
        "organization"
    ]["projectsV2"]["nodes"]


def get_project_field_list(project_number: int, org_name: str = ""):
    return gql_queries.run_query(
        sprint_list_id_query.replace("<PROJ_NUM>", str(project_number)).replace(
            "<ORG_NAME>", org_name
        )
    )["data"]["organization"]["projectV2"]["fields"]["nodes"]
