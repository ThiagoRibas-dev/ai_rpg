from app.gui.main_view import MainView
from app.core.orchestrator import Orchestrator
from dotenv import load_dotenv

def main():
    load_dotenv()
    view = MainView()
    orchestrator = Orchestrator(view)
    orchestrator.run()

if __name__ == "__main__":
    main()
