from pathlib import Path

# Imports de tes modules internes
from ingestion_pipeline.parser_router import ParserRouter
from ingestion_pipeline.populate_database import populate_database
from agent import agent_executor


def run_pipeline_test():
    # 1. Instanciation des composants
    router = ParserRouter()
    agent = agent_executor

    """BASE_DIR = Path(__file__).resolve().parent
    test_file_path = BASE_DIR / "data" / "planning_old.xlsx"

    print(f"Chemin recherché : {test_file_path}")
    print(f"Le fichier existe ? {test_file_path.exists()}")

    doc_type = "planning"
    kwargs = {
        "sheet_name": "CR",
        "template": ["Noté le", "Sujet", "Par", "Pour le", "Fait le"],
    }

    # Ouverture en binaire (BinaryIO) comme le fera FastAPI
    with open(test_file_path, "rb") as file_obj:
        parsed_data = router.parse(
            file_obj=file_obj,
            filename=test_file_path.name,
            doc_type=doc_type,
            **kwargs,
        )

    print(f"✅ Parsing réussi pour '{test_file_path.name}' !")
    print("Données extraites (aperçu) :")
    print(str(parsed_data)[:300])  # Affiche les 300 premiers caractères
    print("\n" + "=" * 40 + "\n")

    populate_database(parsed_data)"""

    # 3. Test de l'Agent avec les données extraites
    print("--- 2. TEST AGENT ---")
    question = "Quelles différences entre le plg planning_new (source) et planning_old ?"

    print(f"Question : {question}")

    answer = agent.invoke({"input" : question})

    print("\nRéponse de l'agent :")
    print(answer)

if __name__ == "__main__":
    run_pipeline_test()

















"""import requests

# URL de ton serveur FastAPI
BASE_URL = "http://localhost:8000"


def test_ingestion_excel():
    1. Test de l'ingestion d'un fichier Excel avec métadonnées.
    print("--- 1. Test Ingestion Excel ---")

    file_path = "exemple_cr.xlsx"  # Remplace par un vrai fichier de test

    with open(file_path, "rb") as f:
        # Envoi via multipart/form-data
        files = {"file": (file_path, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {
            "doc_type": "report",
            "sheet_name": "CR",
            "template": ["Noté le", "Sujet", "Par", "Pour le", "Fait le"],
        }

        response = requests.post(f"{BASE_URL}/ingest", files=files, data=data)

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    assert response.status_code == 200, "L'ingestion a échoué"


def test_ask_agent():
    2. Test de la requête RAG / Agent.
    print("--- 2. Test Question Agent ---")

    payload = {
        "question": "Donne-moi les tâches du lot 1.",
        "top_k": 3,
    }

    response = requests.post(f"{BASE_URL}/chat", json=payload)

    print(f"Status: {response.status_code}")
    print(f"Réponse Agent: {response.json()}\n")
    assert response.status_code == 200, "Le chat a échoué"


if __name__ == "__main__":
    test_ingestion_excel()
    test_ask_agent()"""