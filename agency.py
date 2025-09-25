from dotenv import load_dotenv
from agency_swarm import Agency

from agency_code_agent import agency_code_agent
from planner_agent import planner_agent
from agency_swarm.tools.send_message import SendMessageHandoff


import asyncio

load_dotenv()

# do not remove this method, it is used in the main.py file to deploy the agency (it has to be a method)
def create_agency(load_threads_callback=None):
    agency = Agency(
        agency_code_agent,  # Entry point - users communicate directly with code agent
        communication_flows=[
            (agency_code_agent, planner_agent, SendMessageHandoff),
            (planner_agent, agency_code_agent, SendMessageHandoff),
        ],  # Single agent architecture
        name="AgencyCodeAgency",
        shared_instructions="shared_instructions.md",
        load_threads_callback=load_threads_callback,
    )

    return agency

if __name__ == "__main__":
    agency = create_agency()

    # test 1 message
    # async def main():
    #     response = await agency.get_response("Hello, how are you?")
    #     print(response)
    # asyncio.run(main())

    # run in terminal
    agency.terminal_demo()