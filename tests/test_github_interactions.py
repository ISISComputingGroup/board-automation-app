import datetime
import json
from unittest import TestCase
from unittest.mock import patch

import requests_mock

from github_interactions.board_checks import BoardChecks
from tests.test_helpers import (
    issue_entry,
    pull_request_entry,
    draft_issue_entry,
    build_response,
    QlCommand,
    PiDefaultResponseValues,
)
from github_interactions.automation_information import AutomationInfo
from github_interactions.card_info import CardInfo
from github_interactions.project_increment_information import ProjectIncrement
from github_interactions.repo_information import RepoInfo
from github_interactions.sprint_information import SprintInfo

url = "https://api.github.com/graphql"


class TestAutomationInfo(TestCase):
    @patch(
        "github_interactions.automation_information.AutomationInfo.set_previous_current_and_next_sprint"
    )
    @patch("github_interactions.automation_information.AutomationInfo.update_projects")
    def test_automation_info_dummy(self, mock_update_projects, mock_set_prev_next):
        # Please note, there will be red text displayed in relation to the missing Burndown information in this test,
        # but the test should pass
        try_class = AutomationInfo()
        mock_update_projects.assert_called()
        mock_set_prev_next.assert_called()
        self.assertEqual(try_class.today_year, datetime.datetime.today().strftime("%Y"))

    @requests_mock.mock()
    @patch(
        "github_interactions.automation_information.AutomationInfo.set_previous_current_and_next_sprint"
    )
    @patch("github_interactions.automation_information.AutomationInfo.update_projects")
    def test_add_repo(self, m, mock_update_projects, mock_set_prev_next):
        # Set up the class instance, and check that repos are empty
        try_class = AutomationInfo()
        mock_update_projects.assert_called()
        mock_set_prev_next.assert_called()
        self.assertEqual(try_class.repos, {})

        # Add the first repo
        test_repos = {}
        repo_1 = "Repo 1"
        test_repos[repo_1] = repo_1
        m.post(
            url,
            text=build_response(QlCommand.find_repo_info, repo_name=repo_1, expected_labels={}),
            status_code=200,
        )
        try_class.add_repo(repo_1)
        self.assertEqual(try_class.repos.keys(), test_repos.keys())

        # Add a second repo
        repo_2 = "Repo 2"
        test_repos[repo_2] = repo_2
        m.post(
            url,
            text=build_response(QlCommand.find_repo_info, repo_name=repo_2, expected_labels={}),
            status_code=200,
        )
        try_class.add_repo(repo_2)
        self.assertEqual(try_class.repos.keys(), test_repos.keys())

        # Re-add the first repo
        m.post(
            url,
            text=build_response(QlCommand.find_repo_info, repo_name=repo_1, expected_labels={}),
            status_code=200,
        )
        try_class.add_repo(repo_1)
        self.assertEqual(try_class.repos.keys(), test_repos.keys())

    @patch(
        "github_interactions.automation_information.AutomationInfo.set_previous_current_and_next_sprint"
    )
    @patch("github_interactions.automation_information.AutomationInfo.update_projects")
    def test_set_today(self, mock_update_projects, mock_set_prev_next):
        try_class = AutomationInfo()
        mock_update_projects.assert_called()
        mock_set_prev_next.assert_called()
        self.assertEqual(try_class.today_year, datetime.datetime.today().strftime("%Y"))
        self.assertEqual(try_class.today_month, datetime.datetime.today().strftime("%m"))
        self.assertEqual(try_class.today_day, datetime.datetime.today().strftime("%d"))
        self.assertEqual(
            try_class.today,
            datetime.datetime(
                year=int(try_class.today_year),
                month=int(try_class.today_month),
                day=int(try_class.today_day),
            ),
        )

    @patch("github_interactions.automation_information.AutomationInfo.update_projects")
    def test_set_previous_current_and_next_sprint(self, mock_update_projects):
        # Creating an instance of the object with the method under test patched locally
        with patch(
            "github_interactions.automation_information.AutomationInfo.set_previous_current_and_next_sprint"
        ):
            try_class = AutomationInfo()
        mock_update_projects.assert_called()

        # Test the method with attributes patched
        sprint_id = "sprint_id"
        today_to_use = datetime.datetime(year=2025, month=2, day=20)
        previous_sprint = datetime.datetime(year=2025, month=1, day=1)
        current_sprint = datetime.datetime(year=2025, month=2, day=2)
        next_sprint = datetime.datetime(year=2025, month=3, day=3)
        sprint_start_dates = [previous_sprint, current_sprint, next_sprint]
        sprint_start_dates.sort()
        sprint_by_class = {}
        for start_date in sprint_start_dates:
            sprint_by_class[start_date.strftime("%Y_%m_%d")] = SprintInfo(
                {"name": start_date.strftime("%Y_%m_%d"), "id": sprint_id}
            )

        with (
            patch.object(try_class, "sprint_starts", sprint_start_dates),
            patch.object(try_class, "today", today_to_use),
            patch.object(try_class, "sprint_by_class", sprint_by_class),
        ):
            try_class.set_previous_current_and_next_sprint()
            self.assertEqual(try_class.current_sprint, current_sprint.strftime("%Y_%m_%d"))
            self.assertEqual(try_class.next_sprint, next_sprint.strftime("%Y_%m_%d"))
            self.assertEqual(try_class.previous_sprint, previous_sprint.strftime("%Y_%m_%d"))

    # Skipping the test below as there is nothing specific to test
    # def test_update_sprints(self):

    @requests_mock.mock()
    @patch(
        "github_interactions.automation_information.AutomationInfo.set_previous_current_and_next_sprint"
    )
    def test_update_projects(self, m, mock_set_prev_next):
        # This class to mock the project increment will generate suitable and predictable data using the information passed when called
        class MockPI:
            def __init__(
                self, project_id: int = 0, number: int = 0, title: str = "None", org_name: str = ""
            ):
                self.number = number
                self.title = title
                self.org = org_name
                self.project_id = project_id
                self.sprint_by_class = None
                self.start_date = datetime.datetime(
                    year=int(self.title[3:7]), month=int(self.title[8:]), day=1
                )
                self.all_sprint_starts = None

        # Create an instance with very little information and no calls to things which call the api
        m.post(url, text="Something", status_code=200)
        with patch("github_interactions.automation_information.AutomationInfo.update_projects"):
            try_class = AutomationInfo()
        mock_set_prev_next.assert_called()

        # Mock out Project Increment and the response for the organisations projects
        test_year = 2025
        pi_months = [2, 4, 6]
        extra_projects = 1

        project_increments = []
        projects = []
        expected_start_dates = []

        for month in pi_months:
            project_increments.append(f"PI_{test_year}_{month:02d}")
            projects.append(
                {
                    "title": f"PI_{test_year}_{month:02d}",
                    "id": f"project_id_{month}",
                    "number": month,
                    "template": False,
                    "closed": False,
                }
            )
            expected_start_dates.append(datetime.datetime(year=test_year, month=month, day=1))
        for ident in range(0, extra_projects):
            projects.append({"title": f"Extra one number {ident}"})

        expected_start_dates.sort()

        test_values_for_current_next = [
            {"test_month": 1, "proj_number": 0, "next_proj": 0},
            {"test_month": 2, "proj_number": 2, "next_proj": 4},
            {"test_month": 3, "proj_number": 2, "next_proj": 4},
            {"test_month": 4, "proj_number": 4, "next_proj": 6},
            {"test_month": 5, "proj_number": 4, "next_proj": 6},
        ]

        test_response = {"data": {"organization": {"projectsV2": {"nodes": projects}}}}
        m.post(url, text=json.dumps(test_response), status_code=200)

        for test_values in test_values_for_current_next:
            with (
                patch(
                    "github_interactions.project_increment_information.ProjectIncrement", new=MockPI
                ),
                patch.object(
                    try_class,
                    "today",
                    datetime.datetime(year=test_year, month=test_values["test_month"], day=1),
                ),
            ):
                try_class.update_projects()

                # Assertions to add - may need new calls to update_projects!
                # Available PIs as expected
                self.assertEqual(
                    list(try_class.available_program_increments.keys()), project_increments
                )

                # Available Starts as expected
                self.assertEqual(try_class.pi_starts, expected_start_dates)

                if test_values["proj_number"] == 0:
                    expected_proj_number = ""
                    expected_project = None
                else:
                    expected_proj_number = test_values["proj_number"]
                    expected_project = f"PI_2025_{test_values['proj_number']:02d}"

                if test_values["next_proj"] == 0:
                    expected_next_proj_number = None
                else:
                    expected_next_proj_number = f"PI_2025_{test_values['next_proj']:02d}"

                # Current, Next, and Project Number are all correct
                self.assertEqual(try_class.project_number, expected_proj_number)
                self.assertEqual(try_class.current_project, expected_project)
                self.assertEqual(try_class.next_project, expected_next_proj_number)

    # Skipping the test below as it is simply calling something else that is already tested
    # def test_get_cards_snapshot(self):

    # Skipping the test below as it is simply calling something else that is already tested
    # def test_get_sprint_columns_snapshot_html(self):

    # Skipping the test below as it is simply calling something else that is already tested
    # def test_get_planning_priority_snapshot(self):

    # Skipping the test below as it is simply calling something else that is already tested
    # def test_move_tickets_to_next_sprint(self):


