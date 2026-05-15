extends SceneTree

const CASES_DIR := "res://fixtures/cases"

func _init() -> void:
	var failures: Array[String] = []
	var scenes := _list_generated_scenes(CASES_DIR)
	if scenes.is_empty():
		failures.append("No generated scenes found under %s" % CASES_DIR)
	for scene_path in scenes:
		var scene := load(scene_path)
		if scene == null:
			failures.append("Unable to load %s" % scene_path)
		else:
			print("Loaded %s" % scene_path)
	if failures.is_empty():
		print("Loaded %d generated scenes." % scenes.size())
		quit(0)
	else:
		for failure in failures:
			push_error(failure)
		quit(1)

func _list_generated_scenes(base: String) -> Array[String]:
	var result: Array[String] = []
	var dir := DirAccess.open(base)
	if dir == null:
		return result
	dir.list_dir_begin()
	while true:
		var entry := dir.get_next()
		if entry == "":
			break
		if entry.begins_with(".") or not dir.current_is_dir():
			continue
		var scene_path := "%s/%s/generated/%s.tscn" % [base, entry, entry]
		if FileAccess.file_exists(scene_path):
			result.append(scene_path)
	dir.list_dir_end()
	result.sort()
	return result
