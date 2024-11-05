import graph_ql_interactions.graph_ql_functions as gql_queries

card_info_query = gql_queries.open_graph_ql_query_file("findCardInfo.txt")


def get_cards_in_project(org_name="", project_number=""):
    # Note that there should always be at least one page so the pagination is added afterwards
    result = gql_queries.run_query(card_info_query.
                                   replace("<ORG_NAME>", org_name).
                                   replace("<PROJ_NUM>", str(project_number)).
                                   replace("<AFTER>", "null"))
    has_next_page = result["data"]["organization"]["projectV2"]["items"]["pageInfo"]["hasNextPage"]
    cards_in_project = []
    for node in result["data"]["organization"]["projectV2"]["items"]["nodes"]:
        cards_in_project.append(node)
    # Add items from any further pages
    while has_next_page:
        end_cursor = result["data"]["organization"]["projectV2"]["items"]["pageInfo"]["endCursor"]
        result = gql_queries.run_query(card_info_query.
                                       replace("<ORG_NAME>", org_name).
                                       replace("<PROJ_NUM>", str(project_number)).
                                       replace("<AFTER>", "\"" + end_cursor + "\""))
        has_next_page = result["data"]["organization"]["projectV2"]["items"]["pageInfo"]["hasNextPage"]
        for node in result["data"]["organization"]["projectV2"]["items"]["nodes"]:
            cards_in_project.append(node)

    return cards_in_project


def get_cards_in_sprint(org_name="", project_number="", sprint=""):
    cards_in_project = get_cards_in_project(org_name=org_name, project_number=project_number)

    # Get the cards in this sprint
    cards_in_sprint = []
    for card in cards_in_project:
        # Split to a further iterable
        field_values = card["fieldValues"]["nodes"]
        for value in field_values:
            try:
                if value["field"]["name"] == "Sprint" and value["name"] == sprint:
                    # Get rid of empty values
                    cards_in_sprint.append([i for i in field_values if i])
            except KeyError:
                # Section is empty ignore it
                pass

    return cards_in_sprint
