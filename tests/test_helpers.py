import json
from enum import Enum, auto

import pandas


class QlCommand(Enum):
    find_card_info = auto()
    find_orgs = auto()
    find_projects = auto()
    find_project_sprints = auto()
    find_repo_info = auto()
    find_repo_label_id = auto()
    find_last_comment = auto()
    find_labels_added = auto()
    find_assignees = auto()
    find_field_change = auto()
    find_pull_requests = auto()
    find_issue_repo = auto()
    find_project_field_list = auto()
    remove_label = auto()
    set_project = auto()
    update_item_label = auto()
    update_points_for_item_in_project = auto()
    update_sprint_for_item_in_project = auto()
    update_status_for_item_in_project = auto()


def bad_return():
    """
    To ensure errors are handled in a known way use this helper
    :return: Something that will not be usable by any code
    """
    return json.dumps("Testing Errors")


def labels_list(expected_labels: dict):
    """
    Formats a list of labels to the correct examples for use via response_mock for the GitHub graphQL API
    :param expected_labels: a dictionary of {"label_name_1": "label_id_1", "label_name_2": "label_id_2", etc.}
    :return: a list of dictionaries of the format [{"name": "label_name_1", "id": "label_id_1"},
                                                   {"name": "label_name_2", "id": "label_id_=2"}, etc.]
    """
    labels = []
    for entry in expected_labels.keys():
        labels.append({"name": entry, "id": expected_labels[entry]})
    return labels


def fields_list(expected_fields: dict):
    """
    Formats a list of labels to the correct examples for use via response_mock for the GitHub graphQL API
    :param expected_fields: a dictionary of {"field_name_1": "field_value_1", "field_name_2": "field_value_2", etc.}
    :return: a list of dictionaries of the format [{'name': 'field_value_1', 'field': {'name': 'field_name_1'}},
                                                   {'name': 'field_value_2', 'field': {'name': 'field_name_2'}}, etc.]
    """
    fields = []
    for entry in expected_fields.keys():
        if pandas.api.types.is_numeric_dtype(type(expected_fields[entry])):
            fields.append({"number": expected_fields[entry], "field": {"name": entry}})
        else:
            fields.append({"name": expected_fields[entry], "field": {"name": entry}})
    return fields


def field_options(expected_options: dict):
    """
    Formats a list of options to the correct examples for use via response_mock for the GitHub graphQL API
    :param expected_options: a dictionary of {"option_name_1": "option_id_1", "option_name_2": "option_id_2", etc.}
    :return: a list of dictionaries of the format [{"name": "option_name_1", "id": "option_id_1"},
                                                   {"name": "option_name_2", "id": "option_id_=2"}, etc.]
    """
    options = []
    for entry in expected_options.keys():
        options.append({"name": entry, "id": expected_options[entry]})
    return options


def issue_entry(ident: int, content_id: str, labels: dict, fields: dict, repo_name: str):
    issue = {
        "id": f"node_{ident}",
        "type": "ISSUE",
        "content": {
            "id": content_id,
            "number": ident,
            "title": f"Issue {ident}",
            "labels": {"nodes": labels_list(labels)},
            "repository": {"name": repo_name},
        },
        "fieldValues": {"nodes": fields_list(fields)},
    }
    return issue


def draft_issue_entry(ident: int, fields: dict):
    draft_issue = {
        "id": f"node_{ident}",
        "type": "DRAFT_ISSUE",
        "content": {"title": f"Draft issue {ident}", "id": f"draft_{ident}"},
        "fieldValues": {"nodes": fields_list(fields)},
    }
    return draft_issue


def pull_request_entry(ident: int, fields: dict):
    pull_request = {
        "id": f"node_{ident}",
        "type": "PULL_REQUEST",
        "content": {"title": f"Pull request {ident}"},
        "fieldValues": {"nodes": fields_list(fields)},
    }
    return pull_request


