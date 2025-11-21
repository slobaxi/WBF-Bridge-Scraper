function calculate(board) {
    let payload = {
        board: board,
        contract: document.getElementById("contract-" + board).value,
        declarer: document.getElementById("decl-" + board).value,
        tricks: document.getElementById("tricks-" + board).value
    };

    fetch("/calculate", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(result => {
        document.getElementById("yourscore-" + board).innerText = result.your_score;
        document.getElementById("officialscore-" + board).innerText = result.official_score;
        document.getElementById("diff-" + board).innerText = result.difference;
        document.getElementById("imps-" + board).innerText = result.imps;
    });
}
