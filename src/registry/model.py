import re

class Feature:
  def __init__(self, data, id):
    self.id = id
    self.name = data.name
    self.data = data

    self.api = data.api
    self.number = data.number

    self.requiredEnums = set() #[registry.enumIdsByName[name] for name in feature.reqEnumStrings]
    self.removedEnums  = set() #[registry.enumIdsByName[name] for name in feature.remEnumStrings]

    self.requiredCommands = set() #[registry.commandIdsByName[name] for name in feature.reqCommandStrings]
    self.removedCommands  = set() #[registry.commandIdsByName[name] for name in feature.remCommandStrings]

    self.inheritsFromFeature = None
    self.inheritingFeature = None

  def __str__(self):
    return '%s_%s' % (self.api, self.number)

  def toDictionary(self):
    data = {}
    data['id'] = self.id
    data['name'] = self.name

    data['api'] = self.api
    data['number'] = self.number

    data['require_comments'] = self.data.requireComments

    data['required_enums'] = map(lambda e: e.id, self.requiredEnums)
    data['removed_enums'] = map(lambda e: e.id, self.removedEnums)

    data['required_commands'] = map(lambda c: c.id, self.requiredCommands)
    data['removed_commands'] = map(lambda c: c.id, self.removedCommands)

    return data


class Enum:
  def __init__(self, data, id):
    self.id = id
    self.name = data.name
    self.value = data.value
    self.data = data

    self.features = set()
    self.groups = set()

  def toDictionary(self):
    data = {}
    data['id'] = self.id
    data['name'] = self.name
    data['value'] = self.value

    data['features'] = map(lambda f: f.id, self.features)
    
    return data


class Group:
  def __init__(self, data, id):
    self.id = id
    self.name = data.name
    self.data = data

    self.features = set()
    self.enums = set()

  def toDictionary(self):
    data = {}
    data['id'] = self.id
    data['name'] = self.name

    data['features'] = map(lambda f: f.id, self.features)
    data['enums'] = map(lambda e: e.id, self.enums)

    return data

_TYPE_NAME_REGEX_ = re.compile('(const[ ]+)?([^ *]+)([ ]*\*)?') # (const )(typename)( *)
class Parameter:
  def __init__(self, data, id):
    self.id = id
    self.name = data.name
    self.group = None
    self.type = data.type
    self.baseType = _TYPE_NAME_REGEX_.match(self.type).group(2)
    self.isPointer = '*' in self.type
    self.data = data
    self.hash = data.hash
    self.commands = set()

  def __str__(self):
    return str(self.data)

  def toDictionary(self):
    data = {}
    data['id'] = self.id
    data['name'] = self.name
    data['type'] = self.type
    if self.group:
      data['group'] = self.group.id
    return data


class Command:
  def __init__(self, data, id):
    self.id = id
    self.name = data.name
    self.data = data

    self.returngroup = None
    self.returntype = self.data.returntype
    self.baseReturnType =  _TYPE_NAME_REGEX_.match(self.returntype).group(2)

    self.features = set()
    self.parameters = []

    self.parameterHashes = [p.hash for p in data.params]

  def toDictionary(self):
    data = {}
    data['id'] = self.id
    data['name'] = self.name

    data['features'] = map(lambda f: f.id, self.features)
    data['parameters'] = map(lambda p: p.id, self.parameters)
    data['return_type'] = self.returntype
    if self.returngroup:
      data['return_group'] = self.returngroup

    return data


