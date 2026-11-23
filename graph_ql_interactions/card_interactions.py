from collections import Counter
from datetime import datetime

import graph_ql_interactions.github_request_functions as gql_queries
from github_interactions import card_info

card_info_query = gql_queries.open_graph_ql_query_file("findCardInfo.txt")
update_labels = gql_queries.open_graph_ql_query_file("UpdateItemLabel.txt")
remove_label_mutation = gql_queries.open_graph_ql_query_file("RemoveLabel.txt")
set_sprint_mutation = gql_queries.open_graph_ql_query_file("UpdateSprintForItemInProject.txt")
set_points_mutation = gql_queries.open_graph_ql_query_file("UpdatePointsForItemInProject.txt")
get_last_comment_datetime = gql_queries.open_graph_ql_query_file("findIssueInfo.txt")
get_issue_labels_added = gql_queries.open_graph_ql_query_file("findIssueInfo.txt")
get_issue_assignees = gql_queries.open_graph_ql_query_file("findIssueInfo.txt")
get_field_changes = gql_queries.open_graph_ql_query_file("findIssueInfo.txt")


def get_cards_in_project(org_name: str = "", project_number: str = ""):
    # Note that there should always be at least one page so the pagination is added afterwards
    result = gql_queries.run_query(
        card_info_query.replace("<ORG_NAME>", org_name)
        .replace("<PROJ_NUM>", str(project_number))
        .replace("<AFTER>", "null")
    )
    has_next_page = result["data"]["organization"]["projectV2"]["items"]["pageInfo"]["hasNextPage"]
    cards_in_project = []
    for node in result["data"]["organization"]["projectV2"]["items"]["nodes"]:
        cards_in_project.append(card_info.CardInfo(node))
    # Add items from any further pages
    while has_next_page:
        end_cursor = result["data"]["organization"]["projectV2"]["items"]["pageInfo"]["endCursor"]
        result = gql_queries.run_query(
            card_info_query.replace("<ORG_NAME>", org_name)
            .replace("<PROJ_NUM>", str(project_number))
            .replace("<AFTER>", '"' + end_cursor + '"')
        )
        has_next_page = result["data"]["organization"]["projectV2"]["items"]["pageInfo"][
            "hasNextPage"
        ]
        for node in result["data"]["organization"]["projectV2"]["items"]["nodes"]:
            cards_in_project.append(card_info.CardInfo(node))

    return cards_in_project


def get_cards_and_points_snapshot_for_sprint(
    org_name: str = "", project_number: str = "", sprint: str = ""
):
    cards_in_project = get_cards_in_project(org_name=org_name, project_number=project_number)
    snapshot = {
        "ready": {"count": 0, "points": 0},
        "rework": {"count": 0, "points": 0},
        "in_progress": {"count": 0, "points": 0},
        "impeded": {"count": 0, "points": 0},
        "review": {"count": 0, "points": 0},
        "done": {"count": 0, "points": 0},
    }
    for card in cards_in_project:
        if card.sprint == sprint:
            match card.status:
                case "Backlog":
                    snapshot["ready"]["count"] += 1
                    snapshot["ready"]["points"] += card.points
                    if "rework" in card.labels:
                        snapshot["rework"]["count"] += 1
                        snapshot["rework"]["points"] += card.points
                case "In Progress":
                    snapshot["in_progress"]["count"] += 1
                    snapshot["in_progress"]["points"] += card.points
                case "Impeded":
                    snapshot["impeded"]["count"] += 1
                    snapshot["impeded"]["points"] += card.points
                case "Review":
                    snapshot["review"]["count"] += 1
                    snapshot["review"]["points"] += card.points
                case "Done":
                    snapshot["done"]["count"] += 1
                    snapshot["done"]["points"] += card.points
                case _:
                    # This is not a status I'm interested in, and probably shouldn't exist
                    pass

    return snapshot


def get_cards_in_sprint(org_name: str = "", project_number: str = "", sprint: str = ""):
    cards_in_project = get_cards_in_project(org_name=org_name, project_number=project_number)
    cards_in_sprint = []
    for card in cards_in_project:
        if card.sprint == sprint:
            cards_in_sprint.append(card)
    return cards_in_sprint


def get_card_list_snapshot_for_sprint(
    org_name: str = "", project_number: str = "", sprint: str = ""
):
    snapshot = {
        "ready": [],
        "rework": [],
        "in_progress": [],
        "impeded": [],
        "review": [],
        "done": [],
    }
    for card in get_cards_in_sprint(
        org_name=org_name, project_number=project_number, sprint=sprint
    ):
        match card.status:
            case "Backlog":
                snapshot["ready"].append({"number": card.number, "repo": card.repo})
                if "rework" in card.labels:
                    snapshot["rework"].append({"number": card.number, "repo": card.repo})
            case "In Progress":
                snapshot["in_progress"].append({"number": card.number, "repo": card.repo})
            case "Impeded":
                snapshot["impeded"].append({"number": card.number, "repo": card.repo})
            case "Review":
                snapshot["review"].append({"number": card.number, "repo": card.repo})
            case "Done":
                snapshot["done"].append({"number": card.number, "repo": card.repo})
            case _:
                # This is not a status I'm interested in, and probably shouldn't exist
                pass
    return snapshot


def get_planning_snapshot(org_name: str = "", project_number: str = "", sprint: str = ""):
    cards_in_project = get_cards_in_project(org_name=org_name, project_number=project_number)
    snapshot = {
        "high": [],
        "medium": [],
        "low": [],
    }
    for card in cards_in_project:
        if card.sprint == sprint:
            try:
                match card.priority:
                    case "High":
                        snapshot["high"].append({"number": card.number, "repo": card.repo})
                    case "Medium":
                        snapshot["medium"].append({"number": card.number, "repo": card.repo})
                    case "Low":
                        snapshot["low"].append({"number": card.number, "repo": card.repo})
                    case _:
                        # This is not a status I'm interested in, and probably shouldn't exist
                        pass
            except AttributeError:
                pass
    return snapshot


