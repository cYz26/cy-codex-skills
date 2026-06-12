.PHONY: web wechat wechat-debug audit audit-wechat test lint typecheck

NPM ?= npm

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
