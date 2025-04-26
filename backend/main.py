from fastapi import FastAPI, WebSocket
from kafka import KafkaProducer, KafkaConsumer
import asyncio
import threading

app = FastAPI()

producer = KafkaProducer(bootstrap_servers="localhost:9092")

def kafka_listener(websocket: WebSocket):
    consumer = KafkaConsumer(
        'chat',
        bootstrap_servers='localhost:9092',
        auto_offset_reset='earliest',
        group_id=None
    )
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for message in consumer:
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

    threading.Thread(target=kafka_listener, args=(websocket,), daemon=True).start()

    # Broadcast that the user has joined
    join_message = f"🚀 {username} has joined the {roomName}!"
    producer.send('chat', join_message.encode('utf-8'))
    producer.flush()

    while True:
        try:
            data = await websocket.receive_text()
            full_message = f"[{roomName}] {username}: {data}"
            producer.send('chat', full_message.encode('utf-8'))
            producer.flush()
        except Exception as e:
            print(f"WebSocket error: {e}")
            break