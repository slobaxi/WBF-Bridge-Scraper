IMP_TABLE = [
    (20, 1), (50, 2), (90, 3), (130, 4), (170, 5), (220, 6), (270, 7),
    (320, 8), (370, 9), (430, 10), (500, 11), (600, 12), (750, 13),
    (900, 14), (1100, 15), (1300, 16), (1500, 17), (1750, 18),
    (2000, 19), (2250, 20), (2500, 21), (3000, 22), (3500, 23),
    (4000, 24)
]

def score_to_imps(diff):
    diff = abs(diff)
    for threshold, imps in IMP_TABLE:
        if diff < threshold:
            return imps
    return 25   # max

def calculate_imps(user_score, table_score):
    return score_to_imps(user_score - table_score)
