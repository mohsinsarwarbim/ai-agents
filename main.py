import os
from dotenv import load_dotenv

import wikipedia as wikipedia_client
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import GoogleSerperAPIWrapper, WikipediaAPIWrapper

load_dotenv()

# B) LLM model
llm = ChatAnthropic(
    model="claude-haiku-4-5",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    temperature=0,
)

# Wikimedia rejects the library's default User-Agent and returns HTML instead of JSON.
wikipedia_client.set_user_agent("ai-agents-demo/0.1 (dev@example.com)")

# C) Tools the model can select from
ddg_search = DuckDuckGoSearchRun()
wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
google_serper = GoogleSerperAPIWrapper(serper_api_key=os.environ["SERPER_API_KEY"])


@tool
def google_search(query: str) -> str:
    """Search Google for up-to-date information from the internet."""
    return google_serper.run(query)


TOOLS = [ddg_search, wikipedia, google_search]

SYSTEM_PROMPT = (
    "You are a research assistant. Select and call the search tools available to you "
    "to retrieve current information before answering. Cite the source of each fact "
    "and answer only from retrieved results."
)

agent = create_agent(llm, TOOLS, system_prompt=SYSTEM_PROMPT)


def run(query: str) -> str:
    """Run the A -> B -> C -> D -> E loop and return the final answer."""
    final_state = None
    # Each streamed step is one pass of the loop: model turn (B) or tool retrieval (D).
    for step in agent.stream({"messages": [{"role": "user", "content": query}]}):
        for node, update in step.items():
            for message in update.get("messages", []):
                if getattr(message, "tool_calls", None):
                    for call in message.tool_calls:
                        print(f"[{node}] selected {call['name']}({call['args']})")
                elif node == "tools":
                    print(f"[{node}] retrieved {len(message.content)} chars")
            final_state = update

    return final_state["messages"][-1].content


if __name__ == "__main__":
    # A) Query
    answer = run("Who is the current president of Italy?")
    # E) Answer
    print("\n" + answer)
