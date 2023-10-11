
from dotenv import load_dotenv
import concurrent.futures
import random
import time
import re
import sys
import argparse
import os
import tkinter as tk
from tkinter import filedialog
from pprint import pprint

#from openai import encodings

#langchain
from langchain.text_splitter import RecursiveCharacterTextSplitter

#local files
from token_counter import num_tokens_from_strings, num_tokens_from_messages
from document_db import DocumentDB
from document_loader import Document, DocumentLoader
from ai_prompts import generate_keywords_prompt_user, generate_keywords_prompt_system, doc_refine_prompt_system, doc_refine_prompt_user, doc_map_reduce_prompt_system, doc_map_reduce_prompt_user, doc_map_reduce_combine_prompt_system, doc_map_reduce_combine_prompt_user
from index_search import search_files
from embeddings import EmbeddingDB
from openai_chat_interface import OpenAI_LLM, create_message, calculate_cost

#system variables
VERBOSE = False

load_dotenv()
# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
assert OPENAI_API_KEY, "OPENAI_API_KEY environment variable is missing from .env"

OPENAI_API_MODEL = os.getenv("OPENAI_API_MODEL", "gpt-3.5-turbo")
assert OPENAI_API_MODEL, "OPENAI_API_MODEL environment variable is missing from .env"

def print_verbose(*args):
    if VERBOSE:
        print("##############################################################")
        for arg in args:
            if isinstance(arg, list):
                for item in arg:
                    print(item)
            else:
                print(arg)
        # print("##############################################################")


        
def get_max_tokens(model_name: str = None):
    # Define a dictionary to map model names to their max token counts
    model_to_tokens = {
        "gpt-4-32k-0613": 32768,
        "gpt-4-32k": 32768,
        "gpt-4-0613": 8192,
        "gpt-4": 8192,
        "gpt-3.5-turbo-16k-0613": 16385,
        "gpt-3.5-turbo-16k": 16385,
        "gpt-3.5-turbo-0613": 4097,
        "gpt-3.5-turbo": 4097
    }
    if model_name is None:
        return 4097
    return model_to_tokens.get(model_name, 4097)
    
def extract_last_line(text):
    lines = text.split('\n')
    last_line = lines[-1].strip()
    last_line_no_punctuation = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', last_line)
    last_line_no_punctuation = re.sub(r'[^\w\s]+', ' ', last_line_no_punctuation)    
    return last_line_no_punctuation
    
def remove_stopwords(text):
    stopwords = {'and', 'or', 'to', 'on', 'the', 'I', 'is', 'with', 'in', 'of', 'for', 'by', 'at', 'but', 'as', 'if', 'it', 'that', 'this', 'are', 'be', 'has', 'have', 'had', 'not', 'you', 'we', 'they', 'he', 'she', 'can', 'will', 'from', 'one', 'an', 'any', 'all', 'some', 'few', 'many', 'much', 'more', 'most', 'no', 'yes', 'so', 'than', 'when', 'where', 'why', 'how', 'other', 'each', 'every', 'any', 'either', 'neither', 'these', 'those', 'us', 'them', 'our', 'your', 'their', 'its', 'his', 'her', 'out', 'up', 'down', 'over', 'under', 'above', 'below', 'off', 'through', 'across', 'around', 'between', 'among', 'within'}
    words = text.split()
    filtered_words = [word for word in words if word.lower() not in stopwords]
    filtered_text = ' '.join(filtered_words)
    return filtered_text
    
def enter_folder():
    # Prompt user to select folder
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory()
    if not folder_path:
        sys.exit("No folder selected")
    folder_path = os.path.normpath(folder_path)
    return folder_path

