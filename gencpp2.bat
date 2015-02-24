@echo off

if not exist build\* mkdir build
if not exist build\lib\* mkdir build\lib
if not exist build\lib\include\* mkdir build\lib\include
if not exist build\lib\include\glpp\* mkdir build\lib\include\glpp
if not exist build\lib\src\* mkdir build\lib\src
if not exist build\lib\src\gles2\* mkdir build\lib\src\gles2

copy assets\cpp\include\*.* ..\glpp\include\glpp\
copy assets\cpp\src\*.* ..\glpp\src\gles2\

python src/gen.py assets/gl.xml -p assets/gl-patch.xml -o ../glpp/ --includesubdir include/glpp --sourcesubdir src --namespace gles2 --force --cpp --es2only
