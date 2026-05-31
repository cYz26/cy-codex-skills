#!/usr/bin/env bash
# ==============================================================================
# Codex Profile Switcher
# ==============================================================================
# Safely switches Codex between official OpenAI subscription mode and DeepSeek
# API mode through CCX.
#
# Usage:
#   switch-profile.sh status               Show current profile state
#   switch-profile.sh deepseek [model]     Switch CLI/App to DeepSeek mode
#   switch-profile.sh deepseek --cli-only  Generate/update DeepSeek overlay only
#   switch-profile.sh activate-deepseek    Compatibility alias for App activation
#   switch-profile.sh official             Disable overlay or restore official base config
#   switch-profile.sh setup-deepseek       First-time DeepSeek setup wizard
#   switch-profile.sh backup               Create a timestamped backup
#   switch-profile.sh restore <path>       Restore base config from a backup
# ==============================================================================

set -euo pipefail

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
PROFILES_DIR="$CODEX_HOME/profiles"
CONFIG_FILE="$CODEX_HOME/config.toml"
DEEPSEEK_PROFILE_FILE="$CODEX_HOME/deepseek.config.toml"
RUNTIME_DEEPSEEK_PROFILE="$PROFILES_DIR/deepseek"
RUNTIME_DEEPSEEK_CATALOG="$RUNTIME_DEEPSEEK_PROFILE/models_catalog.json"
LEGACY_CATALOG_FILE="$CODEX_HOME/models_catalog.json"
CCX_DIR="${CCX_DIR:-$HOME/Dev/agents-dev/ccx}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_resolve_profiles_template_dir() {
    if [[ -n "${PROJECT_TEMPLATES_DIR:-}" ]]; then
        if [[ -d "$PROJECT_TEMPLATES_DIR/profiles" ]]; then
            echo "$PROJECT_TEMPLATES_DIR/profiles"
        else
            echo "$PROJECT_TEMPLATES_DIR"
        fi
        return
    fi

    if [[ -d "$SCRIPT_DIR/profiles" ]]; then
        echo "$SCRIPT_DIR/profiles"
        return
    fi

    local search_dirs=(
        "$HOME/Dev/agents-dev/cy-codex-skills/dev/tools/codex-profile-switch/profiles"
        "$HOME/Dev/cy-codex-skills/dev/tools/codex-profile-switch/profiles"
        "$PROFILES_DIR"
    )
    local dir
    for dir in "${search_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            echo "$dir"
            return
        fi
    done

    echo "$PROFILES_DIR"
}

PROFILES_TEMPLATE_DIR="$(_resolve_profiles_template_dir)"
TOOL_TEMPLATE_DIR="$(dirname "$PROFILES_TEMPLATE_DIR")"

if [[ -n "${NO_COLOR:-}" ]]; then
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
else
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
fi

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

BACKUP_TS=""
SUPPRESS_STATUS=false

resolve_profile_template() {
    local relative_path="$1"
    local project_path="$PROFILES_TEMPLATE_DIR/$relative_path"
    local runtime_path="$PROFILES_DIR/$relative_path"

    if [[ -f "$project_path" ]]; then
        echo "$project_path"
    elif [[ -f "$runtime_path" ]]; then
        echo "$runtime_path"
    else
        echo ""
    fi
}

resolve_ccx_template() {
    local filename="$1"
    local candidates=(
        "$TOOL_TEMPLATE_DIR/ccx/$filename"
        "$SCRIPT_DIR/ccx/$filename"
        "$HOME/Dev/agents-dev/cy-codex-skills/dev/tools/codex-profile-switch/ccx/$filename"
    )
    local path
    for path in "${candidates[@]}"; do
        if [[ -f "$path" ]]; then
            echo "$path"
            return
        fi
    done
    echo ""
}

get_current_model() {
    grep '^model = ' "$CONFIG_FILE" 2>/dev/null | head -1 | sed 's/model = "\(.*\)"/\1/' || echo "unknown"
}

base_has_ccx_provider() {
    [[ -f "$CONFIG_FILE" ]] &&
        grep -q '^model_provider = "ccx"' "$CONFIG_FILE" &&
        grep -q '^\[model_providers\.ccx\]' "$CONFIG_FILE"
}

