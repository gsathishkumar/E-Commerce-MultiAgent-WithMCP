from pymongo import MongoClient

client = MongoClient(
    "mongodb://ecommerce_user:ecommerce_pwd@localhost:27017/?authSource=ecommerce_db"
)

print(client.list_database_names())