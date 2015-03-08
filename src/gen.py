#!/usr/bin/python
'''OpenGL registry parser'''

__author__    = 'Paul Cechner'
__license__   = 'Boost Software License, Version 1.0'
__copyright__ = '2015, Paul Cechner <at cechner.com>'
__version__   = '0.1'


import os
import sys
import re
import json

from registry.parsers import *
from registry.model import *
from registry.serializers import *

import xml.etree.cElementTree as etree

# see also https://github.com/AlexandreFournier/gl-spec-parser
# see also https://github.com/hpicgs/glbinding

# sys dir(sys)  dir()

# dictionary: DICT = { x: v1, y: v2}
#             for k in DICT.keys(): 

# func prog: my_new_list = filter(lambda x : re.match(my_re, x), my_list) # .sort()
# string: n = s.count('x')  s = s.replace('a', 'b')  s.startswith('aaa')
#         s = s[2:]  s = 'a %s' % mystr  '\n'.join(mystr)
#         'What is your {0}?  It is {1}.'.format(q, a)
# reversed(xrange(1,10,2))
# for k, v in knights.iteritems():


# TODO: extensions
# TODO: commands without 'features' are always 'aliases' ?
#  if so, create an 'aliases' collection and remove them from commands

# TODO: incorporate <groups ... type="bitmask> (verify it matches <param type=GLbitfield)
# TODO: resolve command return value enums (currently resolving to GLenum)
# TODO: incorporate <require profile="compatability|core|common"> ...

def checkDirExists(outputpath, force):
  if not os.path.exists(outputpath):
    if not force:
      print 'error: output path %s does not exist. Specify --force to force creation of this directory' % outputpath
      sys.exit(1)
    os.makedirs(outputpath)

def writeEntitiesToExistingFile(entities, varname, fp):
  fp.write('{ "%s": ' % varname)
  writeJson(entities, fp)
  fp.write('}')