class TestCardInfo(TestCase):
    # Test 1: Empty dict -> error
    def test_empty_card(self):
        self.assertRaises(KeyError, CardInfo, {})

    # Test 2: Issue with everything
    def test_issue_with_all(self):
        card_ident = 2
        repo_name = "Repo"
        expected_labels = {
            "label_1": "label_1_id",
            "label_2": "label_2_id",
            "label_3": "label_3_id",
        }
        sprint = "Sprint"
        status = "Status"
        points = 10
        priority = "Medium"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        class_response = CardInfo(
            issue_entry(
                ident=card_ident,
                content_id=f"issue_{card_ident}",
                labels=expected_labels,
                fields=provided_fields,
                repo_name=repo_name,
            )
        )
        self.assertEqual(class_response.node_id, f"node_{card_ident}")
        self.assertEqual(class_response.type, "ISSUE")
        self.assertEqual(class_response.id, f"issue_{card_ident}")
        self.assertEqual(class_response.number, card_ident)
        self.assertEqual(class_response.repo, repo_name)
        self.assertEqual(class_response.labels, list(expected_labels.keys()))
        self.assertEqual(class_response.name, str(card_ident))
        self.assertEqual(class_response.status, status)
        self.assertEqual(class_response.points, points)
        self.assertEqual(class_response.priority, priority)
        self.assertEqual(class_response.sprint, sprint)

    # Test 3: Issue with bare minimum
    def test_issue_with_minimum(self):
        card_ident = 3
        repo_name = "Repo"
        issue = {
            "id": f"node_{card_ident}",
            "type": "ISSUE",
            "content": {
                "number": card_ident,
                "title": f"Issue_{card_ident}",
                "labels": {"nodes": []},
                "repository": {"name": repo_name},
            },
            "fieldValues": {"nodes": []},
        }
        class_response = CardInfo(issue)
        self.assertEqual(class_response.node_id, f"node_{card_ident}")
        self.assertEqual(class_response.type, "ISSUE")
        self.assertEqual(class_response.id, None)
        self.assertEqual(class_response.number, card_ident)
        self.assertEqual(class_response.repo, repo_name)
        self.assertEqual(class_response.name, str(card_ident))
        self.assertEqual(class_response.labels, [])
        self.assertEqual(class_response.status, None)
        self.assertEqual(class_response.points, 0)
        self.assertEqual(class_response.sprint, None)

    # Test 4: DRAFT_ISSUE
    def test_draft_issue(self):
        card_ident = 4
        class_response = CardInfo(draft_issue_entry(card_ident, {}))
        self.assertEqual(class_response.node_id, f"node_{card_ident}")
        self.assertEqual(class_response.type, "DRAFT_ISSUE")
        self.assertEqual(class_response.id, f"draft_{card_ident}")
        self.assertEqual(class_response.number, f"Draft issue {card_ident}")
        self.assertEqual(class_response.repo, "draft")
        self.assertEqual(class_response.name, f"Draft issue {card_ident}")

    # Test 5: PULL_REQUEST
    def test_pull_request(self):
        card_ident = 5
        class_response = CardInfo(pull_request_entry(card_ident, {}))
        self.assertEqual(class_response.node_id, f"node_{card_ident}")
        self.assertEqual(class_response.type, "PULL_REQUEST")
        self.assertEqual(class_response.id, None)
        self.assertEqual(class_response.number, None)
        self.assertEqual(class_response.repo, None)
        self.assertEqual(class_response.name, "None")