def generate_search_keywords(user_query, system_prompt, user_prompt):
    #CODE  
    user_prompt = generate_keywords_prompt_user
    system_prompt = generate_keywords_prompt_system.format(user_query=user_query)
    
    #AI call placeholder
    llm_keywords = OpenAI_LLM(api_key=OPENAI_API_KEY, model=OPENAI_API_MODEL, temperature=0.2, system_message=system_prompt, user_message=user_prompt)
    content_data = {
        "user_query": user_query
    }
    llm_keywords.run(content_dict=content_data)
    response_text = llm_keywords.response_content
    response_text = extract_last_line(response_text)
    search_keywords = remove_stopwords(response_text)
    return search_keywords

def split_docs(text, chunk_size=500, chunk_overlap=20):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap  = 20,
        length_function = len,
    )
    texts = text_splitter.split_text(text)
    return texts

import concurrent.futures
import random
import time

def document_query_map_reduce(user_query, system_prompt, user_prompt, system_prompt_combine, user_prompt_combine, document_texts, max_concurrent_requests=7):
    
    def run_llm_request(document_text, index):
        delay = 0.3 * index + random.uniform(0.0, 0.3)  # Calculate delay in seconds.
        time.sleep(delay)
        print_verbose(f"Sending ai response {index}")
        local_llm = OpenAI_LLM(api_key=OPENAI_API_KEY, model=OPENAI_API_MODEL, temperature=0.2, system_message=system_prompt, user_message=user_prompt)
        content_data = {
            "user_query": user_query,
            "document_text": document_text,
            "partial_answers": ""
        }
        local_llm.run(content_dict=content_data)
        print_verbose(f"Received ai response {index}")
        response = f"[\n[{local_llm.response_content}]\n" 
        local_llm.clear_memory()
        # print_verbose(response)
        return response

    combined_responses = ""   
    document_text = ""

    if len(document_texts) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_requests) as executor:
            futures = [executor.submit(run_llm_request, doc_text, idx+1) for idx, doc_text in enumerate(document_texts)]
            for future in concurrent.futures.as_completed(futures):
                combined_responses += future.result()
    else:
        document_text = document_texts[0]

    llm_map_combine = OpenAI_LLM(api_key=OPENAI_API_KEY, model=OPENAI_API_MODEL, temperature=0.2, system_message=system_prompt_combine, user_message=user_prompt_combine)
    content_data = {
        "user_query": user_query,
        "document_text": document_text,
        "partial_answers": combined_responses
    }
    print_verbose(f"Sending final ai response")
    llm_map_combine.run(content_dict=content_data)
    print_verbose(f"Received final ai response")
    return llm_map_combine.response_content

def document_query_refine(user_query, system_prompt, user_prompt, document_texts):
    partial_answers = ""    
    # user_message = [create_message("user", user_prompt)]
    llm_refine = OpenAI_LLM(api_key=OPENAI_API_KEY, model=OPENAI_API_MODEL, temperature=0.2, system_message=system_prompt, user_message=user_prompt)
    for document_text in document_texts:
        content_data = {
            "user_query": user_query,
            "document_text": document_text,
            "partial_answers": partial_answers
        }
        llm_refine.run(content_dict=content_data)
        partial_answers = llm_refine.response_content
        llm_refine.clear_memory()
    return partial_answers
    # llm.add_messages([llm.response_message])
    
