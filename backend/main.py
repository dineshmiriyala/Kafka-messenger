from fastapi import FastAPI, WebSocket
from kafka import KafkaProducer, KafkaConsumer
import asyncio
from datetime import datetime


app = FastAPI()

connected_users = set()

def broadcast_online_users(roomName):
    user_list_message = f"👥 Online Users: {', '.join(connected_users) if connected_users else 'No users online.'}"
    producer = KafkaProducer(bootstrap_servers="localhost:9092")
    topic = f"chat_{roomName.lower()}"
    producer.send(topic, user_list_message.encode('utf-8'))
    producer.flush()
    producer.close()

@app.websocket("/ws/{username}/{roomName}")
async def websocket_endpoint(websocket: WebSocket, username: str, roomName: str):
    await websocket.accept()
    connected_users.add(username)
    broadcast_online_users(roomName)

    topic = f"chat_{roomName.lower()}"
    producer = KafkaProducer(bootstrap_servers='localhost:9092')
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers='localhost:9092',
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id=f"{roomName}-{username}-group"
    )

    join_message = f"🚀 {username} has joined {roomName}!"
    producer.send(topic, join_message.encode('utf-8'))
    producer.flush()

    async def kafka_to_websocket():
        try:
            while True:
                records = consumer.poll(timeout_ms = 100)
                for tp, messages in records.items():
                    for message in messages:
                        await websocket.send_text(message.value.decode('utf-8'))
                await asyncio.sleep(0.001) # prevents CPU hogging
        except asyncio.CancelledError:
            pass

    kafka_task = asyncio.create_task(kafka_to_websocket())

    try:
        while True:
            data = await websocket.receive_text()
            timestamp = datetime.now().strftime("%I:%M %p")
            full_message = f"[{timestamp}] [{roomName}] {username}: {data}"
            producer.send(topic, full_message.encode('utf-8'))
            producer.flush()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        connected_users.discard(username)
        broadcast_online_users(roomName)
        kafka_task.cancel()
        leave_time = datetime.now().strftime("%I:%M %p")
        leave_message = f"[{leave_time}] 🚪 {username} has left {roomName}!"
        producer.send(topic, leave_message.encode('utf-8'))
        producer.flush()
        producer.close()
        consumer.close()
        await websocket.close() # ensures closing of websocket