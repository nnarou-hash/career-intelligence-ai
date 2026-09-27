import json


def load_candidate_profile():

    with open("data/candidate_profile.json", "r", encoding="utf-8") as file:
        return json.load(file)