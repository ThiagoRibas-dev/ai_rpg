
import os
import sys
import unittest

# Ensure we can import from 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.setup.schemas import LoreData, NpcData


class TestRefactor(unittest.TestCase):
    def test_lore_normalization(self):
        print("Testing LoreData normalization...")

        # Test case 1: Partial data (missing name, has tags)
        data1 = {"content": "The sky is green.", "tags": ["nature"]}
        lore1 = LoreData.model_validate(data1)
        self.assertEqual(lore1.name, "Nature")

        # Test case 2: Content-based name (no tags)
        data2 = {"content": "Ancient ruins of an old city and more text here.", "tags": []}
        lore2 = LoreData.model_validate(data2)
        self.assertTrue(lore2.name.startswith("Ancient ruins"))

        # Test case 3: Full data
        data3 = {"name": "The Great War", "content": "A war that lasted 100 years.", "tags": ["history"]}
        lore3 = LoreData.model_validate(data3)
        self.assertEqual(lore3.name, "The Great War")
        print("Lore normalization PASSED.")

    def test_tag_injection_logic(self):
        print("Testing tag injection simulation...")

        # Simulation of WorldGenService logic for NPC
        category_type = "NPC"
        npc = NpcData(name="Guard", visual_description="A guard.", tags=["warrior"])

        # Injected logic
        tag_to_add = category_type.lower()
        if tag_to_add in npc.tags:
            npc.tags.remove(tag_to_add)
        npc.tags.insert(0, tag_to_add)

        self.assertEqual(npc.tags[0], "npc")
        self.assertIn("warrior", npc.tags)

        # Simulation for Lore
        category_type = "SYSTEMS"
        lore = LoreData(name="Magic", content="Magic is real.", tags=["mystical"])

        tag_to_add = category_type.lower()
        if tag_to_add in lore.tags:
            lore.tags.remove(tag_to_add)
        lore.tags.insert(0, tag_to_add)

        self.assertEqual(lore.tags[0], "systems")
        self.assertIn("mystical", lore.tags)
        print("Tag injection simulation PASSED.")

if __name__ == "__main__":
    unittest.main()
