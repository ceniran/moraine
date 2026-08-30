import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from moraine.core import LocalIndex
from moraine.sources import JsonFileSource


class FakeEmbedder:
    identity = "fake:v1"

    def passages(self, texts, batch_size):
        return [self._vector(text) for text in texts]

    def query(self, text):
        return self._vector(text)

    @staticmethod
    def _vector(text):
        lowered = text.lower()
        return np.asarray([
            lowered.count("local") + lowered.count("本地"),
            lowered.count("light") + lowered.count("灯"),
        ], dtype=np.float32)


class LocalIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source_file = self.root / "memories.json"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, rows):
        self.source_file.write_text(json.dumps({"memories": rows}, ensure_ascii=False), encoding="utf-8")

    def index(self):
        return LocalIndex(JsonFileSource(self.source_file), FakeEmbedder(), self.root / "index.json", batch_size=1)

    def test_refresh_search_and_incremental_update(self):
        self.write([
            {"id": "a", "title": "local", "content": "本地 model", "state": "active"},
            {"id": "b", "title": "light", "content": "leave a 灯", "state": "active"},
        ])
        index = self.index()
        self.assertEqual(index.refresh()["changed"], 2)
        self.assertEqual(index.search("本地", 1)[0]["id"], "a")
        self.assertEqual(index.refresh()["changed"], 0)

        self.write([
            {"id": "a", "title": "local", "content": "灯", "state": "active"},
            {"id": "b", "title": "light", "content": "leave a 灯", "state": "archived"},
        ])
        result = index.refresh()
        self.assertEqual(result, {"accepted": True, "indexed": 1, "changed": 1})
        self.assertEqual(index.search("灯", 5)[0]["id"], "a")

    def test_reloads_compatible_index(self):
        self.write([{"id": "a", "title": "local", "content": "本地", "state": "active"}])
        first = self.index()
        first.refresh()
        second = self.index()
        self.assertEqual(second.health()["indexed"], 1)


if __name__ == "__main__":
    unittest.main()
