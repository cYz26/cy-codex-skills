def order_events(events):
    return sorted(events, key=lambda event: event["timestamp"])
