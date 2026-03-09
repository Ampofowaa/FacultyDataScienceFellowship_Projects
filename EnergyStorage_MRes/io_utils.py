import csv

def write_policy_dict_to_csv(policy_dict, filename):

    header = [
        "t","battery","demand","renewable","buy_price","sell_price",
        "energy_bought","energy_sold","energy_stored","energy_lost"
    ]

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for state, action in policy_dict.items():
            writer.writerow((*state, *action))