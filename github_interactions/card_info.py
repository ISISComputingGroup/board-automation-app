class CardInfo:
    def __init__(self, card):
        self.node_id = card["id"]
        self.type = card["type"]
        try:
            self.id = card["content"]["id"]
        except KeyError:
            self.id = None
        self.labels = []
        self.assignees = []
        match self.type:
            case "DRAFT_ISSUE":
                self.number = card["content"]["title"]
                self.repo = "draft"
                self.title = f"DRAFT - {card['content']['title']}"
            case "ISSUE":
                self.number = card["content"]["number"]
                self.repo = card["content"]["repository"]["name"]
                self.title = f"{card['content']['number']} - {card['content']['title']}"
                try:
                    for label in card["content"]["labels"]["nodes"]:
                        self.labels.append(label["name"])
                except KeyError:
                    # Section is empty ignore it
                    pass
                try:
                    for assignee in card["content"]["assignees"]["edges"]:
                        if assignee["node"]["name"] is None:
                            self.assignees.append(assignee["node"]["login"])
                        else:
                            self.assignees.append(assignee["node"]["name"])
                except KeyError:
                    pass
            case "PULL_REQUEST":
                # These are not handled yet
                self.number = None
                self.repo = None
                self.title = "Pull Request"
            case _:
                self.number = None
                self.repo = None
                self.title = "Unknown"
        self.name = str(self.number)
        field_values = card["fieldValues"]["nodes"]
        self.status = None
        self.sprint = None
        self.points = 0
        self.priority = None
        for value in field_values:
            try:
                match value["field"]["name"]:
                    case "Sprint":
                        self.sprint = value["name"]
                    case "Status":
                        self.status = value["name"]
                    case "Points":
                        self.points = value["number"]
                    case "Planning Priority":
                        self.priority = value["name"]
                    case _:
                        pass
            except KeyError:
                pass

    def __str__(self):
        return self.name
