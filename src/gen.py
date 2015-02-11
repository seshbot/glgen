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
  parser.add_argument('-j', '--json', action='store_true')
  parser.add_argument('-c', '--cpp', action='store_true')
  parser.add_argument('--verify', action='store_true')
  parser.add_argument('--es2only', action='store_true')
  parser.add_argument('regfile', help='XML registry file')

  args = parser.parse_args()

  genJson = args.json
  genCpp = args.cpp
  if not genCpp and not genJson:
    genJson = True
    genCpp = True

  inputfile = args.regfile # os.path.join(os.path.dirname(__file__), 'gl.xml')
  outputpath = args.outputdir
  if not os.path.exists(outputpath):
    if not args.force:
      print 'error: output path %s does not exist. Specify --force to force creation of this directory' % outputpath
      sys.exit(1)
    os.makedirs(outputpath)

  print 'parsing registry file %s' % inputfile
  xmltree       = etree.parse(inputfile)
  xmlregistry   = xmltree.getroot()

  features = parseXmlFeatures(xmlregistry)
  print '%d features found' % len(features)

  enums = parseXmlEnums(xmlregistry)
  print '%d enums found' % len(enums)

  groups = parseXmlGroups(xmlregistry, enums)
  print '%d groups found' % len(groups)

  commands = parseXmlCommands(xmlregistry)
  print '%d commands found' % len(commands)

  patchfile = args.patchfile
  if patchfile:
    print 'applying patches from file %s' % patchfile
    patch_xmltree       = etree.parse(patchfile)
    patch_xmlregistry   = patch_xmltree.getroot()

    patch_features = parseXmlFeatures(patch_xmlregistry)
    print '%d features found' % len(patch_features)

    patch_enums = parseXmlEnums(patch_xmlregistry)
    print '%d enums found' % len(patch_enums)

    patch_groups = parseXmlGroups(patch_xmlregistry, patch_enums)
    print '%d groups found' % len(patch_groups)

    patch_commands = parseXmlCommands(patch_xmlregistry)
    print '%d commands found' % len(patch_commands)

    features = patchEntities(features, patch_features)
    enums = patchEntities(enums, patch_enums)
    groups = patchEntities(groups, patch_groups)
    commands = patchEntities(commands, patch_commands)

  registry = Registry(features, enums, groups, commands, args.es2only)

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

  if genCpp:
    filename = os.path.join(outputpath, 'enums.h')
    print 'writing %s' % filename
    fp = open(filename, 'w')
    writeCppEnums(registry.coreGroups, fp)
    fp.close

    filename = os.path.join(outputpath, 'commands.h')
    print 'writing %s' % filename
    fp = open(filename, 'w')
    writeCppCommandsHeader(registry.coreCommands, fp)
    fp.close

    filename = os.path.join(outputpath, 'commands.cpp')
    print 'writing %s' % filename
    fp = open(filename, 'w')
    writeCppCommandsCpp(registry.coreCommands, fp)
    fp.close

