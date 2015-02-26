import json
import time
import sys

#
# json routines
#

PROJECT_NAME = 'glgen'
PROJECT_REPO = 'https://github.com/seshbot/glgen'

JSON_PRELUDE = """\
// This file was autogenerated by %s (%s) on %s
// Command line: %s
""" % (PROJECT_NAME, PROJECT_REPO, time.strftime('%Y-%m-%d'), ' '.join(sys.argv))

def writePreludeToFile(fp):
  fp.write(JSON_PRELUDE)

def writeJson(entities, fp):
  fp.write("[\n")
  for entity in entities:
    data = entity.toDictionary()
    #json.dump(data, fp, indent=2, separators=(',', ': '))
    json.dump(data, fp)
    fp.write(',\n')
  fp.write("]")


#
# C++ routines
#

# template patterns:
#  ${DATE} - generation date
#  ${HEADER_GUARD} - to be used in header guard
#  ${CONTENTS} - entire contents of the file
HEADER_TEMPLATE = """\
/**
 * This file was autogenerated by ${PROJECT_NAME} (${PROJECT_REPO}) on ${TIME}
 * Command line: ${COMMANDLINE}
 */

#ifndef ${HEADER_GUARD}
#define ${HEADER_GUARD}

{{'\\n'.join(['#include <%s>' % h for h in SYSTEM_HEADERS]) if 'SYSTEM_HEADERS' in locals() else ''}}
{{'\\n'.join(['#include "%s"' % h for h in LOCAL_HEADERS]) if 'LOCAL_HEADERS' in locals() else ''}}

namespace ${NAMESPACE} {
${CONTENT}
} // namespace ${NAMESPACE}

#endif // #ifndef ${HEADER_GUARD}
"""

CPP_TEMPLATE = """\
/**
 * This file was autogenerated by ${PROJECT_NAME} (${PROJECT_REPO}) on ${TIME}
 * Command line: ${COMMANDLINE}
 */

{{'\\n'.join(['#include <%s>' % h for h in SYSTEM_HEADERS]) if 'SYSTEM_HEADERS' in locals() else ''}}
{{'\\n'.join(['#include "%s"' % h for h in LOCAL_HEADERS]) if 'LOCAL_HEADERS' in locals() else ''}}

namespace ${NAMESPACE} {
${CONTENT}
}
"""

ENUM_CLASS_TEMPLATE = """\
  enum class ${NAME} : unsigned int {
${CONTENT}  };
"""

BITMASK_ENUM_CLASS_TEMPLATE = """\
  enum class ${NAME} : unsigned int {
${CONTENT}  };
  CREATE_ENUM_BITMASK_TYPE(${MASKTYPE_NAME}, ${NAME})
"""


ENUM_VALUE_TEMPLATE = """\
    ${NAME} = ${VALUE},
"""

COMMAND_PARAMETER_TEMPLATE = "${TYPE} ${NAME}"
COMMAND_PROTOTYPE_TEMPLATE = """\
    ${RETURN_TYPE} ${NAME}(${PARAMETER_LIST});
"""

EXT_COMMAND_PROTOTYPE_TEMPLATE = """\
   /**
    * Required by extensions:
{{'\\n'.join(['    *  - %s (%s)' % (e.name, ','.join(map(lambda api: api.name, e.apis))) for e in REQUIRED_EXTENSIONS])}}
    */
    ${RETURN_TYPE} ${NAME}(${PARAMETER_LIST});
"""

COMMAND_IMPLEMENTATION_TEMPLATE = """\
    ${RETURN_TYPE} ${NAME}(${PARAMETER_LIST}) {
      {{''.join(['%s %s_; ' % (p.baseType, p.name) for p in params if p.isPointer and p.group])}}
      ${MAYBE_RETURN}${STATIC_CAST_BEGIN}${GL_NAME}(${ARGUMENT_LIST})${STATIC_CAST_END};
      {{''.join(['*%s = static_cast<%s>(%s_); ' % (p.name, param_types[p.name], p.name) for p in params if p.isPointer and p.group])}}
    }
"""

