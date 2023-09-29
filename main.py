
import json
import sys
import faiss
import argparse
import os
import tkinter as tk
from tkinter import filedialog
from dotenv import load_dotenv
from typing import List
from langchain import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.prompts.chat import (
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
)
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.document_loaders import UnstructuredPDFLoader
from langchain.indexes import VectorstoreIndexCreator
from langchain.document_loaders import PyMuPDFLoader

import index_search

verbose = False

load_dotenv()
# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
#print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")
assert OPENAI_API_KEY, "OPENAI_API_KEY environment variable is missing from .env"

OPENAI_API_MODEL = os.getenv("OPENAI_API_MODEL", "gpt-3.5-turbo")
assert OPENAI_API_MODEL, "OPENAI_API_MODEL environment variable is missing from .env"
        
def print_verbose(*args):
    if verbose:
        print("##############################################################")
        for arg in args:
            if isinstance(arg, list):
                for item in arg:
                    print(item)
            else:
                print(arg)
        
        print("##############################################################")
    if slow:
        a = input("press enter con continue")

    
def enter_folder():
    # Prompt user to select folder
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory()
    if not folder_path:
        sys.exit("No folder selected")
    folder_path = os.path.normpath(folder_path)
    return folder_path
    
def remove_stopwords(text):
    stopwords = {'and', 'or', 'to', 'on', 'the', 'I', 'is', 'with', 'in', 'of', 'for', 'by', 'at', 'but', 'as', 'if', 'it', 'that', 'this', 'are', 'be', 'has', 'have', 'had', 'not', 'you', 'we', 'they', 'he', 'she', 'can', 'will', 'from', 'one', 'an', 'any', 'all', 'some', 'few', 'many', 'much', 'more', 'most', 'no', 'yes', 'so', 'than', 'when', 'where', 'why', 'how', 'other', 'each', 'every', 'any', 'either', 'neither', 'these', 'those', 'us', 'them', 'our', 'your', 'their', 'its', 'his', 'her', 'out', 'up', 'down', 'over', 'under', 'above', 'below', 'off', 'through', 'across', 'around', 'between', 'among', 'within'}
    words = text.split()
    filtered_words = [word for word in words if word.lower() not in stopwords]
    filtered_text = ' '.join(filtered_words)
    return filtered_text

def extract_search_term(query):
    with open("search_query_prompt.txt", "r") as f:
        search_query_prompt = f.read()

    llm = ChatOpenAI(model_name=OPENAI_API_MODEL, openai_api_key=OPENAI_API_KEY, temperature=0.5)

    # Create a HumanMessagePromptTemplate from the search_query_prompt
    human_message_prompt = HumanMessagePromptTemplate.from_template(search_query_prompt)

    # Create a ChatPromptTemplate from the HumanMessagePromptTemplate
    chat_prompt = ChatPromptTemplate.from_messages([human_message_prompt])

    # Format the ChatPromptTemplate with the query
    formatted_prompt = chat_prompt.format_prompt(query=query).to_messages()

    # Pass the formatted_prompt (list of messages) to the Chat API
    response = llm(formatted_prompt)
    search_term = response.content

    search_term = remove_stopwords(search_term)
    return search_term
    

def similarity_search_and_extract(query, db, documents, num_docs):
    # Perform similarity search using the FAISS database
    print("Number of vectors in the index: ", db.ntotal)
    print("Dimension of the vectors: ", db.d)
    distances, indices = db.search(query, num_docs)

    #indices = indices[0]
    extended_indices = []
    for idx in indices:
        if idx >= 1:
            extended_indices.append(idx - 1)
        extended_indices.append(idx)
        if idx < len(db):
            extended_indices.append(idx + 1)
    unique_indices = sorted(list(set(extended_indices)))
    # Extract the relevant documents
    selected_docs = [db[i] for i in unique_indices]
    return selected_docs

