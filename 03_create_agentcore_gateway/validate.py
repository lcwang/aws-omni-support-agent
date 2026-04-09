import json
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
with open("target_config.json") as f:
    data = json.load(f)
print("JSON valid, tools:", len(data["lambdaTarget"]["toolSchema"]["inlinePayload"]))
