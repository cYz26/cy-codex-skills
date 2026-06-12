extends SceneTree

# Replace with your project entry scene
const ENTRY_SCENE := "res://Main.tscn"

# Replace with must-exist node paths after startup
const MUST_HAVE_NODE_PATHS := [
	"/root/Main",
]

func _init() -> void:
	var packed := load(ENTRY_SCENE)
	if packed == null:
		push_error("Smoke: failed to load entry scene: %s" % ENTRY_SCENE)
		quit(1)
		return

	var root := packed.instantiate()
	get_root().add_child(root)

	# Allow startup lifecycle to complete
	for _i in range(10):
		await process_frame

	for p in MUST_HAVE_NODE_PATHS:
		if get_root().get_node_or_null(p) == null:
			push_error("Smoke: missing node path: %s" % p)
			quit(2)
			return

	print("Smoke: OK")
	quit(0)
