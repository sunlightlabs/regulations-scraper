import pyes

conn = pyes.ES(['localhost:9500'])
print conn.delete_index_if_exists("regulations")