EXT_COMMAND_IMPLEMENTATION_TEMPLATE = """\
    ${RETURN_TYPE} ${NAME}(${PARAMETER_LIST}) {
#if {{' || '.join([e.name for e in REQUIRED_EXTENSIONS])}}    
      {{''.join(['%s %s_; ' % (p.baseType, p.name) for p in params if p.isPointer and p.group])}}
      ${MAYBE_RETURN}${STATIC_CAST_BEGIN}${GL_NAME}(${ARGUMENT_LIST})${STATIC_CAST_END};
      {{''.join(['*%s = static_cast<%s>(%s_); ' % (p.name, param_types[p.name], p.name) for p in params if p.isPointer and p.group])}}
#else
      throw std::runtime_error("OpenGL command '${GL_NAME}' not available on this platform");
#endif
    }
"""


GET_CORE_PROC_ADDRESS_DECLARATION_TEMPLATE = """\
    // some extension managers use a 'getProcAddress()' function to load core functions 
    // although getProcAddress() functions are only meant to be used to load extensions.
    gl::gl_proc get_core_proc_address(const char* proc_name);

    // ANGLE's eglGetProcAddress() only returns pointers to extension functions, this function
    // behaves the way GLAD would expect it to
    gl::gl_proc get_proc_address(get_gl_proc_func get_extension_proc, const char* proc_name);

    bool is_core_proc(const char* proc_name);

"""

GET_CORE_PROC_ADDRESS_DEFINITION_TEMPLATE = """\
  namespace {
     struct proc_name_address_t {
        const char * name;
        gl::gl_proc address;
     };

     gl::gl_proc get_proc_address_impl(const char* proc_name) {
        static const proc_name_address_t proc_info[] = {
          {{'\\n          '.join(['{ "%s", reinterpret_cast<gl::gl_proc>(%s) },' % (c.name, c.name) for c in commands])}}
        };

        for (auto & inf : proc_info) {
          if (strcmp(proc_name, inf.name) == 0)
            return inf.address;
        }
        
        return nullptr;
     }
  }

  gl::gl_proc get_core_proc_address(const char* proc_name) {
    return get_proc_address_impl(proc_name);
  }

  gl::gl_proc get_proc_address(get_gl_proc_func get_extension_proc, const char* proc_name) {
    if (is_core_proc(proc_name)) return get_core_proc_address(proc_name);
    return get_extension_proc(proc_name);
  }

  bool is_core_proc(const char* proc_name) {
    return nullptr != get_proc_address_impl(proc_name);
  }

"""

import re

def compileTemplate(template, vars):
  vars['time'] = time.strftime('%Y-%m-%d')
  vars['commandline'] = ' '.join(sys.argv)
  vars['PROJECT_NAME'] = PROJECT_NAME
  vars['PROJECT_REPO'] = PROJECT_REPO
  compiled = template

  # match {{.*}} and capture expression
  eval_expr_pattern = re.compile('{{(.*?)}}', re.IGNORECASE)

  def evalExpression(match):
    expr = match.group(1)
    return eval(expr, {}, vars)

  compiled = eval_expr_pattern.sub(evalExpression, compiled)

  # match '${.*}' and capture variable name
  subst_var_pattern = re.compile('\${(.*?)}', re.IGNORECASE)
  lowervars = {name.lower(): val for name, val in vars.iteritems()}

  def substituteVar(match):
    var = match.group(1).lower()
    return lowervars[var] if var in lowervars else match.group()

  return subst_var_pattern.sub(substituteVar, compiled)

#
# name conversion utilities
#

_CAMEL_CASE_TO_SNAKE_CASE_REGEX_ = re.compile('((?<=[a-z])[A-Z0-9]|(?!^)[A-Z](?=[a-z]))')
_TYPE_NAME_REGEX_ = re.compile('(const[ ]+)?([^ *]+)([ ]*\*)?') # (const )(typename)( *)

def toTypeName(v):
  exceptions = {'void'} # do not modify these types

  prevTypename = _TYPE_NAME_REGEX_.match(v).group(2)
  newTypename = prevTypename[2:] if prevTypename.startswith('GL') else prevTypename
  newTypename = 'gl::%s_t' % newTypename if newTypename not in exceptions else newTypename
  return v.replace(prevTypename, newTypename)

def getGroupEnumName(group):
  enumname = _CAMEL_CASE_TO_SNAKE_CASE_REGEX_.sub(r'_\1', group.name).lower() + '_t'
  if group.isBitmask:
    return re.sub('(_mask)?_t$', '_flags_t', enumname)
  return enumname

def getGroupMasktypeName(group):
  enumname = _CAMEL_CASE_TO_SNAKE_CASE_REGEX_.sub(r'_\1', group.name).lower() + '_t'
  return re.sub('(_mask)?_t$', '_mask_t', enumname)

