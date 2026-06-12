.DEFAULT_GOAL := help

.PHONY: help build web wechat wechat-debug audit audit-wechat test lint typecheck clean preview

NPM ?= npm

help:
	@printf "Available targets:\n"
	@printf "  make web           Build the web bundle\n"
	@printf "  make wechat        Build the WeChat release bundle\n"
	@printf "  make wechat-debug  Build the WeChat debug bundle\n"
	@printf "  make audit         Audit the packaged WeChat build\n"
	@printf "  make test          Run the test suite\n"
	@printf "  make lint          Run ESLint\n"
	@printf "  make typecheck     Run TypeScript type-checking\n"
	@printf "  make clean         Remove build outputs\n"
	@printf "  make preview       Start the Vite preview server\n"

build: web

web:
	$(NPM) run build:web

wechat:
	$(NPM) run build:wechat

wechat-debug:
	$(NPM) run build:wechat:debug

audit: audit-wechat

audit-wechat:
	$(NPM) run audit:wechat

test:
	$(NPM) run test

lint:
	$(NPM) run lint

typecheck:
	$(NPM) run typecheck

clean:
	rm -rf build dist

preview:
	$(NPM) run preview
