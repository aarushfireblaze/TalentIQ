from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestCombinedOnlySurface(unittest.TestCase):
    def test_service_exposes_no_runtime_mode_switch(self):
        service_source = (ROOT / "src/voice_filtering/service.py").read_text()
        self.assertNotIn('Route("/api/mode"', service_source)

    def test_ui_exposes_no_filter_mode_selector(self):
        html = (ROOT / "apps/ui/index.html").read_text()
        javascript = (ROOT / "apps/ui/app.js").read_text()
        self.assertNotIn('name="mode"', html)
        self.assertNotIn('"/api/mode"', javascript)


if __name__ == "__main__":
    unittest.main()
