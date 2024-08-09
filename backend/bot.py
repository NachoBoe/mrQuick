from src import Activity, BaseBot

from langchain_core.prompts import ChatPromptTemplate
from langchain.prompts import MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser

from fastapi import FastAPI, WebSocket

from typing import List, Dict, Any, Optional, Callable, Union

from utils import print_flows, print_flow_inputs
from langchain_openai import ChatOpenAI

import prompts as p
import dotenv
import os 

dotenv.load_dotenv("../.env")

llm = ChatOpenAI(model="gpt-4o-mini",temperature=0.0,streaming=True,model_kwargs={"response_format": {"type": "json_object"}},api_key=os.getenv("OPENAI_API_KEY"))


class Bot(BaseBot):
    
    async def on_start(self):
        
        start_activity = Activity(
            type="message",
            content="Hola! Soy MrQuick, su asistente financiero. ¿En qué puedo ayudarte hoy?",
            timestamp="2024-07-25T12:34:56Z",
            sender="bot"
        )
        self.chat_history.append(("ai", start_activity.content))
        await self.websocket.send_json(start_activity.dict())
        self.state_memory.append(start_activity)

        
        start_suggestion_activity = Activity(
            type="suggestion",
            content="",
            timestamp="2024-07-25T12:34:56Z",
            sender="bot",
            suggestion_content = ["Consultar saldo", "Transferir dinero", "¿Qué es MrQuick?"]
        )
        await self.websocket.send_json(start_suggestion_activity.dict())
        self.state_memory.append(start_suggestion_activity)


    async def on_activity(self, activity: Activity):
        try:
            self.state_memory.append(activity)
            if not self.current_flow:
                # Check if the activity triggers any flow
                trigger_flow_chain = p.trigger_flow_prompt | llm | JsonOutputParser()
                decision = trigger_flow_chain.invoke({"input": activity.content, "flows": print_flows(self.all_flows), "chat_history": self.chat_history})
                if decision["ejecutar_flujo"] == "true":
                    for flow in self.all_flows:
                        if flow.__class__.__name__ == decision["nombre_flujo"]:
                            self.current_flow = flow
                            if flow.entradas:
                                parse_flow_inputs_chain = p.parse_flow_inputs | llm | JsonOutputParser()
                                inputs = parse_flow_inputs_chain.invoke({"input": activity.content, "entradas": print_flow_inputs(flow), "chat_history": self.chat_history})
                                self.current_flow.default_inputs = inputs
                            self.current_step_index = 0
                            await self.advance_flow(activity)
                            return
                    response_activity = Activity(
                        type="message",
                        content="No se encontró el flujo solicitado.",
                        timestamp="2024-07-25T12:34:56Z",
                        sender="bot"
                    )
                    await self.websocket.send_json(response_activity.dict())
                    self.state_memory.append(response_activity)
                else:
                    response_activity = Activity(
                        type="message",
                        content=decision["mesaje_directo"],
                        timestamp="2024-07-25T12:34:56Z",
                        sender="bot"
                    )
                    self.chat_history.append(("human", activity.content))
                    self.chat_history.append(("ai", response_activity.content))
                    await self.websocket.send_json(response_activity.dict())
                    self.state_memory.append(response_activity)
                    start_suggestion_activity = Activity(
                        type="suggestion",
                        content="",
                        timestamp="2024-07-25T12:34:56Z",
                        sender="bot",
                        suggestion_content = ["Consultar saldo", "Transferir dinero"]
                    )
                    await self.websocket.send_json(start_suggestion_activity.dict())
                    self.state_memory.append(start_suggestion_activity)
            else:
                # Proceed with the current flow
                await self.advance_flow(activity)
        except Exception as e:
            print(f"Error: {e}")
            error_activity = Activity(
                type="message",
                content="Ocurrió un error. Por favor, intente nuevamente.",
                timestamp="2024-07-25T12:34:56Z",
                sender="bot"
            )
            await self.websocket.send_json(error_activity.dict())
            self.current_flow = None
            self.current_step_index = 0
            
    async def run_current_step(self, activity: Activity):
        if self.current_flow and self.current_step_index < len(self.current_flow.steps):
            step = self.current_flow.steps[self.current_step_index]
            await step.run_step(self, activity)

    async def advance_flow(self, activity: Activity):
        if self.current_flow and self.current_step_index <= len(self.current_flow.steps)-1:
            await self.run_current_step(activity)
            self.current_step_index += 1

        if self.current_step_index >= len(self.current_flow.steps):
            self.current_flow = None
            self.current_step_index = 0
            start_suggestion_activity = Activity(
                type="suggestion",
                content="",
                timestamp="2024-07-25T12:34:56Z",
                sender="bot",
                suggestion_content = ["Consultar saldo", "Transferir dinero"]
            )
            await self.websocket.send_json(start_suggestion_activity.dict())
            self.state_memory.append(start_suggestion_activity)
        