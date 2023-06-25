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

class ClientAgent(Agent):
    resource_requirements = 20
    available_in_seconds = 10
    job_in_progress = False
    offers = {}
    class OfferRequester(OneShotBehaviour):
        async def run(self):
            print(f"Requesting offers from ManagerAgent matching the resource requirements of {self.agent.resource_requirements}")

            msg = Message(to=MANAGER_ADDRESS + MANAGER_ID)
            msg.set_metadata("performative", "cfp") # Call for proposal
            msg.body = json.dumps({"resource_requirements": self.agent.resource_requirements,
                "available_in": (datetime.datetime.now() + datetime.timedelta(seconds=self.agent.available_in_seconds)).isoformat()
                })

            await self.send(msg)
            print("Request sent!")
            self.kill(exit_code=0)
        
        async def on_end(self):
            print("End of OfferRequester")

    
    #inform
    class JobCompletion(OneShotBehaviour):
        async def run(self):
            print("Waiting for job to complete...")
            time = (datetime.datetime.fromisoformat(self.agent.offers["available_in"]) - datetime.datetime.now()).total_seconds()
            print(time)
            msg = await self.receive(timeout=time + 2) # 10 seconds timeout backup for any delays
            if msg:
                print("Job completed!")
                print("Received message:", msg.body)
                self.agent.job_in_progress = False
            else:
                print("Job timed out!")
                
                self.agent.job_in_progress = False
                self.agent.add_behaviour(self.agent.OfferReceiver(), Template(metadata={"performative": "propose"}))
                self.agent.add_behaviour(self.agent.OfferRequester())
                

    #propose
    class OfferReceiver(CyclicBehaviour):
        async def on_start(self):
            print("Behavior started.")

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                #print("Received offer:", msg.body)
                await self.on_message(msg)
            else:
                self.agent.add_behaviour(self.agent.OfferRequester())

        async def on_message(self, msg: Message):
            print("Received offer:", msg.body)
            self.agent.offers = json.loads(msg.body)
            # Accept or reject offer logic
            print(self.agent.job_in_progress)
            if self.agent.resource_requirements >= self.agent.offers["price"] and self.agent.job_in_progress == False:
                print("Offer accepted!")
                msg = Message(to=MANAGER_ADDRESS + MANAGER_ID)
                msg.set_metadata("performative", "accept-proposal")
                msg.body = json.dumps({"offer": self.agent.offers})
                print("Sending message:", msg.body, "to", msg.to)
                await self.send(msg)
                self.agent.job_in_progress = True
                self.kill(exit_code=0)

            elif self.agent.job_in_progress == True:
                print("Offer rejected!")
                msg = Message(to=MANAGER_ADDRESS + MANAGER_ID)
                msg.set_metadata("performative", "reject-proposal")
                msg.body = json.dumps({"offer": self.agent.offers})
                await self.send(msg)
                self.agent.job_in_progress = False

            # END of acceptance logic

        async def on_end(self):
            print("Finished with exit code {}.".format(self.exit_code))
            if self.agent.job_in_progress == True:
                print("Server is starting job...")
                self.agent.add_behaviour(self.agent.JobCompletion(), Template(metadata={"performative": "inform"}))
                
            else:
                print("No job to start!")
                self.kill(exit_code=0)

    async def setup(self):
        #print(self.is_alive())
        print("ClientAgent started")
        self.add_behaviour(self.OfferRequester())
        self.add_behaviour(self.OfferReceiver(), Template(metadata={"performative": "propose"}))

    async def on_stop(self):
        print("ClientAgent stopped")


c = ClientAgent(os.getenv("MANAGER_ADDRESS") + "/c1", os.getenv("MANAGER_PASSWORD"))
c.start()