class CardInfo:
    def __init__(self, card):
        self.node_id = card["id"]
        self.type = card["type"]
        try:
            self.id = card["content"]["id"]
        except KeyError:
            self.id = None
        self.labels = []
        match self.type:
            case "DRAFT_ISSUE":
                self.number = card["content"]["title"]
                self.repo = "draft"
            case "ISSUE":
                self.number = card["content"]["number"]
                self.repo = card["content"]["repository"]["name"]
                try:
                    for label in card["content"]["labels"]["nodes"]:
                        self.labels.append(label["name"])
                except KeyError:
                    # Section is empty ignore it
                    pass
            case "PULL_REQUEST":
                # These are not handled yet
                self.number = None
                self.repo = None
            case _:
                self.number = None
                self.repo = None
        self.name = str(self.number)
        field_values = card["fieldValues"]["nodes"]
        self.status = None
        self.sprint = None
        self.points = 0
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
