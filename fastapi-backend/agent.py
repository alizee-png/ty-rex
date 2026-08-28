from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from config import llm
from tools.tools import query_chroma, query_parquet, compare_plannings, search_documents

tools = [query_chroma, query_parquet, compare_plannings, search_documents]


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "Tu es un agent supervisant l'analyse de données de projets de construction (BTP)."
                "Tu es concis et précis."
                "Ton but est d'analyser la requête utilisateur et d'utiliser l'outil adapté pour y répondre."

                "Si des informations critiques sont manquantes pour exécuter un outil, demande une précision à l'utilisateur avant d'agir. \n"
                "Utilise search_documents pour associer la requête de l'utilisateur à un fichier."

                "REGLES STRICTES pour répondre à l'utilisateur :\n"
                    "Donne d'abord une réponse synthétique à la question utilisateur, puis cite tes sources."

                 "Quand tu utilises compare_plannings :"
                    "Quand l'utilisateur ne donne pas le nom exact des plannings, utilise search_documents pour essayer de déduire le nom des fichiers."
                    "Demande TOUJOURS à l'utilisateur confirmation du nom des fichiers à utiliser et quel est le planning source. "
                    "Dans ta réponse utilisateur, concentre-toi UNIQUEMENT sur les modifications apportées au planning source."
                    "- deleted_lines_md : indique quelles lignes ont été supprimées"
                    "- Colonne 'Analyse' de analysis_table_md : indique quelles lignes ont été ajoutées"
                    "- Colonne 'Différence' de analysis_table_md : indique le décalage temporel entre deux tâches"
                    "- Si la valeur dans la colonne 'Différence' est NEGATIVE, la tâche est en avance"
                    "- Si la valeur dans la colonne 'Différence' est POSITIVE, la tâche est en retard"
                    "- Si la valeur dans la colonne 'Différence' est positive et la colonne 'Analyse' indique 'Nouvelle ligne', la tâche n'est PAS en retard"
                    

                "Quand tu utilises query_parquet :"
                    "Répond de manière synthétique mais cite les dates exactes."
                    "- Source à citer : Nom du ou des documents. \n"

                "Quand tu utilises query_main_documentation :"
                    "Répond de manière synthétique."
                    "- Source à citer : Nom du document et la page\n"


                

            ),
        ),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False, handle_parsing_errors=True)

#si router trop peu efficace, réfléchir à créer un router selon mots-clés dans requête utilisateur
#télécharger = ingestion
#cr, compterendus = query_report
#à écrire puisqu'on a sorti l'ingestion du truc 

if __name__ == "__main__":
    # Test RAG
    # agent_executor.invoke({"input": "Que disent nos documents sur la procédure d'ingestion ?"})
    
    # Test Analyse Parquet
    # agent_executor.invoke({"input": "Donne-moi un aperçu des données du fichier planning.parquet"})
    
    # Test Calcul
    # agent_executor.invoke({"input": "Combien font (450 * 12) / 3.5 ?"})
    
    # Test Internet
    agent_executor.invoke({"input": "Que dit sur le CR sur le mur de soutènement ?"})
