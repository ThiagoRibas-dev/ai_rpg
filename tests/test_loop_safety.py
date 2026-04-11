import logging
import os
import threading

from dotenv import load_dotenv
from pydantic import BaseModel

from app.llm.gemini_connector import GeminiConnector
from app.llm.openai_connector import OpenAIConnector
from app.models.message import Message

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LoopSafetyTest")

class LoopTestSchema(BaseModel):
    message: str

def reproduce_issue(connector_class):
    logger.info(f"--- Testing Loop Safety for {connector_class.__name__} ---")
    load_dotenv()

    # Instantiate once
    try:
        connector = connector_class()
    except Exception as e:
        logger.error(f"Failed to initialize connector: {e}")
        return

    def call_sync_wrapper(i):
        logger.info(f"Call {i} starting...")
        try:
            # This uses asyncio.run() internally in LLMConnector
            # For OpenAI, the first call should work, subsequent should fail if not fixed.
            res = connector.get_structured_response(
                "You are a helpful assistant.",
                [Message(role="user", content="Say 'Hello'")],
                LoopTestSchema
            )
            logger.info(f"Call {i} succeeded: {res}")
        except Exception as e:
            logger.error(f"Call {i} failed with {type(e).__name__}: {e}")

    # Call 1
    call_sync_wrapper(1)

    # Call 2 (in the same thread, but new loop via asyncio.run)
    call_sync_wrapper(2)

    # Call 3 (in a different thread, new loop via asyncio.run)
    t = threading.Thread(target=call_sync_wrapper, args=(3,))
    t.start()
    t.join()

if __name__ == "__main__":
    # Test OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        reproduce_issue(OpenAIConnector)
    else:
        logger.warning("Skipping OpenAI test: OPENAI_API_KEY not set.")

    # Test Gemini
    if os.environ.get("GEMINI_API_KEY"):
        reproduce_issue(GeminiConnector)
    else:
        logger.warning("Skipping Gemini test: GEMINI_API_KEY not set.")
