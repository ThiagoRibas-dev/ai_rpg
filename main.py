from app.gui.main_view import MainView
from app.core.orchestrator import Orchestrator
from app.database.db_manager import DBManager
from dotenv import load_dotenv

DB_PATH = "ai_rpg.db"

def main():
    load_dotenv()
    with DBManager(DB_PATH) as db_manager:
        db_manager.create_tables()
        view = MainView(db_manager)
        orchestrator = Orchestrator(view, db_manager)
        orchestrator.run()

if __name__ == "__main__":
    main()
