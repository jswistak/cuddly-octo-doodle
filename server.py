from math import sqrt
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

JOIN_NETWORK_TIMEOUT = 20

class ServerAgent(Agent):
    #Server will be able to perform the task requiring resource_available units or less
    resource_available = 45
    price_per_unit = 1

    job_in_progress = datetime.datetime.now()
    jobs = []
    class ConfirmJoinNetwork(OneShotBehaviour):
        async def run(self):
            print("Waiting for confirmation from manager...")
            msg = await self.receive(timeout=JOIN_NETWORK_TIMEOUT)
            if msg:
                print("Received message:", msg.body)
                self.agent.add_behaviour(self.agent.Job())
            else:
                print("Confirmation timed out! Trying again...")
                self.agent.add_behaviour(self.agent.JoinNetwork())


    class JoinNetwork(OneShotBehaviour):
        async def run(self):
            print(
                f"""Joining network with resource_available of 
                {self.agent.resource_available} and price_per_unit {self.agent.price_per_unit}."""
            )
            msg = Message(to=MANAGER_ADDRESS + MANAGER_ID)
            msg.set_metadata("performative", "inform")
            data = {
                "resource_available": self.agent.resource_available,
                "price_per_unit": self.agent.price_per_unit,
                "available_from": self.agent.job_in_progress.isoformat(),
                }
            #print(type(data))
            x = json.dumps(data)
            #print(x)
            msg.body = json.dumps(data)
            

            await self.send(msg)
        
        async def on_end(self):
            self.agent.add_behaviour(self.agent.ConfirmJoinNetwork())
            
            
    class JobCompletion(TimeoutBehaviour):
        async def run(self):
            print("Job completed!")
            job = self.agent.jobs.pop(0)
            msg = Message(to=MANAGER_ADDRESS + MANAGER_ID)
            msg.set_metadata("performative", "inform")
            job["status"] = "DONE"
            msg.body = json.dumps(job)
            await self.send(msg)

    class Job(CyclicBehaviour):
        async def run(self):
            print("Waiting for job...")
            msg = await self.receive(timeout=10)
            if msg:
                print("Received job offer:", msg.body)

                #Calculate completion time
                offer = json.loads(msg.body)
                completion_time = offer.get("resource_requirements") / sqrt(self.agent.resource_available)
                self.agent.job_in_progress = max(datetime.datetime.now(), self.agent.job_in_progress) + datetime.timedelta(seconds=completion_time)
                
                self.agent.jobs.append(offer) 
                
                self.agent.add_behaviour(self.agent.JobCompletion(start_at=self.agent.job_in_progress))
                #Add timeout behaviour to wait for job completion


    async def setup(self):
        print("Server started")
        self.add_behaviour(self.JoinNetwork())

                

    async def on_stop(self):
        #TODO: Send message to manager to remove me from the list
        msg = Message(to=MANAGER_ADDRESS + MANAGER_ID)
        msg.set_metadata("performative", "inform")
        msg.body = json.dumps({
            "resource_available": 0,
                                })
        await self.send(msg)
        print("Server stopped")



c = ServerAgent(os.getenv("MANAGER_ADDRESS") + "/s1", os.getenv("MANAGER_PASSWORD"))
c.start()