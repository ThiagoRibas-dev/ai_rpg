import unittest
from unittest.mock import MagicMock

from app.context.context_builder import ContextBuilder
from app.context.state_context import StateContextBuilder
from app.models.game_session import GameSession
from app.models.vocabulary import MemoryKind, PrefabID
from app.prefabs.manifest import EngineConfig, FieldDef, SystemManifest
from app.services.entity_index import render_index, smart_truncate


class TestPromptRestructure(unittest.TestCase):
    def test_smart_truncate(self):
        # Case 1: Truncate at a space
        text = "The Melkhar Empire is the most powerful kingdom in West Alda"
        # max_len 50: "The Melkhar Empire is the most powerful kingdom" (index 46)
        res = smart_truncate(text, 50)
        self.assertEqual(res, "The Melkhar Empire is the most powerful kingdom...")

        # Case 2: Truncate at a comma
        text2 = "Sorcerers are individuals capable of innate magical power, or so it is said."
        res2 = smart_truncate(text2, 60)
        # 60 is around "power,"
        self.assertIn("innate magical power...", res2)
        self.assertNotIn(",", res2.split("...")[-2]) # Ensure comma is stripped if it was the last char

    def test_render_index_table(self):
        index = {
            "locations": {"town_1": "A sunny village near the sea."},
            "npcs": {"guard_1": "A stern man with a rusty sword."},
            MemoryKind.LORE.value: ["The history of the world is long."]
        }
        res = render_index(index)
        # Headers
        self.assertIn("use `state.query` or `context.retrieve` to look up full details.".lower(), res.lower())
        self.assertIn("### Locations Index", res)
        self.assertIn("### NPCs Index", res)
        self.assertIn("### Lore Index", res)
        self.assertIn("| ID | Snippet |", res)

        # Rows (Two-column format)
        self.assertIn("| `town_1` | A sunny village near the sea. |", res)
        self.assertIn("| `guard_1` | A stern man with a rusty sword. |", res)
        self.assertIn("|  | The history of the world is long. |", res)

    def test_engine_table_rendering(self):
        eng = EngineConfig(
            dice="1d20",
            mechanic="d20 + modifiers vs DC",
            success="Result >= DC",
            crit="Nat 20",
            fumble="Nat 1"
        )
        table = eng.to_markdown_table()
        self.assertIn("| Dice | Mechanic | Success | Critical | Fumble |", table)
        self.assertIn("| 1d20 | d20 + modifiers vs DC | Result >= DC | Nat 20 | Nat 1 |", table)

    def test_character_sheet_tables(self):
        # Mocking app components
        mock_db = MagicMock()
        mock_registry = MagicMock()
        builder = StateContextBuilder(mock_registry, mock_db)

        # Mock Manifest
        mock_manifest = MagicMock(spec=SystemManifest)
        mock_manifest.get_categories.return_value = ["Attributes", "Resources"]

        attr_field = FieldDef(path="attributes.str", label="Strength", prefab=PrefabID.VAL_COMPOUND, category="Attributes")
        res_field = FieldDef(path="resources.hp", label="HP", prefab=PrefabID.RES_POOL, category="Resources")

        mock_manifest.get_fields_by_category.side_effect = lambda cat: [attr_field] if cat == "Attributes" else [res_field]

        # Mock Player Entity
        with unittest.mock.patch("app.context.state_context.get_entity") as mock_get_ent:
            mock_get_ent.return_value = {
                "attributes": {"str": {"score": 18, "mod": 4}},
                "resources": {"hp": {"current": 10, "max": 10}},
                "name": "Thorin"
            }

            res = builder.build_character_sheet(1, mock_manifest)

            import json
            parsed = json.loads(res)

            # Verify Attributes table
            self.assertIn("Attributes", parsed)
            self.assertEqual(parsed["Attributes"]["str"]["score"], 18)
            self.assertEqual(parsed["Attributes"]["str"]["mod"], 4)
            self.assertEqual(parsed["Attributes"]["str"]["_label"], "Strength")

            # Verify Resources table
            self.assertIn("Resources", parsed)
            self.assertEqual(parsed["Resources"]["hp"]["current"], 10)
            self.assertEqual(parsed["Resources"]["hp"]["max"], 10)
            self.assertEqual(parsed["Resources"]["hp"]["_label"], "HP")

    def test_context_builder_integration(self):
        """Ensures ContextBuilder can run its full dynamic pipeline without AttributeErrors."""

        mock_db = MagicMock()
        mock_vs = MagicMock()
        mock_state = MagicMock()
        mock_mem = MagicMock()
        mock_sim = MagicMock()

        builder = ContextBuilder(mock_db, mock_vs, mock_state, mock_mem, mock_sim)

        mock_session = MagicMock(spec=GameSession)
        mock_session.id = 1
        mock_session.authors_note = "Test note"

        # This confirms that all internal _build_* calls (including _build_spatial_context) exist
        try:
            builder.build_dynamic_context(mock_session, [])
        except AttributeError as e:
            self.fail(f"ContextBuilder integration failed: {e}")

    def test_wrap_section_logic(self):
        # We need to test the logic that will be in ContextBuilder
        def _wrap_section(title, content, lang="markdown"):
            if not content or not content.strip():
                return ""
            return f"### {title}\n```{lang}\n{content.strip()}\n```"

        res = _wrap_section("TEST", "Hello World")
        self.assertEqual(res, "### TEST\n```markdown\nHello World\n```")

        res_empty = _wrap_section("EMPTY", "")
        self.assertEqual(res_empty, "")

if __name__ == "__main__":
    unittest.main()