class TestBoardChecks(TestCase):
    # Test 6: Multiple points labels
    @patch(
        "configparser.ConfigParser.__getitem__",
        return_value={
            "no_points_labels": "no_points_labels_allowed",
            "zero_points_labels": "zero_points_labels_allowed",
            "release_notes_repo": "Repo",
            "check_points_labels": "True",
        },
    )
    @patch("github_interactions.board_checks.BoardChecks.check_assignees")
    @patch("github_interactions.board_checks.BoardChecks.check_if_stale")
    @patch("github_interactions.board_checks.BoardChecks.check_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_present_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_release_note_prs")
    def test_number_of_points_labels_and_checking_points_labels(
        self, prs, release_notes, check_release_notes, check_stale, assignees, config_parser
    ):
        card_ident = 6
        card_title = f"{card_ident} - Issue {card_ident}"
        repo_name = "Repo"
        expected_labels = {
            "1": "label_1_id",
            "2": "label_2_id",
            "status": "status_label_id",
        }
        sprint = "Sprint"
        status = "Status"
        points = 2
        priority = "Medium"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        class_response = BoardChecks(
            [
                CardInfo(
                    issue_entry(
                        ident=card_ident,
                        content_id=f"issue_{card_ident}",
                        labels=expected_labels,
                        fields=provided_fields,
                        repo_name=repo_name,
                    )
                )
            ]
        )
        self.assertEqual(
            class_response.problem_text,
            [f"ERROR: Issue {card_title} in {repo_name} assigned to [] has multiple points labels"],
        )

    # Test 7: No points labels
    @patch(
        "configparser.ConfigParser.__getitem__",
        return_value={
            "no_points_labels": "no_points_labels_allowed",
            "zero_points_labels": "zero_points_labels_allowed",
            "release_notes_repo": "Repo",
            "check_points_labels": "True",
        },
    )
    @patch("github_interactions.board_checks.BoardChecks.check_assignees")
    @patch("github_interactions.board_checks.BoardChecks.check_if_stale")
    @patch("github_interactions.board_checks.BoardChecks.check_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_present_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_release_note_prs")
    def test_no_points_labels_and_checking_points_labels(
        self, release_notes, prs, check_notes, check_stale, assignees, config_parser
    ):
        card_ident = 7
        card_title = f"{card_ident} - Issue {card_ident}"
        repo_name = "Repo"
        expected_labels = {
            "label_1": "label_1_id",
            "label_2": "label_2_id",
            "status": "status_label_id",
        }
        sprint = "Sprint"
        status = "Status"
        points = 2
        priority = "Medium"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        class_response = BoardChecks(
            [
                CardInfo(
                    issue_entry(
                        ident=card_ident,
                        content_id=f"issue_{card_ident}",
                        labels=expected_labels,
                        fields=provided_fields,
                        repo_name=repo_name,
                    )
                )
            ]
        )
        self.assertEqual(
            class_response.problem_text,
            [
                f"ERROR: Issue {card_title} in {repo_name} assigned to [] has no points labels and it should have"
            ],
        )

    # Test 8: No points labels
    @patch(
        "configparser.ConfigParser.__getitem__",
        return_value={
            "no_points_labels": "no_points_labels_allowed",
            "zero_points_labels": "zero_points_labels_allowed",
            "release_notes_repo": "Repo",
            "check_points_labels": "True",
        },
    )
    @patch("github_interactions.board_checks.BoardChecks.check_assignees")
    @patch("github_interactions.board_checks.BoardChecks.check_if_stale")
    @patch("github_interactions.board_checks.BoardChecks.check_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_present_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_release_note_prs")
    def test_no_points_labels_permitted_and_checking_points_labels(
        self, release_notes, prs, check_notes, comment_stale, assignees, config_parser
    ):
        card_ident = 8
        repo_name = "Repo"
        expected_labels = {
            "label_1": "label_1_id",
            "label_2": "label_2_id",
            "no_points_labels_allowed": "no_points_labels_allowed",
            "status": "status_label_id",
        }
        sprint = "Sprint"
        status = "Status"
        points = 0
        priority = "Medium"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        class_response = BoardChecks(
            [
                CardInfo(
                    issue_entry(
                        ident=card_ident,
                        content_id=f"issue_{card_ident}",
                        labels=expected_labels,
                        fields=provided_fields,
                        repo_name=repo_name,
                    )
                )
            ]
        )
        self.assertEqual(class_response.problem_text, [])

    # Test 9: No points labels
    # Note Config Parser is a patch, so is not used directly but is needed in the called section
    @patch(
        "configparser.ConfigParser.__getitem__",
        return_value={
            "no_points_labels": "no_points_labels_allowed",
            "zero_points_labels": "zero_points_labels_allowed",
            "release_notes_repo": "Repo",
            "check_points_labels": "True",
        },
    )
    @patch("github_interactions.board_checks.BoardChecks.check_assignees")
    @patch("github_interactions.board_checks.BoardChecks.check_if_stale")
    @patch("github_interactions.board_checks.BoardChecks.check_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_present_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_release_note_prs")
    def test_zero_points_labels_permitted_and_checking_points_labels(
        self, prs, release_notes, check_notes, stale, assignees, config_parser
    ):
        card_ident = 9
        repo_name = "Repo"
        expected_labels = {
            "0": "0_point_label_id",
            "label_2": "label_2_id",
            "zero_points_labels_allowed": "zero_points_labels_allowed",
            "status": "status_label_id",
        }
        sprint = "Sprint"
        status = "Status"
        points = 0
        priority = "Medium"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        class_response = BoardChecks(
            [
                CardInfo(
                    issue_entry(
                        ident=card_ident,
                        content_id=f"issue_{card_ident}",
                        labels=expected_labels,
                        fields=provided_fields,
                        repo_name=repo_name,
                    )
                )
            ]
        )
        self.assertEqual(class_response.problem_text, [])

    # Test 10: Check Freshness by comment, ticket should error on the status value
    # Note Config Parser is a patch, so is not used directly but is needed in the called section
    @requests_mock.mock()
    @patch(
        "configparser.ConfigParser.__getitem__",
        return_value={
            "comment_errors": "comment:28",
            "label_warnings": "status check:7",
            "label_errors": "status check:28",
            "release_notes_repo": "Repo",
            "check_points_labels": "True",
        },
    )
    @patch("github_interactions.board_checks.BoardChecks.check_assignees")
    @patch("github_interactions.board_checks.BoardChecks.verify_card_pointing_correct")
    @patch("github_interactions.board_checks.BoardChecks.check_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_present_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_release_note_prs")
    def test_stale_comment_error(
        self, m, prs, release_notes, check_notes, pointing, assignees, config_parser
    ):
        card_ident = 10
        content_id = f"issue_{card_ident}"
        card_title = f"{card_ident} - Issue {card_ident}"
        repo_name = "Repo"
        expected_labels = {"status error": "Status Error ID", "comment": "comment ID for testing"}
        sprint = "Sprint"
        status = "Comment"
        points = 0
        priority = "Medium"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        today = datetime.datetime.today()
        recent_comment_date = today - datetime.timedelta(days=5)
        turning_comment_date = today - datetime.timedelta(days=28)
        old_comment_date = today - datetime.timedelta(days=50)
        date_format = "%Y-%m-%dT%H:%M:%SZ"
        m.post(
            url,
            text=build_response(
                QlCommand.find_last_comment,
                created_at=recent_comment_date.strftime(date_format),
                expected_labels=expected_labels,
            ),
        )
        class_response = BoardChecks(
            [
                CardInfo(
                    issue_entry(
                        ident=card_ident,
                        content_id=content_id,
                        labels=expected_labels,
                        fields=provided_fields,
                        repo_name=repo_name,
                    )
                )
            ]
        )
        self.assertEqual(class_response.problem_text, [])
        m.post(
            url,
            text=build_response(
                QlCommand.find_last_comment,
                created_at=turning_comment_date.strftime(date_format),
                expected_labels=expected_labels,
            ),
        )
        class_response.update_checks()
        self.assertTrue(
            f"ERROR: Issue {card_title} in {status} assigned to [] last had a comment added 28 days or more ago."
            in class_response.problem_text
        )
        m.post(
            url,
            text=build_response(
                QlCommand.find_last_comment,
                created_at=old_comment_date.strftime(date_format),
                expected_labels=expected_labels,
            ),
        )
        class_response.update_checks()
        self.assertTrue(
            f"ERROR: Issue {card_title} in {status} assigned to [] last had a comment added 28 days or more ago."
            in class_response.problem_text
        )

    # Test 11: Check Freshness by label added date
    # Note Config Parser is a patch, so is not used directly but is needed in the called section
    @requests_mock.mock()
    @patch(
        "configparser.ConfigParser.__getitem__",
        return_value={
            "comment_errors": "comment:28",
            "label_warnings": "status check:7",
            "label_errors": "status check:28",
            "release_notes_repo": "Repo",
            "check_points_labels": "True",
        },
    )
    @patch("github_interactions.board_checks.BoardChecks.check_assignees")
    @patch("github_interactions.board_checks.BoardChecks.verify_card_pointing_correct")
    @patch("github_interactions.board_checks.BoardChecks.check_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_present_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_release_note_prs")
    def test_stale_label_error(self, m, prs, notes, check_notes, points, assignees, config_parser):
        card_ident = 11
        card_title = f"{card_ident} - Issue {card_ident}"
        label_warning_at = 7
        label_error_at = 28
        content_id = f"issue_{card_ident}"
        repo_name = "Repo"
        sprint = "Sprint"
        status = "Status Check"
        points = 0
        priority = "Medium"
        label = "status check"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        expected_labels = {}
        today = datetime.datetime.today()
        stale_warning = today - datetime.timedelta(days=label_warning_at)
        stale_error = today - datetime.timedelta(days=label_error_at)
        date_format = "%Y-%m-%dT%H:%M:%SZ"

        # Check One - no issues
        expected_labels["status check"] = today.strftime(date_format)
        m.post(
            url,
            text=build_response(QlCommand.find_labels_added, expected_label_dates=expected_labels),
        )
        class_response = BoardChecks(
            [
                CardInfo(
                    issue_entry(
                        ident=card_ident,
                        content_id=content_id,
                        labels=expected_labels,
                        fields=provided_fields,
                        repo_name=repo_name,
                    )
                )
            ]
        )
        self.assertEqual(class_response.problem_text, [])

        # Check Two - Warning
        expected_labels["status check"] = stale_warning.strftime(date_format)
        m.post(
            url,
            text=build_response(QlCommand.find_labels_added, expected_label_dates=expected_labels),
        )
        class_response.update_checks()
        self.assertTrue(
            f"Warning: Issue {card_title} assigned to [] had {label} label added more than {label_warning_at} days ago."
            in class_response.problem_text
        )

        # Check Three - Error
        expected_labels["status check"] = stale_error.strftime(date_format)
        m.post(
            url,
            text=build_response(QlCommand.find_labels_added, expected_label_dates=expected_labels),
        )
        class_response.update_checks()
        self.assertTrue(
            f"ERROR: Issue {card_title} assigned to [] had {label} label added more than {label_error_at} days ago."
            in class_response.problem_text
        )

    # Test 12: No assignee allowed, and none given
    # Note Config Parser is a patch, so is not used directly but is needed in the called section
    @requests_mock.mock()
    @patch("github_interactions.board_checks.BoardChecks.get_present_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_release_note_prs")
    @patch("github_interactions.board_checks.BoardChecks.check_if_stale")
    @patch("github_interactions.board_checks.BoardChecks.check_release_notes")
    @patch(
        "configparser.ConfigParser.__getitem__",
        return_value={
            "allow_unassigned": "unassigned_allowed",
            "release_notes_repo": "Repo",
            "check_points_labels": "True",
        },
    )
    def test_check_assignees_unassigned_allowed(
        self, m, config_parser, check_notes, check_stale, prs, release_notes
    ):
        card_ident = 12
        repo_name = "Repo"
        expected_labels = {"5": "5", "unassigned_allowed": "status_label_id"}
        sprint = "Sprint"
        status = "unassigned_allowed"
        points = 0
        priority = "Medium"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        expected_assignees = []
        m.post(
            url,
            text=build_response(QlCommand.find_assignees, expected_assignees=expected_assignees),
        )
        class_response = BoardChecks(
            [
                CardInfo(
                    issue_entry(
                        ident=card_ident,
                        content_id=f"issue_{card_ident}",
                        labels=expected_labels,
                        fields=provided_fields,
                        repo_name=repo_name,
                    )
                )
            ]
        )
        self.assertEqual(class_response.problem_text, [])
        expected_assignees.append("Assignee 1")
        expected_assignees.append("Assignee 2")
        m.post(
            url,
            text=build_response(QlCommand.find_assignees, expected_assignees=expected_assignees),
        )
        class_response.update_checks()
        self.assertEqual(class_response.problem_text, [])

    # Test 13: No assignee allowed, and none given
    # Note Config Parser is a patch, so is not used directly but is needed in the called section
    @requests_mock.mock()
    @patch("github_interactions.board_checks.BoardChecks.get_present_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_release_note_prs")
    @patch("github_interactions.board_checks.BoardChecks.check_if_stale")
    @patch("github_interactions.board_checks.BoardChecks.check_release_notes")
    @patch(
        "configparser.ConfigParser.__getitem__",
        return_value={
            "allow_unassigned": "unassigned_allowed",
            "release_notes_repo": "Repo",
            "check_points_labels": "True",
        },
    )
    def test_check_assignees_when_required(
        self, m, config_parser, check_notes, check_stale, release_notes, prs
    ):
        card_ident = 13
        card_title = f"{card_ident} - Issue {card_ident}"
        repo_name = "Repo"
        expected_labels = {
            "5": "5",
            "assigned_required": "status_label_id",
        }
        sprint = "Sprint"
        status = "assigned_required"
        points = 0
        priority = "Medium"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        expected_assignees = []
        m.post(
            url,
            text=build_response(QlCommand.find_assignees, expected_assignees=expected_assignees),
        )
        class_response = BoardChecks(
            [
                CardInfo(
                    issue_entry(
                        ident=card_ident,
                        content_id=f"issue_{card_ident}",
                        labels=expected_labels,
                        fields=provided_fields,
                        repo_name=repo_name,
                    )
                )
            ]
        )
        self.assertTrue(
            f"ERROR: Issue {card_title} in {repo_name} with {status} status does not have anyone assigned."
            in class_response.problem_text
        )
        class_response.problem_text = []
        expected_assignees.append("Assignee 1")
        m.post(
            url,
            text=build_response(QlCommand.find_assignees, expected_assignees=expected_assignees),
        )
        class_response.update_checks()
        self.assertEqual(class_response.problem_text, [])
        expected_assignees.append("Assignee 2")
        m.post(
            url,
            text=build_response(QlCommand.find_assignees, expected_assignees=expected_assignees),
        )
        class_response.update_checks()
        self.assertEqual(class_response.problem_text, [])

    # Test 14: Don't check points
    # Note Config Parser is a patch, so is not used directly but is needed in the called section
    @patch(
        "configparser.ConfigParser.__getitem__",
        return_value={
            "no_points_labels": "no_points_labels_allowed",
            "zero_points_labels": "zero_points_labels_allowed",
            "release_notes_repo": "Repo",
            "check_points_labels": "False",
        },
    )
    @patch("github_interactions.board_checks.BoardChecks.check_assignees")
    @patch("github_interactions.board_checks.BoardChecks.check_if_stale")
    @patch("github_interactions.board_checks.BoardChecks.check_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_present_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_release_note_prs")
    def test_do_not_test_points_labels(
        self, prs, release_notes, check_notes, stale, assignees, config_parser
    ):
        card_ident = 9
        repo_name = "Repo"
        expected_labels = {
            "label_2": "label_2_id",
            "status": "status_label_id",
        }
        sprint = "Sprint"
        status = "Status"
        points = 0
        priority = "Medium"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        class_response = BoardChecks(
            [
                CardInfo(
                    issue_entry(
                        ident=card_ident,
                        content_id=f"issue_{card_ident}",
                        labels=expected_labels,
                        fields=provided_fields,
                        repo_name=repo_name,
                    )
                )
            ]
        )
        self.assertEqual(class_response.problem_text, [])

    # Test 15: Check Status and Labels match
    # Note Config Parser is a patch, so is not used directly but is needed in the called section
    @patch(
        "configparser.ConfigParser.__getitem__",
        return_value={
            "no_points_labels": "no_points_labels_allowed",
            "zero_points_labels": "zero_points_labels_allowed",
            "release_notes_repo": "Repo",
            "check_points_labels": "False",
        },
    )
    @patch("github_interactions.board_checks.BoardChecks.check_assignees")
    @patch("github_interactions.board_checks.BoardChecks.check_if_stale")
    @patch("github_interactions.board_checks.BoardChecks.check_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_present_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_release_note_prs")
    def test_check_status_and_labels_match(
        self, prs, release_notes, check_notes, stale, assignees, config_parser
    ):
        card_ident = 15
        repo_name = "Repo"
        expected_labels = {
            "status": "status_label_id",
            "another_label": "another_label_id",
        }
        sprint = "Sprint"
        status = "Status"
        points = 0
        priority = "Medium"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        class_response = BoardChecks(
            [
                CardInfo(
                    issue_entry(
                        ident=card_ident,
                        content_id=f"issue_{card_ident}",
                        labels=expected_labels,
                        fields=provided_fields,
                        repo_name=repo_name,
                    )
                )
            ]
        )
        self.assertEqual(class_response.problem_text, [])

    # Test 16: Check Status and Labels match
    # Note Config Parser is a patch, so is not used directly but is needed in the called section
    @patch(
        "configparser.ConfigParser.__getitem__",
        return_value={
            "no_points_labels": "no_points_labels_allowed",
            "zero_points_labels": "zero_points_labels_allowed",
            "release_notes_repo": "Repo",
            "check_points_labels": "False",
        },
    )
    @patch("github_interactions.board_checks.BoardChecks.check_assignees")
    @patch("github_interactions.board_checks.BoardChecks.check_if_stale")
    @patch("github_interactions.board_checks.BoardChecks.check_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_present_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_release_note_prs")
    def test_check_status_and_labels_match_ignore_done(
        self, prs, release_notes, check_notes, stale, assignees, config_parser
    ):
        card_ident = 16
        repo_name = "Repo"
        expected_labels = {
            "status": "status_label_id",
            "another_label": "another_label_id",
        }
        sprint = "Sprint"
        status = "Done"
        points = 0
        priority = "Medium"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        class_response = BoardChecks(
            [
                CardInfo(
                    issue_entry(
                        ident=card_ident,
                        content_id=f"issue_{card_ident}",
                        labels=expected_labels,
                        fields=provided_fields,
                        repo_name=repo_name,
                    )
                )
            ]
        )
        self.assertEqual(class_response.problem_text, [])

    # Test 17: Check Status and Labels match
    # Note Config Parser is a patch, so is not used directly but is needed in the called section
    @patch(
        "configparser.ConfigParser.__getitem__",
        return_value={
            "no_points_labels": "no_points_labels_allowed",
            "zero_points_labels": "zero_points_labels_allowed",
            "release_notes_repo": "Repo",
            "check_points_labels": "False",
        },
    )
    @patch("github_interactions.board_checks.BoardChecks.check_assignees")
    @patch("github_interactions.board_checks.BoardChecks.check_if_stale")
    @patch("github_interactions.board_checks.BoardChecks.check_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_present_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_release_note_prs")
    def test_check_status_and_labels_match_ignore_backlog(
        self, prs, release_notes, check_notes, stale, assignees, config_parser
    ):
        card_ident = 17
        repo_name = "Repo"
        expected_labels = {
            "status": "status_label_id",
            "another_label": "another_label_id",
        }
        sprint = "Sprint"
        status = "Backlog"
        points = 0
        priority = "Medium"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        class_response = BoardChecks(
            [
                CardInfo(
                    issue_entry(
                        ident=card_ident,
                        content_id=f"issue_{card_ident}",
                        labels=expected_labels,
                        fields=provided_fields,
                        repo_name=repo_name,
                    )
                )
            ]
        )
        self.assertEqual(class_response.problem_text, [])

    # Test 18: Check Status and Labels match
    # Note Config Parser is a patch, so is not used directly but is needed in the called section
    @patch(
        "configparser.ConfigParser.__getitem__",
        return_value={
            "no_points_labels": "no_points_labels_allowed",
            "zero_points_labels": "zero_points_labels_allowed",
            "release_notes_repo": "Repo",
            "check_points_labels": "False",
        },
    )
    @patch("github_interactions.board_checks.BoardChecks.check_assignees")
    @patch("github_interactions.board_checks.BoardChecks.check_if_stale")
    @patch("github_interactions.board_checks.BoardChecks.check_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_present_release_notes")
    @patch("github_interactions.board_checks.BoardChecks.get_release_note_prs")
    def test_check_status_and_labels_match_error(
        self, prs, release_notes, check_notes, stale, assignees, config_parser
    ):
        card_ident = 18
        repo_name = "Repo"
        expected_labels = {
            "mismatch": "status_label_id",
            "another_label": "another_label_id",
        }
        sprint = "Sprint"
        status = "Status"
        points = 0
        priority = "Medium"
        provided_fields = {
            "Points": points,
            "Planning Priority": priority,
            "Status": status,
            "Sprint": sprint,
        }
        class_response = BoardChecks(
            [
                CardInfo(
                    issue_entry(
                        ident=card_ident,
                        content_id=f"issue_{card_ident}",
                        labels=expected_labels,
                        fields=provided_fields,
                        repo_name=repo_name,
                    )
                )
            ]
        )
        expected_response = (
            f"Error: Issue {card_ident} - Issue {card_ident} does not have a "
            f"suitable label to match the current status of {status}"
        )
        self.assertEqual(class_response.problem_text, [expected_response])


