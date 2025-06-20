from langchain_groq import ChatGroq
from langgraph.graph import StateGraph
import pickle
from typing import TypedDict, Annotated, List
from langgraph.graph.message import add_messages
import geocoder
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langchain_community.utilities import GoogleSerperAPIWrapper
import requests
from bs4 import BeautifulSoup
import re
import json
from dotenv import load_dotenv
load_dotenv()
import os
import requests
import streamlit as st
import re
from jinja2 import Template
from PIL import Image
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
#from langchain.embeddings import OpenAIEmbeddings
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain.schema import Document
import io


llm_70b = ChatGroq(model="llama-3.3-70b-versatile", api_key=st.secrets["GROQ"]["GROQ_API_KEY"])
llm_8b = ChatGroq(model="llama-3.1-8b-instant", api_key=st.secrets["GROQ"]["GROQ_API_KEY"])


def get_user_location():
    """
    Ottieni la posizione dell'utente tramite IP.
    
    Returns:
        tuple: Latitudine e longitudine dell'utente o None se non disponibile.
    """
    location = geocoder.ip('me')
    return location.latlng if location.latlng else (None, None)


def process_pdf_emergency(file_path):
    """
    Carica e processa un file PDF per estrarre il contenuto delle pagine desiderate.

    Args:
        file_path (str): Percorso al file PDF.

    Returns:
        str: Testo processato e unificato delle pagine selezionate.
    """
    print('process_pdf_emergency')
    loader = PyPDFLoader(file_path)
    pages = loader.load()[40:]
    full_text = "\n".join([doc.page_content for doc in pages])
    full_text = full_text.replace("MANUALE PER GLI INCARICATI DI PRIMO SOCCORSO", "")
    full_text = full_text.replace("LE POSIZIONI DI SICUREZZA", "")
    full_text = full_text.replace("APPARATO VISIVO", "")
    full_text = full_text.replace("APPARATO UDITIVO", "")
    full_text = full_text.replace("SISTEMA NERVOSO - anatomia", "")
    full_text = full_text.replace("IL SISTEMA NERVOSO\n", "")
    full_text = full_text.replace("-\n", "")
    # Espressione regolare per identificare titoli in maiuscolo (che terminano con \n)
    main_title_pattern = r'(?:\n|^)([A-Z\s\’\’]+(?:\n[A-Z\s\’\’]+)*)\n'
    sub_section_pattern = r'(?:^|\n)([a-z]\))'  # Per riconoscere sottosezioni come "a)" o "b)"
    degree_section_pattern = r'(?:^|\n)([IV]+\s+GRADO)'

    # Mappa dei numeri di pagina
    page_number_map = []
    for page in pages:
        page_number_map.append({"text": page.page_content, "page_number": page.metadata["page"]})

    # Trova tutti i titoli principali
    matches = list(re.finditer(main_title_pattern, full_text))
    documents = []
    current_content = ""
    current_title = None
    current_page = None

    for i in range(len(matches)):
        # Ottieni il titolo corrente
        title_start = matches[i].start()
        title_end = matches[i].end()
        title = full_text[title_start:title_end].strip()

        # Determina il contenuto fino al prossimo titolo principale o alla fine del testo
        if i + 1 < len(matches):
            content_start = title_end
            content_end = matches[i + 1].start()
            content = full_text[content_start:content_end].strip()
        else:
            content = full_text[title_end:].strip()

        # Trova il numero di pagina del titolo corrente
        if current_page is None:
            for page in page_number_map:
                if title in page["text"]:
                    current_page = page["page_number"]
                    break

        # Accorpa sottosezioni (es: "a)", "b)", "I GRADO", "II GRADO") al contenuto principale
        content_lines = content.split("\n")
        organized_content = []
        current_subsection = None

        for line in content_lines:
            # Riconosci sottosezioni come "a)", "b)"
            if re.match(sub_section_pattern, line):
                current_subsection = line
                organized_content.append(f"\n{line}")
            # Riconosci sezioni come "I GRADO", "II GRADO"
            elif re.match(degree_section_pattern, line):
                current_subsection = line
                organized_content.append(f"\n{line}")
            elif current_subsection:
                # Accorpa le righe successive alla sottosezione corrente
                organized_content[-1] += f" {line.strip()}"
            else:
                # Accorpa al contenuto principale
                organized_content.append(line.strip())

        content = "\n".join(organized_content)

        # Salva il documento precedente
        if current_title:
            documents.append({"title": current_title, "page_content": current_content, "page_nr": current_page})

        # Inizia un nuovo documento
        current_title = title
        current_content = content
        current_page = None  # Reset del numero di pagina

    # Salva l'ultimo documento
    if current_title:
        documents.append({"title": current_title, "page_content": current_content, "page_nr": current_page})

    # Converti in oggetti Document compatibili con LangChain
    documents = [
        Document(
            page_content=doc["page_content"],
            metadata={"title": doc["title"], "page_nr": doc["page_nr"]}
        )
        for doc in documents
    ]
    return documents


