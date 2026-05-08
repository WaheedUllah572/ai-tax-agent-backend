import json
import os

FILE = "vendor_memory.json"

def load_memory():
    if not os.path.exists(FILE):
        return {}
    return json.load(open(FILE))


def save_memory(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)


def learn_vendor(vendor, category):
    data = load_memory()
    data[vendor] = category
    save_memory(data)


def get_vendor_category(vendor):
    data = load_memory()
    return data.get(vendor)