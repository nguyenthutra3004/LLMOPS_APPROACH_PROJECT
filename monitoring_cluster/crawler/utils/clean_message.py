import os
import json

def count_chinese_characters(line):
    chinese_count = 0
    for char in line:
        if '\u4e00' <= char <= '\u9fff':
            chinese_count += 1
    contains_chinese = chinese_count > 0
    return chinese_count


def mixed_err_chinese_remove(line):
    words = line.split()
    chinese_words = 0
    for word in words:
        if count_chinese_characters(word) > 0:
            if count_chinese_characters(word)/len(word) < 0.5 and len(word) > 3: 
                return True
            chinese_words += 1
    
    if chinese_words/len(words) > 0.4:
        return True
    return False

def remove_chinese(messages):
    flag = False 
    for message in messages:
        if 'content' in message:
            content = message['content']
            if count_chinese_characters(content) > 0:
                flag = True
                break
    return flag

def prune_chinese(data):

    count_prune = 0
    keep = []
    for message in data:
        should_remove = remove_chinese(message['messages'])
        if should_remove:
            count_prune += 1
        else:
            keep.append(message)
    print(f"Removed {count_prune} messages with Chinese characters.")
    return keep


def check_messages(data):
    keep_data = []
    for messages in data:
        new_messages = []
        try:
            for message in messages['messages']:
                if message['content'] == '':
                    if messages['role'] == 'assistant':
                        new_messages.pop()
                    break
                else:
                    new_messages.append(message)
            if len(new_messages) > 1:
                keep_data.append({
                    'messages': new_messages,
                })
        except KeyError:
            print(f"KeyError: {messages}")
            continue
    return keep_data
