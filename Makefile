KICAD_VER ?= "10.99"
# PCM layout: plugins and resources under 3rdparty
PLUGIN_DIR_LOCAL = ~/.local/share/kicad/$(KICAD_VER)/3rdparty/plugins
RESOURCE_DIR_LOCAL = ~/.local/share/kicad/$(KICAD_VER)/3rdparty/resources
PLUGIN_DIR_FLATPAK = ~/.var/app/org.kicad.KiCad/data/kicad/$(KICAD_VER)/3rdparty/plugins
RESOURCE_DIR_FLATPAK = ~/.var/app/org.kicad.KiCad/data/kicad/$(KICAD_VER)/3rdparty/resources
PLUGIN_ID_DOT = vn.onekiwi.fanouttool
PLUGIN_ID_UNDER = vn_onekiwi_fanouttool

test:
	@echo "Run test"
	python3 dialog.py

release: release.sh
	@echo "Create release"
	./release.sh

install:
	@echo "Install Plugin"
	@rm -rf $(PLUGIN_ID_UNDER)
	# Build staging structure to match PCM install
	mkdir -p $(PLUGIN_ID_UNDER)/$(PLUGIN_ID_DOT)
	cp __init__.py $(PLUGIN_ID_UNDER)/
	cp -r onekiwi/ $(PLUGIN_ID_UNDER)/
	cp plugin.json $(PLUGIN_ID_UNDER)/$(PLUGIN_ID_DOT)/
	cp fanout_action.py $(PLUGIN_ID_UNDER)/$(PLUGIN_ID_DOT)/
	cp -r onekiwi/ $(PLUGIN_ID_UNDER)/$(PLUGIN_ID_DOT)/
	cp -r icon/ $(PLUGIN_ID_UNDER)/$(PLUGIN_ID_DOT)/
	@echo "kicad-python>=0.2.0" > $(PLUGIN_ID_UNDER)/$(PLUGIN_ID_DOT)/requirements.txt
	@echo "wxPython~=4.2" >> $(PLUGIN_ID_UNDER)/$(PLUGIN_ID_DOT)/requirements.txt
	@if [ -d $$(dirname $(PLUGIN_DIR_LOCAL)) ]; then \
		mkdir -p $(PLUGIN_DIR_LOCAL) $(RESOURCE_DIR_LOCAL); \
		echo "Installing to local KiCad: $(PLUGIN_DIR_LOCAL)"; \
		rm -rf $(PLUGIN_DIR_LOCAL)/$(PLUGIN_ID_UNDER)/; \
		cp -r $(PLUGIN_ID_UNDER)/ $(PLUGIN_DIR_LOCAL)/; \
		rm -rf $(RESOURCE_DIR_LOCAL)/$(PLUGIN_ID_UNDER)/; \
		mkdir -p $(RESOURCE_DIR_LOCAL)/$(PLUGIN_ID_UNDER); \
		cp icon/icon_64x64.png $(RESOURCE_DIR_LOCAL)/$(PLUGIN_ID_UNDER)/icon.png; \
	elif [ -d $$(dirname $(PLUGIN_DIR_FLATPAK)) ]; then \
		mkdir -p $(PLUGIN_DIR_FLATPAK) $(RESOURCE_DIR_FLATPAK); \
		echo "Installing to Flatpak KiCad: $(PLUGIN_DIR_FLATPAK)"; \
		rm -rf $(PLUGIN_DIR_FLATPAK)/$(PLUGIN_ID_UNDER)/; \
		cp -r $(PLUGIN_ID_UNDER)/ $(PLUGIN_DIR_FLATPAK)/; \
		rm -rf $(RESOURCE_DIR_FLATPAK)/$(PLUGIN_ID_UNDER)/; \
		mkdir -p $(RESOURCE_DIR_FLATPAK)/$(PLUGIN_ID_UNDER); \
		cp icon/icon_64x64.png $(RESOURCE_DIR_FLATPAK)/$(PLUGIN_ID_UNDER)/icon.png; \
	else \
		echo "Error: No KiCad plugin directory found"; \
		rm -rf $(PLUGIN_ID_UNDER)/; \
		exit 1; \
	fi
	@rm -rf $(PLUGIN_ID_UNDER)/

uninstall:
	@echo "Uninstall Plugin"
	@rm -rf $(PLUGIN_DIR_LOCAL)/$(PLUGIN_ID_UNDER)/ 2>/dev/null || true
	@rm -rf $(RESOURCE_DIR_LOCAL)/$(PLUGIN_ID_UNDER)/ 2>/dev/null || true
	@rm -rf $(PLUGIN_DIR_FLATPAK)/$(PLUGIN_ID_UNDER)/ 2>/dev/null || true
	@rm -rf $(RESOURCE_DIR_FLATPAK)/$(PLUGIN_ID_UNDER)/ 2>/dev/null || true
