
import math
import pickle
import os

#local files
from token_counter import num_tokens_from_strings

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
            text_token_counts = [num_tokens_from_strings(text) for text in texts]
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
                "text_token_counts": text_token_counts,
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
        
    def get_texts_from_ids(self, ids, neighbor_text_count=0, overlap=0, max_tokens=0):
        organized_data = {}
        
        # 1. Split ids into file_ids and text_ids.
        ids = [item for sublist in ids for item in sublist]
        for id_str in ids:
            file_id, text_id = map(int, id_str.split('.'))
            if not organized_data.get(file_id):
                organized_data[file_id] = []
            organized_data[file_id].append(text_id)
        
        # 2. Organize them by file_paths.
        organized_by_file_path = {}
        for file_id, text_ids in organized_data.items():
            file_path = self.get_file_path_from_id(file_id)
            if file_path:
                organized_by_file_path[file_path] = sorted(text_ids)
        
        output = []
        for file_path, text_ids in organized_by_file_path.items():
            # 3. Retrieve the necessary document details.
            doc = self.documents.get(file_path)
            print(f"file_path: {file_path}")
            # 4. Get neighboring text_ids.
            extended_text_ids = []
            for tid in text_ids:
                extended_text_ids.extend(range(tid - neighbor_text_count, tid + neighbor_text_count + 1))
            extended_text_ids = sorted(list(set(extended_text_ids)))
            max_index = len(doc['texts']) - 1
            extended_text_ids = [i for i in extended_text_ids if 0 <= i <= max_index]


            # 5. Fetch matched_texts and matched_text_token_counts
            matched_texts = [doc['texts'][i] for i in extended_text_ids if 0 <= i < len(doc['texts'])]
            matched_text_token_counts = [doc['text_token_counts'][i] for i in extended_text_ids if i < len(doc['text_token_counts'])]
            metadata_str = "; ".join([f"{key}: {value}" for key, value in doc['metadata'].items()])
            metadata_tokens = num_tokens_from_strings(metadata_str)

            # 6. Assemble metadata and text.
            combined_texts = []
            prev_tid = None
            for tid in extended_text_ids:
                if prev_tid and tid - prev_tid != 1:
                    combined_texts.append("\n\n...TEXT GAP...\n\n")
                if tid < len(doc['texts']):
                    combined_texts.append(doc['texts'][tid])
                prev_tid = tid
            combined_texts = " ".join(combined_texts)

            # 7. Enforce max_tokens on the combined text and metadata.
            available_tokens = max_tokens - metadata_tokens
            if available_tokens <= 0:
                continue  # Metadata itself exceeds max_tokens. Consider handling this edge case.

            part_texts = []  # For storing text
            part_token_counts = []  # For storing token count for each text in part_texts
            current_token_count = 0
            part_text = ""

            for idx, text in enumerate(matched_texts):
                current_text_token_counts = matched_text_token_counts[idx]
                
                # If adding the next text would exceed the available tokens
                if current_token_count + current_text_token_counts > available_tokens:
                    # If we've already accumulated some texts in this part, append it and reset
                    if part_text:
                        part_texts.append(part_text)
                        part_token_counts.append(current_token_count)
                        part_text = text
                        current_token_count = current_text_token_counts
                    else:
                        # Handle the scenario where one text's tokens exceed available_tokens multiple times.
                        num_splits = math.ceil(current_text_token_counts / available_tokens)

                        # Calculate approximate character counts for each split
                        chars_per_split = len(text) / num_splits

                        for i in range(num_splits):
                            start_index = int(i * chars_per_split)
                            end_index = int((i + 1) * chars_per_split)
                            part_text_split = text[start_index:end_index]

                            # Estimating tokens for the part using a uniform distribution assumption
                            if i != num_splits - 1:
                                tokens_for_split = available_tokens
                            else:
                                # For the last part, just take the remaining tokens
                                tokens_for_split = current_text_token_counts - available_tokens * i

                            part_texts.append(part_text_split)
                            part_token_counts.append(tokens_for_split)

                        current_token_count = 0
                        part_text = ""

                else:
                    # If the text fits, simply add it
                    if part_text:
                        part_text += " "
                    part_text += text
                    current_token_count += current_text_token_counts

            # Add any remaining text to part_texts
            if part_text:
                part_texts.append(part_text)
                part_token_counts.append(current_token_count)

            # Formulate combined_texts_and_metadatas
            for idx, part in enumerate(part_texts):
                combined_texts_and_metadatas = f"[TEXT EXTRACT:'{part}'] [METADATA: '{metadata_str}']\n"
                total_tokens = metadata_tokens + part_token_counts[idx]
                output.append([combined_texts_and_metadatas, total_tokens])


        # 8. Use a greedy algorithm to group them.
        grouped_texts_and_metadatas = []
        current_group = ""
        current_tokens = 0
        for item in output:
            if current_tokens + item[1] <= max_tokens:
                current_group += item[0]
                current_tokens += item[1]
            else:
                grouped_texts_and_metadatas.append(current_group)
                current_group = item[0]
                current_tokens = item[1]
        if current_group:
            grouped_texts_and_metadatas.append(current_group)

        return grouped_texts_and_metadatas

        
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
