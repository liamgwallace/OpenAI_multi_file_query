
import pickle
import os

class DocumentDB:

    def __init__(self, file_path=None):
        self.file_path = file_path
        if file_path and os.path.exists(file_path):
            self.load(file_path)
        else:
            self.documents = {}
        
    def check_by_file(self, file_paths, updated_times=None):
        in_db = []
        not_in_db = []
        
        for file_path in file_paths:
            doc = self.documents.get(file_path)
            
            # If updated_times is provided, check both existence and updated time.
            if updated_times:
                updated_time = updated_times[file_paths.index(file_path)]
                if doc and doc['updated_time'] == updated_time:
                    in_db.append(file_path)
                else:
                    not_in_db.append(file_path)
            # If updated_times is not provided, only check for existence.
            else:
                if doc:
                    in_db.append(file_path)
                else:
                    not_in_db.append(file_path)
                    
        return in_db, not_in_db
 
    def upsert(self, documents_list):
        for document in documents_list:
            file_path = document.metadata['filepath']
            updated_time = document.metadata['updated_time']
            metadata = document.metadata
            texts = document.texts
            embeddings = document.embeddings

            # Generate a unique file_id
            file_id = len(self.documents) + 1
            while any(doc['file_id'] == file_id for doc in self.documents.values()):
                file_id += 1

            # Store the document in the `documents` dictionary
            self.documents[file_path] = {
                "file_id": file_id,
                "updated_time": updated_time,
                "metadata": metadata,
                "texts": texts,
                "embeddings": embeddings
            }

    def get_embeddings_from_path(self, file_paths):
        result = {
            "file_ids": [],
            "embeddings": []
        }

        for file_path in file_paths:
            doc = self.documents.get(file_path)
            if doc:
                result["embeddings"].extend(doc["embeddings"])
                result["file_ids"].extend([f"{doc['file_id']}.{idx}" for idx, _ in enumerate(doc['texts'], 1)])

        return result
      
    def get_documents_from_path(self, file_paths):
        result = {
            "file_ids": [],
            "embeddings": [],
            "metadatas": [],
            "texts": []
        }
        
        for file_path in file_paths:
            doc = self.documents.get(file_path)
            if doc:
                result["file_ids"].extend([f"{doc['file_id']}.{idx}" for idx, _ in enumerate(doc['texts'], 1)])
                result["embeddings"].extend(doc["embeddings"])
                result["metadatas"].extend([doc["metadata"]] * len(doc["texts"]))
                result["texts"].extend(doc["texts"])

        return result
        
    def get_file_path_from_id(self, file_id):
        for path, doc_data in self.documents.items():
            if doc_data["file_id"] == int(file_id):
                return path
        return None

       
    def get_texts_from_ids(self, ids, neighbor_text_count=0, overlap=0):
        metadatas = []
        texts = []

        # Flatten the ids list
        flat_ids = [item for sublist in ids if isinstance(sublist, list) for item in sublist] + [item for item in ids if not isinstance(item, list)]
        
        # Group by file_path
        file_path_groups = {}
        for text_id in flat_ids:
            file_id, text_num = text_id.rsplit('.', 1)
            file_path = self.get_file_path_from_id(file_id)
            text_num = int(text_num)

            # Determine the range of text numbers to retrieve based on `neighbor_text_count`
            start_text_num = max(1, text_num - neighbor_text_count)
            end_text_num = text_num + neighbor_text_count

            if file_path not in file_path_groups:
                file_path_groups[file_path] = []

            for i in range(start_text_num, end_text_num + 1):
                if i > 0 and i not in file_path_groups[file_path]:
                    file_path_groups[file_path].append(i)

        # Process each file path group
        for file_path, idxs in file_path_groups.items():
            idxs.sort()
            doc = self.documents.get(file_path)

            if doc:
                current_text = ""
                for idx in range(len(idxs)):
                    if 0 < idxs[idx] <= len(doc["texts"]):
                        # Trim the text if the next index is directly following
                        if idx + 1 < len(idxs) and idxs[idx + 1] == idxs[idx] + 1:
                            current_text += doc["texts"][idxs[idx] - 1]
                            #current_text += doc["texts"][idxs[idx] - 1][:-overlap]
                        else:
                            current_text += doc["texts"][idxs[idx] - 1]
                        # Add gap text if there's a gap between this and the next index
                        if idx + 1 < len(idxs) and idxs[idx + 1] != idxs[idx] + 1:
                            current_text += "\n\n...TEXT GAP...\n\n"
                
                metadatas.append(doc["metadata"])
                texts.append(current_text)

        return {
            "metadatas": metadatas,
            "texts": texts
        }

        
    def load(self, file_path):
        with open(file_path, "rb") as f:
            self.documents = pickle.load(f)
        self.file_path = file_path  # Update the file_path attribute when loading

    def save(self, file_path=None):
        # If no filepath is provided, use the stored filepath
        if file_path is None:
            if self.file_path is None:
                raise ValueError("No filepath provided and no default filepath found.")
            file_path = self.file_path
        with open(file_path, "wb") as f:
            pickle.dump(self.documents, f)
            
    def dump_to_txt(self, file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            for _, doc in self.documents.items():
                
                # Truncate the number of embedding lists and the length of each embedding
                truncated_embedding_list = doc["embeddings"][:5]
                truncated_embeddings = [embedding[:5] for embedding in truncated_embedding_list]
                
                if len(doc["embeddings"]) > 5:
                    truncated_embeddings.append("...")
                
                # Truncate texts
                truncated_texts = [text[:100] + ("..." if len(text) > 100 else "") for text in doc["texts"]]
                
                # Write metadata to the file
                f.write(f"metadata:[\n") 
                for key, value in doc["metadata"].items():
                    f.write(f"  {key}: {value}\n")                
                f.write(f"]\n") 
                
                # Write truncated embeddings and texts to the file
                f.write(f"Embeddings: {truncated_embeddings}\n")
                f.write(f"Texts: {truncated_texts}\n")
                
                f.write("-" * 50 + "\n")  # Separator
                
def test_document_db():
    # Create an instance of the documentDB
    db = documentDB()

    # Insert some documents
    documents_list = [
        {
            'file_path': 'doc1.txt',
            'updated_time': '2023-10-03',
            'metadata': {'author': 'John'},
            'texts': ['This is a sample text for the document.', 'This text will be split into multiple texts for demonstration purposes.', 'Each text is approximately 100 words or less.', 'Continue writing more text to fill up the content.'],
            'embeddings': [[0.1]*5, [0.2]*5, [0.3]*5, [0.4]*5]
        },
        {
            'file_path': 'doc2.txt',
            'updated_time': '2023-10-04',
            'metadata': {'author': 'Jane'},
            'texts': ['Another sample document to be inserted into the database.', 'This will also be split into texts.', 'Lets add more content to create multiple texts.'],
            'embeddings': [[0.5]*5, [0.6]*5, [0.7]*5]
        }
    ]

    db.upsert(documents_list)

    # Retrieve documents based on file paths
    result = db.get_documents_from_path(['doc1.txt'])
    print(f"File IDs: {result['file_ids']}")
    print(f"Embeddings: {result['embeddings']}")
    print(f"Metadatas: {result['metadatas']}")
    print(f"Texts: {result['texts']}")

    # Retrieve specific texts (and their neighbors) from the database
    result = db.get_texts_from_ids(['doc1.txt.2'], 1)
    print(f"text Metadatas: {result['metadatas']}")
    print(f"Texts: {result['texts']}")

    # Save the current state of the database to a file
    db.save('my_database.pkl')

    # Load the saved database into a new instance
    new_db = DocumentDB()
    new_db.load('my_database.pkl')

    # Confirm if the documents in the loaded instance match the original
    print(new_db.documents == db.documents)  # Should return True
    
    # Retrieve specific texts (and their neighbors) from the database
    result = db.get_texts_from_ids(['doc1.txt.2'], 1)
    print(f"text Metadatas: {result['metadatas']}")
    print(f"Texts: {result['texts']}")

if __name__ == '__main__':
    test_document_db()
