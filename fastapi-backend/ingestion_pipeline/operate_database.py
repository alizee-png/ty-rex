import pandas as pd
from pathlib import Path
from typing import Dict, List
from config import PARQUET_DB_DIR, document_vector_store, mail_vector_store

def get_indexed_documents(include_mails: bool = True, include_documents: bool = True, include_parquet: bool = True) -> List[dict]:

    indexed_docs: Dict[str, dict] = {}

    

    #simplification écriture ?
    '''    collection = mail_vector_store._collection
    raw_results = collection.get(limit=30) # On récupère un échantillon large pour le filtrer ensuite'''

    #chromadb - documents
    if include_documents:
        try:
            data = document_vector_store.get(include=["metadatas"])
            metadatas = data.get("metadatas", [])

            if metadatas:
                for meta in metadatas:
                    if not meta:
                        continue

                    filename = meta.get("filename")
                    doc_type = meta.get("type")

                    if filename and filename not in indexed_docs:
                        indexed_docs[filename] = {
                            "filename": filename,
                            "type": doc_type,
                            "storage": "chromadb",
                        }

        except Exception as e:
            print(f"Avertissement lors de la lecture des documents ChromaDB : {e}")

    #chromadb - mails
    if include_mails:
        try:
            data = mail_vector_store.get(include=["metadatas"])
            metadatas = data.get("metadatas", [])

            if metadatas:
                for meta in metadatas:
                    if not meta:
                        continue

                    filename = meta.get("filename")
                    doc_type = meta.get("type")

                    if filename and filename not in indexed_docs:
                        indexed_docs[filename] = {
                            "filename": filename,
                            "type": doc_type,
                            "storage": "chromadb",
                        }

        except Exception as e:
            print(f"Avertissement lors de la lecture des mails ChromaDB : {e}")

    #parquet
    if include_parquet:
        parquet_path = Path(PARQUET_DB_DIR)

        if parquet_path.exists():
            for parquet_file in parquet_path.rglob("*.parquet"):

                template = ""
                filename = ""
                doc_type = ""
                
                try:
                    df_meta = pd.read_parquet(parquet_file)

                    if not df_meta.empty:
                        first_row = df_meta.iloc[0]
                        template = first_row.get("template", "")
                        filename = first_row.get("filename", "")
                        doc_type = first_row.get("type", parquet_file.parent.name)
                        
                except Exception as e:
                    print(f"Erreur lors de la lecture des métadonnées de {parquet_file}: {e}")
                    pass

                if filename and filename not in indexed_docs:
                    indexed_docs[filename] = {
                        "filename": filename,
                        "type": doc_type,
                        "template" : template,
                        "storage": "parquet",

                    }

    return list(indexed_docs.values())


def delete_document_from_db(filename: str) -> bool:

    deleted = False

    #parquet
    base_dir = Path(PARQUET_DB_DIR)

    matching_files = list(base_dir.rglob(filename))

    if matching_files:
        #parquet
        for parquet_path in matching_files:
            if parquet_path.is_file():
                parquet_path.unlink()
                deleted = True
                print(f"Fichier supprimé de parquet : {parquet_path}")
    else:
        #documents chromadb
        try:
            results = document_vector_store.get(where={"filename": filename})
            ids_to_delete = results.get("ids", [])

            if ids_to_delete:
                document_vector_store.delete(ids=ids_to_delete)
                deleted = True
                print(f"Fichier supprimé de chromadb : {filename}")

        except Exception as e:
            print(f"Erreur lors de la suppression des documents ChromaDB : {e}")

        #mails chromadb
        try:
            results = mail_vector_store.get(where={"filename": filename})
            ids_to_delete = results.get("ids", [])

            if ids_to_delete:
                mail_vector_store.delete(ids=ids_to_delete)
                deleted = True
                print(f"Fichier supprimé de chromadb : {filename}")

        except Exception as e:
            print(f"Erreur lors de la suppression des mails ChromaDB : {e}")

    return deleted