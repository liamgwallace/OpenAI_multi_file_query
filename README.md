
# Document Search Engine

This project provides a solution for querying content within documents using OpenAI's model. The tool not only extracts content from various file formats like .pdf, .docx, and .pptx, but also indexes and searches them efficiently. First it generates a keyword search based on the user query. This is used to return relevant documents. If the files are not already indexed, if not they will be split and indexed and added to the database. all the relevant embeddings are retrieved from the db and are vector searched to return relevant text from the db. It then uses OpenAI for answering questions based on the content found in the documents.

## File Summary

### main.py
The main script orchestrates the entire flow of the program. It integrates different components like document loading, embedding generation, database operations, and OpenAI API calls to provide a seamless querying experience to the user.

### .env
This file contains environment variables, mainly the OpenAI API key and model specifications.

### document_db.py
Handles database operations for the project. It utilizes pickling to save and retrieve the indexed documents, metadata, embeddings, etc.

### document_loader.py
Facilitates loading content from various file formats. It reads the content from PDFs, DOCX, and PPTX files and provides them in a unified format.

### embeddings.py
Provides functionality for generating and querying embeddings for text using OpenAI's model and ChromaDB.

### ai_prompts.py
Contains prompt templates for generating search keywords and refining documents based on user queries.

### token_counter.py
Utility functions for counting tokens in text strings and OpenAI messages.

### index_search.py
Functions to build search queries and search for files in a given folder using Windows Search.

## Prerequisites
- Libraries: 
  - PyPDF2
  - python-docx
  - python-pptx
  - pywin32
  - tkinter
  - dotenv
  - openai
  - argparse
  - chromadb
  - tiktoken
  - langchain
There may be more, I used OpenAI to generate this

## Setup

1. **Environment Variables**: Ensure that the `.env` file is present in the root directory and contains the `OPENAI_API_KEY` and `OPENAI_API_MODEL`.
  
   Example:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_API_MODEL=gpt-3.5-turbo
   ```

2. **Python Libraries**: Install the necessary Python libraries.
   ```bash
   pip install -r requirements.txt
   ```

3. **Folder Indexing**: Update `folder_path` in main. Then ensure the folder containing the PDF documents is indexed. If it's not indexed, the application might not return results.

## Usage

1. Run the application:
   ```bash
   python main.py
   ```

2. You will be prompted to input a query. Enter your query related to the content you wish to search in the documents.

3. The application will display the answer based on the content found in the documents.

## Arguments

- **Verbose Mode**: The application can be run in verbose mode using the `--verbose` argument, which provides more detailed output.
- **Slow Mode**: With the `--slow` argument, the application will pause during verbose output, waiting for the user to press enter before proceeding.

## Features
- **File Search**: The application utilizes the Windows Search index to quickly locate files containing the search terms.

## Limitations

1. Limited to Windows as the Windows folder containing the files must be indexed.

## Future Work

- write OpenAI query - add in [existing repo](https://github.com/liamgwallace/OpenAI-FunctionCalling-HomeAssistantTools) with tools
- Update to use OpenAI function calling
- Add conversation memory to the chats
- Provide a graphical user interface for easier interaction.

