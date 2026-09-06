from pathlib import Path
from typing import Any,  Dict

from config import PARQUET_DB_DIR, vector_store


def populate_database(parsed_data: Dict[str, Any]):

    documents = []

    if parsed_data["metadata"]["type"] in {"tableau", "planning"}:

        df = parsed_data["content"]
        filename = parsed_data["metadata"]["filename"]
        parquet_repertory = parsed_data["metadata"]["type"]

        base_filename = Path(filename).stem

        parquet_dir = Path(PARQUET_DB_DIR) / parquet_repertory
        parquet_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = parquet_dir / f"{base_filename}.parquet"
        df.to_parquet(parquet_path, index=False)

    else:
        chunks = parsed_data["content"]
        file_metadata = parsed_data["metadata"]

        for chunk in chunks:
            chunk.metadata.update(file_metadata)

        vector_store.add_documents(chunks)


