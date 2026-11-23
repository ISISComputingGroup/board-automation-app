import datetime


class SprintInfo:
    def __init__(self, values: dict):
        if "Next" in values["name"]:
            self.sprint_name = values["name"][9:-1]
            self.in_next_pi = True
        else:
            self.sprint_name = values["name"]
            self.in_next_pi = False
        self.sprint_year = self.sprint_name[:4]
        self.sprint_month = self.sprint_name[5:7]
        self.sprint_day = self.sprint_name[8:]
        self.sprint_id = values["id"]
        try:
            self.sprint_start_date = datetime.datetime(
                year=int(self.sprint_year), month=int(self.sprint_month), day=int(self.sprint_day)
            )
        except ValueError:
            self.sprint_start_date = datetime.datetime(year=2020, month=1, day=1)

    def __str__(self):
        return str(self.sprint_start_date)
