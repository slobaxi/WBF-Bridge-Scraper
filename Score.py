
class Score:
    def __init__(self):
        self.BoardNumber = None
        self.Table = None
        self.Home_Team = None
        self.Visiting_Team = None
        self.Room = None
        self.Contract = None
        self.Declarer = None
        self.Lead = None
        self.Tricks = None
        self.NS = None
        self.EW = None
        self.Home_Result = None
        self.Vis_Result = None

    def __str__(self):
        values = [
            self.BoardNumber,
            self.Table,
            self.Home_Team,
            self.Visiting_Team,
            self.Room,
            self.Contract,
            self.Declarer,
            self.Lead,
            self.Tricks,
            self.NS,
            self.EW,
            self.Home_Result,
            self.Vis_Result
        ]
        return " ".join("" if v is None else str(v) for v in values)