def get_number_of_cards_by_status(org_name: str = "", project_number: str = "", sprint: str = ""):
    cards_in_project = get_cards_in_project(org_name=org_name, project_number=project_number)
    card_statuses = []
    for card in cards_in_project:
        if card.sprint == sprint:
            card_statuses.append(card.status)
    return Counter(card_statuses)


def get_card_issue_ids_in_sprint(org_name: str = "", project_number: str = "", sprint: str = ""):
    cards_in_project = get_cards_in_project(org_name=org_name, project_number=project_number)

    # Get the cards in this sprint
    cards_in_sprint = []
    for card in cards_in_project:
        if card.sprint == sprint and card.type == "ISSUE":
            cards_in_sprint.append(card.id)

    return cards_in_sprint


def add_label(issue_id: str, label_id_to_add: str):
    gql_queries.run_query(
        update_labels.replace("<ISSUE>", issue_id).replace("<LABEL_ID>", label_id_to_add)
    )


def remove_label(issue_id: str, label_id_to_remove: str):
    if label_id_to_remove == "NONE_NONE":
        print("NONE_NONE Found")
        # This magic string should be removed, but not all repos on a board necessarily
        # have the labels being looked for, this is a default until those checks are in place
        return
    gql_queries.run_query(
        remove_label_mutation.replace("<ISSUE>", issue_id).replace("<LABEL_ID>", label_id_to_remove)
    )


def get_when_last_commented_created_on_issue(issue_id: str):
    try:
        last_comment_datetime = gql_queries.run_query(
            get_last_comment_datetime.replace("<ISSUE>", issue_id)
        )["data"]["node"]["comments"]["nodes"][0]["createdAt"]
    except (TypeError, IndexError):
        last_comment_datetime = datetime.today().strftime("%Y-%m-%dT%H:%M:%SZ")
    return last_comment_datetime


def get_when_labels_were_added_to_issue(issue_id: str):
    response = gql_queries.run_query(get_issue_labels_added.replace("<ISSUE>", issue_id))
    try:
        labels = response["data"]["node"]["labels"]["nodes"]
        labels_timeline = response["data"]["node"]["timelineItems"]["edges"]
    except KeyError:
        labels = []
        labels_timeline = []
    labels_timeline.reverse()
    label_added = {}
    for label in labels:
        for timeline_item in labels_timeline:
            timeline_label_name = timeline_item["node"]["label"]["name"]
            if timeline_label_name == label["name"]:
                label_added[label["name"]] = timeline_item["node"]["createdAt"]
                break
    return label_added


def get_assignees(issue_id: str):
    response = gql_queries.run_query(get_issue_assignees.replace("<ISSUE>", issue_id))
    try:
        assignees = response["data"]["node"]["assignees"]["edges"]
    except KeyError:
        assignees = []
    assignee_names = []
    for assignee in assignees:
        assignee_names.append(assignee["node"]["name"])
    return assignee_names


def get_when_specified_project_field_was_last_changed(issue_id: str, field_value: str):
    field_values = gql_queries.run_query(get_field_changes.replace("<ISSUE>", issue_id))["data"][
        "node"
    ]["projectItems"]["nodes"][0]["fieldValues"]["nodes"]
    status_changed_date = datetime.today()
    for value in field_values:
        if value:
            if value["name"] == field_value:
                status_changed_date = datetime.strptime(value["createdAt"], "%Y-%m-%dT%H:%M:%SZ")
                continue
    return status_changed_date


def set_sprint(item_id: str, sprint_field_id: str, sprint_to_use: str, project_id: str):
    gql_queries.run_query(
        set_sprint_mutation.replace("<ITEM_ID>", item_id)
        .replace("<SPRINT_FIELD_ID>", sprint_field_id)
        .replace("<SPRINT_ID>", sprint_to_use)
        .replace("<PROJ_ID>", project_id)
    )


def update_sprint_for_all_open_cards(
    org_name: str,
    project_number: str,
    current_sprint: str,
    next_sprint: str,
    sprint_field_id: str,
    project_id: str,
):
    cards_in_project = get_cards_in_project(org_name=org_name, project_number=project_number)
    for card in cards_in_project:
        if card.sprint == current_sprint:
            match card.status:
                case "Backlog":
                    if "rework" in card.labels:
                        set_sprint(card.node_id, sprint_field_id, next_sprint, project_id)
                case "In Progress":
                    set_sprint(card.node_id, sprint_field_id, next_sprint, project_id)
                case "Impeded":
                    set_sprint(card.node_id, sprint_field_id, next_sprint, project_id)
                case "Review":
                    set_sprint(card.node_id, sprint_field_id, next_sprint, project_id)
                case _:
                    # This is not a status to update
                    pass


def set_points(item_id: str, points_field_id: str, points: str, project_id: str):
    print(
        set_points_mutation.replace("<ITEM_ID>", item_id)
        .replace("<POINTS_FIELD_ID>", points_field_id)
        .replace("<POINTS>", points)
        .replace("<PROJ_ID>", project_id)
    )
    gql_queries.run_query(
        set_points_mutation.replace("<ITEM_ID>", item_id)
        .replace("<POINTS_FIELD_ID>", points_field_id)
        .replace("<POINTS>", points)
        .replace("<PROJ_ID>", project_id)
    )
