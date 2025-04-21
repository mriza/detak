import os
from dotenv import load_dotenv
import pika
import time
import logging
import json
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

HEARTBEAT_QUEUE = os.getenv("HEARTBEAT_QUEUE")
STATIC_UUID = os.getenv("STATIC_UUID")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_heartbeat():
    connection_params = pika.ConnectionParameters(
        host=RABBITMQ_CONFIG["host"],
        port=RABBITMQ_CONFIG["port"],
        virtual_host=RABBITMQ_CONFIG["virtual_host"],
        credentials=RABBITMQ_CONFIG["credentials"],
        heartbeat=600,
        blocked_connection_timeout=300
    )

    try:
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()
        channel.queue_declare(queue=HEARTBEAT_QUEUE, durable=False)

        logger.info("Connected to RabbitMQ. Sending heartbeats every minute...")

        while True:
            # Send timestamp in UTC
            message_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uuid": STATIC_UUID
            }
            
            channel.basic_publish(
                exchange='',
                routing_key=HEARTBEAT_QUEUE,
                body=json.dumps(message_data),
                properties=pika.BasicProperties(
                    delivery_mode=1,
                    content_type='application/json'
                )
            )
            logger.info(f"Sent heartbeat: {message_data}")
            time.sleep(60)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        if 'connection' in locals() and connection.is_open:
            connection.close()

if __name__ == "__main__":
    send_heartbeat()