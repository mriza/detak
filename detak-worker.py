import os
from dotenv import load_dotenv
import pika
import json
import logging
from pymongo import MongoClient
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# RabbitMQ Configuration
RABBITMQ_CONFIG = {
    "host": os.getenv("RABBITMQ_HOST"),
    "port": int(os.getenv("RABBITMQ_PORT")),
    "virtual_host": os.getenv("RABBITMQ_VIRTUAL_HOST"),
    "credentials": pika.PlainCredentials(
        os.getenv("RABBITMQ_USERNAME"), os.getenv("RABBITMQ_PASSWORD")
    ),
}

# MongoDB Configuration
MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DB")
COLLECTION_NAME = os.getenv("MONGODB_COLLECTION")
OBJECTS_COLLECTION = os.getenv("MONGODB_OBJECTS_COLLECTION")
HEARTBEAT_QUEUE = os.getenv("HEARTBEAT_QUEUE")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_to_mongodb(message):
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        main_collection = db[COLLECTION_NAME]
        objects_collection = db[OBJECTS_COLLECTION]

        # Check if UUID exists in the message
        uuid = message.get("uuid")
        if not uuid:
            logger.error("Message does not contain a UUID. Skipping...")
            return False

        # Check if UUID exists in the objects collection
        if not objects_collection.find_one({"uuid": uuid}):
            # Create a new entry in the objects collection
            objects_collection.insert_one({"uuid": uuid, "object_name": "Unknown Object"})
        else:
            # Optionally update the object_name if needed
            if "object_name" in message:
                objects_collection.update_one(
                    {"uuid": uuid},
                    {"$set": {"object_name": message["object_name"]}}
                )

        # Insert the message into the main collection
        main_collection.insert_one(message)
        client.close()
        return True
    except Exception as e:
        logger.error(f"MongoDB Error: {str(e)}")
        return False

def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        logger.info(f"Received message: {message}")
        
        # Add processing timestamp in UTC
        message['processed_at'] = datetime.now(timezone.utc).isoformat()
        
        if save_to_mongodb(message):
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            logger.warning("Message storage failed, requeuing...")
            ch.basic_nack(delivery_tag=method.delivery_tag)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON message")
        ch.basic_nack(delivery_tag=method.delivery_tag)

def start_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=RABBITMQ_CONFIG["host"],
        port=RABBITMQ_CONFIG["port"],
        virtual_host=RABBITMQ_CONFIG["virtual_host"],
        credentials=RABBITMQ_CONFIG["credentials"]
    ))
    channel = connection.channel()
    channel.queue_declare(queue=HEARTBEAT_QUEUE)
    
    channel.basic_consume(
        queue=HEARTBEAT_QUEUE,
        on_message_callback=callback,
        auto_ack=False
    )
    
    logger.info("Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()

if __name__ == "__main__":
    start_consumer()