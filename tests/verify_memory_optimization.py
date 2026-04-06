
import json
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.context.memory_retriever import MemoryRetriever
from app.database.db_manager import DBManager
from app.models.message import Message
from app.models.vocabulary import MemoryKind
from app.tools.handlers.context_retrieve import handler as context_retrieve_handler


class MockSession:
    def __init__(self, id):
        self.id = id
    def get_history(self):
        return []

def verify_memory_optimization():
    print("Starting Memory Optimization Verification...")

    # 1. Setup In-Memory DB
    with DBManager(":memory:") as db:
        db.create_tables()

        # 2. Create a Prompt and Session
        db.conn.execute("INSERT INTO prompts (id, name, content) VALUES (?, ?, ?)", (1, "Test System", "Test Content"))
        session_id = 1
        db.conn.execute("INSERT INTO sessions (id, name, session_data, prompt_id) VALUES (?, ?, ?, ?)",
                        (session_id, "Test Session", json.dumps({"history": []}), 1))

        # 3. Create some Memories
        # Memory 1 (Rule)
        m1 = db.memories.create(session_id, kind=MemoryKind.RULE.value, content="Rule #1: Be cool.", priority=5)
        # Memory 2 (Lore)
        m2 = db.memories.create(session_id, kind=MemoryKind.LORE.value, content="The sky is green.", priority=4)
        # Memory 3 (Episodic)
        m3 = db.memories.create(session_id, kind=MemoryKind.EPISODIC.value, content="Met a scary goblin.", priority=3)

        print(f"Created memories with IDs: {m1.id}, {m2.id}, {m3.id}")

        # 4. Test MemoryRetriever.get_relevant with exclusion
        mr = MemoryRetriever(db, None)
        sess = MockSession(session_id)
        # Use keywords that match our memories
        recent = [Message(role="user", content="tell me about rules, green sky and goblin")]

        # Without exclusion
        all_mems = mr.get_relevant(sess, recent_messages=recent)
        all_ids = [m.id for kind_list in all_mems.values() for m in kind_list]
        print(f"All IDs found: {all_ids}")
        assert m1.id in all_ids
        assert m2.id in all_ids
        assert m3.id in all_ids

        # With exclusion of m1
        excl_mems = mr.get_relevant(sess, recent_messages=recent, exclude_ids=[m1.id])
        excl_ids = [m.id for kind_list in excl_mems.values() for m in kind_list]
        print(f"Excluded IDs found: {excl_ids}")
        assert m1.id not in excl_ids
        assert m2.id in excl_ids
        assert m3.id in excl_ids
        print("MemoryRetriever exclusion logic: SUCCESS")

        # 5. Test ContextRetrieve handler with pre_fetched_mems
        # Simulate pre-fetched mems containing m1
        pre_fetched = {
            MemoryKind.RULE: [m1]
        }

        ctx = {
            "session_id": session_id,
            "db_manager": db,
            "vector_store": None,
            "pre_fetched_mems": pre_fetched
        }

        result = context_retrieve_handler(query="tell me about rules, the sky and the scary goblin", limit=5, **ctx)

        retrieved_ids = result["memory_ids"]
        print(f"Handler retrieved IDs: {retrieved_ids}")

        # Should contain m1 (from pre-fetched) AND m2, m3 (from new retrieval)
        assert m1.id in retrieved_ids, "Pre-fetched M1 missing from result"
        assert m2.id in retrieved_ids, "Newly retrieved M2 missing from result"
        assert m3.id in retrieved_ids, "Newly retrieved M3 missing from result"

        # Verify text consolidated
        text = result["text"]
        assert "Rule #1: Be cool." in text
        assert "The sky is green." in text
        assert "Met a scary goblin." in text
        print("ContextRetrieve handler consolidation: SUCCESS")

    print("\nVerification Complete: ALL TESTS PASSED!")

if __name__ == "__main__":
    verify_memory_optimization()
