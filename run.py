import asyncio
from manager import ManagerAgent
from client import ClientAgent
from server import ServerAgent
import os
from dotenv import load_dotenv

load_dotenv()


async def setup():
    c1 = ClientAgent(os.getenv("MANAGER_ADDRESS") + "/c1",
                     os.getenv("MANAGER_PASSWORD"))
    c1.resource_requirements = 10
    c2 = ClientAgent(os.getenv("MANAGER_ADDRESS") + "/c2",
                     os.getenv("MANAGER_PASSWORD"))
    c2.resource_requirements = 30
    c3 = ClientAgent(os.getenv("MANAGER_ADDRESS") + "/c3",
                     os.getenv("MANAGER_PASSWORD"))
    c3.resource_requirements = 20
    c4 = ClientAgent(os.getenv("MANAGER_ADDRESS") + "/c4",
                     os.getenv("MANAGER_PASSWORD"))
    c4.resource_requirements = 15

    s1 = ServerAgent(os.getenv("MANAGER_ADDRESS") + "/s1",
                     os.getenv("MANAGER_PASSWORD"))
    s2 = ServerAgent(os.getenv("MANAGER_ADDRESS") + "/s2",
                     os.getenv("MANAGER_PASSWORD"))
    s2.resource_available = 35

    m = ManagerAgent(os.getenv("MANAGER_ADDRESS") + "/manager",
                     os.getenv("MANAGER_PASSWORD"))

    m.start()
    c1.start()
    c2.start()
    c3.start()
    c4.start()
    s1.start()
    s2.start()

if __name__ == "__main__":
    asyncio.run(setup())
    while True:
        pass
