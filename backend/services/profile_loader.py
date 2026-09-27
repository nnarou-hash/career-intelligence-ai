import json
import os

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)


def load_candidate_profile():

    path = os.path.join(_DATA_DIR, "candidate_profile.json")
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)