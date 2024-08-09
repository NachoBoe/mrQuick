from fastapi import FastAPI, WebSocket

from typing import List


from src import Activity
from bot import Bot
from flujos import all_flows

from langsmith import Client
from dotenv import load_dotenv
from pyprojroot import here
import os


# VARIABLES DE ENTORNO
dotenv_path = here() / ".env"
load_dotenv(dotenv_path=dotenv_path)

# LANGSMITH
client = Client()
os.environ["LANGCHAIN_PROJECT"] = f"MrQuick"


app = FastAPI()



class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> Bot:
        await websocket.accept()
        bot = Bot(websocket, flows = all_flows)
        await bot.on_start()
        self.active_connections.append(websocket)
        return bot

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    bot = await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            activity = Activity(**data)
            await bot.on_activity(activity)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)