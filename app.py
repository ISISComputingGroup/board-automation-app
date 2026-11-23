import asyncio
from pathlib import Path

import tornado
from github_interactions import automation_information, update_item_info
import os
import hashlib
import hmac
import configparser
import logging
from logging.handlers import TimedRotatingFileHandler

# Set up the logging as soon as possible
pm_log_filepath = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "log", "board_automation.log"
)
output_file = Path("/some/path/file.txt")
output_file.parent.mkdir(exist_ok=True, parents=True)
output_file.write_text("some text")

if not os.path.exists(pm_log_filepath):
    file = Path(pm_log_filepath)
    file.parent.mkdir(exist_ok=True, parents=True)
    file = open(pm_log_filepath, "w+")
    file.close()

pm_logger = logging.getLogger("board_automation")
pm_handler = TimedRotatingFileHandler(pm_log_filepath, when="midnight", backupCount=30)
pm_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
pm_logger.setLevel(logging.INFO)
pm_logger.addHandler(pm_handler)

points_labels = ["0", "1", "2", "3", "5", "8", "13", "20", "40"]


def pm_logging(message: str, message_level: str) -> None:
    if app_log_level == "developer":
        print(message)
    match message_level:
        case "error":
            pm_logger.exception(message)
        case "info":
            if app_log_level in ["developer", "info", "all"]:
                pm_logger.info(message)
        case "debug":
            if app_log_level in ["developer", "debug", "all"]:
                pm_logger.debug(message)


# Initialise the classes that will be needed for the overall app
working_information = automation_information.AutomationInfo()

# Get the items from the config file
config = configparser.ConfigParser()
config.read(os.path.join(f"{os.path.dirname(__file__)}", "config_info", "config.ini"))
try:
    secret = config["GITHUB.INTERACTION"]["webhook_secret"]
    host = config["WWW.INTERACTION"]["host"]
    port = int(config["WWW.INTERACTION"]["port"])
    app_log_level = config["SETTINGS"]["log_level"]
except KeyError as ke:
    match ke.args[0]:
        case "GITHUB.INTERACTION", "WWW.INTERACTION":
            pm_logging("Config section needed but not present: {}".format(ke), "error")
        case "log_level":
            app_log_level = ""
        case _:
            pm_logging("Section missing from config: {}".format(ke), "error")


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render(
            os.path.join(f"{os.path.dirname(__file__)}", "pi_and_sprint_actions", "home.html")
        )


class SprintHandler(tornado.web.RequestHandler):
    def get(self):
        self.render(
            os.path.join(
                f"{os.path.dirname(__file__)}", "pi_and_sprint_actions", "sprint_data.html"
            ),
            current_sprint=working_information.current_sprint,
            next_sprint=working_information.next_sprint,
            misc_message=working_information.html_message,
        )

    def post(self):
        working_information.update_sprints()
        self.render(
            os.path.join(
                f"{os.path.dirname(__file__)}", "pi_and_sprint_actions", "updated_sprint_data.html"
            ),
            current_sprint=working_information.current_sprint,
            next_sprint=working_information.next_sprint,
            misc_message=working_information.html_message,
        )


class MoveTicketsHandler(tornado.web.RequestHandler):
    def post(self):
        working_information.move_tickets_to_next_sprint()
        self.render(
            os.path.join(f"{os.path.dirname(__file__)}", "pi_and_sprint_actions", "home.html")
        )


class ColumnFrequencyHandler(tornado.web.RequestHandler):
    def get(self):
        snapshot = working_information.get_cards_snapshot()
        self.render(
            os.path.join(
                f"{os.path.dirname(__file__)}",
                "pi_and_sprint_actions",
                "column_count_and_points.html",
            ),
            misc_message=working_information.html_message,
            ready_count=snapshot["ready"]["count"],
            ready_points=snapshot["ready"]["points"],
            rework_count=snapshot["rework"]["count"],
            rework_points=snapshot["rework"]["points"],
            in_progress_count=snapshot["in_progress"]["count"],
            in_progress_points=snapshot["in_progress"]["points"],
            impeded_count=snapshot["impeded"]["count"],
            impeded_points=snapshot["impeded"]["points"],
            review_count=snapshot["review"]["count"],
            review_points=snapshot["review"]["points"],
            done_count=snapshot["done"]["count"],
            done_points=snapshot["done"]["points"],
        )


class ColumnEntriesHandler(tornado.web.RequestHandler):
    def get(self):
        # snapshot = working_information.get_cards_snapshot()
        self.write(working_information.get_sprint_columns_snapshot_html())


class PlanningPrioritiesHandler(tornado.web.RequestHandler):
    def get(self):
        # snapshot = working_information.get_cards_snapshot()
        self.write(working_information.get_planning_priority_snapshot())


class ProjectBoardChecksHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(working_information.check_board_rules_for_sprints())


