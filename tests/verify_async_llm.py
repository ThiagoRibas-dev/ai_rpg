import asyncio
import logging
import os
import time

from dotenv import load_dotenv
from pydantic import BaseModel

from app.llm.gemini_connector import GeminiConnector
from app.llm.llm_connector import LLMConnector
from app.llm.openai_connector import OpenAIConnector
from app.models.message import Message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AsyncVerify")

class TestSchema(BaseModel):
    message: str

async def test_parallel_execution(connector: LLMConnector):
    logger.info("--- Testing Parallel Execution & Semaphore ---")

    # Temporarily set a strict semaphore for testing
    test_limit = 2
    connector.semaphore = asyncio.Semaphore(test_limit)
    connector.timeout = 20 # 20 seconds for test

    prompts = [
        "Say 'Task A' and nothing else.",
        "Say 'Task B' and nothing else.",
        "Say 'Task C' and nothing else.",
    ]

    start_time = time.time()

    async def run_task(p, i):
        t0 = time.time()
        logger.info(f"Starting Task {i}...")
        # Note: We use the async_ method directly for testing
        res = await connector.async_get_structured_response(
            "You are a helpful assistant.",
            [Message(role="user", content=p)],
            TestSchema
        )
        t1 = time.time()
        logger.info(f"Finished Task {i} in {t1-t0:.2f}s: {res}")
        return res

    tasks = [run_task(p, i) for i, p in enumerate(prompts)]
    await asyncio.gather(*tasks)

    end_time = time.time()
    logger.info(f"All tasks completed in {end_time - start_time:.2f}s")

    # Verification logic:
    # If limit is 2, Task 3 should have started AFTER at least one of the first two finished.
    # We can inspect the logs manually to verify the overlap.

async def test_timeout(connector: LLMConnector):
    logger.info("--- Testing Timeout Enforcement ---")
    connector.timeout = 1 # Ridiculously short timeout

    try:
        await connector.async_get_structured_response(
            "You are a helpful assistant.",
            [Message(role="user", content="Write a lengthy story about a time-traveling toaster.")],
            TestSchema
        )
        logger.error("Error: Timeout should have triggered but didn't.")
    except TimeoutError:
        logger.info("Success: Timeout triggered correctly.")
    except Exception as e:
        logger.info(f"Caught expected exception or other error: {type(e).__name__}: {e}")

async def main():
    load_dotenv()
    # Ensure we are in the project root for imports to work
    provider = os.environ.get("LLM_PROVIDER", "GEMINI").upper()
    logger.info(f"Provider: {provider}")

    connector: LLMConnector
    if provider == "GEMINI":
        connector = GeminiConnector()
    else:
        connector = OpenAIConnector()

    try:
        await test_parallel_execution(connector)
        await test_timeout(connector)
    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
