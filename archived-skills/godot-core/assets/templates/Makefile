GODOT ?= godot
PRESET_WEB ?= Web
PRESET_ANDROID ?= Android
BUILD_DIR ?= build
WEB_DIR ?= $(BUILD_DIR)/web
TEST_RESULTS_DIR ?= $(BUILD_DIR)/test-results
GUT_JUNIT ?= $(TEST_RESULTS_DIR)/gut-junit.xml

# ---- Code quality ----
fmt:
	@echo "==> gdformat"
	gdformat .

lint:
	@echo "==> gdlint"
	gdlint .

# ---- Tests ----
test:
	@echo "==> GUT unit tests"
	mkdir -p "$(TEST_RESULTS_DIR)"
	$(GODOT) --headless -s res://addons/gut/gut_cmdln.gd --path "$$PWD" -gdir=res://tests -ginclude_subdirs -gexit

test-junit:
	@echo "==> GUT unit tests (JUnit XML)"
	mkdir -p "$(TEST_RESULTS_DIR)"
	$(GODOT) --headless -s res://addons/gut/gut_cmdln.gd --path "$$PWD" -gdir=res://tests -ginclude_subdirs -gjunit_xml_file="$(GUT_JUNIT)" -gexit

smoke:
	@echo "==> smoke test"
	$(GODOT) --headless -s res://tools/smoke_test_runner.gd

# ---- Web export ----
export-web:
	@echo "==> export web (preset must match export_presets.cfg)"
	mkdir -p "$(WEB_DIR)"
	$(GODOT) --headless --export-release "$(PRESET_WEB)" "$(WEB_DIR)/index.html"

web-smoke:
	@echo "==> local serve + load check"
	bash tools/web_smoke_test.sh "$(WEB_DIR)"
