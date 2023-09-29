
# Document Search Engine

This application allows users to search through PDF documents within a folder by inputting a query. First it generates a keyword search based on the user query. This is used to return relevant documents. Using that document list it creates embeddings to do a vector search to return relevant text. It then uses OpenAI for answering questions based on the content found in the documents.

## Files in the Repository

1. `main.py`: Contains the primary code for querying, processing, and displaying results.
2. `index_search.py`: Provides utilities for searching for files in a folder based on given search terms.
3. `search_query_prompt.txt`: text file containing the prompt to generate windows search query

## Prerequisites
- Libraries: 
  - `json`
  - `sys`
  - `faiss`
  - `argparse`
  - `os`
  - `tkinter`
  - `dotenv`
  - `win32com`
  - `pythoncom`
  - `re`

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

2. You will be prompted to input a query. Enter your query related to the content you wish to search in the PDF documents.

3. The application will display the answer based on the content found in the documents.

## Arguments

- **Verbose Mode**: The application can be run in verbose mode using the `--verbose` argument, which provides more detailed output.
- **Slow Mode**: With the `--slow` argument, the application will pause during verbose output, waiting for the user to press enter before proceeding.

## Features
- **File Search**: The application utilizes the Windows Search index to quickly locate files containing the search terms.

## Limitations

1. Limited to Windows as the Windows folder containing the PDFs must be indexed.
2. The application currently supports only PDF documents.

## Future Work

- Extend support for other document formats. Possibly use Llama index 
- Smarter ways to return found chunks. 
  - Return the top n chunks and then also return the neighbouring chunks from those documents to increase context.
  - I'll need to do my own file splitting and vector creation to allow,
- Use map reduce method to perform deep search on lots of text
- Improve response from AI to include context such as document title, relevant page number or section number. Or even quoted text.(have a semi-working version of this)
- Add conversation memory to the chats
- Update to use OpenAI function calling
- Get away from Langchain
- Provide a graphical user interface for easier interaction.

