from pymongo import MongoClient
import os

import dotenv
from pathlib import Path

# Get the directory of the current file
env_path = Path(__file__).parent.parent / '.env'

# Load the .env file
dotenv.load_dotenv(dotenv_path=env_path)

def connect_to_mongo(uri = None, username = None, password = None, db_name=None, collection_name=None):
    try:
        if uri is None:
            uri = os.getenv('MONGODB_URI')
        if username is None:
            username = os.getenv('MONGODB_USERNAME')
        if password is None:
            password = os.getenv('MONGODB_PASSWORD')


        client = MongoClient(uri, username=username, password=password, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')  # Kiểm tra kết nối
        print("MongoDB connection successful")

        if collection_name and db_name:
            db = client[db_name]
            collection = db[collection_name]
            return collection
        
        return client[db_name] if db_name else client
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return None
