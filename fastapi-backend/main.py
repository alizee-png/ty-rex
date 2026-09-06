import shutil
import traceback
import json
from pathlib import Path

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, UploadFile
from pydantic import BaseModel
from typing import Any, Optional, List

from ingestion_pipeline.parser_router import ParserRouter
from ingestion_pipeline.populate_database import populate_database
from ingestion_pipeline.operate_database import get_indexed_documents, delete_document_from_db
from agent import agent_executor
from config import DATA_DIR
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


app = FastAPI()
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#--- schéma données
class Message(BaseModel):
    role: str 
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]

#--- endpoints
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print("--- ERREUR 422 DÉTAILLÉE ---")
    print("Erreurs :", exc.errors())
    print(" Corps reçu :", exc.body)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )


#--- endpoints

#root
@app.get("/")
def read_root():
    return {"message": "FastAPI backend is running"}

#answering the chat
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    current_user_message = next(
        (msg.content for msg in reversed(request.messages) if msg.role == "user"),
        None,
    )
    if not current_user_message:
        raise HTTPException(status_code=400, detail="Le message utilisateur est vide.")


    result = agent_executor.invoke({"input": current_user_message})

    # 1. Le texte de synthèse rédigé par l'agent
    synthesis_text = result.get("output", "")

    print(synthesis_text)

    # 2. Extraction des tableaux et des documents des étapes intermédiaires
    collected_tables = []
    collected_documents = []
    intermediate_steps = result.get("intermediate_steps", [])
    
    for action, tool_output in intermediate_steps:

        if isinstance(tool_output, dict):
            if "tables" in tool_output:
                collected_tables.extend(tool_output["tables"])
            if "documents" in tool_output:
                collected_documents.extend(tool_output["documents"])

    print(collected_tables)
    print(collected_documents)

    # 3. Réponse unifiée complète conforme au contrat
    return {
        "message": synthesis_text,
        "tables": collected_tables,
        "documents": collected_documents
    }

#upload file to databse
@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(...), #obligatoire 
    sheet_name: Optional[str] = Form(None),  #requis si .xlsx
    table_number: Optional[str] = Form(None),  #requis si .docx
    template: Optional[str] = Form(None),  #requis si doc_type == "cr"
):

    allowed_extensions = [".pdf", ".docx", ".xls", ".xlsx", ".eml", ".msg"]

    #check if file has a name
    if not file.filename:
        raise HTTPException(status_code=400, detail="Le fichier envoyé n'a pas de nom valide.")

    file_ext = Path(file.filename).suffix.lower()

    #check if extension is valid
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Format non supporté. Formats acceptés : {allowed_extensions}",)

    #check if needed metadata is precised for each extension
    if (file_ext in [".xlsx", ".xls"] and doc_type == "tableau") and not sheet_name:
        raise HTTPException(status_code=400, detail="Le champ 'Onglet' est obligatoire pour les fichiers Excel.",)

    if file_ext == ".docx" and table_number is None:
        raise HTTPException(status_code=400, detail="Le champ 'N° tableau' est obligatoire pour les fichiers Word.",)

    if doc_type == "tableau" and not template:
        raise HTTPException(status_code=400, detail="Le champ 'Modèle' est obligatoire pour les compte-rendus (cr).",)

    #path to save the file
    file_path = Path(DATA_DIR) / file.filename

    #copying the file into data directory
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    #gestion du template
    template_list = []
    if template:
        try:
            template_list = json.loads(template)
        except json.JSONDecodeError:
            template_list = [t.strip() for t in template.split(",")]

    print("TYPE de template_list :", type(template_list))
    print("CONTENU de template_list :", template_list)

    #clean kwargs
    kwargs = {
        k: v
        for k, v in {
            "sheet_name": sheet_name,
            "table_number": int(table_number) if table_number else None,
            "template": template_list,
        }.items()
        if v is not None
    }

    print(kwargs)

    try:

        router = ParserRouter()
        
        with open(file_path, "rb") as file_obj:
            parsed_data = router.parse(
                file_obj=file_obj,
                filename=file_path.name,
                doc_type=doc_type,
                **kwargs,
            )

            print(parsed_data)

        populate_database(parsed_data)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement du document : {str(e)}",)

    return {
        "status": "success",
        "filename": file.filename,
        "content_type": file.content_type,
        "message": "Fichier ajouté à la database avec succès.",
    }

#show docs in database
@app.get("/api/documents")
async def list_documents():
    try:
        documents = get_indexed_documents()
        print("DEBUG - Documents lus :", documents) # <--- Regarde ton terminal ici
        return {
            "status": "success",
            "count": len(documents),
            "documents": documents
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des documents : {str(e)}")

#delete doc in database
@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    # Supprime du dossier data + retire les embeddings dans ChromaDB
    delete_document_from_db(filename)
    return {"status": "deleted", "filename": filename}