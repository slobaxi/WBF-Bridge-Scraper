import pandas as pd
from Score import Score

def load_scores_from_excel(path: str):
    df = pd.read_excel(path)
    scores = []

    for _, row in df.iterrows():
        s = Score()
        s.BoardNumber   = int(row.get("BoardNumber"))
        s.Table         = row.get("Table")
        s.Home_Team     = row.get("Home_Team")
        s.Visiting_Team = row.get("Visiting_Team")
        s.Room          = row.get("Room")
        s.Contract      = row.get("Contract")
        s.Declarer      = row.get("Declarer")
        s.Lead          = row.get("Lead")
        s.Tricks        = row.get("Tricks")

        # Handle NS and EW safely
        ns = row.get("NS")
        ew = row.get("EW")

        if pd.notna(ns):
            s.NS = int(ns)
        if pd.notna(ew):
            s.EW = int(ew)

        # Derive the missing one
        if pd.isna(ns):
            s.NS = s.EW * -1
        else:
            s.EW = s.NS * -1

        scores.append(s)

    return scores