def build_cards_simple(
    number_of_issues: int = 1,
    number_of_drafts: int = 1,
    labels=None,
    statuses=None,
    repo_name: str = "repo_name",
):
    if statuses is None:
        statuses = {"status": "status_value"}
    if labels is None:
        labels = {"label_1": "label_1_id"}
    issues = []
    for index in range(0, number_of_issues):
        issues.append(issue_entry(index + 1, f"issue_{index + 1}", labels, statuses, repo_name))
    for index in range(number_of_issues + 1, number_of_drafts):
        issues.append(draft_issue_entry(index + 1, statuses))
    return build_response_contents(issues)


def build_response_contents(issues: list, has_next: bool = False, has_previous: bool = False):
    page_info = {
        "endCursor": "EC",
        "startCursor": "NC",
        "hasNextPage": has_next,
        "hasPreviousPage": has_previous,
    }
    cards_mock = {
        "data": {"organization": {"projectV2": {"items": {"nodes": issues, "pageInfo": page_info}}}}
    }
    return cards_mock


def snapshot_name_to_status_lookup(snapshot_name: str):
    match snapshot_name:
        case "ready" | "rework":
            return "Backlog"
        case "in_progress":
            return "In Progress"
        case "impeded":
            return "Impeded"
        case "review":
            return "Review"
        case "done":
            return "Done"
        case __:
            return ""


def priority_lookup(snapshot_name: str):
    match snapshot_name:
        case "high":
            return "High"
        case "medium":
            return "Medium"
        case "low":
            return "Low"
        case __:
            return ""


def build_points_snapshot_cards(expected_snapshot: dict, sprint_name: str = "sprint"):
    issues = []
    outer_index = 0
    for entry in expected_snapshot.keys():
        outer_index += 10
        target = expected_snapshot[entry]["count"]
        if entry == "ready":
            target = expected_snapshot[entry]["count"] - expected_snapshot["rework"]["count"]
        for index in range(0, target):
            fields = {
                "Points": 1.0,
                "Status": snapshot_name_to_status_lookup(entry),
                "Sprint": sprint_name,
            }
            labels = {entry: f"{entry}_label_id"}
            if entry == "rework":
                labels["rework"] = "rework_label_id"
            issues.append(
                issue_entry(
                    outer_index + index, f"issue_{outer_index + index}", labels, fields, "repo_name"
                )
            )
    return build_response_contents(issues)


def build_card_list_snapshot(expected_snapshot: dict, sprint_name: str = "sprint"):
    issues = []
    for entry in expected_snapshot.keys():
        if entry == "rework":
            continue
        for item in expected_snapshot[entry]:
            fields = {"Status": snapshot_name_to_status_lookup(entry), "Sprint": sprint_name}
            labels = {entry: f"{entry}_label_id"}
            if item in expected_snapshot["rework"]:
                labels["rework"] = "rework_label_id"
            issues.append(
                issue_entry(item["number"], f"issue_{item['number']}", labels, fields, item["repo"])
            )
    return build_response_contents(issues)


def build_planning_list_snapshot(expected_snapshot: dict, sprint_name: str = "sprint"):
    issues = []
    for entry in expected_snapshot.keys():
        for item in expected_snapshot[entry]:
            fields = {"Planning Priority": priority_lookup(entry), "Sprint": sprint_name}
            issues.append(
                issue_entry(item["number"], f"issue_{item['number']}", {}, fields, item["repo"])
            )
    return build_response_contents(issues)


def build_pi_statuses(
    status_field_id: str, statuses: dict, sprint_field_id: str, sprints: dict, points_field_id: str
):
    return {
        "data": {
            "organization": {
                "projectV2": {
                    "fields": {
                        "nodes": [
                            {
                                "name": "Status",
                                "id": status_field_id,
                                "options": field_options(statuses),
                            },
                            {
                                "name": "Sprint",
                                "id": sprint_field_id,
                                "options": field_options(sprints),
                            },
                            {"name": "Points", "id": points_field_id},
                        ]
                    }
                }
            }
        }
    }


def build_label_dates(expected_label_dates: dict):
    labels = []
    for entry in expected_label_dates:
        labels.append({"name": entry})
    edges = []
    for label in expected_label_dates:
        edges.append({"node": {"createdAt": expected_label_dates[label], "label": {"name": label}}})
    return {"data": {"node": {"labels": {"nodes": labels}, "timelineItems": {"edges": edges}}}}


