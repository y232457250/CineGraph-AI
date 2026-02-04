import chromadb
client = chromadb.PersistentClient(path="data/chroma_db")
collection = client.get_collection("mashup_lines")
# 查看前10条
results = collection.peek(10)
print(results)