def create_bm25_retriever_emergency(pdf_file_path, bm25_index_path):
    """
    Crea o carica un retriever BM25.

    Args:
        documents (list): Lista di documenti da indicizzare.
        bm25_index_path (str): Percorso per salvare o caricare l'indice BM25.

    Returns:
        BM25Retriever: Un retriever BM25.
    """
    # Se esiste un file salvato, carica il retriever
    if os.path.exists(bm25_index_path):
        #print("Caricamento retriever BM25 esistente.")
        with open(bm25_index_path, "rb") as f:
            bm25_retriever = pickle.load(f)
            bm25_retriever.k = 3
            documents = []
    else:
        #print("Creazione di un nuovo retriever BM25.")
        # Creazione del retriever BM25
        documents = process_pdf_emergency(pdf_file_path)
        bm25_retriever = BM25Retriever.from_documents(documents)
        bm25_retriever.k = 3
        # Salva il retriever
        with open(bm25_index_path, "wb") as f:
            pickle.dump(bm25_retriever, f)
    
    return bm25_retriever, documents


def create_emergency_retriever(pdf_file_path,  bm25_index_path, faiss_path):
    # Step 1: Configura l'indice BM25 per i titoli
    bm25_retriever, documents = create_bm25_retriever_emergency(pdf_file_path, bm25_index_path)
    # Step 2: Configura FAISS per i contenuti
    embedding = OpenAIEmbeddings(api_key=st.secrets["OPENAI"]["OPENAI_API_KEY"])
    if os.path.exists(faiss_path):
        vectorstore = FAISS.load_local(faiss_path, embeddings=embedding, allow_dangerous_deserialization=True)
        print('load emergency retriever')
    else:
        if documents:
            vectorstore = FAISS.from_documents(documents, embedding=embedding)
            vectorstore.save_local(faiss_path)
        else:
            documents = process_pdf_emergency(pdf_file_path)
            vectorstore = FAISS.from_documents(documents, embedding=embedding)
            vectorstore.save_local(faiss_path)
    similarity_retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": 4})

    # Step 3: Configura un MultiRetriever
    ensemble_retriever = EnsembleRetriever(retrievers=[
        bm25_retriever,
        similarity_retriever
    ], weights=[0.3, 0.7])
    return ensemble_retriever


class AgentState(TypedDict):
    query: str
    full_query:str
    severity: int
    messages: Annotated[list, add_messages]
    prompt: Template

    rag_answer : str
    ensemble_retriever : EnsembleRetriever

    keywords_youtube: str
    search_results: str
    video_title:str
    youtube_api_key : str
    retry_count_youtube: int

    google_maps_api_key : str
    google_maps_url: str
    user_location : List[str]
    hospital_name : str
    
    
    web_search_keywords : str
    retry_count_web_search : int
    web_answer : str

    final_result: List[str]