def llm_query_split_docs(query,folder_path):
    
    search_term = extract_search_term(query)
    print_verbose("keywords: ", search_term)
    num_files=8;
    found_file_paths = index_search.search_files(folder_path, search_term, num_files)
    print_verbose("found_file_paths: ",found_file_paths)
    # Load and process the pdf files
    loaders = [PyMuPDFLoader(file_path) for file_path in found_file_paths]    
    #print_verbose("loaders: ",loaders)
    #loader = [UnstructuredPDFLoader(file_path) for file_path in found_file_paths]
    #documents = [loader.load() for loader in loaders]
    #documents = loader.load()        
    documents = [doc for loader in loaders for doc in loader.load()]
    #print_verbose("documents: ",documents)
    
    text_splitter = CharacterTextSplitter(        
        chunk_size=3000,
        chunk_overlap=750,
        separator="\n",
        length_function=len,
    )
  
    split_docs = text_splitter.split_documents(documents)
    
    print_verbose(f"making {len(split_docs)}embeddings")       
    embeddings = OpenAIEmbeddings()
    db = FAISS.from_documents(split_docs, embeddings)
    similar_split_docs = db.similarity_search(query)   
    #similar_split_docs = similarity_search_and_extract(query, db, documents, 4) 
    #similar_split_docs = db.similarity_search_with_score(query)    
    print_verbose("running QA chain")
    chain = load_qa_chain(OpenAI(temperature=0.1), chain_type="stuff", verbose=False)
    
    template = """
    %%%INSTRUCIOTNS
    You are called AnswerGPT. Given the following extracted parts of a long document and a question. 
    Give me a detailed and verbose answer that includes as much information as possible. Where possible include any page numbers, chapters or headings in your answer.
    If you don't know the answer, just say that you don't know. Don't try to make up an answer.
    Respond in json format only. Do not include any other text
    ALWAYS return a "SOURCES" part in your answer.
    
    %%%EXAMPLES
    QUESTION: What is Google's policy regarding Anti-Bribery Laws?
    =========
    Content: (b) if Google believes, in good faith, that the Distributor has violated or caused Google to violate any Anti-Bribery Laws (as defined in Clause 8.5) or that such a violation is reasonably likely to occur,
    Source: 4-pl
    Content: All Distributors are expected to adhere to the highest standards of business ethics and to fully comply with all applicable Anti-Bribery Laws.
    Source: 9-pl
    =========
    AnswerGPT response:
{{
    "FINAL_ANSWER": "Google believes in good faith that if a distributor violates or causes Google to violate Anti-Bribery Laws, it's a serious issue. They expect all distributors to adhere to the highest standards of business ethics and fully comply with these laws.",
    "SOURCES": [
        {{
            "FILE_PATH": "C:\\path\\to\\file1.pdf",
            "PAGE_OR_HEADING": "Page 10"
        }},
        {{
            "FILE_PATH": "C:\\path\\to\\file2.pdf",
            "PAGE_OR_HEADING": "Chapter 3"
        }}
    ]
}}

    QUESTION: Did the president discuss the issue of rising gas prices?
    =========
    Content: Tonight, I can announce that the United States has worked with 30 other countries to release 60 Million barrels of oil from reserves around the world.
    Source: 5-pl
    Content: These steps will help blunt gas prices here at home. And I know the news about what’s happening can seem alarming.
    Source: 8-pl
    =========    
    AnswerGPT response:
{{
    "FINAL_ANSWER": "No, the president did not specifically discuss the issue of rising gas prices.",
    "SOURCES": []
}}

    %%%ANSWER THE FOLLOWING
    QUESTION: {question}
    =========
    {summaries}
    =========
    AnswerGPT response:
"""
    PROMPT = PromptTemplate(template=template, input_variables=["summaries", "question"])

    #print(PROMPT)
#    chain = load_qa_with_sources_chain(OpenAI(temperature=0.1),
#                                        chain_type="stuff", 
#                                        prompt=PROMPT, 
#                                        verbose=verbose
#                                        )
    response = chain.run(input_documents=similar_split_docs, question=query)
    
    # Parse the JSON output into a Python dictionary.
    #response = response.replace("\\", "\\\\")
    #parsed_output = json.loads(response)

    # Now you can access the answer and sources like this:
    #answer = parsed_output.get("FINAL_ANSWER", "")
    #sources = parsed_output.get("SOURCES", [])

    #return answer, sources, response
    return response

def main():
    #folder_path = enter_folder()
    while True:
        print()
        query = input("Enter your query: ")
        #query = "what is the terms on the motor policy for jenny"
        folder_path = r"C:\Users\liamg\Scripts\AI\Langchain\pdfsearch\pdfs"
        #answer, sources, result = llm_query_split_docs(query, folder_path)
        answer = llm_query_split_docs(query, folder_path)
        print()
        print("Answer: \n", answer)
        print()
        #print("Sources:")
        #for source in sources:
        #    file_path = source["FILE_PATH"]
        #    page_or_heading = source["PAGE_OR_HEADING"]
        #    if page_or_heading:  # Check if page or heading exists
        #        print(f"- {file_path} ({page_or_heading})")
        #    else:
        #        print(f"- {file_path}")
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search PDF documents with a query.")
    parser.add_argument('--verbose', dest='verbose', action='store_true', help='Enable verbose mode')
    parser.add_argument('--slow', dest='slow', action='store_true', help='Enable slow verbose mode')
    parser.set_defaults(verbose=False, slow=False)
    args = parser.parse_args()
    verbose = args.verbose
    slow = args.slow
    main()


