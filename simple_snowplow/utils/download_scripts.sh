#!/bin/bash

SCRIPTS_VERSION=${SCRIPTS_VERSION:-3.15.0}
SCRIPTS_URL="https://github.com/snowplow/snowplow-javascript-tracker/releases/download/$SCRIPTS_VERSION"
SCRIPTS_OUTPUT_DIR=${SCRIPTS_OUTPUT_DIR:-./simple_snowplow/static}

echo "Create scripts directory: $SCRIPTS_OUTPUT_DIR"
mkdir -p "$SCRIPTS_OUTPUT_DIR"
echo "Download scripts v$SCRIPTS_VERSION from github"
curl -sLO --output-dir "$SCRIPTS_OUTPUT_DIR" "$SCRIPTS_URL/sp.js"
curl -sLO --output-dir "$SCRIPTS_OUTPUT_DIR" "$SCRIPTS_URL/sp.js.map"
curl -sLO --output-dir "$SCRIPTS_OUTPUT_DIR" "$SCRIPTS_URL/plugins.umd.zip"
echo "Unzip plugins"
unzip -oq "$SCRIPTS_OUTPUT_DIR/plugins.umd.zip" -d "$SCRIPTS_OUTPUT_DIR"
cp "$SCRIPTS_OUTPUT_DIR/sp.js" "$SCRIPTS_OUTPUT_DIR/loader.js"
cp "$SCRIPTS_OUTPUT_DIR/sp.js.map" "$SCRIPTS_OUTPUT_DIR/loader.js.map"

echo "Remove archive"
rm "$SCRIPTS_OUTPUT_DIR/plugins.umd.zip"
