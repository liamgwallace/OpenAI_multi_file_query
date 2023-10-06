import os
import sys
import pythoncom
import win32com.client
from typing import List
import re

def build_query_old(folder_path: str, search_term: str) -> str:
    # Replace ')(' with ') AND ('
    search_term = search_term.replace(')(', ') AND (')
    # Replace ') (' with ') AND ('
    search_term = search_term.replace(') (', ') AND (')
    
    # Split the search term using regular expressions to capture parentheses, 'AND', 'OR' keywords, including optional whitespace 
    terms = re.findall(r'\(\s*|\)\s*|AND|OR|[^\s()]+', search_term)
    conditions = []

    for term in terms:
        if term.strip() in ('(', ')', 'AND', 'OR'):
            conditions.append(term.strip())
        else:
            conditions.append(f"CONTAINS(*, '{term}')")
    conditions_str = " ".join(conditions)
    query = f'''SELECT System.ItemPathDisplay 
                FROM SystemIndex 
                WHERE scope='file:{folder_path}' AND 
                ({conditions_str})
                ORDER BY System.Search.Rank DESC'''
    return query
    
def build_query(folder_path: str, search_term: str) -> str:
    # Remove anything other than letters, numbers, and spaces from the input_str
    search_term = re.sub(r'[^a-zA-Z0-9\s]', '', search_term)
    #print(f"#################################{search_term}")
    terms = search_term.split(" ")
    conditions = []

    for term in terms:
        conditions.append(f"CONTAINS(*, '{term}')")

    conditions_str = " OR ".join(conditions)
    query = f'''SELECT System.ItemPathDisplay 
                FROM SystemIndex 
                WHERE scope='file:{folder_path}' AND 
                ({conditions_str})
                ORDER BY System.Search.Rank DESC'''
    return query


def search_files(folder_path, search_term, num_files):

    #print(f"searching for [{search_term}] in [{folder_path}]")
    
    pythoncom.CoInitialize()

    # Create a connection to the Windows Search index
    conn = win32com.client.Dispatch("ADODB.Connection")
    conn.Provider = "Search.CollatorDSO"
    conn.Open()

    # Prepare the search query
    query = build_query(folder_path, search_term)
    a = f'''SELECT System.ItemPathDisplay 
				FROM SystemIndex 
				WHERE scope='file:folder_path' AND 
				((CONTAINS(*, 'terms') OR CONTAINS(*, 'liam') OR CONTAINS(*, 'coverage')) AND (CONTAINS(*, 'Jenny') OR CONTAINS(*, 'wallace')))
				ORDER BY System.Search.Rank DESC'''
    #print(f"#######{query}")

    # Execute the search query
    rs = win32com.client.Dispatch("ADODB.Recordset")
    rs.Open(query, conn)
    
    folder_indexed = not rs.EOF
    
    if not folder_indexed:
        #print(f"The folder {folder_path} is indexed.")
        print(f"Error: The folder {folder_path} is not indexed or there are no matches.")
    # Collect the search results
    result_paths = []
    while not rs.EOF:
        result_paths.append(rs.Fields.Item("System.ItemPathDisplay").Value)
        rs.MoveNext()

    rs.Close()
    conn.Close()
    pythoncom.CoUninitialize()
    # Check if num_files is greater than the number of files found
    if num_files >= len(result_paths):
        return result_paths
    
    return result_paths[:num_files]


if __name__ == "__main__":
    #folder_path = input("Please enter the folder path: ")
    folder_path = r"C:\Users\liamg\Scripts\AI\Langchain\pdfsearch\pdfs"
    while True:
        search_term = input("Please enter the search term: ")

        results = search_files(folder_path, search_term, 5)

        print("Search results:")
        for path in results:
            print(path)
