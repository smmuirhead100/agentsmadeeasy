from ame import AgentWithTools
from ame.llms.gemini.llm import LLM as GeminiLLM
from ame.core.chat_context import ChatMessage
import asyncio


async def main():
    llm = GeminiLLM()
    agent = AgentWithTools(llm=llm, instructions="You are a helpful assistant that can answer questions and help with tasks.")

    async for chunk in agent.astream(chat_message=ChatMessage(role="user", content="What is the capital of France?")):
        print(chunk)

if __name__ == "__main__":
    asyncio.run(main())