import configparser
import json
import os
from datetime import datetime

from graph_ql_interactions.github_request_functions import get_contents_of_file_in_repo

import graph_ql_interactions.card_interactions as card_i
import graph_ql_interactions.repo_interactions as repo_i

config = configparser.ConfigParser()
config.read(os.path.join(f"{os.path.dirname(__file__)}", "..", "config_info", "config.ini"))


class BoardChecks:
    def __init__(self, cards):
        self.cards = cards
        self.release_notes = ""
        self.prs = {}
        self.problem_text = []
        self.last_update = datetime.now()
        self.summary = {}
        self.error_count = 0
        self.warning_count = 0
        self.do_the_checks()

    def get_json(self):
        # 3600 seconds is one hour, this means that this will cache this slightly
        if (datetime.now() - self.last_update).seconds > 3600:
            self.do_the_checks()
        return json.dumps(self.summary)

    def do_the_checks(self):
        self.error_count = 0
        self.warning_count = 0
        self.get_present_release_notes()
        self.get_release_note_prs()
        for card in self.cards:
            if card.type != "ISSUE":
                # Not checking on PRs
                continue
            if card.status is None:
                # If there is no status it is not properly in the system
                continue
            if card.sprint is None:
                # If it has no sprint there is no scheduling aspect so will not check
                continue
            self.check_if_stale(card)
            self.check_assignees(card)
            if card.repo == config["BOARD.CHECKS"]["release_notes_repo"]:
                # Limiting the repo to begin with to those in the release notes being considered
                self.check_release_notes(card)
            if config["BOARD.CHECKS"]["check_points_labels"] == "True":
                self.verify_card_pointing_correct(card)
            self.check_statuses_and_labels_match(card)
        self.last_update = datetime.now()
        self.summary["total_num"] = self.error_count + self.warning_count
        self.summary["error_num"] = self.error_count
        self.summary["warning_num"] = self.warning_count
        self.summary["details"] = self.problem_text

    def update_checks(self):
        self.do_the_checks()

    def verify_card_pointing_correct(self, card):
        if card.priority is None:
            # If everything is there except this then it should mean that it has yet to be
            # prioritised, so can be assumed to be a future sprint and therefore doesn't need points
            return
        points_label_count = 0
        zero_point_label = False
        new_problem_text = None
        for label in card.labels:
            if label.isdigit():
                points_label_count += 1
            if label == "0":
                zero_point_label = True
        if points_label_count > 1:
            new_problem_text = (
                f"ERROR: Issue {card.title} in {card.repo} assigned to "
                f"{card.assignees} has multiple points labels"
            )
            self.error_count += 1
        elif zero_point_label:
            if not list(
                set(card.labels) & set(config["BOARD.CHECKS"]["zero_points_labels"].split(","))
            ):
                new_problem_text = (
                    f"ERROR: Issue {card.title} in {card.repo} assigned to {card.assignees} has "
                    f"a zero-point label and nothing to indicate this is valid"
                )
                self.error_count += 1
        elif points_label_count == 0:
            if not list(
                set(card.labels) & set(config["BOARD.CHECKS"]["no_points_labels"].split(","))
            ):
                new_problem_text = (
                    f"ERROR: Issue {card.title} in {card.repo} assigned to {card.assignees} has "
                    f"no points labels and it should have"
                )
                self.error_count += 1
        if new_problem_text:
            self.problem_text.append(new_problem_text)

    def check_assignees(self, card):
        if card.status not in config["BOARD.CHECKS"]["allow_unassigned"].split(","):
            if not card_i.get_assignees(card.id):
                self.problem_text.append(
                    f"ERROR: Issue {card.title} in {card.repo} with {card.status} status does not "
                    f"have anyone assigned."
                )
                self.error_count += 1

    def check_if_stale(self, card):
        # Based on self.status and intersections with the settings returned do the stale checks
        comment_errors = dict(
            item.split(":") for item in config["BOARD.CHECKS"]["comment_errors"].split(",")
        )
        label_warnings = dict(
            item.split(":") for item in config["BOARD.CHECKS"]["label_warnings"].split(",")
        )
        label_errors = dict(
            item.split(":") for item in config["BOARD.CHECKS"]["label_errors"].split(",")
        )
        comment_check = {k: comment_errors[k] for k in (comment_errors.keys() & card.labels)}
        error_check = {k: label_errors[k] for k in (label_errors.keys() & card.labels)}
        warning_check = {k: label_warnings[k] for k in (label_warnings.keys() & card.labels)}

        if comment_check:
            for check in comment_check:
                if self.check_if_last_comment_stale(
                    comment_errors[check], card.id, card.title, card.status, card.assignees
                ):
                    self.error_count += 1
                    return
                else:
                    try:
                        label_errors.pop(check)
                        label_warnings.pop(check)
                    except KeyError:
                        # There is no guarantee that this will be available in other areas
                        pass
        else:
            if card.status.lower() in comment_errors.keys():
                if self.check_if_last_comment_stale(
                    comment_errors[card.status.lower()],
                    card.id,
                    card.title,
                    card.status,
                    card.assignees,
                ):
                    self.error_count += 1
                    return
                else:
                    try:
                        label_errors.pop(card.status.lower())
                        label_warnings.pop(card.status.lower())
                    except KeyError:
                        # There is no guarantee that this will be available in other areas
                        pass

        start_error_count = self.error_count
        if error_check:
            if self.check_if_label_status_stale(
                "ERROR",
                label_errors,
                card.id,
                card.title,
                card.assignees,
            ):
                self.error_count += 1
                return
        else:
            if card.status.lower() in label_errors.keys():
                if self.check_stale_status(
                    card.id, card.status, label_errors, "ERROR", card.number, card.assignees
                ):
                    self.error_count += 1
                    return

        # If the error count is the same, then there is no need to check for warning as an error
        # has been found
        if self.error_count == start_error_count:
            if warning_check:
                if self.check_if_label_status_stale(
                    "Warning",
                    label_warnings,
                    card.id,
                    card.title,
                    card.assignees,
                ):
                    self.warning_count += 1
                    return
            else:
                if card.status.lower() in label_warnings.keys():
                    if self.check_stale_status(
                        card.id, card.status, label_warnings, "Warning", card.title, card.assignees
                    ):
                        self.error_count += 1
                        return

    def check_if_last_comment_stale(self, duration, ident, title, status, assignees):
        last_comment = datetime.strptime(
            card_i.get_when_last_commented_created_on_issue(ident), "%Y-%m-%dT%H:%M:%SZ"
        )
        today_to_compare = datetime.today()
        if (today_to_compare - last_comment).days >= int(duration):
            self.problem_text.append(
                f"ERROR: Issue {title} in {status} assigned to {assignees} last had a comment "
                f"added {duration} days or more ago."
            )
            return True
        return False

    def check_if_label_status_stale(self, status, label_list, ident, title, assignees):
        labels = card_i.get_when_labels_were_added_to_issue(ident)
        today_for_labels = datetime.today()
        for check in label_list:
            if check in labels:
                label_in_place_since = (
                    today_for_labels - datetime.strptime(labels[check], "%Y-%m-%dT%H:%M:%SZ")
                ).days
                if label_in_place_since >= int(label_list[check]):
                    self.problem_text.append(
                        f"{status}: Issue {title} assigned to {assignees} had {check} label added "
                        f"more than {int(label_list[check])} days ago."
                    )
                    return True
        return False

    def get_present_release_notes(self):
        self.release_notes = get_contents_of_file_in_repo(
            repo_owner=config["GITHUB.INTERACTION"]["org_name"],
            repo_name=config["BOARD.CHECKS"]["release_notes_repo"],
            file_path=config["BOARD.CHECKS"]["release_notes_file_path"],
            branch=config["BOARD.CHECKS"]["release_notes_branch"],
        )

    def get_release_note_prs(self):
        result = repo_i.get_pull_requests(
            org_name=config["GITHUB.INTERACTION"]["org_name"],
            repo_name=config["BOARD.CHECKS"]["release_notes_repo"],
        )
        for value in result:
            self.prs[value["title"]] = value["bodyText"]

    def check_release_notes(self, card):
        if card.status in config["BOARD.CHECKS"]["need_notes"].split(","):
            if not list(set(card.labels) & set(config["BOARD.CHECKS"]["notes_exempt"].split(","))):
                card_in_release_notes = False
                card_in_prs = False
                if card.name in self.release_notes:
                    card_in_release_notes = True
                for pr in self.prs.keys():
                    if card.name in pr:
                        card_in_prs = True
                    if card.name in self.prs[pr]:
                        card_in_prs = True
                # Hard coding as this is complicated, and want to have something that works ASAP
                if card_in_release_notes and card_in_prs:
                    self.problem_text.append(
                        f"ERROR: Issue {card.title} assigned to {card.assignees} is {card.status} "
                        f"and has both release notes and open PRs."
                    )
                    self.error_count += 1
                    return
                if not card_in_release_notes and not card_in_prs:
                    self.problem_text.append(
                        f"ERROR: Issue {card.title} assigned to {card.assignees} is {card.status} "
                        f"and has no release notes or PRs for release notes."
                    )
                    self.error_count += 1
                    return
                if card.status == "Done":
                    if not card_in_release_notes and card_in_prs:
                        self.problem_text.append(
                            f"ERROR: Issue {card.title} assigned to {card.assignees} is "
                            f"{card.status} and has open PRs for release notes."
                        )
                        self.error_count += 1

                if card.status == "Review":
                    if card_in_release_notes and not card_in_prs:
                        self.problem_text.append(
                            f"ERROR: Issue {card.title} assigned to {card.assignees} is "
                            f"{card.status} and has an entry in the release notes without being "
                            f"completed."
                        )
                        self.error_count += 1

    def check_stale_status(self, ident, status, label_list, message_status, title, assignees):
        today_for_status = datetime.today()
        status_changed_date = card_i.get_when_specified_project_field_was_last_changed(
            ident, status
        )
        status_in_place_since = (today_for_status - status_changed_date).days
        if status_in_place_since >= int(label_list[status.lower()]):
            self.problem_text.append(
                f"{message_status}: Issue {title} assigned to {assignees} had {status} assigned "
                f"more than {int(label_list[status.lower()])} days ago."
            )
            return True
        return False

    def check_statuses_and_labels_match(self, card):
        if (card.status.lower() not in card.labels) and (
            card.status.lower() not in ["done", "backlog"]
        ):
            self.problem_text.append(
                f"Error: Issue {card.title} does not have a suitable label to match the current "
                f"status of {card.status}"
            )
            return True
        return False
