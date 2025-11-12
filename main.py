from app.gui.main_view import MainView
from app.core.orchestrator import Orchestrator
from app.database.db_manager import DBManager
from dotenv import load_dotenv
import logging # Import logging

DB_PATH = "ai_rpg.db"


def main():
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    load_dotenv()
    with DBManager(DB_PATH) as db_manager:
        db_manager.create_tables()
        view = MainView(db_manager)
        orchestrator = Orchestrator(view, DB_PATH)  # Pass DB_PATH instead of db_manager
        view.set_orchestrator(orchestrator)
        orchestrator.tool_event_callback = view.log_tool_event
        orchestrator.run()


if __name__ == "__main__":
    main()