def toFunctionName(v):
  tmp = v[2:] if v.startswith('gl') else v
  return _CAMEL_CASE_TO_SNAKE_CASE_REGEX_.sub(r'_\1', tmp).lower()

def getTypeString(param):
  def typeNameToUse():
    if param.group:
      enumName = getGroupEnumName(param.group)
      if param.type == 'GLbitfield':
        return 'gl::bitmask<%s>' % enumName
      return enumName
    return toTypeName(param.baseType)

  newTypename = typeNameToUse()

  return param.type.replace(param.baseType, newTypename)


#
# serialisation procedures
#

def writeCppEnums(groups, fp, namespace, headerGuard):
  def compileEnum(enum):
    def toEnumValue(v):
      reserved_words = ['return', 'bool', 'true', 'false', 'byte', 'long', 'int', 'short', 'char', 'float', 'double', 'unsigned_byte', 'unsigned_short', 'unsigned_int']
      val = v[3:] if v.startswith('GL_') else v
      val = val.lower()
      val = val + '_' if val in reserved_words else val
      return val
    vars = {'name' : toEnumValue(enum.name), 'value': enum.value}
    return compileTemplate(ENUM_VALUE_TEMPLATE, vars)

  # todo: incorporate 'bitmask' tag from enum collection?
  def compileGroup(group):
    content = ''.join([compileEnum(e) for e in sorted(group.enums, key=lambda e: e.value)])
    vars = group.toDictionary()
    glname = vars['name']
    vars['content'] = content
    vars['name'] = getGroupEnumName(group)
    vars['masktype_name'] = getGroupMasktypeName(group)
    template = BITMASK_ENUM_CLASS_TEMPLATE if group.isBitmask else ENUM_CLASS_TEMPLATE
    return compileTemplate(template, vars)

  content = '\n'.join([compileGroup(g) for g in groups])

  vars = {
    'namespace': namespace,
    'content': content,
    'header_guard': headerGuard,
  }

  fp.write(compileTemplate(HEADER_TEMPLATE, vars))


def writeCppCommandsHeader(commands, fp, namespace, headers, headerGuard):
  def compileParameter(param):
    typename = getTypeString(param)
    vars = {'type': typename, 'name': param.name}
    return compileTemplate(COMMAND_PARAMETER_TEMPLATE, vars)

  def compileCommand(command):
    parameters = ', '.join([compileParameter(p) for p in command.parameters])
    vars = command.toDictionary()
    vars['name'] = toFunctionName(vars['name'])
    vars['parameter_list'] = parameters
    vars['return_type'] = toTypeName(command.returntype) if not command.returngroup else getGroupEnumName(command.returngroup)
    return compileTemplate(COMMAND_PROTOTYPE_TEMPLATE, vars)

  # content = compileTemplate(GET_CORE_PROC_ADDRESS_DECLARATION_TEMPLATE, {'commands': commands})
  content = '\n'.join([compileCommand(c) for c in commands])

  vars = {
    'namespace': namespace,
    'content': content,
    'header_guard': headerGuard,
    'LOCAL_HEADERS': headers,
  }

  fp.write(compileTemplate(HEADER_TEMPLATE, vars))

def writeCppCommandsCpp(commands, fp, namespace, headers, sysHeaders):
  def compileParameter(param):
    typename = getTypeString(param)
    vars = {'type': typename, 'name': param.name}
    return compileTemplate(COMMAND_PARAMETER_TEMPLATE, vars)
  def compileArgument(param):
    paramName = '&%s_' % param.name if param.isPointer and param.group else param.name
    shouldCast = param.group and not param.isPointer
    if shouldCast:
      if param.type == 'GLbitfield':
        paramName = paramName + '.value' 
      return 'static_cast<%s>(%s)' % (param.type, paramName)
    return paramName

  def compileCommand(command):
    parameters = ', '.join([compileParameter(p) for p in command.parameters])
    arguments = ', '.join([compileArgument(p) for p in command.parameters])
    vars = command.toDictionary()
    vars['gl_name'] = vars['name']
    vars['name'] = toFunctionName(vars['name'])
    vars['parameter_list'] = parameters
    vars['argument_list'] = arguments
    vars['return_type'] = toTypeName(command.returntype) if not command.returngroup else getGroupEnumName(command.returngroup)
    vars['maybe_return'] = 'return ' if vars['return_type'] != 'void' else ''
    vars['static_cast_begin'] = 'static_cast<%s>(' % vars['return_type'] if command.returngroup else ''
    vars['static_cast_end'] = ')' if command.returngroup else ''
    vars['params'] = command.parameters
    vars['param_types'] = {p.name: toTypeName(p.baseType) if not p.group else getGroupEnumName(p.group) for p in command.parameters}
    return compileTemplate(COMMAND_IMPLEMENTATION_TEMPLATE, vars)

  #content = compileTemplate(GET_CORE_PROC_ADDRESS_DEFINITION_TEMPLATE, {'commands': commands})
  content = '\n'.join([compileCommand(c) for c in commands])

  vars = {
    'namespace': namespace,
    'content': content,
    'LOCAL_HEADERS': headers,
    'SYSTEM_HEADERS': sysHeaders
  }

  fp.write(compileTemplate(CPP_TEMPLATE, vars))