def answer_from_rag(state:AgentState):
    log_state("answer_from_rag", state)
    full_query = state['full_query']
    ensemble_retriever = state['ensemble_retriever']
    #retrieved_docs = ensemble_retriever.invoke(full_query)
    #retrieved_info = [doc.page_content for doc in retrieved_docs[:2]]
    prompt = state['prompt'].render(full_query=full_query, retrieved_info=None)
    response = llm_70b.invoke([HumanMessage(content=prompt)]).content.strip()
    print(f"response: {response}")
    return {"rag_answer" : response, "full_query" : full_query}


def log_state(node_name, state:AgentState):
    print(f"Node '{node_name}' State: {state}")


def web_search(state: AgentState) -> str:
    """
    Searches the Internet to retrieve reliable and certified information related to a specific medical query.

    Args:
        query (str): A simplified string, optimized for an effective Google search based on the user's query.

    Returns:
        str: A string containing useful and relevant information retrieved from certified websites related to the user's query. 
             If no pertinent information is found, it returns a message indicating the absence of results.
    """
    # Fase 1: Ricerca su Internet
    log_state("web_search", state)
    query = state['web_search_keywords']
    if not isinstance(query, str):
        return "Nessun contenuto pertinente trovato su Internet"
    compliant_links = ['webmd', 'mayoclinic']
    serper = GoogleSerperAPIWrapper(api_key=os.environ["SERPER_API_KEY"])
    try:
        search_results = serper.results(query)['organic']
        # Filtra e seleziona un link per ciascun dominio compliant
        selected_links = []
        for domain in compliant_links:
            for result in search_results:
                if domain in result['link']:
                    selected_links.append(result['link'])
                    break  # Esci dal ciclo per passare al prossimo dominio

        general_content = []
        selected_links = [selected_links[0]]
        for url in selected_links:
            try:
                # Effettua una richiesta al sito
                response = requests.get(url)
                response.raise_for_status()  # Controlla se la richiesta è andata a buon fine
                
                # Analizza il contenuto della pagina con BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Estrai il contenuto principale della pagina (potresti dover adattare il selettore)
                page_content = soup.get_text(separator=' ', strip=True)
                
                general_content.append(page_content)

            except requests.exceptions.RequestException as e:
                print(f"NO Info")
        return {"web_info" : general_content}
    except:
        return {"web_info" : "NO Info"}
    

def extract_keywords_web_search(state:AgentState):
   log_state("extract_keywords_web_search", state)
   query = state['full_query']
   previous_keywords = state.get('web_search_keywords', '')
    # Costruisci il prompt
   prompt = f"""You are a highly skilled virtual assistant with expertise in first aid. Your task is to extract the most relevant medical keywords from the user's query. These keywords will help optimize searches for first aid guidance on various websites. Follow these instructions carefully:
    
    1. **Understand User Needs:** Analyze the user query to understand the specific medical needs or issues.
    2. **Focus on Medical Relevance:** Extract only essential information about the medical issue or injury, including:
    - Type of injury or symptom (e.g., "cut," "burn," "panic attack").
    - Cause of the issue, if specified (e.g., "knife," "hot water," "bee sting").
    3. **Omit redundant or irrelevant details:** Ignore unnecessary context, such as who the injury happened to or extraneous background information.
    4. **Output format:** Return the result strictly as a JSON object with the key 'keywords' containing the extracted keywords. **Do not include any other text outside the JSON object.**""" + \
    """
    1. Query: "I am feeling anxious, I think I am having a panic attack. What should I do?"  
   Output : {"keywords": "panic attack, first aid"}

    2. Query: "What should I do if I get stung by a bee?"  
    Output : {"keywords": "bee sting, first aid"}

    3. Query: "How do I treat a deep cut from a knife?"  
    Output : {"keywords": "deep cut knife, first aid"}

    4. Query: "How do I treat a burn from boiling water?"  
    Output : {"keywords": "boiling water burn, first aid"}

    5. Query: "What should I do in case of a sudden allergic reaction?"  
    Output : {"keywords": "allergic reaction, first aid"}

    6. Query: "A friend of mine is having a panic attack"  
    Output : {"keywords": "panic attack, first aid"}
    """

   if previous_keywords:
        prompt += f" Previous search with keywords '{previous_keywords}' returned no results. Try a different search query."
    
   prompt += f"""    ### Input:
   Query: '{query}'

    Return the data strictly as a JSON object, with the following structure:
    {
        "keywords": "allergic reaction help, first aid"
    }
    """
        
   # Chiamata al modello LLM
   response = llm_70b.invoke([HumanMessage(content=prompt)])
   return {"web_search_keywords": json.loads(response.content)["keywords"], "retry_count_web_search" : state["retry_count_web_search"]+1}