overlay_model() {
    grep '^model = ' "$DEEPSEEK_PROFILE_FILE" 2>/dev/null | head -1 | sed 's/model = "\(.*\)"/\1/' || echo "not generated"
}

backup_config() {
    local label="${1:-auto}"
    BACKUP_TS="$(date +%Y%m%d-%H%M%S)"
    local backup_path="$CODEX_HOME/config.toml.bak-${BACKUP_TS}-${label}"

    mkdir -p "$CODEX_HOME"
    if [[ -f "$CONFIG_FILE" ]]; then
        cp "$CONFIG_FILE" "$backup_path"
        log_info "Backed up config to: $(basename "$backup_path")"
    fi

    if [[ -f "$LEGACY_CATALOG_FILE" ]]; then
        cp "$LEGACY_CATALOG_FILE" "$LEGACY_CATALOG_FILE.bak-${BACKUP_TS}-${label}"
        log_info "Backed up legacy models_catalog.json"
    fi
}

save_to_profile() {
    local profile_name="$1"
    local profile_dir="$PROFILES_DIR/$profile_name"

    mkdir -p "$profile_dir"
    if [[ -f "$CONFIG_FILE" ]]; then
        cp "$CONFIG_FILE" "$profile_dir/config.toml"
        get_current_model > "$profile_dir/model.txt"
        log_info "Saved base config snapshot to runtime profile: $profile_name"
    fi
}

install_deepseek_catalog() {
    local catalog_src
    catalog_src="$(resolve_profile_template "deepseek/models_catalog.json")"

    if [[ -z "$catalog_src" ]]; then
        log_error "DeepSeek models_catalog.json not found."
        log_error "Expected at: $PROFILES_TEMPLATE_DIR/deepseek/models_catalog.json"
        return 1
    fi

    mkdir -p "$RUNTIME_DEEPSEEK_PROFILE"
    cp "$catalog_src" "$RUNTIME_DEEPSEEK_CATALOG"
    log_info "Installed DeepSeek model catalog to: $RUNTIME_DEEPSEEK_CATALOG"
}

generate_deepseek_profile() {
    local deepseek_model="${1:-ccx}"
    local provider_config
    provider_config="$(resolve_profile_template "deepseek/config.openai.toml")"

    if [[ -z "$provider_config" ]]; then
        log_error "DeepSeek provider config not found."
        log_error "Expected at: $PROFILES_TEMPLATE_DIR/deepseek/config.openai.toml"
        log_error "Run 'switch-profile.sh setup-deepseek' first."
        return 1
    fi

    install_deepseek_catalog

    python3 - "$provider_config" "$DEEPSEEK_PROFILE_FILE" "$deepseek_model" "$RUNTIME_DEEPSEEK_CATALOG" <<'PYEOF'
import json
import sys
import tomllib
from pathlib import Path

provider_config_path = Path(sys.argv[1])
profile_path = Path(sys.argv[2])
model = sys.argv[3]
catalog_path = Path(sys.argv[4])

provider_data = tomllib.loads(provider_config_path.read_text())
if provider_data.get("model_providers", {}).get("ccx") is None:
    raise SystemExit("provider config must define [model_providers.ccx]")

provider_section = provider_config_path.read_text().strip()
q = json.dumps

content = "\n".join(
    [
        f"model = {q(model)}",
        'model_provider = "ccx"',
        "model_context_window = 1000000",
        "model_max_output_tokens = 384000",
        'model_reasoning_effort = "high"',
        f"model_catalog_json = {q(str(catalog_path))}",
        "",
        provider_section,
        "",
    ]
)

profile_path.parent.mkdir(parents=True, exist_ok=True)
profile_path.write_text(content)
PYEOF

    log_ok "Generated DeepSeek Codex profile overlay: $DEEPSEEK_PROFILE_FILE"
}

show_deepseek_usage() {
    cat <<EOF
Usage:
  $(basename "$0") deepseek [model] [--cli-only]

Without --cli-only, this switches both Codex CLI and Codex Desktop App to
DeepSeek mode. Use --cli-only to only generate the codex --profile deepseek
overlay without changing $CONFIG_FILE.
EOF
}

