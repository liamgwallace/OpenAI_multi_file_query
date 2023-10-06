import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

class EmbeddingDB:
    def __init__(self, api_key=None, model_name="text-embedding-ada-002"):
        if not api_key:
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY")
            print(f"loaded api key from dotenv: {api_key}")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables or provided as argument.")
        
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name=model_name
        )
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(name='my_collection', embedding_function=self.embedding_function)

    def make_embeddings(self, texts):
        return self.embedding_function(texts)

    def query_embeddings(self, query_texts, embeddings, ids, n_results=10):
        self.collection.add(
            embeddings=embeddings,
            ids=ids
        )
        results = self.collection.query(
            query_texts=query_texts,
            n_results=n_results,
            include=[]
        )        
        # Reset the collection after querying
        self.reset_collection()

        return results

    def reset_collection(self):
        # Store the name of the current collection
        collection_name = self.collection.name
        
        # Delete the collection
        self.client.delete_collection(name=collection_name)
        
        # Recreate the collection with the same name
        self.collection = self.client.create_collection(collection_name)

def test_embeddings():
    # Example usage:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    # Sample texts and their IDs
    texts = ["Hello world", "I love cats", "The sun is shining."]
    ids = ["ID1", "ID2", "ID3"]

    # Create embeddings for these texts
    db = EmbeddingDB(api_key=api_key)
    embeddings = db.make_embeddings(texts)

    # Let's say you want to find which of the above texts are most similar to "Hi world"
    query_texts = ["weather", "kitten"]

    # Query the embeddings using the ChromaDB object
    results = db.query_embeddings(query_texts, embeddings, ids, n_results=1)

    # Print the results
    print(results)
    # {
        # 'ids': [
            # ['ID3'],
            # ['ID2']
        # ],
        # 'distances': [
            # [0.3416097164154053],
            # [0.2682076096534729]
        # ],
        # 'metadatas': [
            # [None],
            # [None]
        # ],
        # 'embeddings': None,
        # 'documents': [
            # [None],
            # [None]
        # ]
    # }

if __name__ == '__main__':
    test_embeddings()