# Funzione per controllare se continuare
def should_continue_web_search(state:AgentState):
    web_search_results = state.get('web_answer', '')
    #log_state("should_continue_web_search", state)
    #print(state['retry_count_web_search'])
    retry_count_web_search = state.get('retry_count_web_search', 0)
    if (not web_search_results or web_search_results == "NO Info") and retry_count_web_search <2:
        # Incrementa il contatore dei retry
        return "retry"
    return "end"


# Funzione per controllare se continuare
def should_web_search(state:AgentState):
    rag_answer = state.get('rag_answer', '')
    if not rag_answer or "no info available" in rag_answer.lower():
        return "web_search"
    return "end"


def extract_keywords_youtube(state:AgentState):
   log_state("extract_keywords_youtube", state)
   query = state['full_query']
   previous_keywords = state.get('keywords_youtube', '')
    # Costruisci il prompt
   prompt = f"""From the following user medical situation: '{query}', extract the most relevant keywords to optimize the search for a video on YouTube. 
    Return just a Json object with the key: 'keywords'
    Here are examples of user queries and the corresponding optimized output:""" + \
    """
    1. Query: "I am feeling anxious, I think I am having a panic attack. What should I do?" 
       Output : {"keywords": "panic attack, first aid"}
    2. Query: "What should I do if I get stung by a bee?"
       Output : {"keywords": "bee sting treatment, first aid"}
    3. Query: "Cosa succede se sono stato punto da un ape?"
       Output : {"keywords": "bee sting treatment, first aid"}
    3. Query: "How to treat a deep cut made with a knife?"
       Output : {"keywords": "knife deep cut treatment, first aid"}
    4. Query: "How to treat a burn from boiling water?"
       Output : {"keywords": "boiling water burn, first aid"}
    5. Query: "What to do in case of a sudden allergic reaction?"
       Output : {"keywords": "allergic reaction help, first aid"} 
    
    ### Output:
    Return strictly as a JSON object in form of, in form:
    {"keywords": "allergic reaction help, first aid"}

    """

   if previous_keywords:
        prompt += f" Previous search with keywords '{previous_keywords}' returned no results. Try a different search query."
   
    # Chiamata al modello LLM
   response = llm_70b.invoke([HumanMessage(content=prompt)])
   return {"keywords_youtube": json.loads(response.content)["keywords"], "retry_count_youtube" : state["retry_count_youtube"]+1}


# Funzione per controllare se continuare
def should_continue_youtube(state:AgentState):
    search_results = state.get('search_results', '')
    retry_count_youtube = state.get('retry_count_youtube', 0)
    if (not search_results or "No videos found" in search_results) and retry_count_youtube <2:
        return "retry"
    return "end"


# Funzione per controllare se continuare
def should_find_hospital(state:AgentState):
    severity = state.get('severity')
    if severity>2:
        return "high_severity"
    return "low_severity"


def create_response_from_web_search(state:AgentState):
    web_info = state.get('web_info', '')
    query = state.get('full_query', '')
    prompt = f"""Using the following context: {web_info}, provide a detailed and comprehensive response to the user query: "{query}". Focus on offering practical and actionable support for someone already facing the issue. Avoid mentioning precautions unless explicitly relevant to resolving the problem. Ensure your answer is clear, accurate, and concise, and limit it in a range of 400-1000 words."""
    response = llm_70b.invoke([HumanMessage(content=prompt)])
    return {"web_answer" : response.content}


