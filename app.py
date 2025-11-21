from flask import Flask, render_template, request, jsonify
from importer import load_scores_from_excel
from ButlerCalulator import calculate_imps
from matchpointCalculator import calculate_mps

app = Flask(__name__)
all_scores = load_scores_from_excel("scores.xlsx")


# ------------ Tournament ------------
@app.route("/")
@app.route("/tournament")
def tournament_page():
    # dedupe boards
    seen = {}
    for s in all_scores:
        seen[s.BoardNumber] = s
    boards = list(seen.values())

    return render_template("tournament.html",
                           title="Tournament",
                           boards=boards)


# ------------ Board Details ------------
@app.route("/board/<int:board_number>")
def board_detail(board_number):
    boards = [s for s in all_scores if s.BoardNumber == board_number]

    return render_template("board_detail.html",
                           title=f"Board {board_number}",
                           boards=boards)


# ------------ AJAX API ------------
@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.json
    board = data["board"]
    contract = data["contract"]
    declarer = data["declarer"]
    tricks = int(data["tricks"])

    your_score = calculate_imps(contract, declarer, tricks)
    official_score = next(s.NS for s in all_scores if s.BoardNumber == board)

    diff = your_score - official_score
    imps = calculate_imps(diff)

    return jsonify({
        "your_score": your_score,
        "official_score": official_score,
        "difference": diff,
        "imps": imps
    })


if __name__ == "__main__":
    app.run(debug=True)
