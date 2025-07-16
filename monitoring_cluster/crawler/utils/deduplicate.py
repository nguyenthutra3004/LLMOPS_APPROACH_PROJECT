import json

data = dict()

with open("link_tg.jsonl", "r") as f:
    for line in f:
        try:
            page = json.loads(line)
            data[page["link"]] = page
        except:
            pass

with open("link_tg.jsonl", "w") as f:
    for key, val in data.items():
        f.write(json.dumps(val) + "\n")
        