class WebhookError(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail


def verify_signature(payload_body, secret_token, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.

    Raise and return 403 if not authorised.

    Args:
        payload_body: original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
    """
    if not signature_header:
        raise WebhookError(status_code=403, detail="x-hub-signature-256 header is missing!")
    hash_object = hmac.new(secret_token.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        raise WebhookError(status_code=403, detail="Request signatures didn't match!")


class WebhookHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            verify_signature(self.request.body, secret, self.request.headers["X-Hub-Signature-256"])
        except WebhookError as e:
            pm_logging("Found a signature issue: {}".format(e.detail), "error")
            self.set_status(e.status_code)
            return
        request = tornado.escape.json_decode(self.request.body)
        # This is assuming a post from GitHub, other sources will not do much
        match request["action"]:
            case "unlabeled":
                pm_logging(
                    "Label removed, nothing to do: {}".format(request["label"]["name"]), "debug"
                )
            case "labeled":
                label_added(request)
            case "edited":
                try:
                    match request["changes"]["field_value"]["field_name"]:
                        case "Labels":
                            # Labels should already have been handled elsewhere
                            pass
                        case "Status":
                            pm_logger.exception(request)
                            status_changed(request)
                        case _:
                            pm_logging(
                                "Nothing decided yet for: {}".format(
                                    request["changes"]["field_value"]["field_name"]
                                ),
                                "debug",
                            )
                except KeyError as e:
                    pm_logging("Error matching the request: {}".format(e), "error")
            case _:
                pm_logging("No cases for action: {}".format(request["action"]), "debug")


# Display the burndown chart of the IBEX board
class BurndownHandler(tornado.web.RequestHandler):
    def get(self):
        # Update the display before displaying
        working_information.current_burndown.update_display()
        self.write(working_information.current_burndown.burndown_display())


def status_changed(info):
    if info["projects_v2_item"]["content_type"] == "Issue":
        try:
            status_from = info["changes"]["field_value"]["from"]["name"]
        except (KeyError, TypeError):
            status_from = "Unknown"
        try:
            status_to = info["changes"]["field_value"]["to"]["name"]
        except KeyError:
            status_to = "Unknown"
        current_issue = update_item_info.IssueToUpdate(info["projects_v2_item"]["content_node_id"])
        current_issue.get_repo()
        working_information.add_repo(current_issue.repo_name)
        match status_from:
            case "Done":
                # Nothing to do for Done
                pass
            case "In Progress":
                current_issue.remove_label(
                    working_information.repos[current_issue.repo_name].labels["in progress"]
                )
            case "Impeded":
                current_issue.remove_label(
                    working_information.repos[current_issue.repo_name].labels["impeded"]
                )
            case "Review":
                current_issue.remove_label(
                    working_information.repos[current_issue.repo_name].labels["review"]
                )
                current_issue.remove_label(
                    working_information.repos[current_issue.repo_name].labels["under review"]
                )
            case "Backlog":
                # Nothing to do for Backlog here
                pass
            case _:
                pm_logging(
                    "Nothing planned for going from this status: {}".format(status_from), "debug"
                )
        match status_to:
            case "Done":
                # Nothing to do for Done
                pass
            case "In Progress":
                current_issue.add_label(
                    working_information.repos[current_issue.repo_name].labels["in progress"]
                )
                if status_from == "Review":
                    current_issue.add_label(
                        working_information.repos[current_issue.repo_name].labels["rework"]
                    )
            case "Impeded":
                current_issue.add_label(
                    working_information.repos[current_issue.repo_name].labels["impeded"]
                )
            case "Review":
                current_issue.add_label(
                    working_information.repos[current_issue.repo_name].labels["review"]
                )
            case "Backlog":
                if status_from == "Review":
                    current_issue.add_label(
                        working_information.repos[current_issue.repo_name].labels["rework"]
                    )
            case _:
                pm_logging(
                    "Nothing planned for going to this status: {}".format(status_to), "debug"
                )


def label_added(info):
    pm_logging("Label added: {}".format(info["label"]["name"]), "info")
    current_issue = update_item_info.IssueToUpdate(info["issue"]["node_id"])
    current_issue.set_project(
        working_information.available_program_increments[working_information.current_project],
        working_information.current_sprint,
        working_information.next_sprint,
    )
    label_name = info["label"]["name"]
    if label_name in points_labels:
        pm_logging("Points label, need to apply this in time", "debug")
        current_issue.set_points(label_name)
    else:
        match label_name:
            case "proposal":
                pm_logging("Proposed ticket being added to project in next sprint", "info")
                current_issue.place_in_next_sprint()
            case "added during sprint":
                current_issue.place_in_current_sprint()
            case "in progress":
                current_issue.set_status(current_issue.project_to_use.status_ids["In Progress"])
            case "impeded":
                current_issue.set_status(current_issue.project_to_use.status_ids["Impeded"])
            case "review":
                current_issue.set_status(current_issue.project_to_use.status_ids["Review"])
            case "rework":
                current_issue.set_status(current_issue.project_to_use.status_ids["Backlog"])
            case _:
                pass
                # print("Nothing to be done with this label: ", label_name)


def make_app():
    return tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/burndown", BurndownHandler),
            (r"/webhook", WebhookHandler),
            (r"/sprint", SprintHandler),
            (r"/col_no_points", ColumnFrequencyHandler),
            (r"/col_entries", ColumnEntriesHandler),
            (r"/plan_priorities", PlanningPrioritiesHandler),
            (r"/move_open_tickets", MoveTicketsHandler),
            (r"/projectboardchecks", ProjectBoardChecksHandler),
        ]
    )


async def main():
    app = make_app()
    app.listen(port, host)
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pm_logging("Shutting down with Keyboard Interrupt", "info")
