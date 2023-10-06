import tiktoken

def num_tokens_from_strings(input_data: [str, list], model: str = "gpt-3.5-turbo-0613") -> int:
    """Returns the total number of tokens in a string or list of text strings."""
    encoding = tiktoken.encoding_for_model('gpt-3.5-turbo')    
    # If input is a single string, convert it to a list
    if isinstance(input_data, str):
        input_data = [input_data]    
    total_tokens = sum(len(encoding.encode(s)) for s in input_data)
    return total_tokens


def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613"):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4
        tokens_per_name = -1
    elif "gpt-3.5-turbo" in model:
        print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with assistant
    return num_tokens

if __name__ == "__main__":
    # For a single string
    single_string = "Hello, world!"
    encoding_model = "gpt-3.5-turbo-16k-0613"
    token_count = num_tokens_from_strings(single_string, encoding_model)
    print(f"Total number of tokens for the string with '{encoding_model}' model: {token_count}")

    # For a list of strings
    strings_list = ["Hello, world!", "How are you?", "I am using tiktoken."]
    token_count = num_tokens_from_strings(strings_list, encoding_model)
    print(f"Total number of tokens for the string with '{encoding_model}' model: {token_count}")



    # Example usage of num_tokens_from_messages
    example_messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "What's the weather today?"
        }
    ]
    print(f"\nNumber of tokens for messages: {num_tokens_from_messages(example_messages)}")