ensure_ccx_running() {
    if curl -fsS http://127.0.0.1:3688/health >/dev/null 2>&1; then
        log_info "CCX is running at http://127.0.0.1:3688"
    else
        local ccx_bin="$CCX_DIR/dist/ccx-go"
        if [[ -f "$ccx_bin" && -d "$CCX_DIR/backend-go" ]]; then
            log_info "Starting CCX..."
            (cd "$CCX_DIR/backend-go" && nohup "$ccx_bin" >/dev/null 2>&1 &)
            sleep 2
            if curl -fsS http://127.0.0.1:3688/health >/dev/null 2>&1; then
                log_ok "CCX started successfully"
            else
                log_warn "CCX may still be starting. Check: curl http://127.0.0.1:3688/health"
            fi
        else
            log_warn "CCX binary not found at $ccx_bin"
            log_warn "Run 'switch-profile.sh setup-deepseek' first, or start CCX manually."
        fi
    fi
}

switch_to_deepseek() {
    local deepseek_model="ccx"
    local model_set=false
    local cli_only=false
    local arg

    for arg in "$@"; do
        case "$arg" in
            --cli-only|--profile-only)
                cli_only=true
                ;;
            -h|--help)
                SUPPRESS_STATUS=true
                show_deepseek_usage
                return 0
                ;;
            --*)
                log_error "Unknown deepseek option: $arg"
                log_info "Run '$(basename "$0") deepseek --help' for usage."
                return 1
                ;;
            *)
                if [[ "$model_set" == "true" ]]; then
                    log_error "Only one model alias can be provided."
                    log_info "Run '$(basename "$0") deepseek --help' for usage."
                    return 1
                fi
                deepseek_model="$arg"
                model_set=true
                ;;
        esac
    done

    if [[ "$cli_only" == "true" ]]; then
        log_info "Preparing DeepSeek CLI profile overlay (model: $deepseek_model)..."
        if ! base_has_ccx_provider; then
            save_to_profile "official"
        else
            log_warn "Base config already appears to use CCX; keeping existing official snapshot."
        fi
        generate_deepseek_profile "$deepseek_model"
        log_info "Use it with CLI runtime commands: codex --profile deepseek"
    else
        log_info "Switching Codex CLI/App to DeepSeek mode (model: $deepseek_model)..."
        generate_deepseek_profile "$deepseek_model"
        activate_deepseek_app "$deepseek_model"
        log_info "CLI runtime commands can also use: codex --profile deepseek"
    fi

    ensure_ccx_running
}

activate_deepseek_app() {
    local deepseek_model="${1:-ccx}"
    local provider_config
    provider_config="$(resolve_profile_template "deepseek/config.openai.toml")"

    if [[ -z "$provider_config" ]]; then
        log_error "DeepSeek provider config not found."
        log_error "Expected at: $PROFILES_TEMPLATE_DIR/deepseek/config.openai.toml"
        return 1
    fi

    log_info "Applying DeepSeek mode to base Codex config for Codex Desktop App (model: $deepseek_model)..."

    if ! base_has_ccx_provider; then
        save_to_profile "official"
    else
        log_warn "Base config already appears to use CCX; keeping existing official snapshot."
    fi
    backup_config "before-deepseek-app"
    install_deepseek_catalog

    python3 - "$CONFIG_FILE" "$provider_config" "$deepseek_model" "$RUNTIME_DEEPSEEK_CATALOG" <<'PYEOF'
import json
import re
import sys
import tomllib
from pathlib import Path

config_path = Path(sys.argv[1])
provider_config_path = Path(sys.argv[2])
model = sys.argv[3]
catalog_path = Path(sys.argv[4])

provider_data = tomllib.loads(provider_config_path.read_text())
if provider_data.get("model_providers", {}).get("ccx") is None:
    raise SystemExit("provider config must define [model_providers.ccx]")

provider_section = provider_config_path.read_text().strip()
lines = config_path.read_text().splitlines()
out = []
skip_ccx_provider = False
seen_table = False
top_level_deepseek_key = re.compile(
    r'^(model|model_provider|model_context_window|model_max_output_tokens|model_reasoning_effort|model_catalog_json)\s*='
)

for line in lines:
    stripped = line.strip()
    if re.match(r'^\[model_providers\.ccx\]$', stripped):
        skip_ccx_provider = True
        seen_table = True
        continue
    if skip_ccx_provider and stripped.startswith("[") and stripped.endswith("]"):
        skip_ccx_provider = False
    if skip_ccx_provider:
        continue
    if stripped.startswith("[") and stripped.endswith("]"):
        seen_table = True
    if not seen_table and top_level_deepseek_key.match(line):
        continue
    out.append(line)

body = "\n".join(out).strip()
q = json.dumps
top = "\n".join(
    [
        f"model = {q(model)}",
        'model_provider = "ccx"',
        "model_context_window = 1000000",
        "model_max_output_tokens = 384000",
        'model_reasoning_effort = "high"',
        f"model_catalog_json = {q(str(catalog_path))}",
    ]
)

content = top + "\n"
if body:
    content += "\n" + body + "\n"
content += "\n" + provider_section + "\n"

tomllib.loads(content)
config_path.write_text(content)
PYEOF

    log_ok "Base config now targets DeepSeek via CCX."
    log_info "Launch Codex Desktop App normally after fully quitting it."
}

