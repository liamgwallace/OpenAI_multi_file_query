
# Project: Document Query Tool with OpenAI Integration

## Overview
This project provides a solution for querying content within documents using OpenAI's model. The tool not only extracts content from various file formats like .pdf, .docx, and .pptx, but also indexes and searches them efficiently. The major advantage of this tool is its ability to process queries in natural language, making it intuitive and user-friendly. It leverages the power of OpenAI's models to generate and refine queries and integrates with a custom database to efficiently retrieve and display results.

## Installation

### Prerequisites:
- Python 3.7 or higher.
- Required Python libraries: PyPDF2, python-docx, python-pptx, win32api.
- An OpenAI API Key.

### Steps:

1. Clone the repository:
```
git clone <repository_url>
cd <repository_directory>
```
2. Create a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows: .env\Scriptsctivate
```
3. Install the required packages:
```
pip install -r requirements.txt
```
4. Set up your OpenAI API Key:
   - Create a .env file in the root directory of the project.
   - Add your OpenAI API key:
```
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_API_MODEL=gpt-3.5-turbo
```
   Replace `YOUR_OPENAI_API_KEY` with your actual API key.

5. Run the main program:
```
python main.py
```

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

## Usage

1. Run the `main.py` script.
2. You will be prompted to enter your query.
3. The program will process the query, search the indexed documents, and return the most relevant content.
4. Continue entering queries or exit the program.
