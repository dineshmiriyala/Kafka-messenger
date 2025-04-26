from fastapi import FastAPI, WebSocket
from kafka import KafkaProducer, KafkaConsumer
import asyncio
import threading
from datetime import datetime


app = FastAPI()

producer = KafkaProducer(bootstrap_servers="localhost:9092")

connected_users = set()

def kafka_listener(websocket: WebSocket, stop_event: threading.Event):
    consumer = KafkaConsumer(
        'chat',
        bootstrap_servers='localhost:9092',
        auto_offset_reset='earliest',
        group_id=None
    )
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for message in consumer:
        if stop_event.is_set():
            break
        text = message.value.decode('utf-8')
        try:
            coro = websocket.send_text(text)
            loop.run_until_complete(coro)
        except Exception as e:
            print(f"Listener error: {e}")
            break

@app.websocket("/ws/{username}/{roomName}")
async def websocket_endpoint(websocket: WebSocket, username: str, roomName: str):
    await websocket.accept()

    stop_event = threading.Event()
    thread = threading.Thread(target=kafka_listener, args=(websocket, stop_event), daemon=True)
    thread.start()

    connected_users.add(username)

    join_time = datetime.now().strftime("%I:%M %p")
    join_message = f"[{join_time}] 🚀 {username} has joined the {roomName}!"
    producer.send('chat', join_message.encode('utf-8'))
    producer.flush()

    user_list_message = f"👥 Online Users: {', '.join(connected_users)}"
    producer.send('chat', user_list_message.encode('utf-8'))
    producer.flush()

    try:
        while True:
            data = await websocket.receive_text()
            timestamp = datetime.now().strftime("%I:%M %p")
            full_message = f"[{timestamp}] [{roomName}] {username}: {data}"
            producer.send('chat', full_message.encode('utf-8'))
            producer.flush()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        connected_users.discard(username)
        stop_event.set()

        leave_time = datetime.now().strftime("%I:%M %p")
        leave_message = f"[{leave_time}] 🚪 {username} has left the {roomName}!"
        producer.send('chat', leave_message.encode('utf-8'))
        producer.flush()

        user_list_message = f"👥 Online Users: {', '.join(connected_users) if connected_users else 'No users online.'}"
        producer.send('chat', user_list_message.encode('utf-8'))
        producer.flush()