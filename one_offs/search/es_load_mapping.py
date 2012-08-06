import pyes, json

mapping = json.load(open("es_mapping.json"))
conn = pyes.ES(['localhost:9500'])
conn.create_index("regulations")
print conn.put_mapping("document", mapping["document"], ["regulations"])