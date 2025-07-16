import json
import os
import tiktoken

enc = tiktoken.get_encoding("o200k_base")

def count_valid_lines(file_path):
    valid_lines = 0
    with open(file_path, 'r') as file:
        for line in file:
            try:
                json.loads(line)
                valid_lines += 1
            except json.JSONDecodeError:
                continue
    print(f"Total valid lines: {valid_lines}")

def get_file_size(file_path):
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert bytes to MB
    print(f"File size: {file_size:.2f} MB")

import concurrent.futures

def count_tokens(file_path):
    enc = tiktoken.get_encoding("o200k_base")
    total_tokens = 0

    def process_line(line):
        try:
            data = json.loads(line)
            content = data.get("content", "")
            tokens = enc.encode(content)
            return len(tokens)
        except json.JSONDecodeError:
            return 0

    with open(file_path, 'r') as file:
        lines = file.readlines()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_line, lines))

    total_tokens = sum(results)
    print(f"Total tokens: {total_tokens}")

def count_tokens_messages(messages):
    
    total_tokens = 0

    for message in messages:
        content = message.get("content", "")
        tokens = enc.encode(content)
        total_tokens += len(tokens)

    # print(f"Total tokens: {total_tokens}")
    return total_tokens

if __name__ == "__main__":
    file_path = '../data/tuyengiao.jsonl'
    count_valid_lines(file_path)
    count_tokens(file_path)
    get_file_size(file_path)
