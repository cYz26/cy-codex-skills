extends SceneTree

const CASES_DIR := "res://fixtures/cases"
const EVENT_SCRIPT := preload("res://tools/demo_event_receiver.gd")

func _init() -> void:
	var failures: Array[String] = []
	var cases := _list_case_dirs(CASES_DIR)
	if cases.is_empty():
		failures.append("No cases found under %s" % CASES_DIR)
	for case_dir in cases:
		var err := _build_case(case_dir)
		if err != "":
			failures.append(err)
	if failures.is_empty():
		print("Generated %d Godot skeletal animation fixture scenes." % cases.size())
		quit(0)
	else:
		for failure in failures:
			push_error(failure)
		quit(1)

func _list_case_dirs(base: String) -> Array[String]:
	var result: Array[String] = []
	var dir := DirAccess.open(base)
	if dir == null:
		return result
	dir.list_dir_begin()
	while true:
		var entry := dir.get_next()
		if entry == "":
			break
		if entry.begins_with("."):
			continue
		if dir.current_is_dir() and FileAccess.file_exists("%s/%s/rig_meta.json" % [base, entry]):
			result.append("%s/%s" % [base, entry])
	dir.list_dir_end()
	result.sort()
	return result

func _read_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		push_error("Missing JSON file: %s" % path)
		return null
	var file := FileAccess.open(path, FileAccess.READ)
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if parsed == null:
		push_error("Invalid JSON file: %s" % path)
	return parsed

func _build_case(case_dir: String) -> String:
	var rig: Variant = _read_json("%s/rig_meta.json" % case_dir)
	if rig == null:
		return "Unable to read rig_meta.json for %s" % case_dir

	var root := Node2D.new()
	root.name = rig.get("case_id", "generated_case")
	root.set_script(EVENT_SCRIPT)

	var skeleton := Skeleton2D.new()
	skeleton.name = "Skeleton2D"
	root.add_child(skeleton)
	skeleton.owner = root

	var bones: Dictionary = {}
	var pending: Array = rig["skeleton"]["bones"].duplicate()
	var safety := 0
	while not pending.is_empty() and safety < 512:
		safety += 1
		var next_pending: Array = []
		for bone_meta in pending:
			var parent_name = bone_meta.get("parent", null)
			if parent_name != null and not bones.has(parent_name):
				next_pending.append(bone_meta)
				continue
			var bone := Bone2D.new()
			bone.name = bone_meta["name"]
			bone.position = _vec2(bone_meta["position"])
			bone.rotation_degrees = float(bone_meta.get("rotation_degrees", 0.0))
			if parent_name == null:
				skeleton.add_child(bone)
			else:
				bones[parent_name].add_child(bone)
			bone.owner = root
			bones[bone.name] = bone
		if next_pending.size() == pending.size():
			return "Unresolved bone parents in %s" % case_dir
		pending = next_pending

	for part_meta in rig["parts"]:
		if not bones.has(part_meta["bone"]):
			return "Part %s references missing bone %s" % [part_meta["id"], part_meta["bone"]]
		var sprite := Sprite2D.new()
		sprite.name = part_meta["id"]
		sprite.texture = load("%s/%s" % [case_dir, part_meta["file"]])
		if sprite.texture == null:
			return "Unable to load texture %s/%s" % [case_dir, part_meta["file"]]
		sprite.centered = false
		sprite.position = _vec2(part_meta["offset"]) - _vec2(part_meta["pivot"])
		sprite.z_index = int(part_meta["z_index"])
		bones[part_meta["bone"]].add_child(sprite)
		sprite.owner = root

	for socket_meta in rig.get("sockets", []):
		if not bones.has(socket_meta["bone"]):
			return "Socket %s references missing bone %s" % [socket_meta["name"], socket_meta["bone"]]
		var socket := Marker2D.new()
		socket.name = socket_meta["name"]
		socket.position = _vec2(socket_meta["local_position"])
		socket.rotation_degrees = float(socket_meta.get("local_rotation_degrees", 0.0))
		bones[socket_meta["bone"]].add_child(socket)
		socket.owner = root

	var hitboxes := Node2D.new()
	hitboxes.name = "Hitboxes"
	root.add_child(hitboxes)
	hitboxes.owner = root
	for hitbox_meta in rig.get("hitboxes", []):
		var marker := Marker2D.new()
		marker.name = hitbox_meta["name"]
		marker.position = _vec2(hitbox_meta.get("offset", [0, 0]))
		hitboxes.add_child(marker)
		marker.owner = root

	var player := AnimationPlayer.new()
	player.name = "AnimationPlayer"
	root.add_child(player)
	player.owner = root
	player.root_node = NodePath("..")
	var library := AnimationLibrary.new()

	var motions := _list_json_files("%s/motions" % case_dir)
	for motion_path in motions:
		var motion: Variant = _read_json(motion_path)
		if motion == null:
			return "Unable to read motion %s" % motion_path
		var animation := _build_animation(root, bones, motion)
		library.add_animation(motion["animation"], animation)
	player.add_animation_library("", library)

	var generated_dir := "%s/generated" % case_dir
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(generated_dir))
	var scene_path := "%s/%s.tscn" % [generated_dir, rig["case_id"]]
	var packed := PackedScene.new()
	var pack_result := packed.pack(root)
	if pack_result != OK:
		return "Unable to pack scene %s" % scene_path
	var save_result := ResourceSaver.save(packed, scene_path)
	if save_result != OK:
		return "Unable to save scene %s" % scene_path
	_write_preview("%s/preview.png" % generated_dir)
	root.free()
	print("Generated %s" % scene_path)
	return ""