class TestProjectIncrement(TestCase):
    # Test 1: There's an X in the title
    @requests_mock.mock()
    def test_x_in_title(self, m):
        default_pi = PiDefaultResponseValues()
        m.post(url, text=default_pi.response, status_code=200)
        title = "PI_2020_02X"
        test_class = ProjectIncrement(0, 0, title, "Org")
        self.assertEqual(test_class.title, title + " is not a Program Increment")
        self.assertEqual(test_class.year, "2000")
        self.assertEqual(test_class.month, "01")

    # Test 2: Not a PI Title
    @requests_mock.mock()
    def test_not_a_pi(self, m):
        default_pi = PiDefaultResponseValues()
        m.post(url, text=default_pi.response, status_code=200)
        title = "Example"
        test_class = ProjectIncrement(0, 0, title, "Org")
        self.assertEqual(test_class.title, title + " is not a Program Increment")
        self.assertEqual(test_class.year, "2000")
        self.assertEqual(test_class.month, "01")

    # Test 3: PI in Title but no date
    @requests_mock.mock()
    def test_incorrectly_named_pi(self, m):
        default_pi = PiDefaultResponseValues()
        m.post(url, text=default_pi.response, status_code=200)
        title = "PI_2020A_02A"
        test_class = ProjectIncrement(0, 0, title, "Org")
        self.assertEqual(test_class.title, title + " is not a Program Increment")
        self.assertEqual(test_class.year, "2000")
        self.assertEqual(test_class.month, "01")

    # Test 4: PI in Title with date
    @requests_mock.mock()
    def test_correctly_named_pi(self, m):
        default_pi = PiDefaultResponseValues()
        m.post(url, text=default_pi.response, status_code=200)
        title = "PI_2020_02"
        test_class = ProjectIncrement(0, 0, title, "Org")
        self.assertEqual(test_class.title, title)
        self.assertEqual(test_class.year, "2020")
        self.assertEqual(test_class.month, "02")

    # Test 5: Returned string
    @requests_mock.mock()
    def test_returned_string(self, m):
        default_pi = PiDefaultResponseValues()
        m.post(url, text=default_pi.response, status_code=200)
        title = "PI_2020_01"
        expected_string = "This is project increment: " + title
        test_class = ProjectIncrement(0, 0, title, "Org")
        self.assertEqual(str(test_class), expected_string)

    # Test 6: Get sprints and statuses
    @requests_mock.mock()
    def test_get_sprints_and_statuses(self, m):
        default_pi = PiDefaultResponseValues()
        m.post(url, text=default_pi.response, status_code=200)
        test_class = ProjectIncrement(0, 0, "Example", "Org")
        self.assertEqual(test_class.sprint_field_id, default_pi.sprint_field_id)
        self.assertEqual(test_class.status_field_id, default_pi.status_field_id)
        self.assertEqual(test_class.points_field_id, default_pi.points_field_id)
        self.assertDictEqual(test_class.sprint_ids, default_pi.sprints)
        self.assertDictEqual(test_class.status_ids, default_pi.statuses)
        self.assertEqual(test_class.first_sprint, default_pi.first_sprint)
        self.assertEqual(test_class.last_sprint, default_pi.last_sprint)