def writeEntitiesToNewFile(entities, filename, varname):
  fp = open(filename, 'w')
  writePreludeToFile(fp)
  fp.write("var %s = " % varname)
  writeJson(entities, fp)
  fp.write(";\n")
  fp.close

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-p', '--patchfile', help='XML patch file')
  parser.add_argument('-o', '--outputdir', default='.', help='directory into which output files are dumped')
  parser.add_argument('--force', action='store_true', help='force creation of output directory')
  parser.add_argument('-i', '--includesubdir', help='sub-directory into which output header files are dumped')
  parser.add_argument('-s', '--sourcesubdir', help='sub-directory into which output source files are dumped')
  parser.add_argument('--namespace', default='gl', help='C++ namespace into which all symbols will be placed')
  parser.add_argument('-j', '--json', action='store_true')
  parser.add_argument('-c', '--cpp', action='store_true')
  parser.add_argument('--verify', action='store_true')
  parser.add_argument('--es2only', action='store_true')
  parser.add_argument('--gl2only', action='store_true')
  parser.add_argument('--synth', action='store_true', help='synthesise core functions from extension functions (experimental)')
  parser.add_argument('regfile', help='XML registry file')

  args = parser.parse_args()

  genJson = args.json
  genCpp = args.cpp
  if not genCpp and not genJson:
    genJson = True
    genCpp = True

  inputfile = args.regfile # os.path.join(os.path.dirname(__file__), 'gl.xml')
  outputpath = args.outputdir  

  checkDirExists(outputpath, args.force)

  print 'parsing registry file %s' % inputfile
  xmltree       = etree.parse(inputfile)
  xmlregistry   = xmltree.getroot()

  features = parseXmlFeatures(xmlregistry)
  print ' - %d features found' % len(features)

  extensions = parseXmlExtensions(xmlregistry)
  print ' - %d extensions found' % len(extensions)

  enums = parseXmlEnums(xmlregistry)
  print ' - %d enums found' % len(enums)

  groups = parseXmlGroups(xmlregistry, enums)
  print ' - %d groups found' % len(groups)

  commands = parseXmlCommands(xmlregistry)
  print ' - %d commands found' % len(commands)

  patchfile = args.patchfile
  if patchfile:
    print 'applying patches from file %s' % patchfile
    patch_xmltree       = etree.parse(patchfile)
    patch_xmlregistry   = patch_xmltree.getroot()

    patch_features = parseXmlFeatures(patch_xmlregistry)
    print ' - %d features found' % len(patch_features)

    patch_extensions = parseXmlExtensions(patch_xmlregistry)
    print ' - %d extensions found' % len(patch_extensions)

    patch_enums = parseXmlEnums(patch_xmlregistry)
    print ' - %d enums found' % len(patch_enums)

    patch_groups = parseXmlGroups(patch_xmlregistry, patch_enums)
    print ' - %d groups found' % len(patch_groups)

    patch_commands = parseXmlCommands(patch_xmlregistry)
    print ' - %d commands found' % len(patch_commands)

    features = patchEntities(features, patch_features)
    extensions = patchEntities(extensions, patch_extensions)
    enums = patchEntities(enums, patch_enums)
    groups = patchEntities(groups, patch_groups)
    commands = patchEntities(commands, patch_commands)

  getFilterApiName = lambda: "gles2" if args.es2only else "gl" if args.gl2only else None
  getFilterApiNumber = lambda: "2.0" if args.es2only or args.gl2only else None
  registry = Registry(features, extensions, enums, groups, commands, getFilterApiName(), getFilterApiNumber())

  apis = registry.apis if not getFilterApiName() else set([registry.apisByName[getFilterApiName()]])

  # if 'glBegin' not in registry.commandsByName:
  #   print 'COMMAND NOT FOUND!!!'
  # else:
  #   c = registry.commandsByName['glBegin']
  #   print 'glBegin features: %s' % (['%s:%s' % (f.api, f.number) for f in c.features])

  # print 'features: %s' % (['%s:%s' % (f.api, f.number) for f in registry.features])
  # for f in registry.features:
  #   if f.api.name != 'gl' or f.number != '2.0':
  #     continue
  #   print ' %s commands: %s' % (f.name, sorted([c.name for c in f.requiredCommands]))
  # sys.exit(1)

  angleExtensions = set([
    'GL_OES_element_index_uint',
    'GL_OES_get_program_binary',
    'GL_OES_packed_depth_stencil',
    'GL_OES_rgb8_rgba8',
    'GL_OES_standard_derivatives',
    'GL_OES_texture_half_float',
    'GL_OES_texture_half_float_linear',
    'GL_OES_texture_float',
    'GL_OES_texture_float_linear',
    'GL_OES_texture_npot',
    'GL_EXT_occlusion_query_boolean',
    'GL_EXT_read_format_bgra',
    'GL_EXT_robustness',
    'GL_EXT_texture_compression_dxt1',
    'GL_EXT_texture_filter_anisotropic',
    'GL_EXT_texture_format_BGRA8888',
    'GL_EXT_texture_storage',
    'GL_ANGLE_depth_texture',
    'GL_ANGLE_framebuffer_blit',
    'GL_ANGLE_framebuffer_multisample',
    'GL_ANGLE_instanced_arrays',
    'GL_ANGLE_pack_reverse_row_order',
    'GL_ANGLE_texture_compression_dxt3',
    'GL_ANGLE_texture_compression_dxt5',
    'GL_ANGLE_texture_usage',
    'GL_ANGLE_translated_shader_source',
    'GL_NV_fence',

    'EGL_EXT_create_context_robustness',
    'EGL_ANGLE_d3d_share_handle_client_buffer',
    'EGL_ANGLE_query_surface_pointer',
    'EGL_ANGLE_software_display',
    'EGL_ANGLE_surface_d3d_texture_2d_share_handle',
    'EGL_NV_post_sub_buffer',]
  )


  # # exploring extensions

  # hashapis = lambda apis: ','.join(map(lambda a: a.name, apis))
  # apiGroups = {hashapis(e.apis) for e in registry.extensions}
  # for apis in apiGroups:
  #   es = [e for e in registry.extensions if hashapis(e.apis) == apis]
  #   print 'extensions for %s' % apis
  #   for e in es:
  #     angleIndicator = 'x' if e.name in angleExtensions else ''
  #     print ' - %s %s' % (e.name, angleIndicator)

  # allExtensionNames = {e.name for e in registry.extensions}

  # unrecognisedAngleExtensions = angleExtensions - allExtensionNames

  # print 'UNRECOGNISED ANGLE EXTENSIONS:'
  # for name in unrecognisedAngleExtensions:
  #   print name

  # es2Api = next(api for api in registry.apis if api.name == 'gles2')
  # print '\n\nall gles2 extensions:'
  # for e in es2Api.extensions:
  #   angleIndicator = 'x' if e.name in angleExtensions else ''
  #   print ' - %s %s' % (e.name, angleIndicator)

  # sys.exit(1)

  if args.verify:

    #
    # verify all groups referenced by commands are defined
    #

    unlinkedgroups = {}
    for p in registry.coreParameters:
      shouldgroupname = p.data.groupString
      actualgroupname = p.group.name if p.group else ''
      if shouldgroupname and shouldgroupname != actualgroupname:
        if shouldgroupname not in unlinkedgroups:
          unlinkedgroups[shouldgroupname] = []
        unlinkedgroups[shouldgroupname].append(p)

    gles2 = registry.findfeature('gles2', '2.0')

    if len(unlinkedgroups) > 0:
      print('WARNING: unlinked groups referenced by parameters:')

      commandgroups = {}

      for g, ps in unlinkedgroups.iteritems():
        paramnames = map(lambda p: '%s:%s' % (p.name, p.type), ps)
        commandnames = {c.name for p in ps for c in p.commands if gles2 in c.features}
        for n in commandnames:
          if n not in commandgroups:
            commandgroups[n] = set()
          commandgroups[n].add(g)
        print('%s (%s)' % (g, ','.join(paramnames)))

      print('\nby command:')
      groupcommands = {}
      for g, ps in unlinkedgroups.iteritems():
        commands = {c for p in ps for c in p.commands if gles2 in c.features}
        groupcommands[g] = commands

      for g, cs in sorted(groupcommands.iteritems(), key=lambda tup: len(tup[1])):
        print('%s (%s)' % (g, ','.join([c.name for c in cs])))

      print('\nfrom commands:')
      for command, groups in sorted(commandgroups.iteritems(), key=lambda tup: len(tup[1])):
        print('%s (%s)' % (command, ','.join(groups)))

    # print 'verifying enum groups are consistent...'
    # for e in registry.enums:
    #   if len(e.groups) > 1:
    #     print '  - enum %s is a member of groups %s' % (e.name, [g.name for g in e.groups])

    # print 'verifying features have sensible enums...'
    # for f in registry.features:
    #   enum_names = {e.name for e in f.requiredEnums}
    #   print '  - feature %s has %s enums' % (f.name, len(enum_names))
    #   flatten = lambda ll: reduce(lambda a, b: a | b, ll, set())
    #   expanded_enums = flatten([g.enums for e in f.requiredEnums for g in e.groups])
    #   expanded_enum_names = {e.name for e in expanded_enums}
    #   print '               should have %s' % len(expanded_enum_names)
    #   diff = expanded_enum_names - enum_names
    #   print '               diff: %s' % diff

  # TODO: extensions
  # TODO: aliases
  # TODO: investigate '<require comment="Reuse ARB_copy_buffer">' etc

  if genJson:
    print 'writing js files'
    writeEntitiesToNewFile(registry.features, os.path.join(outputpath, 'features.js'), 'GL_REGISTRY_FEATURES')
    writeEntitiesToNewFile(registry.coreEnums, os.path.join(outputpath, 'enums.js'), 'GL_REGISTRY_ENUMS')
    writeEntitiesToNewFile(registry.coreGroups, os.path.join(outputpath, 'groups.js'), 'GL_REGISTRY_GROUPS')
    writeEntitiesToNewFile(registry.coreCommands, os.path.join(outputpath, 'commands.js'), 'GL_REGISTRY_COMMANDS')
    writeEntitiesToNewFile(registry.coreParameters, os.path.join(outputpath, 'parameters.js'), 'GL_REGISTRY_PARAMETERS')

    # NOTE: we normalise command parameters into another file because some commands are reused many times
    # e.g., 'GLuint index' is used by 416 commands

    print 'writing json file'
    fp = open(os.path.join(outputpath, 'data.json'), 'w')
    writePreludeToFile(fp)
    writeEntitiesToExistingFile(registry.features, 'features', fp)
    writeEntitiesToExistingFile(registry.coreEnums, 'enums', fp)
    writeEntitiesToExistingFile(registry.coreGroups, 'groups', fp)
    writeEntitiesToExistingFile(registry.coreCommands, 'commands', fp)
    writeEntitiesToExistingFile(registry.coreParameters, 'parameters', fp)
    fp.close

  GLES2_HEADERS = ['glad/glad.h']
  GL2_HEADERS = ['glad/glad.h']

  if genCpp:
    namespace = args.namespace
    includeSubdir = args.includesubdir if args.includesubdir else 'include'
    sourceSubdir = args.sourcesubdir if args.sourcesubdir else 'src'
    headerpath = os.path.join(outputpath, includeSubdir, namespace)
    sourcepath = os.path.join(outputpath, sourceSubdir, namespace)

    def getHeaderInclude(headerfile):
      filename = os.path.join(headerpath, headerfile)
      # assumes header output file paths will always have an 'include/' in the string
      return re.search('include/(.*)', filename.replace('\\', '/')).group(1)

    print 'writing header files to %s' % headerpath
    print 'writing source files to %s' % sourcepath

    checkDirExists(headerpath, args.force)
    checkDirExists(sourcepath, args.force)

    filename = os.path.join(headerpath, 'enums.h')
    print 'writing %s' % filename
    fp = open(filename, 'w')
    writeCppEnums(registry.coreGroups, fp, namespace, 'ENUMS__H')
    fp.close

    filename = os.path.join(headerpath, 'extensions_enums.h')
    print 'writing %s' % filename
    fp = open(filename, 'w')
    writeCppEnums(registry.extGroups, fp, namespace, 'EXTENSIONS_ENUMS__H')
    fp.close

    filename = os.path.join(headerpath, 'commands.h')
    print 'writing %s' % filename
    fp = open(filename, 'w')
    writeCppCommandsHeader(registry.coreCommands, fp, namespace, ['../types.h', 'enums.h'], 'COMMANDS__H')
    fp.close

    filename = os.path.join(sourcepath, 'commands.cpp')
    print 'writing %s' % filename
    fp = open(filename, 'w')
    writeCppCommandsCpp(registry.coreCommands, fp, namespace, [], GLES2_HEADERS + ['string.h', getHeaderInclude('commands.h')])
    fp.close

    filename = os.path.join(headerpath, 'extensions.h')
    print 'writing %s' % filename
    fp = open(filename, 'w')
    writeCppExtCommandsHeader(registry.extCommands, fp, namespace, ['../types.h', 'enums.h', 'extensions_enums.h'], 'EXTENSIONS__H')
    fp.close

    filename = os.path.join(sourcepath, 'extensions.cpp')
    print 'writing %s' % filename
    fp = open(filename, 'w')
    writeCppExtCommandsCpp(apis, registry.extCommands, fp, namespace, ['angle_extension_macros.h'], GLES2_HEADERS + ['stdexcept', getHeaderInclude('extensions.h')])
    fp.close

    # filename = os.path.join(headerpath, 'extension_synth.h')
    # print 'writing %s' % filename
    # fp = open(filename, 'w')
    # writeCppExtSynthCommandsHeader(registry.synthExtCommandsByBaseCommand, fp, namespace, ['../types.h', 'enums.h', 'extensions_enums.h'], 'EXTENSION_SYNTH__H')
    # fp.close

    # filename = os.path.join(sourcepath, 'extension_synth.cpp')
    # print 'writing %s' % filename
    # fp = open(filename, 'w')
    # writeCppExtSynthCommandsCpp(registry.synthExtCommandsByBaseCommand, fp, namespace, ['angle_extension_macros.h'], ['stdexcept', 'GLES2/gl2.h', 'GLES2/gl2ext.h', 'glpp/gles2/extensions.h'])
    # fp.close

  sys.exit(0)
