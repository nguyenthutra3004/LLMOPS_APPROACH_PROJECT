# process data

import json 
import os

import pymongo

from utils.mongo import connect_to_mongo

import datetime
import re
from tqdm import tqdm


def parse_vietnamese_datetime(time_str):
    """
    Parse a Vietnamese date time string like "Thứ sáu, ngày 25/04/2025 - 11:39"
    into a datetime object
    """
    try:
        # Format: "Thứ sáu, ngày 25/04/2025 - 11:39"
        vn_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', time_str)
        if vn_match:
            date_str = vn_match.groups()[0]
            day, month, year = map(int, date_str.split('/'))

            return datetime.datetime(year, month, day)
        
        # Try other common formats if needed
        # Add more pattern matching here for other date formats
        
    except Exception as e:
        print(f"Error parsing date: {time_str}, error: {e}")
    
    return None

def convert_time_fields():
    """
    Connect to MongoDB and convert all time fields to datetime objects
    """
    # Connect to MongoDB
    client = connect_to_mongo()
    db = client['crawler']
    links = ['links_dantri', 'links_tg', 'links_vnex', 'links_vtc', 'links_vnet', 'links_nd']

    for link in links:
        collection = db[link]
        
        # Find all documents with a 'time' field that is a string
        cursor = collection.find({"time": {"$exists": True, "$type": "string"}})
        
        update_count = 0
        error_count = 0
        
        for doc in cursor:
            time_str = doc.get('time')
            if not time_str or not isinstance(time_str, str):
                continue
                
            datetime_obj = parse_vietnamese_datetime(time_str)
            if datetime_obj:
                # Update the document with the new datetime object
                result = collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"time": datetime_obj}}
                )
                if result.modified_count:
                    update_count += 1
            else:
                error_count += 1
                print(f"Could not parse datetime from: {time_str}")
        
        print(f"Updated {update_count} documents with datetime objects")
        print(f"Failed to parse {error_count} time strings")




def add_word_count_field():
    """
    Connect to MongoDB and add word_count field to all documents with content
    """
    # Connect to MongoDB
    client = connect_to_mongo()
    db = client['crawler']
    links = ['links_dantri', 'links_tg', 'links_vnex', 'links_vtc', 'links_vnet', 'links_nd']

    for link in links:
        collection = db[link]
        
        # Find all documents with content but no word_count field
        cursor = collection.find({
            "content": {"$exists": True},
            "word_count": {"$exists": False}
        })
        
        # Count total documents for progress bar
        total_docs = collection.count_documents({
            "content": {"$exists": True},
            "word_count": {"$exists": False}
        })
        
        update_count = 0
        error_count = 0
        
        # Use tqdm for progress tracking
        for doc in tqdm(cursor, total=total_docs, desc=f"Processing {link}"):
            try:
                content = doc.get('content', '')
                if content and isinstance(content, str):
                    word_count = len(content.split())
                    
                    # Update the document with the word count
                    result = collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"word_count": word_count}}
                    )
                    
                    if result.modified_count:
                        update_count += 1
            except Exception as e:
                error_count += 1
                print(f"Error processing document {doc.get('_id')}: {e}")
        
        print(f"{link}: Updated {update_count} documents with word_count field")
        print(f"{link}: Failed to update {error_count} documents")


