# Ty-Rex 🦖

Agent RAG spécialisé dans le métier d'OPC (Ordonnancement, Pilotage et Coordination) et le secteur de la construction.

## Stack Technique
* **Backend :** FastAPI (Python), LangChain, Agent LLM OpenAI
* **Frontend :** Next.js (TypeScript)

## Organisation de la base de données
* **PDFs :** ChromaDB et embeddings
* **CRs et plannings :** Parquet pour maintenir la structure des tableaux

## Fonctionnalités principales
* **Analyse documentaire métier :** Lecture et traitement de PDF, de comptes-rendus de réunion au format tabulaire, et d'extraits Excel de plannings MSProject.
* **Recherche intelligente :** Capacité pour l'agent de retrouver et d'interroger dynamiquement les documents indexés.
* **Interface interactive :** Chat en temps réel avec support des tableaux source et gestion de l'historique conversationnel.

## Démarrage rapide

### 1. Backend 
cd fastapi-backend
uvicorn main:app --reload

### 2. Frontend
cd frontend
npm run dev
