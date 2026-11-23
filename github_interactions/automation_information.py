import datetime
import configparser
import os
from burndown_interactions import burndown
import logging
import re
import graph_ql_interactions.card_interactions as cards
import graph_ql_interactions.repo_interactions as repos
import graph_ql_interactions.project_interactions as projects
import github_interactions.repo_information as repo_info
import github_interactions.project_increment_information as project_increments
from github_interactions.board_checks import BoardChecks

pm_logger = logging.getLogger("board_automation")


def build_html_table(info: dict):
    data = "<table><tr>"
    for heading in info.keys():
        data += "<th>" + heading + "</th>"
    data += "</tr>"

    lengths = {}
    for item in info:
        lengths[item] = len(info[item])
    for i in range(max(lengths.values())):
        data += "<tr>"
        for item in info.keys():
            try:
                data += (
                    "<td>"
                    + str(info[item][i]["number"])
                    + " ("
                    + str(info[item][i]["repo"])
                    + ")</td>"
                )
            except IndexError:
                data += "<td></td>"
        data += "</tr>"
    data += "</table>"
    return data


class AutomationInfo:
    def __init__(self):
        self.html_message = ""
        # Get values from config.ini
        config = configparser.ConfigParser()
        config.read(os.path.join(f"{os.path.dirname(__file__)}", "..", "config_info", "config.ini"))

        self.user_name = config["GITHUB.INTERACTION"]["user_name"]
        self.org_name = config["GITHUB.INTERACTION"]["org_name"]

        self.today = None
        self.today_day = None
        self.today_month = None
        self.today_year = None
        self.set_today()

        self.available_program_increments = {}
        self.current_project = None
        self.next_project = None
        self.project_number = ""
        self.sprint_by_class = None
        self.sprint_starts = None
        self.pi_starts = []
        self.update_projects()

        # Get current and next sprint
        self.current_sprint = ""
        self.next_sprint = ""
        self.previous_sprint = ""
        self.set_previous_current_and_next_sprint()
        self.current_burndown = burndown.Burndown(
            self.org_name,
            self.project_number,
            self.current_sprint,
            self.next_sprint,
            self.sprint_by_class,
        )

        # Initialise extra parameters needed
        self.repos = {}

    def add_repo(self, repo_name: str):
        if repo_name not in self.repos.keys():
            self.repos[repo_name] = repo_info.RepoInfo(self.org_name, repo_name)

    def set_today(self):
        # Get the date to use to automate some of the coding
        today = datetime.datetime.today()
        self.today_day = today.strftime("%d")
        self.today_month = today.strftime("%m")
        self.today_year = today.strftime("%Y")
        self.today = datetime.datetime(
            year=int(self.today_year), month=int(self.today_month), day=int(self.today_day)
        )

    def set_previous_current_and_next_sprint(self):
        # Find the current sprint
        current_sprint_index = None

        for i in range(len(self.sprint_starts) - 1):
            if self.sprint_starts[i] <= self.today <= self.sprint_starts[i + 1]:
                current_sprint_index = i

        if current_sprint_index is None:
            pm_logger.info("No sprints found")
            return

        try:
            self.current_sprint = self.sprint_by_class[
                self.sprint_starts[current_sprint_index].strftime("%Y_%m_%d")
            ].sprint_name
        except KeyError:
            self.current_sprint = self.available_program_increments[
                self.current_project
            ].first_sprint

        try:
            self.next_sprint = self.sprint_by_class[
                self.sprint_starts[current_sprint_index + 1].strftime("%Y_%m_%d")
            ].sprint_name
        except KeyError:
            self.next_sprint = self.available_program_increments[self.current_project].last_sprint

        try:
            self.previous_sprint = self.sprint_by_class[
                self.sprint_starts[current_sprint_index - 1].strftime("%Y_%m_%d")
            ].sprint_name
        except KeyError:
            self.current_sprint = self.available_program_increments[
                self.current_project
            ].first_sprint

        try:
            if self.sprint_by_class[self.next_sprint].in_next_pi:
                if not (
                    self.available_program_increments[self.next_project].start_date > self.today
                ):
                    self.html_message = "MAKE SURE THAT THE NEXT PI PROJECT IS CREATED!"
                    pm_logger.info("Next PI needed, and/or server restart needed")
        except KeyError:
            pm_logger.info("No sprints found")

    def update_sprints(self):
        self.set_today()
        self.update_projects()
        self.set_today()
        self.set_previous_current_and_next_sprint()
        self.current_burndown.change_sprint(
            self.current_sprint,
            self.next_sprint,
        )
        cards_to_refine = cards.get_card_issue_ids_in_sprint(
            org_name=self.org_name, project_number=self.project_number, sprint=self.current_sprint
        )
        for card in cards_to_refine:
            cards.remove_label(
                card,
                repos.get_label_id(
                    org_name=self.org_name,
                    repo_name=card.repo,
                    label_name="proposal",
                ),
            )

    def update_projects(self):
        # Find the V2 projects owned by the organisation
        self.html_message = ""
        result_projects = projects.get_projects(org_name=self.org_name)

        # Filter out a dictionary of the PIs
        for result_project in result_projects:
            # Matching the title style and using the offset to help define if it is a PI or not
            try:
                is_pi = re.compile(r"PI_\d\d\d\d_\d\d").match(result_project["title"]).span()[0]
            except AttributeError:
                is_pi = -1
            if is_pi >= 0 and not result_project["template"] and not result_project["closed"]:
                if result_project["title"] not in self.available_program_increments.keys():
                    self.available_program_increments[result_project["title"]] = (
                        project_increments.ProjectIncrement(
                            project_id=result_project["id"],
                            number=result_project["number"],
                            title=result_project["title"],
                            org_name=self.org_name,
                        )
                    )
                    self.pi_starts.append(
                        self.available_program_increments[result_project["title"]].start_date
                    )

        self.pi_starts.sort()

        # Find the appropriate project for this PI
        self.current_project = None
        self.next_project = None

        current_pi_index = None

        for i in range(len(self.pi_starts) - 1):
            if self.pi_starts[i] <= self.today < self.pi_starts[i + 1]:
                current_pi_index = i

        if (len(self.pi_starts) - 1) == 0:
            print("The length is 0")
            current_pi_index = -1

        if current_pi_index is None:
            return

        for pi_value in self.available_program_increments.keys():
            if (
                self.available_program_increments[pi_value].start_date
                == self.pi_starts[current_pi_index]
            ):
                self.current_project = pi_value
            if (
                self.available_program_increments[pi_value].start_date
                == self.pi_starts[current_pi_index + 1]
            ):
                self.next_project = pi_value

        self.project_number = self.available_program_increments[self.current_project].number
        self.sprint_by_class = self.available_program_increments[
            self.current_project
        ].sprint_by_class
        self.sprint_starts = self.available_program_increments[
            self.current_project
        ].all_sprint_starts

    def get_cards_snapshot(self):
        return cards.get_cards_and_points_snapshot_for_sprint(
            self.org_name, self.project_number, self.current_sprint
        )

    def get_sprint_columns_snapshot_html(self):
        info = cards.get_card_list_snapshot_for_sprint(
            self.org_name, self.project_number, self.current_sprint
        )
        data = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Issues in 
        Columns</title></head><body><h1>The present listings</h1>"""
        data += build_html_table(info)
        data += "</body></html>"
        return data

    def get_planning_priority_snapshot(self):
        info = cards.get_planning_snapshot(self.org_name, self.project_number, self.current_sprint)
        data = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>
        Planning Priority</title></head><body><h1>The present listings</h1>"""
        data += build_html_table(info)
        data += "</body></html>"
        return data

    def check_board_rules_for_sprints(self):
        return BoardChecks(
            cards.get_cards_in_sprint(self.org_name, self.project_number, self.current_sprint)
        ).get_json()

    def move_tickets_to_next_sprint(self):
        cards.update_sprint_for_all_open_cards(
            self.org_name,
            self.project_number,
            self.current_sprint,
            self.available_program_increments[self.current_project].sprint_ids[self.next_sprint],
            self.available_program_increments[self.current_project].sprint_field_id,
            self.available_program_increments[self.current_project].project_id,
        )
