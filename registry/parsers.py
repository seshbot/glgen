#
# XML info
#

class FeatureXml:
  def __init__(self, xml):
    self.api = xml.attrib["api"]

    self.name   = xml.attrib["name"]   # e.g., GL_VERSION_1_1
    self.number = xml.attrib["number"] # e.g., 1.1

    self.major  = int(self.number[-3:-2])
    self.minor  = int(self.number[-1:])

    self.requireComments   = []

    self.reqEnumStrings    = []
    self.reqCommandStrings = []

    self.remEnumStrings    = []
    self.remCommandStrings = []

    for require in xml.findall("require"):
      if "comment" in require.attrib:
        self.requireComments.append(require.attrib["comment"])

      for child in require:
        if child.tag == "enum":
          self.reqEnumStrings.append(child.attrib["name"])
        elif child.tag == "command":
          self.reqCommandStrings.append(child.attrib["name"])
        # TODO: log unexpected child

    for remove in xml.findall("remove"):
      for child in remove:
        if child.tag == "enum":
          self.remEnumStrings.append(child.attrib["name"])
        elif child.tag == "command":
          self.remCommandStrings.append(child.attrib["name"])
        # TODO: log unexpected child

  def __str__(self):
    return "Feature (%s:%s.%s)" % (self.api, self.major, self.minor)

  def __lt__(self, other):
    if not other:
      return False
    else:
      return self.major < other.major or (self.major == other.major and self.minor < other.minor)

  def __ge__(self, other):
    if not other:
      return False
    else:
      return self.major > other.major or (self.major == other.major and self.minor >= other.minor)

class EnumXml:
  def __init__(self, xml, groupString, groupType):
    self.name  = xml.attrib["name"]
    self.value = xml.attrib["value"]
    self.comment = xml.attrib["comment"] if "comment" in xml.attrib else None
    self.type  = "GLenum"

    self.aliasString = ""
    self.alias = None

    # an enum group is, if defined, defined specifically for an enum
    # but the enum itself might be reused by other groups as well.
    self.groups = set()
    self.groupString = None # ToDo: only supported for GLbitfield for now

    self.aliasString = xml.attrib.get("alias", None)

    if groupString == "SpecialNumbers":
      self.type = self._translateType(xml.attrib.get("type", ""), self.name)
    elif groupType == "bitmask":
      self.type = "GLbitfield"
      self.groupString = groupString

  def __str__(self):
    return "Enum(%s, %s)" % (self.name, self.value)

  def __lt__(self, other):
    return self.value < other.value or (self.value == other.value and self.name < other.name)

  def _translateType(self, t, name):
    if name in [ "GL_TRUE", "GL_FALSE" ]:
      return "GLboolean"

    return { "u" : "GLuint", "ull" : "GLuint64"    }.get(t, "GLenum")


class GroupXml:    
  def __init__(self, xml):
    # TODO: incorporate 'type' (e.g., bitmask) from enum collection (not group)
    
    self.enumStrings = []

    if isinstance(xml, str):
      self.name = xml
      return

    self.name = xml.attrib["name"]
    for enum in xml.iter("enum"):
      self.enumStrings.append(enum.attrib["name"])

  def __str__(self):
    return "Group(%s, %s)" % (self.name, str(len(self.enumStrings)))
  
  def __lt__(self, other):
    return self.name < other.name
    

class ParameterXml:
  _exceptions = ["GetProcAddress", "near", "far"]

  def __init__(self, xml):
    self.name = xml.find("name").text

    # check for additional params
    if list(xml.itertext())[-1] != self.name:
      print(" WARNING: unexpected parameter format for " + self.name)

    self.type = " ".join([t.strip() for t in xml.itertext()][:-1]).strip()

    if self.name in self._exceptions:
      self.name += "_"

    if self.type.startswith("struct "):
      self.type = self.type[7:]

    self.groupString = xml.attrib.get("group", None)

    # must go last
    self.hash = hash(str(self))

  def __str__(self):
    if self.groupString != None:
      return "%s %s" % (self.groupString, self.name)
    else:
      return "%s %s" % (self.type, self.name)

  def __lt__(self, other):
    return self.hash < other.hash


class CommandXml:
  def __init__(self, xml):
    # <command>
    #     <proto>void <name>glActiveTextureARB</name></proto>
    #     <param group="TextureUnit"><ptype>GLenum</ptype> <name>texture</name></param>
    #     <alias name="glActiveTexture"/>
    #     <glx type="render" opcode="197"/>
    # </command>
    proto = xml.find("proto")

    self.name       = proto.find("name").text
    self.returntype = " ".join([t.strip() for t in proto.itertext()][:-1]).strip()

    self.params = []

    for param in xml.iter("param"):
      self.params.append(ParameterXml(param))
    
  def __str__(self):
    return "%s %s ( %s )" % (self.returntype, self.name, ", ".join([str(p) for p in self.params]))

  def __lt__(self, other):
    return self.name < other.name

#
# XML parsing
#

def parseXmlFeatures(xml):
  features = [FeatureXml(f) for f in xml.iter("feature")]
  return sorted(features)

def parseXmlEnums(xml):
  enums = set()

  for E in xml.iter("enums"):
    groupString = E.attrib.get("group", None)
    groupType   = E.attrib.get("type", None)

    for enum in E.findall("enum"):
      enums.add(EnumXml(enum, groupString, groupType))

  return sorted(enums)

def parseXmlGroups(xml, enums):
  groups = []
  groupsByName = dict()
  
  for G in xml.iter("groups"):
    for g in G.iter("group"):
      group = GroupXml(g)
      groups.append(group)
      groupsByName[group.name] = group
      for e in g.iter("enum"):
        group.enumStrings.append(e.attrib["name"])

  # if groups are not listed in groups section 
  # they can be implicitly specified by enums

  for enum in enums:
    _createGroup_ifImplicit(groups, groupsByName, enum)

  return sorted(groups)

def parseXmlCommands(xml):
  commands = [CommandXml(c) for cs in xml.iter("commands") for c in cs.iter("command")]
  return sorted(commands)

#
# patching entities
#
def patchEntities(origEntities, patchEntities):
  if len(patchEntities) == 0:
    return origEntities

  newEntities = origEntities
  newEntityIdxByName = {e.name: idx for idx, e in enumerate(newEntities)}

  for e in patchEntities:
    if e.name in newEntityIdxByName:
      # replace existing entity
      newEntities[newEntityIdxByName[e.name]] = e
    else:
      newEntities.append(e)

  return newEntities

# TODO enum rules:
# (1) no comment attribute exists for <enum> starting with "Not an API enum. ..."
# (2) at least one feature or extension of the requested api requires the enum of requested api
# (3) if the enum has a group and at least one command has a parameter of that group


#
# helper functions
#

def _createGroup_ifImplicit(groups, groupsByName, enum):
    name = enum.groupString

    if name is None:
        return

    if name not in groupsByName:
        group = GroupXml(name)
        groups.append(group)

        groupsByName[name] = group

    groupsByName[name].enumStrings.append(enum.name)