func _build_animation(root: Node2D, bones: Dictionary, motion: Dictionary) -> Animation:
	var animation := Animation.new()
	animation.length = float(motion["length"])
	animation.loop_mode = Animation.LOOP_LINEAR if bool(motion["loop"]) else Animation.LOOP_NONE
	for track_meta in motion["tracks"]:
		if track_meta["target"] != "bone":
			continue
		if not bones.has(track_meta["name"]):
			continue
		var bone: Node = bones[track_meta["name"]]
		var property := _property_name(track_meta["property"])
		var track_index := animation.add_track(Animation.TYPE_VALUE)
		animation.track_set_path(track_index, NodePath("%s:%s" % [root.get_path_to(bone), property]))
		animation.track_set_interpolation_type(track_index, Animation.INTERPOLATION_LINEAR)
		for key in track_meta["keys"]:
			animation.track_insert_key(track_index, float(key["time"]), _value_for_property(track_meta["property"], key["value"]))
	if motion.get("events", []).size() > 0:
		var event_track := animation.add_track(Animation.TYPE_METHOD)
		animation.track_set_path(event_track, NodePath("."))
		for event in motion["events"]:
			animation.track_insert_key(event_track, float(event["time"]), {
				"method": "animation_event",
				"args": [event["name"], event.get("target", "")]
			})
	return animation

func _property_name(property: String) -> String:
	if property == "rotation_degrees":
		return "rotation_degrees"
	return property

func _value_for_property(property: String, value: Variant) -> Variant:
	if property == "position" or property == "scale":
		return _vec2(value)
	return value

func _list_json_files(base: String) -> Array[String]:
	var result: Array[String] = []
	var dir := DirAccess.open(base)
	if dir == null:
		return result
	dir.list_dir_begin()
	while true:
		var entry := dir.get_next()
		if entry == "":
			break
		if not dir.current_is_dir() and entry.ends_with(".json"):
			result.append("%s/%s" % [base, entry])
	dir.list_dir_end()
	result.sort()
	return result

func _vec2(value: Variant) -> Vector2:
	return Vector2(float(value[0]), float(value[1]))

func _write_preview(path: String) -> void:
	var image := Image.create(320, 180, false, Image.FORMAT_RGBA8)
	image.fill(Color(0.92, 0.94, 0.96, 1.0))
	for x in range(70, 250):
		for y in range(60, 120):
			if (x + y) % 11 < 6:
				image.set_pixel(x, y, Color(0.2, 0.45, 0.75, 1.0))
	image.save_png(path)