switch_to_official() {
    log_info "Switching command context back to official subscription mode..."

    if [[ -f "$DEEPSEEK_PROFILE_FILE" ]]; then
        rm "$DEEPSEEK_PROFILE_FILE"
        log_info "Removed generated DeepSeek profile overlay: $DEEPSEEK_PROFILE_FILE"
    else
        log_info "No generated DeepSeek profile overlay found."
    fi

    if base_has_ccx_provider; then
        local official_snapshot="$PROFILES_DIR/official/config.toml"
        if [[ -f "$official_snapshot" ]]; then
            backup_config "before-official-restore"
            cp "$official_snapshot" "$CONFIG_FILE"
            log_ok "Restored official base config from: $official_snapshot"
        else
            log_warn "Base config still contains CCX provider settings, but no official snapshot was found."
            log_warn "Use 'switch-profile.sh restore <backup-path>' if you want to restore an older official backup."
        fi
    else
        log_ok "Official mode uses the unchanged base config: $CONFIG_FILE"
    fi
}

setup_deepseek() {
    log_info "=== DeepSeek API Mode Setup ==="
    echo ""

    if ! command -v go >/dev/null 2>&1; then
        log_error "Go is not installed. CCX requires Go."
        log_info "Install Go: brew install go"
        return 1
    fi

    if [[ ! -d "$CCX_DIR" ]]; then
        log_info "Cloning CCX to $CCX_DIR..."
        mkdir -p "$(dirname "$CCX_DIR")"
        git clone https://github.com/BenedictKing/ccx.git "$CCX_DIR"
    fi

    if [[ ! -d "$CCX_DIR/backend-go" ]]; then
        log_error "CCX backend directory not found: $CCX_DIR/backend-go"
        return 1
    fi

    cd "$CCX_DIR/backend-go"

    local env_template
    env_template="$(resolve_ccx_template ".env.example")"
    if [[ ! -f ".env" && -n "$env_template" ]]; then
        cp "$env_template" .env
        log_info "Created .env from project template."
        log_warn "Edit $CCX_DIR/backend-go/.env and set PROXY_ACCESS_KEY if needed."
    fi

    local config_template
    config_template="$(resolve_ccx_template "config.example.json")"
    if [[ ! -f ".config/config.json" && -n "$config_template" ]]; then
        mkdir -p .config
        cp "$config_template" .config/config.json
        log_info "Created config.json from project template."
        log_warn "Edit $CCX_DIR/backend-go/.config/config.json and set your DeepSeek API key."
    fi

    if [[ ! -f "$CCX_DIR/dist/ccx-go" ]]; then
        log_info "Building CCX..."
        go build -o ../dist/ccx-go .
    fi

    generate_deepseek_profile "ccx"
    log_ok "DeepSeek profile setup complete."
}