def document_query(user_query, folder_paths, chat_history, doc_db):
    #init stuff    
    num_files=20
    num_vector_results=20
    neighbor_text_count=1000
    chunk_overlap=200
    chunk_size=500
    response_token_buffer=1000
    embeddings_db = EmbeddingDB(api_key=OPENAI_API_KEY)
    doc_loader = DocumentLoader(whitelisted_extensions=["txt"])
    
    generate_keywords_prompt_user
    generate_keywords_prompt_system
    doc_refine_prompt_system
    doc_refine_prompt_user
    doc_map_reduce_prompt_system
    doc_map_reduce_prompt_user
    
    
    #generate document search keywords
    search_keywords=generate_search_keywords(user_query, generate_keywords_prompt_system, generate_keywords_prompt_user)
    print_verbose(f"Generated Keywords: '{search_keywords}'")
        
    #return list of matched files
    found_file_paths = search_files(folder_paths[0], search_keywords, num_files)
  
    #check list against db
    file_paths_in_db, file_paths_not_in_db = doc_db.check_by_file(found_file_paths)   
    print_verbose(f"Files already indexed", file_paths_in_db)
    if file_paths_not_in_db:
        #read files
        print_verbose(f"Files not indexed", file_paths_not_in_db, f"\nloading to memory...")
        documents_list = doc_loader.load_from_files(file_paths_not_in_db)  
        #create embeddings
        for doc in documents_list:
            texts  = split_docs(doc.page_content, chunk_size, chunk_overlap)
            print_verbose(f"Making {len(texts)} embeddings for {doc.metadata['filepath']}")
            embeddings = embeddings_db.make_embeddings(texts)
            delattr(doc, 'page_content')
            setattr(doc, 'texts', texts)
            setattr(doc, 'embeddings', embeddings)        
        #add to database    
        print_verbose(f"Indexing files complete")
        doc_db.upsert(documents_list)
        
    #create list of new embeddings
    print_verbose("Getting embeddings from db...")
    embeddings_and_ids = doc_db.get_embeddings_from_path(found_file_paths)
    
    print_verbose("dumping db...")
    doc_db.dump_to_txt('output.txt')
    
    print_verbose("saving db...")
    doc_db.save()
    
    #query the embeddings and return the IDs  
    print_verbose("Querying embeddings...")
    vector_query_results = embeddings_db.query_embeddings(
        query_texts=[user_query],
        embeddings=embeddings_and_ids['embeddings'],
        ids=embeddings_and_ids['file_ids'],
        n_results=num_vector_results        
    )
    relevant_ids = vector_query_results['ids']
    
    # Retrieve relevant texts (and their neighbors) from the database using IDs    
    prompts = [doc_refine_prompt_system, doc_refine_prompt_user]
    prompts_tokens = sum([num_tokens_from_strings(prompt) for prompt in prompts])
    max_allowed_tokens = get_max_tokens(OPENAI_API_MODEL) - prompts_tokens - response_token_buffer
    # Retrieve relevant texts (and their neighbors) from the database using IDs    
    print_verbose("Fetching texts from db...")
    grouped_texts_and_metadatas = doc_db.get_texts_from_ids(
        ids=relevant_ids,
        neighbor_text_count=neighbor_text_count,
        overlap=chunk_overlap,
        max_tokens=max_allowed_tokens
    )

    print_verbose(f"Sending {len(grouped_texts_and_metadatas)} sections to the ai...")
    #AI query
    # result=document_query_refine(user_query, doc_refine_prompt_system, doc_refine_prompt_user, grouped_texts_and_metadatas)
    result=document_query_map_reduce(
        user_query,
        doc_map_reduce_prompt_system,
        doc_map_reduce_prompt_user,
        doc_map_reduce_combine_prompt_system,
        doc_map_reduce_combine_prompt_user,
        grouped_texts_and_metadatas
        )    
    return result

def main():
    if VERBOSE:
        print("Verbose Mode")
    # folder_paths = [enter_folder()]
    folder_paths = [r"C:\Users\liamg\Scripts\AI\Langchain\pdfsearch\docs"]
    chat_history = []
    doc_db = DocumentDB("path_to_database.pkl")
    while True:
        print()
        query = input("Enter your query: ")        
        answer = document_query(query, folder_paths, chat_history, doc_db)
        print(f"\n\n{answer}\n\n")
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search PDF documents with a query.")
    parser.add_argument('--verbose', dest='VERBOSE', action='store_true', help='Enable verbose mode')
    parser.set_defaults(VERBOSE=False)
    args = parser.parse_args()
    VERBOSE = args.VERBOSE
    main()

