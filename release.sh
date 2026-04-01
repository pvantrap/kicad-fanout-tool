#!/bin/bash -e

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: Working directory is dirty. Commit or stash changes before releasing."
    exit 1
fi

version=$(git describe --tags --abbrev=0)
name=$(echo fanout-tool-$version.zip)

echo "Building release $version"
cp metadata.json.template metadata.json
sed -i -e "s/VERSION/$version/g" metadata.json
sed -i '/download_/d' metadata.json
sed -i '/install_size/d' metadata.json

mkdir resources
cp icon/icon_64x64.png resources/
mv resources/icon_64x64.png resources/icon.png

# Create plugins directory with IPC API plugin structure
mkdir -p plugins/vn.onekiwi.fanouttool
cp plugin.json plugins/vn.onekiwi.fanouttool/
cp fanout_action.py plugins/vn.onekiwi.fanouttool/
cp -r onekiwi/ plugins/vn.onekiwi.fanouttool/
cp -r icon/ plugins/vn.onekiwi.fanouttool/
echo "kicad-python>=0.2.0" > plugins/vn.onekiwi.fanouttool/requirements.txt
echo "wxPython~=4.2" >> plugins/vn.onekiwi.fanouttool/requirements.txt

zip -r $name plugins resources metadata.json

rm -rf plugins
rm -rf resources

sha=$(sha256sum $name | cut -d' ' -f1)
size=$(du -b $name | cut -f1)
installSize=$(unzip -l $name | tail -1 | xargs | cut -d' ' -f1)

cp metadata.json.template metadata.json
sed -i -e "s/VERSION/$version/g" metadata.json
sed -i -e "s/SHA256/$sha/g" metadata.json
sed -i -e "s/DOWNLOAD_SIZE/$size/g" metadata.json
sed -i -e "s/INSTALL_SIZE/$installSize/g" metadata.json

ls -lh $name metadata.json