show_status() {
    local base_model
    base_model="$(get_current_model)"

    echo ""
    echo "Codex Profile Status"
    echo "--------------------"

    if base_has_ccx_provider; then
        echo "Base config: DeepSeek/CCX mode"
    else
        echo "Base config: official subscription/default mode"
    fi
    echo "Base model:  $base_model"
    echo "Codex home:  $CODEX_HOME"

    if [[ -f "$DEEPSEEK_PROFILE_FILE" ]]; then
        echo "DeepSeek profile: generated ($DEEPSEEK_PROFILE_FILE)"
        echo "DeepSeek model:   $(overlay_model)"
        echo "Launch:           codex --profile deepseek"
    else
        echo "DeepSeek profile: not generated"
    fi

    if [[ -f "$RUNTIME_DEEPSEEK_CATALOG" ]]; then
        echo "Model catalog:    $RUNTIME_DEEPSEEK_CATALOG"
    else
        echo "Model catalog:    not installed"
    fi

    if curl -fsS http://127.0.0.1:3688/health >/dev/null 2>&1; then
        echo "CCX proxy:        running at http://127.0.0.1:3688"
    else
        echo "CCX proxy:        not running"
    fi

    echo "Templates:        $PROFILES_TEMPLATE_DIR"
    echo ""
}

create_backup() {
    backup_config "manual"
    log_ok "Backup created with timestamp: $BACKUP_TS"

    echo ""
    log_info "Existing backups:"
    ls -la "$CODEX_HOME"/config.toml.bak-* 2>/dev/null || echo "  (none)"
}

restore_backup() {
    local backup_path="$1"

    if [[ ! -f "$backup_path" ]]; then
        log_error "Backup not found: $backup_path"
        return 1
    fi

    backup_config "before-restore"
    cp "$backup_path" "$CONFIG_FILE"
    log_ok "Restored config from: $backup_path"
    show_status
}

validate_profile() {
    if [[ ! -f "$DEEPSEEK_PROFILE_FILE" ]]; then
        log_error "DeepSeek profile overlay not found. Run 'switch-profile.sh deepseek' first."
        return 1
    fi

    python3 - "$DEEPSEEK_PROFILE_FILE" <<'PYEOF'
import sys
import tomllib
from pathlib import Path

path = Path(sys.argv[1])
tomllib.loads(path.read_text())
print(f"profile TOML parse ok: {path}")
PYEOF

    if command -v codex >/dev/null 2>&1; then
        codex -c "model_catalog_json=\"$RUNTIME_DEEPSEEK_CATALOG\"" debug models >/dev/null
        log_ok "Codex model catalog parse ok"
    else
        log_warn "codex CLI not found; skipped Codex catalog parse check"
    fi
}

main() {
    local cmd="${1:-status}"
    shift || true

    case "$cmd" in
        status|s)
            show_status
            ;;

        official|o|openai)
            switch_to_official
            show_status
            ;;

        deepseek|d|ds)
            SUPPRESS_STATUS=false
            switch_to_deepseek "$@"
            if [[ "$SUPPRESS_STATUS" != "true" ]]; then
                show_status
            fi
            ;;

        activate-deepseek|apply-deepseek|app-deepseek)
            activate_deepseek_app "$@"
            show_status
            ;;

        setup-deepseek|setup)
            setup_deepseek
            ;;

        validate|check)
            validate_profile
            ;;

        backup|bak)
            create_backup
            ;;

        restore|rest)
            if [[ $# -lt 1 ]]; then
                log_error "Usage: switch-profile.sh restore <backup-path>"
                log_info "Available backups:"
                ls -la "$CODEX_HOME"/config.toml.bak-* 2>/dev/null || echo "  (none)"
                return 1
            fi
            restore_backup "$1"
            ;;

        help|-h|--help)
            cat <<EOF
Codex Profile Switcher

Usage:
  $(basename "$0") status               Show current profile state
  $(basename "$0") deepseek [model]     Switch CLI/App to DeepSeek mode
  $(basename "$0") deepseek --cli-only  Generate/update DeepSeek CLI overlay only
  $(basename "$0") official             Disable overlay or restore official base config
  $(basename "$0") setup-deepseek       First-time DeepSeek setup
  $(basename "$0") validate             Validate generated DeepSeek profile
  $(basename "$0") backup               Create timestamped backup
  $(basename "$0") restore <path>       Restore base config from backup

Daily use:
  $(basename "$0") deepseek
  $(basename "$0") official

CLI-only mode:
  $(basename "$0") deepseek --cli-only
  codex --profile deepseek

Compatibility aliases:
  $(basename "$0") activate-deepseek    Apply DeepSeek mode to base config only

Templates: $PROFILES_TEMPLATE_DIR
EOF
            ;;

        *)
            log_error "Unknown command: $cmd"
            log_info "Run '$(basename "$0") help' for usage."
            return 1
            ;;
    esac
}

main "$@"