class Registry:
  def __init__(self, xmlFeatures, xmlEnums, xmlGroups, xmlCommands, es2Only=False):
    print('creating registry...')
    #
    # create entities
    #

    self.features = [Feature(e, id) for id, e in enumerate(xmlFeatures)]
    self.enums    = [Enum(e, id) for id, e in enumerate(xmlEnums)]
    self.groups   = [Group(e, id) for id, e in enumerate(xmlGroups)]
    self.commands = [Command(e, id) for id, e in enumerate(xmlCommands)]

    self.features = sorted(self.features, lambda f1, f2: str(f1) < str(f2))
    if es2Only:
      self.features = [f for f in self.features if f.api == 'gles2' and f.number == '2.0']

    self.featuresByApi = {}
    for api in {f.api for f in self.features}:
      cmpKey = lambda f: f.number
      apiFeatures = sorted([f for f in self.features if f.api == api], key=cmpKey)
      self.featuresByApi[api] = apiFeatures
      # link the features in this api together (feature.inheritsFromFeature)
      for idx in range(1, len(apiFeatures)):
        apiFeatures[idx].inheritsFromFeature = apiFeatures[idx - 1]
        apiFeatures[idx - 1].inheritingFeature = apiFeatures[idx]

    # compress all parameters into a single list of unique parameter specifications
    # TODO: verify this doesnt overwrite dissimilar parameters
    paramXmlsByHash = {p.hash: p for c in xmlCommands for p in c.params}
    uniqueXmlParameters = paramXmlsByHash.values()
    self.parameters = [Parameter(e, id) for id, e in enumerate(uniqueXmlParameters)]

    #
    # create lookup tables
    #

    self.featuresById = {e.id: e for e in self.features}
    self.enumsById    = {e.id: e for e in self.enums}
    self.groupsById   = {e.id: e for e in self.groups}
    self.commandsById = {e.id: e for e in self.commands}
    self.parametersById = {e.id: e for e in self.parameters}

    self.featuresByName = {e.name: e for e in self.features}
    self.enumsByName    = {e.name: e for e in self.enums}
    self.groupsByName   = {e.name: e for e in self.groups}
    self.commandsByName = {e.name: e for e in self.commands}
    self.parametersByHash = {e.hash: e for e in self.parameters}

    #
    # update entity relationships
    #

    print(' - updating feature references...')
    for f in self.features:
      f.requiredEnums = {self.enumsByName[name] for name in f.data.reqEnumStrings}
      f.removedEnums  = {self.enumsByName[name] for name in f.data.remEnumStrings}

      f.requiredCommands = {self.commandsByName[name] for name in f.data.reqCommandStrings}
      f.removedCommands  = {self.commandsByName[name] for name in f.data.remCommandStrings}

    print(' - cascading feature requirements...')
    for api, features in self.featuresByApi.iteritems():
      requiredEnums = set()
      requiredCommands = set()

      #assuming features are sorted in ascending order of version number
      prevFeature = None
      for f in features:
        if prevFeature != None and prevFeature.number > f.number:
          print('   - ERROR: features out of order!')
        prevFeature = f

        requiredEnums = requiredEnums - f.removedEnums
        requiredEnums = requiredEnums | f.requiredEnums
        f.requiredEnums = requiredEnums

        requiredCommands = requiredCommands - f.removedCommands
        requiredCommands = requiredCommands | f.requiredCommands
        f.requiredCommands = requiredCommands

    print(' - updating enum references...')
    for e in self.enums:
      e.features = {f for f in self.features if e in f.requiredEnums}

    print(' - updating group references...')
    for g in self.groups:
      for enumString in g.data.enumStrings:
        e = self.enumsByName.get(enumString)
        if e is None:
          print('    - cannot look up value for enum: %s' % enumString)
        else:
          g.enums.add(e)
          e.groups.add(g)

      enum_feature_sets = map(lambda e: e.features, g.enums)

      union = lambda a, b: a | b
      enumFeatures = reduce(union, enum_feature_sets, set())

      g.features = enumFeatures

    print(' - updating command references...')
    for c in self.commands:
      c.features = {f for f in self.features if c in f.requiredCommands}
      c.parameters = map(lambda h: self.parametersByHash[h], c.parameterHashes)
      for p in c.parameters:
        p.commands.add(c)
      groupstr = c.data.returnGroupString
      if groupstr and groupstr in self.groupsByName:
        c.returngroup = self.groupsByName[groupstr]        

    print(' - updating parameter references...')
    for p in self.parameters:
      groupstr = p.data.groupString
      if groupstr and groupstr in self.groupsByName:
        p.group = self.groupsByName[groupstr]

    # filter out all entities that are not associated with any feature
    # (i.e, extension only commands and enums)
    hasFeatures = lambda e: len(e.features) > 0
    self.coreEnums = filter(hasFeatures, self.enums)
    self.coreGroups = filter(hasFeatures, self.groups)
    for g in self.coreGroups:
      g.enums = filter(hasFeatures, g.enums)
    self.coreCommands = filter(hasFeatures, self.commands)
    coreParamSet = {p for c in self.coreCommands for p in c.parameters}
    self.coreParameters = list(coreParamSet)
    
  def findfeature(self, api, number):
    features = [f for f in self.features if f.api == api and f.number == number]
    return features[0]

