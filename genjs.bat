@echo off

python src/gen.py assets/gl.xml -p assets/gl-patch.xml -o build/js/ --force --json
