
from dotenv import load_dotenv
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
from ai_prompts import generate_keywords_prompt_user, generate_keywords_prompt_system, doc_refine_prompt_system, doc_refine_prompt_user
from index_search import search_files
from embeddings import EmbeddingDB

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

def generate_search_keywords(user_query):
    #CODE  
    user_prompt = generate_keywords_prompt_user
    system_prompt = generate_keywords_prompt_system.format(user_query=user_query)
    
    #AI call placeholder
    response_text=user_query
    
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

def combine_texts_with_metadata(texts, metadatas):        
    combined_texts_and_metadatas = []
    
    for text, metadata in zip(texts, metadatas):
        # Convert metadata dictionary into a formatted string
        metadata_str = "; ".join([f"{key}: {value}" for key, value in metadata.items()])
        
        # Combine the text with its metadata
        combined_text_and_metadata = f"[TEXT EXTRACT:'{text}'] [METADATA: '{metadata_str}']\n"
        combined_texts_and_metadatas.append(combined_text_and_metadata)
    
    return combined_texts_and_metadatas

def combine_texts(prompts, texts_and_metadatas, buffer, max_tokens):
    
    # Calculate tokens used
    prompt_tokens = sum([num_tokens_from_strings(prompt, OPENAI_API_MODEL) for prompt in prompts])
    texts_tokens = [(text, num_tokens_from_strings(text, OPENAI_API_MODEL)) for text in texts_and_metadatas]
    
    # Calculate the maximum allowed tokens for texts_and_metadatas
    max_allowed_tokens = max_tokens - prompt_tokens - buffer
    
    combined_texts = []
    current_text = ""
    current_tokens = 0
    
    for text, tokens in texts_tokens:
        # If adding the next text doesn't exceed the max_allowed_tokens, append it
        if current_tokens + tokens <= max_allowed_tokens:
            current_text += f"\n{text}"
            current_tokens += tokens
        else:
            # If it does exceed, then store the current_text and start a new one
            combined_texts.append(current_text)
            current_text = text
            current_tokens = tokens
    
    # Append any remaining text
    if current_text:
        combined_texts.append(current_text)
    
    return combined_texts
    
def document_query(user_query, folder_paths, chat_history, doc_db):
    #init stuff    
    num_files=30
    num_vector_results=20
    neighbor_text_count=2
    chunk_overlap=20
    chunk_size=200
    embeddings_db = EmbeddingDB(api_key=OPENAI_API_KEY)
    doc_loader = DocumentLoader(whitelisted_extensions=["txt"])
    
    
    #generate document search keywords
    search_keywords=generate_search_keywords(user_query)
    print_verbose(f"Generated Keywords: '{search_keywords}'")
        
    #return list of matched files
    found_file_paths = search_files(folder_paths[0], search_keywords, num_files)
    print_verbose(f"Found Files", found_file_paths)
  
    #check list against db
    file_paths_in_db, file_paths_not_in_db = doc_db.check_by_file(found_file_paths)   
    print_verbose(f"Files already indexed", file_paths_in_db)
    if file_paths_not_in_db:
        #read files
        print_verbose(f"Files not indexed", file_paths_not_in_db)
        print_verbose(f"loading to memory...")
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
    
    #query the embeddings and return the IDs  
    print_verbose("Querying embeddings...")
    vector_query_results = embeddings_db.query_embeddings(
        query_texts=[user_query],
        embeddings=embeddings_and_ids['embeddings'],
        ids=embeddings_and_ids['file_ids'],
        n_results=num_vector_results        
    )
    relevant_ids = vector_query_results['ids']
    print_verbose("relevant_ids",relevant_ids)
    # Retrieve relevant texts (and their neighbors) from the database using IDs    
    print_verbose("Fetching texts from db...")
    result = doc_db.get_texts_from_ids(
        ids=relevant_ids,
        neighbor_text_count=neighbor_text_count,
        overlap=chunk_overlap
    )
    
    # print(f"\nText Metadatas:")
    # pprint(result['metadatas'])
    # print(f"\nTexts: {result['texts']}\n")
    # print(f"\nresult: {result}\n")

    texts_and_metadatas=combine_texts_with_metadata(result['texts'], result['metadatas'])    
    # print_verbose(f"\ntexts_and_metadatas:",texts_and_metadatas)
    for text in texts_and_metadatas:
        print(f"num tokens: {num_tokens_from_strings(text, OPENAI_API_MODEL)}")

    doc_db.dump_to_txt('output.txt')
    doc_db.save()

    
    #AI query to go here   
        #either refine mode
            #create answer, using refine loop
    prompts = [doc_refine_prompt_system, doc_refine_prompt_user]
    combined_texts = combine_texts(prompts, texts_and_metadatas,1000 , get_max_tokens(OPENAI_API_MODEL)) 
    print(f"len combined_texts: {len(combined_texts)}")
    for text in combined_texts:
        print(f"num tokens: {num_tokens_from_strings(text, OPENAI_API_MODEL)}")
    # print_verbose(f"\ncombined_texts:",combined_texts)
        #or reduce mode
            #Loop and create answer for each section
            #create final answer from sections
    #return the AI response when completed
    result="result"
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
        print()
        print("Answer: \n", answer)
        print()
        print()
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search PDF documents with a query.")
    parser.add_argument('--verbose', dest='VERBOSE', action='store_true', help='Enable verbose mode')
    parser.set_defaults(VERBOSE=False)
    args = parser.parse_args()
    VERBOSE = args.VERBOSE
    main()

