from dotenv import load_dotenv

#from langchain_ollama import OllamaEmbeddings
#from langchain_ollama import ChatOllama
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
import pandas as pd

DATA_DIR = "./data"
CHROMA_DB_DIR = "./chroma_db"
PARQUET_DB_DIR = "./parquet_db"

DEFAULT_DATE = pd.Timestamp('1970-01-01 00:00:00')

"""embeddings = OllamaEmbeddings(model="nomic-embed-text")
llm = ChatOllama(model="llama3.1", temperature=0)"""

load_dotenv()
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
llm = ChatOpenAI(model="gpt-4o", temperature=0.0)

document_vector_store = Chroma(
    collection_name="documentation_mission",
    embedding_function=embeddings,
    persist_directory=str(CHROMA_DB_DIR)
)

mail_vector_store = Chroma(
    collection_name="mails_produits",
    embedding_function=embeddings,
    persist_directory=str(CHROMA_DB_DIR)
)

#documents partagés à l'échelle de l'entreprise
'''general_documentation_vector_store = Chroma(
    collection_name="documents_generaux",
    embedding_function=embeddings,
    persist_directory=str(CHROMA_DB_DIR)
)'''

