# check_db.py
from src.chroma_backend import SKAChromaManager

db = SKAChromaManager()

print(f"Total chunks in Ops Collection: {db.ops_collection.count()}")
print(f"Total chunks in ICD Collection: {db.icd_collection.count()}")

# Fetch all metadata records to see exactly what filenames are inside Chroma right now
all_ops = db.ops_collection.get(include=["metadatas"])
if all_ops and all_ops["metadatas"]:
    indexed_files = set(m["source"] for m in all_ops["metadatas"] if m and "source" in m)
    print(f"\nFiles actually indexed in Ops right now:\n{indexed_files}")
else:
    print("\nOps database is completely empty.")
