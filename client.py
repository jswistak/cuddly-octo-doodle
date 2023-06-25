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

    def getClientName(self):
        jid_str = str(self.jid)
        return f'ClientAgent { jid_str[jid_str.find("/")+1:] }'

    class OfferRequester(OneShotBehaviour):
        async def run(self):
            print(
                f"[{self.agent.getClientName()}] Requesting offers from ManagerAgent matching the resource requirements of {self.agent.resource_requirements}")

            msg = Message(to=MANAGER_ADDRESS + MANAGER_ID)
            msg.set_metadata("performative", "cfp")  # Call for proposal
            msg.body = json.dumps({"resource_requirements": self.agent.resource_requirements,
                                   "available_in": (datetime.datetime.now() + datetime.timedelta(seconds=self.agent.available_in_seconds)).isoformat()
                                   })

            await self.send(msg)
            print(f"[{self.agent.getClientName()}] Request sent!")
            self.kill(exit_code=0)

        async def on_end(self):
            # print("[ClientAgent] End of OfferRequester")
            pass

    # inform
    class JobCompletion(OneShotBehaviour):
        async def run(self):
            print(f"[{self.agent.getClientName()}] Waiting for job to complete...")
            time = (datetime.datetime.fromisoformat(
                self.agent.offers["available_in"]) - datetime.datetime.now()).total_seconds()
            # print(time)
            # 10 seconds timeout backup for any delays
            msg = await self.receive(timeout=time + 2)
            if msg:
                print(f"[{self.agent.getClientName()}] Job completed!")
                print(f"[{self.agent.getClientName()}] Received message:", msg.body)
                self.agent.job_in_progress = False
            else:
                print(f"[{self.agent.getClientName()}] Job timed out!")

                self.agent.job_in_progress = False
                self.agent.add_behaviour(self.agent.OfferReceiver(
                ), Template(metadata={"performative": "propose"}))
                self.agent.add_behaviour(self.agent.OfferRequester())

    # propose

    class OfferReceiver(CyclicBehaviour):
        async def on_start(self):
            # print("[ClientAgent] Behavior started.")
            pass

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                await self.on_message(msg)
            else:
                self.agent.add_behaviour(self.agent.OfferRequester())

        async def on_message(self, msg: Message):
            print(f"[{self.agent.getClientName()}] Received offer:", msg.body)
            self.agent.offers = json.loads(msg.body)
            # Accept or reject offer logic
            # print("[ClientAgent] ", self.agent.job_in_progress)
            if self.agent.resource_requirements >= self.agent.offers["price"] and self.agent.job_in_progress == False:
                print(f"[{self.agent.getClientName()}] Offer accepted!")
                msg = Message(to=MANAGER_ADDRESS + MANAGER_ID)
                msg.set_metadata("performative", "accept-proposal")
                msg.body = json.dumps({"offer": self.agent.offers})
                print(f"[{self.agent.getClientName()}] Sending message:",
                      msg.body, "to", msg.to)
                await self.send(msg)
                self.agent.job_in_progress = True
                self.kill(exit_code=0)

            elif self.agent.job_in_progress == True:
                print(f"[{self.agent.getClientName()}] Offer rejected!")
                msg = Message(to=MANAGER_ADDRESS + MANAGER_ID)
                msg.set_metadata("performative", "reject-proposal")
                msg.body = json.dumps({"offer": self.agent.offers})
                await self.send(msg)
                self.agent.job_in_progress = False

            # END of acceptance logic

        async def on_end(self):
            # print("[ClientAgent] Finished with exit code {}.".format(self.exit_code))
            if self.agent.job_in_progress == True:
                print(f"[{self.agent.getClientName()}] Server is starting job...")
                self.agent.add_behaviour(self.agent.JobCompletion(
                ), Template(metadata={"performative": "inform"}))

            else:
                print(f"[{self.agent.getClientName()}] No job to start!")
                self.kill(exit_code=0)

    async def setup(self):
        print(f"[{self.getClientName()}] started")
        self.add_behaviour(self.OfferRequester())
        self.add_behaviour(self.OfferReceiver(), Template(
            metadata={"performative": "propose"}))

    async def on_stop(self):
        print(f"[{self.getClientName()}] stopped")
