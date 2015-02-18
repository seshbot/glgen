# GLgen
A set of python scripts that convert the [Khronos OpenGL API registry](https://cvs.khronos.org/svn/repos/ogl/trunk/doc/registry/public/api/gl.xml) into a canonicalised Python model, which can then be serialised to various formats (currently JSON and C++ header/source files)

This project is used by [GLdoc](https://github.com/seshbot/gldoc) and [GL++](https://github.com/seshbot/glpp)

### Usage

See the <code>gencpp.bat</code> and <code>genjs.bat</code> for examples of usage.

    usage: gen.py [-h] [-p PATCHFILE] [-o OUTPUTDIR] [--force] [-j] [-c]
                  [--verify] [--es2only]
                  regfile
    
    positional arguments:
      regfile               XML registry file
    
    optional arguments:
      -h, --help            show this help message and exit
      -p PATCHFILE, --patchfile PATCHFILE
                            XML patch file
      -o OUTPUTDIR, --outputdir OUTPUTDIR
                            directory into which output files are dumped
      --force               force creation of output directory
      -j, --json
      -c, --cpp
      --verify
      --es2only

### TODO
 - doesnt process 'alias' commands (generally provided by extensions)
 - source command description and usage text from somewhere?
