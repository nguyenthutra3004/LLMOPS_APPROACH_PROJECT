import sys
from utils.mongo import connect_to_mongo
from datetime import datetime
from typing import Optional, List, Dict, Any

sys.path.append("..")



skip_line_tags = [
    'Chắc chắn rồi,',
    'Tuyệt vời!',
    'Chào bạn,',
    'Vào thời điểm bài báo được đăng tải,',
    'Thưa quý vị,'

]

remove_first_sent = [

    'cung cấp thông tin chi tiết',
    'gì tôi có',
    'gì tôi được biết',
    'thông tin đã được công bố'
]

remove_tags = [
    'tôi rất tiếc',
    'thông tin được cung cấp',
    'thời điểm bài viết được đăng tải',
    'thông tin có được',
    'tháng 5 năm 2025',
    'dựa trên thông tin',
]

def get_good_msg(msg: list[dict]) -> list[dict]:

    good_msg = []
    
    for i in range(len(msg)):
        
        if msg[i]['role'] != 'assistant':
            continue

        first_sentence = msg[i]['content'].split('.')[0]
        rest_paragraph = '.'.join(msg[i]['content'].split('.')[1:])

        for tag in skip_line_tags:
            if tag in first_sentence:
                msg[i]['content'] = msg[i]['content'].replace(tag, '').strip()

                # Capitalize the first letter of the first sentence
                msg[i]['content'] = msg[i]['content'][0].upper() + msg[i]['content'][1:]

        for tag in remove_first_sent:
            if tag in first_sentence:
                msg[i]['content'] = rest_paragraph.strip()


        flag_get = True
        for tag in remove_tags:
            if tag in msg[i]['content'].lower():
                flag_get = False
                break

        if flag_get:
            good_msg.extend(msg[i-1:i+1])
    return good_msg



def pull_messages(time_start: Optional[datetime] = None, 
                  time_end: Optional[datetime] = None,
                  source: Optional[str] = None, 
                  limit: int = -1) -> List[Dict[Any, Any]]:
    """
    Pull messages from the training_messages.news collection with optional filtering.
    
    Args:
        time_start: Optional start time to filter documents
        time_end: Optional end time to filter documents
        source: Optional source to filter documents (e.g., "vtc")
        limit: Maximum number of documents to return (default: 1000)
        
    Returns:
        List of message documents from the collection
    """
    # Connect to MongoDB collection
    collection = connect_to_mongo(
        db_name='training_messages',
        collection_name='news_v2'
    )
    
    # Build query filters based on parameters
    query_filter = {}
    
    # Add time filter if provided
    if time_start or time_end:
        query_filter["time"] = {}
        if time_start:
            query_filter["time"]["$gte"] = time_start
        if time_end:
            query_filter["time"]["$lte"] = time_end
    
    # Add source filter if provided
    if source:
        query_filter["source"] = source
    
    # Ensure we only get documents with messages generated
    query_filter["message_generated"] = True
    
    # Execute query
    # Only retrieve the messages field, exclude _id
    if limit == -1:
        cursor = collection.find(query_filter, {"messages": 1, "_id": 0})
    else:
        cursor = collection.find(query_filter, {"messages": 1, "_id": 0}).limit(limit)
    
    # Convert cursor to list and return
    clean_messages = []
    for c in cursor:
        if '<content>\n\nnone\n\n</content>' in c["messages"][0]['content'].lower():
            continue
        else:
            clean_c = get_good_msg(c["messages"])
            if len(clean_c) > 0:
                clean_messages.append({

                    "messages": clean_c
                })
    return clean_messages


def pull_contents():
    pass


if __name__ == "__main__":
    # Example usage
    import json
    messages = pull_messages(
        # time_start=datetime(2023, 1, 1),
        # time_end=datetime.now(),
        # source="vtc",
        limit=-1
    )
    
    print(f"Retrieved {len(messages)} messages")
    
    # Print first message if available
    if messages:
        print(f"Sample message from: {messages[0].get('source', 'unknown')}")
        print(f"Content snippet: {messages[0].get('content', '')[:100]}...")
        print(f"Number of conversation turns: {len(messages[0].get('messages', []))//2}")
        with open("news_messages.json", "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=4)