def build_assignees(expected_assignees: dict):
    edges = []
    for assignee in expected_assignees:
        edges.append({"node": {"id": assignee, "login": assignee, "name": assignee}})
    return {"data": {"node": {"assignees": {"edges": edges}}}}


def build_field_change(name: str, createdat: str):
    return {
        "data": {
            "node": {
                "projectItems": {
                    "nodes": [
                        {
                            "fieldValues": {
                                "nodes": [
                                    {
                                        "name": name,
                                        "createdAt": createdat,
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    }


def build_field_list(expected_field_list: list):
    return {"data": {"organization": {"projectV2": {"fields": {"nodes": expected_field_list}}}}}


def build_response(ql_command: QlCommand, **kwargs):
    response = ""
    match ql_command:
        case QlCommand.find_repo_label_id:
            response = {"data": {"repository": {"label": {"id": kwargs["expected_label_id"]}}}}
        case QlCommand.find_repo_info:
            response = {
                "data": {
                    "repository": {
                        "name": kwargs["repo_name"],
                        "id": kwargs["repo_name"],
                        "labels": {"nodes": labels_list(kwargs["expected_labels"])},
                    }
                }
            }
        case QlCommand.find_card_info:
            match kwargs["card_type"]:
                case "simple":
                    response = build_cards_simple(kwargs["number_of_issues"], 0)
                case "points_snapshot":
                    response = build_points_snapshot_cards(
                        kwargs["expected_snapshot"], kwargs["sprint_name"]
                    )
                case "card_list_snapshot":
                    response = build_card_list_snapshot(
                        kwargs["expected_snapshot"], kwargs["sprint_name"]
                    )
                case "card_list_planning":
                    response = build_planning_list_snapshot(
                        kwargs["expected_snapshot"], kwargs["sprint_name"]
                    )
                case __:
                    response = ""
        case QlCommand.find_project_sprints:
            response = build_pi_statuses(
                kwargs["status_field_id"],
                kwargs["statuses"],
                kwargs["sprint_field_id"],
                kwargs["sprints"],
                kwargs["points_field_id"],
            )
        case QlCommand.find_last_comment:
            response = {
                "labels": {"nodes": labels_list(kwargs["expected_labels"])},
                "data": {"node": {"comments": {"nodes": [{"createdAt": kwargs["created_at"]}]}}},
            }
        case QlCommand.find_labels_added:
            response = build_label_dates(kwargs["expected_label_dates"])
        case QlCommand.find_assignees:
            response = build_assignees(kwargs["expected_assignees"])
        case QlCommand.find_field_change:
            response = build_field_change(
                name=kwargs["issue_status"], createdat=kwargs["created_at"]
            )
        case QlCommand.find_projects:
            response = {
                "data": {"organization": {"projectsV2": {"nodes": kwargs["expected_projects"]}}}
            }
        case QlCommand.find_pull_requests:
            response = {"data": {"repository": {"pullRequests": {"nodes": kwargs["expected_prs"]}}}}
        case QlCommand.find_issue_repo:
            response = {"data": {"node": {"repository": {"name": kwargs["repo_name"]}}}}
        case QlCommand.find_project_field_list:
            response = build_field_list(kwargs["expected_field_list"])
        case __:
            response = ""
    return json.dumps(response)


class PiDefaultResponseValues:
    def __init__(self):
        self.sprint_field_id = "sprint_field_id"
        self.status_field_id = "statis_field_id"
        self.points_field_id = "points_field_id"
        self.sprints = {
            "2020_01_01": "sprint_1",
            "Next PI (2020_04_04)": "sprint_2",
            "2020_02_02": "sprint_3",
            "2020_03_03": "sprint_4",
        }
        self.first_sprint = "2020_01_01"
        self.last_sprint = "Next PI (2020_04_04)"
        self.statuses = {"status 1": "status_1", "status 2": "status_2", "status 3": "status_3"}
        self.response = build_response(
            QlCommand.find_project_sprints,
            status_field_id=self.status_field_id,
            statuses=self.statuses,
            sprint_field_id=self.sprint_field_id,
            sprints=self.sprints,
            points_field_id=self.points_field_id,
        )
