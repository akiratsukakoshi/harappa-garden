from modules.freee_client import FreeeClient

client = FreeeClient()
sections = client.get_sections()

print("ID, Name")
for section in sections:
    print(f"{section['id']}, {section['name']}")
