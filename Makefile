KICAD_VER ?= "9.0"
PLUGIN_DIR_LOCAL = ~/.local/share/kicad/$(KICAD_VER)/scripting/plugins
PLUGIN_DIR_FLATPAK = ~/.var/app/org.kicad.KiCad/data/kicad/$(KICAD_VER)/scripting/plugins

test:
	@echo "Run test"
	python3 dialog.py

release: release.sh
	@echo "Create release"
	./release.sh

install:
	@echo "Install Plugin"
	mkdir fanout-tool
	cp __init__.py fanout-tool/
	cp -r onekiwi/ fanout-tool/
	@if [ -d $(PLUGIN_DIR_LOCAL) ]; then \
		echo "Installing to local KiCad: $(PLUGIN_DIR_LOCAL)"; \
		rm -rf $(PLUGIN_DIR_LOCAL)/fanout-tool/; \
		mv fanout-tool/ $(PLUGIN_DIR_LOCAL); \
	elif [ -d $(PLUGIN_DIR_FLATPAK) ]; then \
		echo "Installing to Flatpak KiCad: $(PLUGIN_DIR_FLATPAK)"; \
		rm -rf $(PLUGIN_DIR_FLATPAK)/fanout-tool/; \
		mv fanout-tool/ $(PLUGIN_DIR_FLATPAK); \
	else \
		echo "Error: No KiCad plugin directory found"; \
		rm -rf fanout-tool/; \
		exit 1; \
	fi

uninstall:
	@echo "Uninstall Plugin"
	@rm -rf $(PLUGIN_DIR_LOCAL)/fanout-tool/ 2>/dev/null || true
	@rm -rf $(PLUGIN_DIR_FLATPAK)/fanout-tool/ 2>/dev/null || true
