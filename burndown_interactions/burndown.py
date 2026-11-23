from datetime import datetime, timedelta
import logging
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import graph_ql_interactions.card_interactions as cards


pm_logger = logging.getLogger("board_automation")


class Burndown:
    def __init__(
        self,
        org_name: str,
        project_number: str,
        current_sprint_name: str,
        next_sprint_name: str,
        sprints: dict,
    ):
        self.fig = go.Figure()
        self.org_name = org_name
        self.project_number = project_number
        self.current_sprint_name = current_sprint_name
        self.next_sprint_name = next_sprint_name
        self.sprints = sprints
        self.csv_headings = "Date,Backlog,In Progress,Impeded,Review,Done\n"
        self.burndown_csv = os.path.join(f"{os.path.dirname(__file__)}", "burndown-points.csv")
        if sprints:
            self.update_display()
        else:
            pm_logger.exception("Burndown unavailable as no sprints available")

    def burndown_display(self):
        return self.fig.to_html()

    def update_display(self):
        if self.sprints:
            # print(self.current_sprint_name + " to " + self.next_sprint_name)

            start_date = self.sprints[self.current_sprint_name].sprint_start_date
            end_date = self.sprints[self.next_sprint_name].sprint_start_date

            df = self.get_data_frame()
            start_index = 0

            dates = df["Date"][start_index:]
            last_line_index = len(dates)
            last_day = datetime.strptime(df["Date"][start_index + last_line_index - 1], "%Y-%m-%d")

            done = df["Done"].values[start_index:]
            backlog = df["Backlog"].values[start_index:]
            in_progres = df["In Progress"].values[start_index:]
            impeded = df["Impeded"].values[start_index:]
            review = df["Review"].values[start_index:]

            for i in range(1, (end_date - start_date).days + 1):
                dates = np.append(dates, [(last_day + timedelta(days=i)).strftime("%Y-%m-%d")])
                if i > last_line_index:
                    done = np.append(done, [done[-1]])
                    backlog = np.append(backlog, [backlog[-1]])
                    in_progres = np.append(in_progres, [in_progres[-1]])
                    impeded = np.append(impeded, [impeded[-1]])
                    review = np.append(review, [review[-1]])

            fig = go.Figure(
                data=[
                    go.Bar(
                        name="Done",
                        x=dates,
                        y=done,
                        text=done,
                        offsetgroup=0,
                        marker=dict(color="#0052CC"),
                    ),
                    go.Bar(
                        name="Review",
                        x=dates,
                        y=review,
                        text=review,
                        offsetgroup=0,
                        base=done,
                        marker=dict(color="#5319E7"),
                    ),
                    go.Bar(
                        name="Impeded",
                        x=dates,
                        y=impeded,
                        text=impeded,
                        offsetgroup=0,
                        base=review + done,
                        marker=dict(color="#B60205"),
                    ),
                    go.Bar(
                        name="In Progress",
                        x=dates,
                        y=in_progres,
                        text=in_progres,
                        offsetgroup=0,
                        base=impeded + review + done,
                        marker=dict(color="#0E8A16"),
                    ),
                    go.Bar(
                        name="Backlog",
                        x=dates,
                        y=backlog,
                        text=backlog,
                        offsetgroup=0,
                        base=in_progres + impeded + review + done,
                        marker=dict(color="#B816A5"),
                    ),
                ],
                layout=go.Layout(
                    title="Sprint Tracking",
                    legend=dict(
                        traceorder="reversed",
                    ),
                ),
            )

            fig.update_layout(showlegend=True)
            self.fig = fig
        else:
            with open(
                os.path.join(f"{os.path.dirname(__file__)}", "burndown_unavailable"), "r"
            ) as f:
                self.fig = f.read()

    def add_new_csv_line(self):
        # Build the string for adding to the CSV file
        card_frequency = cards.get_number_of_cards_by_status(
            org_name=self.org_name,
            project_number=self.project_number,
            sprint=self.current_sprint_name,
        )
        today = datetime.today().strftime("%Y-%m-%d")
        entry_list = [
            today,
            ",",
            str(card_frequency["Backlog"]),
            ",",
            str(card_frequency["In Progress"]),
            ",",
            str(card_frequency["Impeded"]),
            ",",
            str(card_frequency["Review"]),
            ",",
            str(card_frequency["Done"]),
            "\n",
        ]
        entry = "".join(entry_list)
        with open(self.burndown_csv, "a") as f:
            f.write(entry)

    def fill_csv_lines(self, today: datetime, last_day_inner: datetime, data: pd.Series):
        for missing_day in range((today - last_day_inner).days - 1):
            with open(self.burndown_csv, "a") as f:
                entry_list = [
                    (last_day_inner + timedelta(days=(missing_day + 1))).strftime("%Y-%m-%d"),
                    ",",
                    str(data["Backlog"]),
                    ",",
                    str(data["In Progress"]),
                    ",",
                    str(data["Impeded"]),
                    ",",
                    str(data["Review"]),
                    ",",
                    str(data["Done"]),
                    "\n",
                ]
                entry = "".join(entry_list)
                f.write(entry)

    def add_csv_titles(self):
        with open(self.burndown_csv, "w") as f:
            f.write(self.csv_headings)

    def get_data_frame(self):
        today = datetime.strptime(datetime.today().strftime("%Y-%m-%d"), "%Y-%m-%d")

        # Make sure the file exists and has something in it (start for today)
        try:
            df = pd.read_csv(self.burndown_csv)
        except (pd.errors.EmptyDataError, FileNotFoundError):
            self.add_csv_titles()
            self.add_new_csv_line()
            return pd.read_csv(self.burndown_csv)

        # Get the last day listed in the file
        start_index = 0
        dates = df["Date"][start_index:]
        last_line_index = len(dates)
        try:
            last_day = datetime.strptime(df["Date"][start_index + last_line_index - 1], "%Y-%m-%d")
        except KeyError:
            # if there is no data just add for today
            self.add_new_csv_line()
            return pd.read_csv(self.burndown_csv)

        if not (
            self.sprints[self.current_sprint_name].sprint_start_date
            < last_day
            < self.sprints[self.next_sprint_name].sprint_start_date
        ):
            pm_logger.exception("Burndown CSV overwritten due to out of date information")
            self.add_csv_titles()
            self.add_new_csv_line()

        if today > last_day:
            if (today - last_day).days > 1:
                self.fill_csv_lines(today, last_day, df.iloc[-1])
            self.add_new_csv_line()

        return pd.read_csv(self.burndown_csv)

    def change_sprint(
        self,
        current_sprint_name: str,
        next_sprint_name: str,
    ):
        # As the titles assume a non-existent file this will overwrite the file contents with
        # just the titles
        self.current_sprint_name = current_sprint_name
        self.next_sprint_name = next_sprint_name
        self.add_csv_titles()
