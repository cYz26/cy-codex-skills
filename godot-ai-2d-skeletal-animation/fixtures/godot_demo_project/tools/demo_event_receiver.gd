extends Node2D

var received_events: Array[String] = []

func animation_event(event_name: String, target: String = "") -> void:
	received_events.append("%s:%s" % [event_name, target])
