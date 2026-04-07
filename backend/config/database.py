"""
Database Configuration
BTech CSE Final Year Project - Data Integrity Platform

This module handles MongoDB connection and configuration.
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Database:
    """MongoDB Database Connection Manager"""
    
    def __init__(self):
        """Initialize database connection"""
        self.mongo_uri = os.getenv('MONGODB_URI')
        self.db_name = os.getenv('MONGO_DB_NAME', 'data_integrity_platform')
        self.client = None
        self.db = None
        
    def connect(self):
        """
        Establish connection to MongoDB
        
        Returns:
            Database object if successful, None otherwise
        """
        try:
            if not self.mongo_uri:
                raise Exception('MONGODB_URI not set in environment')

            # Create MongoDB client
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database
            self.db = self.client[self.db_name]

            # Ensure users.phone index allows missing/null phone values while
            # still enforcing uniqueness for actual phone numbers.
            users_collection = self.db['users']
            phone_index = users_collection.index_information().get('phone_1')
            if phone_index and phone_index.get('unique') and not phone_index.get('sparse'):
                users_collection.drop_index('phone_1')
            users_collection.create_index('phone', unique=True, sparse=True)
            
            print(f"[OK] Connected to MongoDB: {self.db_name}")
            return self.db
            
        except ConnectionFailure as e:
            print(f"[ERROR] Failed to connect to MongoDB: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Database error: {e}")
            return None
    
    def get_collection(self, collection_name):
        """
        Get a specific collection from database
        
        Args:
            collection_name (str): Name of the collection
            
        Returns:
            Collection object
        """
        if self.db is None:
            raise Exception("Database not connected. Call connect() first.")
        return self.db[collection_name]
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            print("[OK] MongoDB connection closed")

# Global database instance
db_instance = Database()