class TestRepoInfo(TestCase):
    @requests_mock.mock()
    def test_repo_info(self, m):
        repo_name = "repo_name"
        expected_labels = {
            "label_1": "label_1_id",
            "label_2": "label_2_id",
            "label_3": "label_3_id",
        }
        m.post(
            url,
            text=build_response(
                QlCommand.find_repo_info, repo_name=repo_name, expected_labels=expected_labels
            ),
            status_code=200,
        )
        test_class = RepoInfo("Org", repo_name)
        self.assertEqual(test_class.name, repo_name)
        self.assertEqual(test_class.labels, expected_labels)


class TestSprintInfo(TestCase):
    # Test 1 - Sprint of format Next PI (2020_04_04)
    def test_sprint_in_next_pi(self):
        sprint_name = "Next PI (2021_01_01)"
        sprint_id = "sprint_id"
        sprint = {"name": sprint_name, "id": sprint_id}
        test_class = SprintInfo(sprint)
        self.assertEqual(test_class.sprint_name, "2021_01_01")
        self.assertTrue(test_class.in_next_pi)
        self.assertEqual(test_class.sprint_year, "2021")
        self.assertEqual(test_class.sprint_month, "01")
        self.assertEqual(test_class.sprint_day, "01")
        self.assertEqual(test_class.sprint_id, sprint_id)
        self.assertEqual(test_class.sprint_start_date, datetime.datetime(2021, 1, 1, 0, 0))
        self.assertEqual(str(test_class), str(f"{datetime.datetime(2021, 1, 1, 0, 0)}"))

    # Test 2 - Standard sprint 2020_01_01
    def test_standard_sprint_name(self):
        sprint_name = "2021_02_02"
        sprint_id = "sprint_id"
        sprint = {"name": sprint_name, "id": sprint_id}
        test_class = SprintInfo(sprint)
        self.assertEqual(test_class.sprint_name, sprint_name)
        self.assertFalse(test_class.in_next_pi)
        self.assertEqual(test_class.sprint_year, "2021")
        self.assertEqual(test_class.sprint_month, "02")
        self.assertEqual(test_class.sprint_day, "02")
        self.assertEqual(test_class.sprint_id, sprint_id)
        self.assertEqual(test_class.sprint_start_date, datetime.datetime(2021, 2, 2, 0, 0))
        self.assertEqual(str(test_class), str(f"{datetime.datetime(2021, 2, 2, 0, 0)}"))

    # Test 3 - Not a date
    def test_incorrect_name(self):
        sprint_name = "Not a sprint"
        sprint_id = "sprint_id"
        sprint = {"name": sprint_name, "id": sprint_id}
        test_class = SprintInfo(sprint)
        self.assertEqual(test_class.sprint_name, sprint_name)
        self.assertFalse(test_class.in_next_pi)
        self.assertEqual(test_class.sprint_year, "Not ")
        self.assertEqual(test_class.sprint_month, " s")
        self.assertEqual(test_class.sprint_day, "rint")
        self.assertEqual(test_class.sprint_id, sprint_id)
        self.assertEqual(test_class.sprint_start_date, datetime.datetime(2020, 1, 1, 0, 0))
        self.assertEqual(str(test_class), str(f"{datetime.datetime(2020, 1, 1, 0, 0)}"))
