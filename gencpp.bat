@echo off

xcopy /E /Y assets\cpp\include\*.* build\lib\include\glpp\
xcopy /E /Y assets\cpp\src\common\*.* build\lib\src\gl2\
xcopy /E /Y assets\cpp\src\common\*.* build\lib\src\gles2\
xcopy /E /Y assets\cpp\src\gl2\*.* build\lib\src\gl2\
xcopy /E /Y assets\cpp\src\gles2\*.* build\lib\src\gles2\

REM GLES2 interface
python src/gen.py assets/gl.xml -p assets/gl-patch.xml -o build/lib/ --includesubdir include/glpp --sourcesubdir src --namespace gles2 --force --cpp --es2only
REM GL2 interface
python src/gen.py assets/gl.xml -p assets/gl-patch.xml -o build/lib/ --includesubdir include/glpp --sourcesubdir src --namespace gl2 --force --cpp --gl2only

REM ANGLE extensions interface
python src/gen.py assets/gl.xml -p assets/gl-patch.xml -o build/lib/ --includesubdir include/glpp --sourcesubdir src --namespace "gles2:angle" --force --cpp --es2only --extensionsimportfile assets/extensions_angle_dx11.txt --extensionsoutputfilename extensions
REM OSX extensions interface
python src/gen.py assets/gl.xml -p assets/gl-patch.xml -o build/lib/ --includesubdir include/glpp --sourcesubdir src --namespace "gl2:osx" --force --cpp --gl2only --extensionsimportfile assets/extensions_osx.txt --extensionsoutputfilename extensions
