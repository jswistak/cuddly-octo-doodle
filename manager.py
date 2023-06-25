import time
import asyncio
import random
import datetime
import json
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, FSMBehaviour, State, OneShotBehaviour, TimeoutBehaviour, CyclicBehaviour
from spade.message import Message
from spade.template import Template


import os
from dotenv import load_dotenv

load_dotenv()

MANAGER_ADDRESS = os.getenv("MANAGER_ADDRESS")
MANAGER_ID = "/manager"

class ManagerAgent(Agent):
    class ServerRegistration(CyclicBehaviour):
        async def run(self):
            #print("Waiting for server registration...")
            msg = await self.receive()
            if msg:
                print("Received message:", msg.body)
                data = json.loads(msg.body)
                data["server_id"] = msg.sender
                data["available_from"] = datetime.datetime.fromisoformat(data["available_from"])


                print("Server added to ", data)
                
                #print(msg.sender)
                msg = Message(to=str(msg.sender))
                msg.set_metadata("performative", "inform")
                msg.body = "Server registered!"
                await self.send(msg)
                #TODO Add server to DB


    async def setup(self):
        print("ManagerAgent started")
        self.add_behaviour(self.ServerRegistration())

    async def on_stop(self):
        print("ManagerAgent stopped")




c = ManagerAgent(os.getenv("MANAGER_ADDRESS") + "/manager", os.getenv("MANAGER_PASSWORD"))
c.start()

