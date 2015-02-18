@echo off

if not exist build\* mkdir build
if not exist build\lib\* mkdir build\lib
if not exist build\lib\include\* mkdir build\lib\include
if not exist build\lib\src\* mkdir build\lib\src
if not exist build\lib\src\gles2\* mkdir build\lib\src\gles2

copy assets\cpp\include\*.* build\lib\include\
copy assets\cpp\src\*.* build\lib\src\gles2\

python src/gen.py assets/gl.xml -p assets/gl-patch.xml -o build/lib/ --force --cpp --es2only

