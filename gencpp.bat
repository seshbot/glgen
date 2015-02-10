@echo off

python src/gen.py assets/gl.xml -p assets/gl-patch.xml -o build/lib/ --force --cpp --es2only
