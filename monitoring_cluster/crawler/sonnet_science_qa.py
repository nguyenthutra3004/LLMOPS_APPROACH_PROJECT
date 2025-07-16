import json
import os

with open('data/sonnet3.5_science_en.json', 'r') as f:
    msg_dataset = json.load(f)

print("Total data",len(msg_dataset))

from llm import RotateGemini, ChatGPT, OpenAIWrapper
from dotenv import load_dotenv
load_dotenv()

# llm = OpenAIWrapper(host= os.getenv('LLM_HOST'), model_name='nvidia/llama-3.3-nemotron-super-49b-v1', api_key=os.getenv('LLM_API_KEY')) 
llm = RotateGemini(model_name = 'gemini-2.0-flash-lite')


def translate_feedback(messages):

    system = (
        "You will be given a conversation between a user and an assistant. The content of a single message will be in English in <msg> tags.\n"
        "Your task is to translate the content the message into Vietnamese.\n"
        "Only return the translation of the content in <msg> tag!!! Do not do anything else.\n"
        "If code is in the content, you can translate the comment of the code but do not translate the code.\n"
        "Translate as natural and human as possible.\nRemove the <msg> tag in the translation\n"
    )

    message = [
        {
            'role': 'system',
            'content': system
        }
    ]
    results = []

    for msg in messages:
        role = msg['role']
        content = msg['content']
        
        vai = 'người dùng' if role == 'user' else 'trợ lí'

        if not isinstance(content,str) or content == '': # error_message
            if role == 'asistant':
                results.pop() # delete the last message
            break

        message.append({
            'role': 'user',
            'content': f"{role} messages:\n <msg>{content}</msg>"
        })

        translate = llm(message)

        # clean up the translation
        translate = translate.replace('<msg>', '').replace('</msg>', '')
        if '```text' == translate[:6]:
            translate = translate[6:-3]

        results.append({
            'role': role,
            'content': translate
        })
        
        message.pop()

        # message.append({
        #     'role': 'assistant',
        #     'content': translate
        # })

        if not isinstance(translate,str) or translate == '':
            results.pop() # delete the last message
            if role == 'asistant':
                results.pop()
            break

    # print(message)

    return results

import json


def process_feedback(data, id_, save_dir):
    
    messages = translate_feedback(data)

    if len(messages) == 0:
        print(f"Skip id {id_}")
        return

    with open(save_dir, 'a') as f: # jsonl file
        # f.write(json.dump({
        #     'id': id_,
        #     'messages': messages
        # }, f)+'\n')
        f.write(json.dumps({
            'id': id_,
            'messages': messages
        })+'\n')


SKIP_NUMBER = 0

from concurrent.futures import ThreadPoolExecutor
import time

def multithread_translate(dataset, save_file, num_threads=2):
    
    # with ThreadPoolExecutor(max_workers=num_threads) as executor:
    #     for id_, data in dataset:
    #         executor.submit(process_feedback, data, id_, save_file)

    for id_, data in dataset:
        process_feedback(data, id_, save_file)
        # time.sleep(10) # sleep 0.5s to avoid rate limit


import os
import json

if __name__ == '__main__':
    save_file = 'data/sonnet_science_qa_vi.jsonl'
    
    done_ids = set()
    if os.path.exists(save_file):
        with open(save_file, 'r') as f:
            for line in f:
                data = json.loads(line)
                done_ids.add(data['id'])

    process_dataset = []
    for i, data in enumerate(msg_dataset):
        if i < SKIP_NUMBER:
            continue
        if i not in done_ids:
            process_dataset.append((i, data['messages']))


    multithread_translate(process_dataset, save_file) # 25000
