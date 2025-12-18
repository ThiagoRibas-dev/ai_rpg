import logging
from pathlib import Path

from app.database.db_manager import DBManager
from app.prefabs.manifest import SystemManifest

logger = logging.getLogger(__name__)


def seed_builtin_manifests(db_path: str):
    """
    Scans app/data/manifests for JSON files and seeds them into the database.
    Updates existing manifests if the file content has changed.
    """
    manifests_dir = Path("app/data/manifests")
    if not manifests_dir.exists():
        logger.warning(f"Manifests directory not found: {manifests_dir}")
        return

    logger.info("Seeding built-in manifests...")

    with DBManager(db_path) as db:
        count = 0
        for file_path in manifests_dir.glob("*.json"):
            if file_path.name == "index.json":
                continue

            try:
                manifest = SystemManifest.from_file(file_path)

                # 1. Upsert Manifest
                db.manifests.upsert_builtin(manifest)

                # 2. Upsert Corresponding Prompt (The UI Bridge)
                # We check if a prompt with this name exists; if not, create it.
                # This ensures the System appears in the "New Game" tab.
                existing_prompt = None
                for p in db.prompts.get_all():
                    if p.name == manifest.name:
                        existing_prompt = p
                        break

                if not existing_prompt:
                    logger.info(f"Creating UI Prompt for: {manifest.name}")
                    db.prompts.create(
                        name=manifest.name,
                        content=f"You are the Game Master for a {manifest.name} campaign.",
                        rules_document=f"Refer to the {manifest.name} System Manifest.",
                        template_manifest=manifest.to_json(),
                    )

                count += 1
            except Exception as e:
                logger.error(f"Failed to seed manifest {file_path.name}: {e}")

        logger.info(f"Seeding complete. {count} manifests processed.")