def add_data(link_path, content_path, collection_name):
    """
    Add data from JSON files to MongoDB collection
    """
    # Connect to MongoDB
    client = connect_to_mongo()
    db = client['crawler']
    
    # Load data from JSON files
    links = []
    if isinstance(link_path, str) and os.path.exists(link_path):
        with open(link_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    links.append(data)
                except json.JSONDecodeError as e:
                    print(f"WARNING: Skip error line")
    
    contents = []
    if isinstance(content_path, str) and  os.path.exists(content_path):
        with open(content_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    contents.append(data)
                except json.JSONDecodeError as e:
                    print(f"WARNING: Skip error line")
        
    # Combine data into a single list of dictionaries
    data_links = []
    for link in links:
        data_links.append({
            "link": link.get("link"),
            "title": link.get("title"),
            "date_added": datetime.datetime.now() 
        })

    data_contents = []
    for content in contents:
        data_contents.append({
            "link": content.get("link"),
            "content": content.get("content"),
            "time": parse_vietnamese_datetime(content.get("time")), 
            "word_count": len(content.get("content", "").split()),
        })
    
    # Insert links into MongoDB collection
    collection = db[collection_name]
    for item in data_links:
        try:
            collection.insert_one(item)
        except pymongo.errors.DuplicateKeyError:
            print(f"Duplicate key error for link: {item['link']}")
        except Exception as e:
            print(f"Error inserting document: {e}")

    print(f"Inserted {len(data_links)} documents into {collection_name} collection")

    for item in data_contents:
        try:
            exist = 0
            added = 0
            # Update if document with this link exists, otherwise insert as new document
            # Check if document with this link exists and has content
            existing_doc = collection.find_one({"link": item["link"]})
            
            if existing_doc and "content" in existing_doc:
                if existing_doc["content"] and len(existing_doc["content"]) > 1:
                    # Document exists with content, only update other fields
                # Document exists with content, only update other fields
                    exist +=1
                    continue

                # Document doesn't exist or has no content, insert/update all fields
            collection.update_one(
                {"link": item["link"]},
                {"$set": item},
                upsert=True
            )
            added += 1
        except Exception as e:
            print(f"Error inserting document: {e}")
    print(f"Inserted {len(data_contents)} documents into {collection_name} collection")


def delete_nhandan_links():
        """
        Delete all documents from links_vnet collection where link contains 'http://nhandan.vn'
        """
        # Connect to MongoDB
        client = connect_to_mongo()
        db = client['crawler']
        collection = db['links_vnet']
        
        # Delete documents that match the pattern
        result = collection.delete_many({"link": {"$regex": "https://nhandan.vn"}})
        
        print(f"Deleted {result.deleted_count} documents with nhandan.vn links")
        return result.deleted_count

def delete_sosanh():
        """
        Delete all documents from links_vnet collection where link contains 'http://nhandan.vn'
        """
        # Connect to MongoDB
        client = connect_to_mongo()
        db = client['crawler']
        collection = db['links_dantri']
        
        # Delete documents that match the pattern
        result = collection.delete_many({"link": {"$regex": "https://websosanh.vn/"}})
        
        print(f"Deleted {result.deleted_count} documents with nhandan.vn links")
        return result.deleted_count
import re 

def is_short_name(content):

    # Pattern for short names with initials like N.Q.A or K.K.H.D
    pattern = r"[A-Z](\.[A-Z])+\."
    matches = re.findall(pattern, content)
    if matches:

        return True
    else:
        return False


def qa_to_message(qa_pairs, content = None):
    messages = []
    
    flag_need_rag = False

    for message in qa_pairs:

        q = message.get("question")
        a = message.get("answer")

        rag_keyword = ['theo', 'này', 'giá', 'trên']
        for keyword in rag_keyword:
            if keyword in q:
                flag_need_rag = True
                break
        if is_short_name(q):
            flag_need_rag = True

        messages.extend(
            [
                {
                    "role": "user",
                    "content": q
                },
                {
                    "role": "assistant",
                    "content": a
                }
            ]
        )
    if flag_need_rag and content:

        messages[0]['content'] = f"""Bạn được cung cấp một đoạn văn bản sau:\n\n<content>\n\n{content}\n\n</content>\n\nDựa vào đoạn văn bản trên, hãy trả lời các câu hỏi sau:\n\n""" + messages[0]['content']

    return messages


def process_and_save_to_mongodb(qa_pairs, source_collection, dest_collection):
    """Process a document and save the results to MongoDB collection"""
    # try:
    if True:
        qa_object = qa_pairs
        qa_object['time'] = datetime.datetime.now()

        link = qa_object.get("link")
        
        if qa_object["qa_pairs"]:

            # Fetch the content from source collection based on link
            source_doc = source_collection.find_one({"link": link})
            if source_doc and "content" in source_doc:
                # Add content field to qa_object
                print(source_doc["content"][:5])
                qa_object["content"] = source_doc["content"]
                
                # Create messages with RAG if needed
                qa_object['messages'] = qa_to_message(qa_object["qa_pairs"], source_doc["content"])
            else:
                # If no content found, create messages without RAG
                qa_object['messages'] = qa_to_message(qa_object["qa_pairs"])

            del qa_object["qa_pairs"]

            # Add message_generated flag
            qa_object["message_generated"] = True
            
            # Insert into destination collection
            dest_collection.insert_one(qa_object)
            
            # Update source collection to mark as processed
            source_collection.update_one(
                {"link": link}, 
                {"$set": {"message_generated": True}}
            )
            
            return True
    # except Exception as e:
    #     print(f"Error processing document: {e}")
    
    return False
    

if __name__ == "__main__":
    # # add_word_count_field()
    # add_data(
    #     link_path=None,
    #     content_path="data/dantri.jsonl",
    #     collection_name="links_nd"
    # )
    # delete_nhandan_links()
    delete_sosanh()
    # source_collection = connect_to_mongo(
    #     db_name='crawler',
    #     collection_name='links_nd'
    # )
    # dest_collection = connect_to_mongo(
    #     db_name='training_messages',
    #     collection_name='news'
    # )

    # qa_pairs = []
    # with open("data/nhandan_qa.jsonl", "r", encoding="utf-8") as f:
    #     for line in f:
    #         try:
    #             data = json.loads(line)
    #             qa_pairs.append(data)
    #         except json.JSONDecodeError as e:
    #             print(f"WARNING: Skip error line")

    # for qa_pair in qa_pairs:
    #     qa_pair['source'] = "nd"
    #     # Process and save each QA pair
    #     process_and_save_to_mongodb(qa_pair, source_collection, dest_collection)