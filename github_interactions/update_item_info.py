import graph_ql_interactions.github_request_functions as gql_queries
import graph_ql_interactions.card_interactions as cards
import github_interactions.project_increment_information as projects


class IssueToUpdate:
    def __init__(self, issue_id: str):
        self.issue_id = issue_id
        self.project_to_use = None
        self.item_id = None
        self.repo_name = None
        self.current_sprint = None
        self.next_sprint = None

    def set_project(
        self, project: projects.ProjectIncrement, current_sprint: str, next_sprint: str
    ):
        self.project_to_use = project
        self.current_sprint = current_sprint
        self.next_sprint = next_sprint
        set_proj_mutation = gql_queries.open_graph_ql_query_file("SetProject.txt")

        result = gql_queries.run_query(
            set_proj_mutation.replace("<ISSUE_ID>", self.issue_id).replace(
                "<PROJ_ID>", self.project_to_use.project_id
            )
        )
        self.item_id = result["data"]["addProjectV2ItemById"]["item"]["id"]

    def set_sprint(self, sprint_to_use: str):
        cards.set_sprint(
            self.item_id,
            self.project_to_use.sprint_field_id,
            sprint_to_use,
            self.project_to_use.project_id,
        )

    def set_status(self, status_to_use: str):
        set_sprint = gql_queries.open_graph_ql_query_file("UpdateStatusForItemInProject.txt")
        gql_queries.run_query(
            set_sprint.replace("<ITEM_ID>", self.item_id)
            .replace("<STATUS_FIELD_ID>", self.project_to_use.status_field_id)
            .replace("<STATUS_ID>", status_to_use)
            .replace("<PROJ_ID>", self.project_to_use.project_id)
        )

    def place_in_next_sprint(self):
        self.set_sprint(self.project_to_use.sprint_ids[self.next_sprint])
        self.set_status(self.project_to_use.status_ids["Backlog"])

    def place_in_current_sprint(self):
        self.set_sprint(self.project_to_use.sprint_ids[self.current_sprint])

    def get_repo(self):
        get_repo_query = gql_queries.open_graph_ql_query_file("findIssueInfo.txt").replace(
            "<ISSUE>", self.issue_id
        )
        self.repo_name = gql_queries.run_query(get_repo_query)["data"]["node"]["repository"]["name"]

    def add_label(self, label_id_to_add: str):
        cards.add_label(self.issue_id, label_id_to_add)

    def remove_label(self, label_id_to_remove: str):
        cards.remove_label(self.issue_id, label_id_to_remove)

    def set_points(self, points_label: str):
        cards.set_points(
            self.item_id,
            self.project_to_use.points_field_id,
            points_label,
            self.project_to_use.project_id,
        )
