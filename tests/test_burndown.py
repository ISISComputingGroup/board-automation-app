from unittest import TestCase
from unittest.mock import mock_open, patch

import requests_mock
from datetime import datetime
import pandas as pd
import pandas.testing as pd_testing

from tests.test_helpers import build_response, QlCommand
from burndown_interactions.burndown import Burndown
from github_interactions.sprint_information import SprintInfo


class TestBurndown(TestCase):
    # Not writing the test below as this is a figure generation inbuilt to an imported library
    # def test_burndown_display(self):

    # Given the complexity of building a figure, at present this will not be tested explicitly
    # def test_update_display(self):

    @requests_mock.mock()
    def test_add_new_csv_line(self, m):
        expected_snapshot = {
            "ready": {"count": 3, "points": 3},
            "rework": {"count": 1, "points": 1},
            "in_progress": {"count": 2, "points": 2},
            "impeded": {"count": 1, "points": 1},
            "review": {"count": 3, "points": 3},
            "done": {"count": 4, "points": 4},
        }
        alternative = [datetime.today().strftime("%Y-%m-%d")]
        for entry in expected_snapshot:
            if entry == "rework":
                continue
            alternative.append(",")
            alternative.append(str(expected_snapshot[entry]["count"]))
        alternative.append("\n")
        sprint_name = "sprint"
        m.post(
            "https://api.github.com/graphql",
            text=build_response(
                QlCommand.find_card_info,
                card_type="points_snapshot",
                expected_snapshot=expected_snapshot,
                sprint_name=sprint_name,
            ),
        )
        test_class = Burndown(
            org_name="",
            project_number="",
            current_sprint_name=sprint_name,
            next_sprint_name="",
            sprints={},
        )
        open_mock = mock_open()
        with patch("builtins.open", open_mock, create=True):
            test_class.add_new_csv_line()
        open_mock.assert_called_with(test_class.burndown_csv, "a")
        open_mock.return_value.write.assert_called_once_with("".join(alternative))

    def test_fill_csv_lines(self):
        # No missing days
        test_class = Burndown(
            org_name="", project_number="", current_sprint_name="", next_sprint_name="", sprints={}
        )
        # fill_csv_lines(today: datetime, last_day_inner: datetime, data: pd.DataFrame)
        test_year = 2025
        test_month = 2
        today_to_use = datetime(year=test_year, month=test_month, day=3)
        last_entry_day_to_use = datetime(year=test_year, month=test_month, day=1)
        data = [[last_entry_day_to_use, 1, 2, 3, 4, 5]]
        df = pd.DataFrame(
            data, columns=["Date", "Backlog", "In Progress", "Impeded", "Review", "Done"]
        )
        entry_list = [
            (datetime(year=test_year, month=test_month, day=2)).strftime("%Y-%m-%d"),
            ",",
            str(df["Backlog"]),
            ",",
            str(df["In Progress"]),
            ",",
            str(df["Impeded"]),
            ",",
            str(df["Review"]),
            ",",
            str(df["Done"]),
            "\n",
        ]
        entry = "".join(entry_list)
        open_mock = mock_open()
        with patch("builtins.open", open_mock, create=True):
            # noinspection bad-argument-type
            test_class.fill_csv_lines(today_to_use, last_entry_day_to_use, df)
        open_mock.assert_called_with(test_class.burndown_csv, "a")
        open_mock.return_value.write.assert_called_with(entry)

    def test_add_csv_titles(self):
        test_class = Burndown(
            org_name="", project_number="", current_sprint_name="", next_sprint_name="", sprints={}
        )
        open_mock = mock_open()
        with patch("builtins.open", open_mock, create=True):
            test_class.add_csv_titles()
        open_mock.assert_called_with(test_class.burndown_csv, "w")
        open_mock.return_value.write.assert_called_once_with(test_class.csv_headings)

    def test_get_data_frame(self):
        sprints = {}
        sprint_start_dates = ["2025_01_01", "2025_02_01"]
        for start_date in sprint_start_dates:
            sprints[start_date] = SprintInfo({"name": start_date, "id": "sprint"})
        with patch("burndown_interactions.burndown.Burndown.update_display"):
            test_class = Burndown(
                org_name="",
                project_number="",
                current_sprint_name="2025_01_01",
                next_sprint_name="2025_02_01",
                sprints=sprints,
            )
        data = [["2025-01-01", 4, 5, 7, 6, 2], ["2025-01-02", 2, 4, 7, 7, 8]]
        df = pd.DataFrame(
            data, columns=["Date", "Backlog", "In Progress", "Impeded", "Review", "Done"]
        )
        file_content = """Date,Backlog,In Progress,Impeded,Review,Done\n2025-01-01,4,5,7,6,2\n2025-01-02,2,4,7,7,8"""
        open_mock = mock_open(read_data=file_content)
        with (
            patch.object(test_class, "burndown_csv", ""),
            patch("builtins.open", open_mock),
            patch("burndown_interactions.burndown.Burndown.add_csv_titles"),
            patch("burndown_interactions.burndown.Burndown.add_new_csv_line"),
            patch("burndown_interactions.burndown.Burndown.update_display"),
        ):
            pd_testing.assert_frame_equal(test_class.get_data_frame(), df)

    def test_change_sprint(self):
        test_class = Burndown(
            org_name="", project_number="", current_sprint_name="", next_sprint_name="", sprints={}
        )
        open_mock = mock_open()
        with patch("builtins.open", open_mock, create=True):
            test_class.change_sprint(current_sprint_name="", next_sprint_name="")
        open_mock.assert_called_with(test_class.burndown_csv, "w")
        open_mock.return_value.write.assert_called_once_with(test_class.csv_headings)
