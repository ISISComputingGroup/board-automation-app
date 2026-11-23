import re
from graph_ql_interactions import project_interactions
from github_interactions.sprint_information import SprintInfo
import datetime


class ProjectIncrement:
    def __init__(
        self, project_id: int = 0, number: int = 0, title: str = "None", org_name: str = ""
    ):
        self.project_id = project_id
        self.number = number
        self.title = title
        self.org_name = org_name
        if "X" in title:
            self.title = title + " is not a Program Increment"
            self.year = "2000"
            self.month = "01"
        else:
            try:
                offset = re.compile(r"\d\d\d\d_\d\d").search(title).span()[0]
                self.year = title[offset : offset + 4]
                self.month = title[offset + 5 : offset + 7]
            except AttributeError:
                self.title = title + " is not a Program Increment"
                self.year = "2000"
                self.month = "01"
        self.sprint_ids = {}
        self.sprint_by_class = {}
        self.status_ids = {}
        self.sprint_field_id = ""
        self.status_field_id = ""
        self.points_field_id = ""
        self.first_sprint = None
        self.last_sprint = None
        self.all_sprint_starts = []
        self.get_sprints_and_statuses()
        self.PI_has_sprints = True
        try:
            self.start_date = self.sprint_by_class[self.first_sprint].sprint_start_date
        except KeyError:
            self.start_date = datetime.datetime.today()
            self.PI_has_sprints = False

    def __str__(self):
        return "This is project increment: " + self.title

    def get_sprints_and_statuses(self):
        fields = project_interactions.get_project_field_list(self.number, self.org_name)
        # Get sprint list
        for field in fields:
            match field["name"]:
                case "Sprint":
                    self.sprint_field_id = field["id"]
                    for option in field["options"]:
                        self.sprint_ids[option["name"]] = option["id"]
                        self.sprint_by_class[option["name"]] = SprintInfo(option)
                        self.all_sprint_starts.append(
                            self.sprint_by_class[option["name"]].sprint_start_date
                        )
                case "Status":
                    self.status_field_id = field["id"]
                    for option in field["options"]:
                        self.status_ids[option["name"]] = option["id"]
                case "Points":
                    self.points_field_id = field["id"]
        self.all_sprint_starts.sort()
        if self.all_sprint_starts:
            for sprint in self.sprint_by_class.keys():
                if self.sprint_by_class[sprint].sprint_start_date == self.all_sprint_starts[0]:
                    self.first_sprint = sprint
                elif self.sprint_by_class[sprint].sprint_start_date == self.all_sprint_starts[-1]:
                    self.last_sprint = sprint
