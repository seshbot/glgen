@echo off

xcopy /E /Y assets\cpp\include\*.* ..\glpp\include\glpp\
xcopy /E /Y assets\cpp\src\common\*.* ..\glpp\src\gl2\
xcopy /E /Y assets\cpp\src\common\*.* ..\glpp\src\gles2\
xcopy /E /Y assets\cpp\src\gl2\*.* ..\glpp\src\gl2\
xcopy /E /Y assets\cpp\src\gles2\*.* ..\glpp\src\gles2\

start /b python src/gen.py assets/gl.xml -p assets/gl-patch.xml -o ../glpp/ --includesubdir include/glpp --sourcesubdir src --namespace gles2 --force --cpp --es2only --synth
start /b python src/gen.py assets/gl.xml -p assets/gl-patch.xml -o ../glpp/ --includesubdir include/glpp --sourcesubdir src --namespace gl2 --force --cpp --gl2only
