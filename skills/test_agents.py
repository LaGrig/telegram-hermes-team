import yaml

with open("agents/team.yaml", "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

print("Список агентов Hermes:")
for agent in data["agents"]:
    print(f"- {agent['name']} ({agent['role']})")