def writeCppExtCommandsHeader(commands, fp, namespace, headers, headerGuard):
  def compileParameter(param):
    typename = getTypeString(param)
    vars = {'type': typename, 'name': param.name}
    return compileTemplate(COMMAND_PARAMETER_TEMPLATE, vars)

  def compileCommand(command):
    parameters = ', '.join([compileParameter(p) for p in command.parameters])
    vars = command.toDictionary()
    vars['REQUIRED_EXTENSIONS'] = command.extensions
    vars['name'] = toFunctionName(vars['name'])
    vars['parameter_list'] = parameters
    vars['return_type'] = toTypeName(command.returntype) if not command.returngroup else getGroupEnumName(command.returngroup)
    return compileTemplate(EXT_COMMAND_PROTOTYPE_TEMPLATE, vars)

  commandsByExtensions = {}
  for c in commands:
    sortedExtensionNames = sorted(list(map(lambda e: e.name, c.extensions)))
    extensionNamesHash = ', '.join(sortedExtensionNames)
    if extensionNamesHash not in commandsByExtensions:
      commandsByExtensions[extensionNamesHash] = []
    commandsByExtensions[extensionNamesHash].append(c)

  sortedCommands = [c for cs in commandsByExtensions.values() for c in cs]

  content = '\n'.join([compileCommand(c) for c in sortedCommands])

  vars = {
    'namespace': namespace,
    'content': content,
    'header_guard': headerGuard,
    'LOCAL_HEADERS': headers,
  }

  fp.write(compileTemplate(HEADER_TEMPLATE, vars))

def writeCppExtCommandsCpp(commands, fp, namespace, headers, sysHeaders):
  def compileParameter(param):
    typename = getTypeString(param)
    vars = {'type': typename, 'name': param.name}
    return compileTemplate(COMMAND_PARAMETER_TEMPLATE, vars)
  def compileArgument(param):
    paramName = '&%s_' % param.name if param.isPointer and param.group else param.name
    shouldCast = param.group and not param.isPointer
    if shouldCast:
      if param.type == 'GLbitfield':
        paramName = paramName + '.value' 
      return 'static_cast<%s>(%s)' % (param.type, paramName)
    return paramName

  def compileCommand(command):
    parameters = ', '.join([compileParameter(p) for p in command.parameters])
    arguments = ', '.join([compileArgument(p) for p in command.parameters])
    vars = command.toDictionary()
    vars['REQUIRED_EXTENSIONS'] = command.extensions
    vars['gl_name'] = vars['name']
    vars['name'] = toFunctionName(vars['name'])
    vars['parameter_list'] = parameters
    vars['argument_list'] = arguments
    vars['return_type'] = toTypeName(command.returntype) if not command.returngroup else getGroupEnumName(command.returngroup)
    vars['maybe_return'] = 'return ' if vars['return_type'] != 'void' else ''
    vars['static_cast_begin'] = 'static_cast<%s>(' % vars['return_type'] if command.returngroup else ''
    vars['static_cast_end'] = ')' if command.returngroup else ''
    vars['params'] = command.parameters
    vars['param_types'] = {p.name: toTypeName(p.baseType) for p in command.parameters}
    return compileTemplate(EXT_COMMAND_IMPLEMENTATION_TEMPLATE, vars)

  content = '\n'.join([compileCommand(c) for c in commands])

  vars = {
    'namespace': namespace,
    'content': content,
    'LOCAL_HEADERS': headers,
    'SYSTEM_HEADERS': sysHeaders
  }

  fp.write(compileTemplate(CPP_TEMPLATE, vars))
