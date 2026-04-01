KICAD_VER ?= "10.99"
# IPC API plugins installed via PCM go to 3rdparty/plugins
PLUGIN_DIR_LOCAL = ~/.local/share/kicad/$(KICAD_VER)/3rdparty/plugins
PLUGIN_DIR_FLATPAK = ~/.var/app/org.kicad.KiCad/data/kicad/$(KICAD_VER)/3rdparty/plugins
PLUGIN_ID = vn.onekiwi.fanouttool

test:
	@echo "Run test"
	python3 dialog.py

release: release.sh
	@echo "Create release"
	./release.sh

install:
	@echo "Install Plugin"
	mkdir -p $(PLUGIN_ID)
	cp plugin.json $(PLUGIN_ID)/
	cp fanout_action.py $(PLUGIN_ID)/
	cp -r onekiwi/ $(PLUGIN_ID)/
	cp -r icon/ $(PLUGIN_ID)/
	@echo "kicad-python>=0.2.0" > $(PLUGIN_ID)/requirements.txt
	@echo "wxPython~=4.2" >> $(PLUGIN_ID)/requirements.txt
	@if [ -d $$(dirname $(PLUGIN_DIR_LOCAL)) ]; then \
		mkdir -p $(PLUGIN_DIR_LOCAL); \
		echo "Installing to local KiCad: $(PLUGIN_DIR_LOCAL)"; \
		rm -rf $(PLUGIN_DIR_LOCAL)/$(PLUGIN_ID)/; \
		mv $(PLUGIN_ID)/ $(PLUGIN_DIR_LOCAL); \
	elif [ -d $$(dirname $(PLUGIN_DIR_FLATPAK)) ]; then \
		mkdir -p $(PLUGIN_DIR_FLATPAK); \
		echo "Installing to Flatpak KiCad: $(PLUGIN_DIR_FLATPAK)"; \
		rm -rf $(PLUGIN_DIR_FLATPAK)/$(PLUGIN_ID)/; \
		mv $(PLUGIN_ID)/ $(PLUGIN_DIR_FLATPAK); \
	else \
		echo "Error: No KiCad plugin directory found"; \
		rm -rf $(PLUGIN_ID)/; \
		exit 1; \
	fi

uninstall:
	@echo "Uninstall Plugin"
	@rm -rf $(PLUGIN_DIR_LOCAL)/$(PLUGIN_ID)/ 2>/dev/null || true
	@rm -rf $(PLUGIN_DIR_FLATPAK)/$(PLUGIN_ID)/ 2>/dev/null || true