def search_youtube_videos(state:AgentState) -> str:
    """
    Cerca video su YouTube da una lista certificata di canali affidabili.

    Args:
        query (str): Una versione semplificata e in inglese, adatta per una ricerca su youtube, della query di ricerca fornita dall'utente.

    Returns:
        str: Un di link utile rispetto alla query, o un messaggio che indica che non sono stati trovati video.
    """
    #log_state("search_youtube_videos", state)
    keywords = state['keywords_youtube']
    print(f"keywords: {keywords}")
    if not isinstance(keywords, str):
        return "Nessun video pertinente trovato per la query specificata nei canali consentiti."
    YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
    allowed_channels=['UCwywRelPfy7U8jAI312J_Xw', #First Aid,
                      'UCQK834Q3xqlo85LJqrEd7fw' #ChatterDocs
                      ]  #'UCTVZkcCKSqFD0TTJ8BjYLDQ' Croce Rossa, 
    max_results = 3
    prompt = """
    You are tasked with determining if a YouTube video is relevant to a described medical situation. The situation provides details about a **medical problem affecting a person**. Analyze the situation and the video title, and decide if the video could be useful. Respond strictly with "YES" or "NO". Do not provide explanations or additional information.

    ### Guidelines:
    1. Assume the described situation pertains to a medical issue involving a person unless explicitly stated otherwise.
    2. Focus only on the **relevance** of the video to the medical situation described.
    3. Base your decision solely on the details provided in the medical situation and the video title.
    4. Respond with **"YES"** or **"NO"** only. Do not provide any explanations.

    ### Input Format:
    - Medical Situation: [Description of the patient's medical situation]
    - Video Title: [Title of the YouTube video]

    ### Output Format:
    - "YES" or "NO"

    ### Examples:
    - Medical Situation: "The patient was stung by a bee and has never had allergic reactions or symptoms such as swelling, itching, or difficulty breathing after being stung by an insect in the past."
      Video Title: "First Aid for Bee Stings"
      Output: "YES"

    - Medical Situation: "The patient was stung by a bee, but suffers from severe seasonal allergies."
      Video Title: "How to Treat Seasonal Allergies"
      Output: "NO"

    - Medical Situation: "The patient accidentally cut their hand with a knife and is experiencing minor bleeding."
      Video Title: "Emergency Care for Cuts"
      Output: "YES"

    - Medical Situation: "A person is having a heart attack."
      Video Title: "First Aid - Heart Attack"
      Output: "YES"

    ### Now process the following input:
    Medical Situation: {query}  
    Video Title: {video_title}
    """
    try:
        for channel_id in allowed_channels:
            params = {
                "part": "snippet",
                "q": keywords,
                "channelId": channel_id,
                "maxResults": max_results,
                "type": "video",
                "key": state['youtube_api_key'],
            }

            response = requests.get(YOUTUBE_SEARCH_URL, params=params)
            data = response.json()

            # Controlla se ci sono risultati
            if "items" in data and len(data["items"]) > 0:
                for item in data["items"]:
                    video_id = item["id"]["videoId"]
                    video_title = item["snippet"]["title"]
                    response = llm_70b.invoke([HumanMessage(content=prompt.format(query=state['full_query'], video_title=video_title))]).content
                    if response.strip().lower() == 'yes':
                        return {"search_results": f"https://www.youtube.com/watch?v={video_id}",
                                "video_title": video_title}
    except requests.exceptions.RequestException as e:
        return {"search_results": f"Error during YouTube search: {str(e)}", "video_title": None}
    return {"search_results": "No relevant videos found for the given query on the allowed channels.", "video_title": None}


