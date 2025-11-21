

def calculate_mps(user_score, all_scores):
    better = sum(1 for s in all_scores if user_score > s)
    equal  = sum(1 for s in all_scores if user_score == s)
    total  = len(all_scores) - 1

    return (better + 0.5 * equal) / total
