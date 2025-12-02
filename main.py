from app.gui.main import run
from app.utils.logger_config import setup_logging
from dotenv import load_dotenv

DB_PATH = "ai_rpg.db"

# Allow __mp_main__ for NiceGUI reload/multiprocessing on Windows
if __name__ in {"__main__", "__mp_main__"}:
    setup_logging()
    load_dotenv()
    run(DB_PATH)