def get_google_maps_url(state:AgentState):
    """
    Trova l'ospedale più vicino utilizzando la Google Places API.

    Args:
        lat (float): Latitudine dell'utente.
        lng (float): Longitudine dell'utente.
        api_key (str): Google Maps API Key.

    Returns:
        dict: Informazioni sull'ospedale più vicino o un messaggio di errore.
    """
    # URL dell'API di Google Places
    places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    lat, lng = state['user_location']
    google_maps_api_key = state['google_maps_api_key']
    # Parametri della richiesta
    params = {
        "location": f"{lat},{lng}",  # Latitudine e longitudine
        "radius": 7000,             # Raggio di ricerca in metri (es. 7km)
        "type": "hospital",         # Tipo di luogo da cercare
        "key": google_maps_api_key,             # Google API Key
    }

    try:
        # Invia la richiesta
        response = requests.get(places_url, params=params)
        data = response.json()

        # Controlla se ci sono risultati
        if "results" in data and len(data["results"]) > 0:
            nearest_hospital = data["results"][0]  # Il primo risultato è il più vicino
            hospital_name = nearest_hospital["name"]
            location = nearest_hospital["geometry"]["location"]
            return {
                "hospital_name": hospital_name,
                "google_maps_url": f"https://www.google.com/maps?q={location['lat']},{location['lng']}",
            }
        else:
            return {"google_maps_url": "No hospitals found nearby."}
    except requests.exceptions.RequestException as e:
        return {"google_maps_url": f"Request failed: {str(e)}"}
    

def start_emergency_bot(state:AgentState):
    # Nodo di coordinamento iniziale, ritorna lo stato invariato
    return state


def combine_results(state:AgentState):
    video_result = state.get("search_results", "No video found.")
    video_title = state.get("video_title", "No video found.")
    google_maps_url = state.get("google_maps_url", "")
    hospital_name = state.get("hospital_name", "No hospital information found.")
    if state.get("web_answer", ""):
        doc_answer = state["web_answer"]
    else:
        doc_answer = state.get("rag_answer", "")
    
    return {"final_result": [doc_answer, google_maps_url, hospital_name, video_result, video_title]}


def create_emergency_agent():
    # Creazione del grafo
    graph = StateGraph(AgentState)

    # Nodo iniziale per avviare i flussi paralleli
    graph.add_node("start_emergency_bot", start_emergency_bot)

    # Setta "start_emergency_bot" come entry point
    graph.set_entry_point("start_emergency_bot")

    # Aggiunta dei nodi
    graph.add_node("extract_keywords_youtube", extract_keywords_youtube)
    graph.add_node("search_youtube_videos", search_youtube_videos)
    graph.add_node("answer_from_rag", answer_from_rag)
    graph.add_node("web_search", web_search)
    graph.add_node("create_response_from_web_search", create_response_from_web_search)


    graph.add_edge("extract_keywords_youtube", "search_youtube_videos")
    graph.add_conditional_edges(
        "search_youtube_videos",
        should_continue_youtube,
        {
            "retry": "extract_keywords_youtube",
            "end": "combine_results",
        }
    )

    # Secondo agente (Location)
    graph.add_node("get_google_maps_url", get_google_maps_url)

    # Terzo agente (Combinazione risultati)
    graph.add_node("combine_results", combine_results)

    # Integrazione flussi paralleli
    graph.add_edge("get_google_maps_url", "combine_results")
    graph.add_conditional_edges(
        "answer_from_rag",
        should_web_search,
        {
            "web_search": "extract_keywords_web_search",
            "end": "combine_results",
        }
    )

    graph.add_node("extract_keywords_web_search", extract_keywords_web_search)
    graph.add_edge("extract_keywords_web_search", "web_search")
    graph.add_conditional_edges(
        "web_search",
        should_continue_web_search,
        {
            "retry": "extract_keywords_web_search",
            "end": "create_response_from_web_search",
        }
    )
    graph.add_edge("create_response_from_web_search", "combine_results")

    # Collegamenti ai flussi paralleli
    graph.add_edge("start_emergency_bot", "extract_keywords_youtube")
    graph.add_conditional_edges(
        "start_emergency_bot",
        should_find_hospital,
        {
            "high_severity": "get_google_maps_url",
            "low_severity": "combine_results",
        }
    )
    graph.add_edge("start_emergency_bot", "answer_from_rag")

    graph.set_finish_point("combine_results")

    # Compilazione del grafo
    app = graph.compile()
    
    # Store the image in memory using BytesIO
    img_bytes = app.get_graph().draw_mermaid_png()
    with open('presentation/agents/specialized.png', 'wb') as f:
        f.write(img_bytes)

    return app