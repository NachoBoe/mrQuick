from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Callable, Union
from fastapi import WebSocket

class Activity(BaseModel):
    type: str
    content: str
    timestamp: str
    sender: str
    card_content: Optional[str] = None
    suggestion_content: Optional[List[str]] = None

class parametro(BaseModel):
    nombre: str
    tipo: str
    descripcion: str

class Step:
    def __init__(self, function: Callable[['BaseBot', Activity], None]):
        self.function = function

    async def run_step(self, bot: 'BaseBot', activity: Activity):
        await self.function(bot, activity)

class Flow:
    def __init__(self, trigger_phrases: List[str], steps: List[Step], entradas: List[parametro], descripcion: str):
        self.trigger_phrases = trigger_phrases
        self.steps = steps
        self.entradas = entradas
        self.descripcion = descripcion
    
    async def go_to_step(self, bot: 'BaseBot', index: int):
        bot.current_step_index = index
        await self.steps[index].run_step(bot, bot.state_memory[-1])
        
class BaseBot:
    def __init__(self, websocket: WebSocket, flows: List['Flow']):
        self.websocket = websocket
        self.state_memory: List[Activity] = []
        self.current_flow: Optional['Flow'] = None
        self.current_step_index: int = 0
        self.chat_history: List[str] = []
        self.all_flows = flows

    async def on_start(self):
        raise NotImplementedError("The on_start method must be implemented by the subclass")

    async def on_activity(self, activity: Activity):
        raise NotImplementedError("The on_activity method must be implemented by the subclass")
