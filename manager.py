from math import sqrt
import time
import asyncio
import random
import datetime
import json
import sqlite3
import os
from dotenv import load_dotenv
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, FSMBehaviour, State, OneShotBehaviour, TimeoutBehaviour, CyclicBehaviour
from spade.message import Message
from spade.template import Template

conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS servers (
                    server_id TEXT PRIMARY KEY,
                    resource_available INTEGER,
                    price_per_unit REAL,
                    available_from DATETIME,
                    blocked_untill DATETIME DEFAULT CURRENT_TIMESTAMP 
                )''')

conn.commit()
conn.close()


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
                if data.get("status") == "DONE":
                    print("Job done!")
                    pass
                    #Notify the client that the job is done
                    # TODO: Notify client

                    #Server finished assigned job
                else:    
                    # Register or deregister server

                    data["server_id"] = str(msg.sender)
                    #data["available_from"] = datetime.datetime.fromisoformat(data["available_from"])
                    msg = Message(to=str(msg.sender))
                    msg.set_metadata("performative", "inform")
                    msg.body = "Server registered!"
                    await self.send(msg)

                    conn = sqlite3.connect('database.db')
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT OR REPLACE INTO servers (server_id, resource_available, price_per_unit, available_from) VALUES (?, ?, ?, ?)",
                        (data['server_id'], data['resource_available'], data['price_per_unit'], data['available_from'])
                        )
                    conn.commit()
                    conn.close()

                    print("Server added. ", data)
                                        

    class OfferSender(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=1)
            if msg and msg.metadata["performative"] == "cfp":
                print("Received message:", msg.body)
                data = json.loads(msg.body)

                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM servers WHERE resource_available >= ? AND available_from <= ?  AND blocked_untill <= ? ORDER BY price_per_unit ASC LIMIT 1",
                    (data["resource_requirements"], data["available_in"], datetime.datetime.now().isoformat()))
                row = cursor.fetchone()
                print(row)
                if row:
                    time_str = (datetime.datetime.now() + datetime.timedelta(seconds=10)).isoformat()
                    cursor.execute("UPDATE servers SET blocked_untill = ? WHERE server_id = ?",
                        (time_str, row[0]))
                    conn.commit()
                    print("Found server:", row)
                    
                    msg = Message(to=str(msg.sender))
                    msg.set_metadata("performative", "propose")
                    offer = {
                        "available_in": (
                        max(datetime.datetime.fromisoformat(row[3]), datetime.datetime.now()) + datetime.timedelta(seconds=data["resource_requirements"] / sqrt(row[1]))).isoformat(),
                        "price": int(row[2] * data["resource_requirements"]),
                        "server_id": row[0],
                        "resource_requirements": data["resource_requirements"]
                        }
                    msg.body = json.dumps(offer)
                    print(msg.body)
                    await self.send(msg)


                    # while True:
                    #     reply = await self.receive(timeout=5)
                    #     if reply is None or reply.sender == msg.sender:
                    #         if reply is None:
                    #             print("Timeout")
                    #         else:
                    #             print("Received message from", reply.sender)
                    #         break
                    # cursor.execute("UPDATE servers SET blocked = ? WHERE server_id = ?",
                    #     (False, row[0]))
                    # conn.commit()

                    # if reply and reply.metadata["performative"] == "accept-proposal":
                    #     print("Client accepted proposal")
                    #     # notify the server to perform the job
                    #     await self.send(Message(to=row[0]),
                    #                      metadata={"performative": "inform"},
                    #                      body=json.dumps({
                    #                          data["resource_requirements"]
                    #                      })
                    #                      )
                    #     cursor.execute("UPDATE servers SET available_from = ? WHERE server_id = ?",
                    #         (offer["available_in"], row[0]))
                    #     conn.commit()

                    # else: 
                    #     print("Client rejected proposal or timeout")

                conn.close()

        #Notify the client that the job is done in this behaviour
    class ReceiveAcceptProposal(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=1)
            if msg:
                data = json.loads(msg.body)
                offer = data["offer"]
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE servers SET blocked_untill = ? WHERE server_id = ?",
                            (datetime.datetime.now().isoformat(), offer["server_id"]))
                conn.commit()


                print("Client accepted proposal")
                # notify the server to perform the job
                request = {
                    "resource_requirements": offer["resource_requirements"]
                    }
                print(request)
                m = Message(to=offer["server_id"])
                m.set_metadata("performative", "inform")
                m.body = json.dumps(request)
                await self.send(m)
                cursor.execute("UPDATE servers SET available_from = ? WHERE server_id = ?",
                    (offer["available_in"], offer["server_id"]))
                conn.commit()
                conn.close()


    class ReceiveRejectProposal(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=1)
            if msg:
                print("Client rejected proposal", msg.body)
                data = json.loads(msg.body)
                offer = data["offer"]
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE servers SET blocked_untill = ? WHERE server_id = ?",
                            (datetime.datetime.now().isoformat(), offer["server_id"]))
                conn.commit()
                conn.close()
                
            
    class Test(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=1)
            if msg:
                print("Received message:", msg.body)
    
    async def setup(self):
        print("ManagerAgent started")
        self.add_behaviour(self.ServerRegistration(), Template(metadata={"performative": "inform"}))
        cfp = Template(metadata={"performative": "cfp"})
        ap = Template(metadata={"performative": "accept-proposal"})
        rp = Template(metadata={"performative": "reject-proposal"})
        self.add_behaviour(self.OfferSender(), cfp)
        self.add_behaviour(self.ReceiveAcceptProposal(), ap)
        self.add_behaviour(self.ReceiveRejectProposal(), rp)
        #self.add_behaviour(self.Test(), Template(metadata={"performative": "accept-proposal"}))






c = ManagerAgent(os.getenv("MANAGER_ADDRESS") + "/manager", os.getenv("MANAGER_PASSWORD"))
c.start()

