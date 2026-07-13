import unittest

from order_events import order_events


class OrderEventsTests(unittest.TestCase):
    def test_equal_timestamp_uses_sequence(self):
        events = [
            {"id": "later", "timestamp": "2026-07-10T10:00:00Z", "sequence": 2},
            {"id": "earlier", "timestamp": "2026-07-10T10:00:00Z", "sequence": 1},
        ]

        self.assertEqual([event["id"] for event in order_events(events)], ["earlier", "later"])


if __name__ == "__main__":
    unittest.main()
