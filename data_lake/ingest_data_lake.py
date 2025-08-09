import os
import shutil
import json

def create_data_lake_directory():
    data_lake_path = "data_lake"
    if not os.path.exists(data_lake_path):
        os.makedirs(data_lake_path)
    return data_lake_path

def ingest_file_to_data_lake(src_path, data_lake_path):
    if os.path.exists(src_path):
        filename = os.path.basename(src_path)
        dest_path = os.path.join(data_lake_path, filename)
        shutil.copy2(src_path, dest_path)
        return filename
    else:
        return None

def create_catalog(data_lake_path, files):
    catalog = []
    for file in files:
        file_path = os.path.join(data_lake_path, file)
        if os.path.exists(file_path):
            file_info = {
                "filename": file,
                "size_bytes": os.path.getsize(file_path),
                "path": file_path
            }
            catalog.append(file_info)
    catalog_path = os.path.join(data_lake_path, "catalog.json")
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=4)
    return catalog_path

def main():
    data_lake_path = create_data_lake_directory()
    # List of source data files to ingest
    source_files = [
        "data/knowledge.txt",
        "data/customer_support_knowledge_base.xlsx",
        "data/customer_knowledge_base.xlsx"
    ]
    ingested_files = []
    for src_file in source_files:
        filename = ingest_file_to_data_lake(src_file, data_lake_path)
        if filename:
            ingested_files.append(filename)
    catalog_path = create_catalog(data_lake_path, ingested_files)
    print(f"Data lake ingestion complete. Catalog created at {catalog_path}")

if __name__ == "__main__":
    main()
