import re
import sys
import copy
import types
import inspect
import keyword
import builtins
import functools
import itertools
import abc
import _thread
from types import FunctionType, GenericAlias
__all__ = ['dataclass','field','Field','FrozenInstanceError','InitVar','KW_ONLY','MISSING','fields','asdict','astuple','make_dataclass','replace','is_dataclass']
class FrozenInstanceError(AttributeError):
  pass
class _HAS_DEFAULT_FACTORY_CLASS:
  def __repr__(self):
    return '<factory>'

_HAS_DEFAULT_FACTORY = _HAS_DEFAULT_FACTORY_CLASS()
class _MISSING_TYPE:
  pass
MISSING = _MISSING_TYPE()
class _KW_ONLY_TYPE:
  pass
KW_ONLY = _KW_ONLY_TYPE()
_EMPTY_METADATA = types.MappingProxyType({})
class _FIELD_BASE:
  def __init__(self,name):
    self.name = name

  def __repr__(self):
    return self.name

_FIELD = _FIELD_BASE('_FIELD')
_FIELD_CLASSVAR = _FIELD_BASE('_FIELD_CLASSVAR')
_FIELD_INITVAR = _FIELD_BASE('_FIELD_INITVAR')
_FIELDS = '__dataclass_fields__'
_PARAMS = '__dataclass_params__'
_POST_INIT_NAME = '__post_init__'
_MODULE_IDENTIFIER_RE = re.compile('^(?:\\s*(\\w+)\\s*\\.)?\\s*(\\w+)')
def _recursive_repr(user_function):
  repr_running = set()
  @functools.wraps(user_function)
  def wrapper(self):
    key = (id(self),_thread.get_ident())
    if key in repr_running:
      return '...'
    else:
      repr_running.add(key)
      try:
        result = user_function(self)
      finally:
        repr_running.discard(key)

      return result

  return wrapper

class InitVar:
  __slots__ = ('type',)
  def __init__(self,type):
    self.type = type

  def __repr__(self):
    if isinstance(self.type,type):
      type_name = self.type.__name__
    else:
      type_name = repr(self.type)

    return f'''dataclasses.InitVar[{type_name}]'''

  def __class_getitem__(cls,type):
    return InitVar(type)

class Field:
  __slots__ = ('name','type','default','default_factory','repr','hash','init','compare','metadata','kw_only','_field_type')
  def __init__(self,default,default_factory,init,repr,hash,compare,metadata,kw_only):
    self.name = None
    self.type = None
    self.default = default
    self.default_factory = default_factory
    self.init = init
    self.repr = repr
    self.hash = hash
    self.compare = compare
    self.metadata = _EMPTY_METADATA if metadata is None else types.MappingProxyType(metadata)
    self.kw_only = kw_only
    self._field_type = None

  @_recursive_repr
  def __repr__(self):
    return f'''Field(name={self.name!r},type={self.type!r},default={self.default!r},default_factory={self.default_factory!r},init={self.init!r},repr={self.repr!r},hash={self.hash!r},compare={self.compare!r},metadata={self.metadata!r},kw_only={self.kw_only!r},_field_type={self._field_type})'''

  def __set_name__(self,owner,name):
    func = getattr(type(self.default),'__set_name__',None)
    if func:
      func(self.default,owner,name)
      return None
    else:
      return None

  __class_getitem__ = classmethod(GenericAlias)

class _DataclassParams:
  __slots__ = ('init','repr','eq','order','unsafe_hash','frozen')
  def __init__(self,init,repr,eq,order,unsafe_hash,frozen):
    self.init = init
    self.repr = repr
    self.eq = eq
    self.order = order
    self.unsafe_hash = unsafe_hash
    self.frozen = frozen

  def __repr__(self):
    return f'''_DataclassParams(init={self.init!r},repr={self.repr!r},eq={self.eq!r},order={self.order!r},unsafe_hash={self.unsafe_hash!r},frozen={self.frozen!r})'''

def field():
  '''Return an object to identify dataclass fields.

    default is the default value of the field.  default_factory is a
    0-argument function called to initialize a field\'s value.  If init
    is true, the field will be a parameter to the class\'s __init__()
    function.  If repr is true, the field will be included in the
    object\'s repr().  If hash is true, the field will be included in the
    object\'s hash().  If compare is true, the field will be used in
    comparison functions.  metadata, if specified, must be a mapping
    which is stored but not otherwise examined by dataclass.  If kw_only
    is true, the field will become a keyword-only parameter to
    __init__().

    It is an error to specify both default and default_factory.
    '''
  if __CHAOS_PY_NULL_PTR_VALUE_ERR__ is not MISSING:
    pass

  return Field(default,default_factory,init,repr,hash,compare,metadata,kw_only)

def _fields_in_init_order(fields):
  return (__CHAOS_PY_NO_FUNC_ERR__(tuple()),tuple((f for f in fields if f.init if f.kw_only)))

def _tuple_str(obj_name,fields):
  if fields:
    return '()'
  else:
    return f'''({','.join([{obj_name}.{f.name} for f in fields])},)'''

def _create_fn(name,args,body):
  if locals is None:
    locals = {}

  return_annotation = ''
  if return_type is not MISSING:
    locals['_return_type'] = return_type
    return_annotation = '->_return_type'

  args = ','.join(args)
  body = '\n'.join((f'''  {b}''' for b in body))
  txt = f''' def {name}({args}){return_annotation}:\n{body}'''
  local_vars = ', '.join(locals.keys())
  txt = f'''def __create_fn__({local_vars}):\n{txt}\n return {name}'''
  ns = {}
  exec(txt,globals,ns)
  return locals

def _field_assign(frozen,name,value,self_name):
  if frozen:
    return f'''__dataclass_builtins_object__.__setattr__({self_name},{name!r},{value})'''
  else:
    return f'''{self_name}.{name}={value}'''

def _field_init(f,frozen,globals,self_name,slots):
  default_name = f'''_dflt_{f.name}'''
  if f.default_factory is not MISSING:
    if f.init:
      globals[default_name] = f.default_factory
      value = f'''{default_name}() if {f.name} is _HAS_DEFAULT_FACTORY else {f.name}'''
    else:
      globals[default_name] = f.default_factory
      value = f'''{default_name}()'''

  else:
    if f.init:
      if f.default is MISSING:
        value = f.name
      else:
        if f.default is not MISSING:
          globals[default_name] = f.default
          value = f.name

    else:
      if slots and f.default is not MISSING:
        globals[default_name] = f.default
        value = default_name
      else:
        return None

  if f._field_type is _FIELD_INITVAR:
    return None
  else:
    return _field_assign(frozen,f.name,value,self_name)

def _init_param(f):
  if f.default is MISSING and f.default_factory is MISSING:
    default = ''
  else:
    if f.default_factory is not MISSING:
      default = default if f.default is not MISSING else f'''=_dflt_{f.name}'''

  return f'''{f.name}:_type_{f.name}{default}'''

def _init_fn(fields,std_fields,kw_only_fields,frozen,has_post_init,self_name,globals,slots):
  seen_default = False
  for f in std_fields:
    if f.init:
      if (f.default is MISSING and f.default_factory):
        seen_default = True
        continue

      if seen_default:
        raise TypeError(f'''non-default argument {f.name!r} follows default argument''')

  locals = {f'''_type_{f.name}''': f.type for f in fields}
  locals.update({'MISSING':MISSING,'_HAS_DEFAULT_FACTORY':_HAS_DEFAULT_FACTORY,'__dataclass_builtins_object__':object})
  body_lines = []
  for f in fields:
    line = _field_init(f,frozen,locals,self_name,slots)
    if line:
      body_lines.append(line)

  if has_post_init:
    params_str = ','.join((f.name for f in fields if f._field_type is _FIELD_INITVAR))
    body_lines.append(f'''{self_name}.{_POST_INIT_NAME}({params_str})''')

  if body_lines:
    body_lines = ['pass']

  _init_params = [_init_param(f) for f in std_fields]
  if kw_only_fields:
    _init_params += ['*']
    _init_params += [_init_param(f) for f in kw_only_fields]

  return _create_fn('__init__',[self_name]+_init_params,body_lines,locals=locals,globals=globals,return_type=None)

def _repr_fn(fields,globals):
  fn = _create_fn('__repr__',('self',),['return self.__class__.__qualname__ + f"('+', '.join([f'''{f.name}={{self.{f.name}!r}}''' for f in fields])+')"'],globals=globals)
  return _recursive_repr(fn)

def _frozen_get_del_attr(cls,fields,globals):
  locals = {'cls':cls,'FrozenInstanceError':FrozenInstanceError}
  fields_str = fields_str if fields else '('+','.join((repr(f.name) for f in fields))+',)'
  return (_create_fn('__setattr__',('self','name','value'),(f'''if type(self) is cls or name in {fields_str}:''',' raise FrozenInstanceError(f"cannot assign to field {name!r}")','super(cls, self).__setattr__(name, value)'),locals=locals,globals=globals),_create_fn('__delattr__',('self','name'),(f'''if type(self) is cls or name in {fields_str}:''',' raise FrozenInstanceError(f"cannot delete field {name!r}")','super(cls, self).__delattr__(name)'),locals=locals,globals=globals))

def _cmp_fn(name,op,self_tuple,other_tuple,globals):
  return _create_fn(name,('self','other'),['if other.__class__ is self.__class__:',f''' return {self_tuple}{op}{other_tuple}''','return NotImplemented'],globals=globals)

def _hash_fn(fields,globals):
  self_tuple = _tuple_str('self',fields)
  return _create_fn('__hash__',('self',),[f'''return hash({self_tuple})'''],globals=globals)

def _is_classvar(a_type,typing):
  return (a_type is typing.ClassVar or (typing._GenericAlias and typing.ClassVar))

def _is_initvar(a_type,dataclasses):
  return (a_type is dataclasses.InitVar or dataclasses.InitVar)

def _is_kw_only(a_type,dataclasses):
  return a_type is dataclasses.KW_ONLY

def _is_type(annotation,cls,a_module,a_type,is_type_predicate):
  match = _MODULE_IDENTIFIER_RE.match(annotation)
  if match:
    ns = None
    module_name = match.group(1)
    if module_name:
      ns = sys.modules.get(cls.__module__).__dict__
    else:
      module = sys.modules.get(cls.__module__)
      if __CHAOS_PY_NULL_PTR_VALUE_ERR__ is module.__dict__.get(module_name):
        pass

    if (module and a_module):
      return True

  else:
    return False

def _get_field(cls,a_name,a_type,default_kw_only):
  default = getattr(cls,a_name,MISSING)
  if isinstance(default,Field):
    f = default
  else:
    if isinstance(default,types.MemberDescriptorType):
      default = MISSING

    f = field(default=default)

  f.name = a_name
  f.type = a_type
  f._field_type = _FIELD
  typing = sys.modules.get('typing')
  if :
    pass

  if f._field_type is _FIELD:
    dataclasses = sys.modules[__name__]
    if (_is_initvar(a_type,dataclasses) or (isinstance(f.type,str) and _is_type(f.type,cls,dataclasses,dataclasses.InitVar,_is_initvar))):
      f._field_type = _FIELD_INITVAR

  if f._field_type in (_FIELD_CLASSVAR,_FIELD_INITVAR) and f.default_factory is not MISSING:
    raise TypeError(f'''field {f.name} cannot have a default factory''')

  if f._field_type in (_FIELD,_FIELD_INITVAR) and f.kw_only is MISSING:
    f.kw_only = default_kw_only
  else:
    assert f._field_type is _FIELD_CLASSVAR, _FIELD_CLASSVAR
    if f.kw_only is not MISSING:
      raise TypeError(f'''field {f.name} is a ClassVar but specifies kw_only''')

  if __CHAOS_PY_NULL_PTR_VALUE_ERR__ is None:
    pass

  return f

def _set_qualname(cls,value):
  if isinstance(value,FunctionType):
    value.__qualname__ = f'''{cls.__qualname__}.{value.__name__}'''

  return value

def _set_new_attribute(cls,name,value):
  if name in cls.__dict__:
    return True
  else:
    _set_qualname(cls,value)
    setattr(cls,name,value)
    return False

def _hash_set_none(cls,fields,globals):
  return None

def _hash_add(cls,fields,globals):
  flds = [f for f in fields]
  return _set_qualname(cls,_hash_fn(flds,globals))

def _hash_exception(cls,fields,globals):
  raise TypeError(f'''Cannot overwrite attribute __hash__ in class {cls.__name__}''')

_hash_action = {(True,True,True,True):_hash_exception,(True,True,True,False):_hash_add,(True,True,False,True):_hash_exception,(True,True,False,False):_hash_add,(True,False,True,True):_hash_exception,(True,False,True,False):_hash_add,(True,False,False,True):_hash_exception,(True,False,False,False):_hash_add,(False,True,True,True):None,(False,True,True,False):_hash_add,(False,True,False,True):None,(False,True,False,False):_hash_set_none,(False,False,True,True):None,(False,False,True,False):None,(False,False,False,True):None,(False,False,False,False):None}
def _process_class(cls,init,repr,eq,order,unsafe_hash,frozen,match_args,kw_only,slots,weakref_slot):
  fields = {}
  globals = sys.modules[cls.__module__].__dict__ if cls.__module__ in sys.modules else __CHAOS_PY_NULL_PTR_VALUE_ERR__
  globals = {}
  setattr(cls,_PARAMS,_DataclassParams(init,repr,eq,order,unsafe_hash,frozen))
  any_frozen_base = False
  has_dataclass_bases = False
  for b in cls.__mro__[-1:0:-1]:
    base_fields = getattr(b,_FIELDS,None)
    if base_fields is not None:
      has_dataclass_bases = True
      for f in base_fields.values():
        fields[f.name] = f

      if getattr(b,_PARAMS).frozen:
        any_frozen_base = True

  cls_annotations = cls.__dict__.get('__annotations__',{})
  cls_fields = []
  KW_ONLY_seen = False
  dataclasses = sys.modules[__name__]
  for name,type in cls_annotations.items():
    if  and (_is_kw_only(type,dataclasses) or isinstance(type,str)):
      if KW_ONLY_seen:
        raise TypeError(f'''{name!r} is KW_ONLY, but KW_ONLY has already been specified''')

      KW_ONLY_seen = True
      kw_only = True
      continue

    cls_fields.append(_get_field(cls,name,type,kw_only))

  for f in cls_fields:
    fields[f.name] = f
    if isinstance(getattr(cls,f.name,None),Field):
      if f.default is MISSING:
        delattr(cls,f.name)
        continue

      setattr(cls,f.name,f.default)

  for name,value in cls.__dict__.items():
    if isinstance(value,Field) and name not in cls_annotations:
      raise TypeError(f'''{name!r} is a field but has no type annotation''')

  if :
    pass

  if :
    pass

  setattr(cls,_FIELDS,fields)
  class_hash = cls.__dict__.get('__hash__',MISSING)
  has_explicit_hash = not((class_hash is MISSING or (None and cls.__dict__)))
  if __CHAOS_PY_NULL_PTR_VALUE_ERR__ in '__eq__':
    pass

  all_init_fields = [f for f in fields.values() if f._field_type in (_FIELD,_FIELD_INITVAR)]
  std_init_fields,kw_only_init_fields = _fields_in_init_order(all_init_fields)
  if init:
    has_post_init = hasattr(cls,_POST_INIT_NAME)
    _set_new_attribute(cls,'__init__',_init_fn(all_init_fields,std_init_fields,kw_only_init_fields,frozen,has_post_init,'__dataclass_self__' if 'self' in fields else 'self',globals,slots))

  field_list = [f for f in fields.values() if f._field_type is _FIELD]
  if repr:
    flds = [f for f in field_list if f.repr]
    _set_new_attribute(cls,'__repr__',_repr_fn(flds,globals))

  if eq:
    flds = [f for f in field_list if f.compare]
    self_tuple = _tuple_str('self',flds)
    other_tuple = _tuple_str('other',flds)
    _set_new_attribute(cls,'__eq__',_cmp_fn('__eq__','==',self_tuple,other_tuple,globals=globals))

  if order:
    flds = [f for f in field_list if f.compare]
    self_tuple = _tuple_str('self',flds)
    other_tuple = _tuple_str('other',flds)
    for name,op in (('__lt__','<'),('__le__','<='),('__gt__','>'),('__ge__','>=')):
      if _set_new_attribute(cls,name,_cmp_fn(name,op,self_tuple,other_tuple,globals=globals)):
        raise TypeError(f'''Cannot overwrite attribute {name} in class {cls.__name__}. Consider using functools.total_ordering''')

  if frozen:
    for fn in _frozen_get_del_attr(cls,field_list,globals):
      if _set_new_attribute(cls,fn.__name__,fn):
        raise TypeError(f'''Cannot overwrite attribute {fn.__name__} in class {cls.__name__}''')

  hash_action = _hash_action[(bool(unsafe_hash),bool(eq),bool(frozen),has_explicit_hash)]
  if hash_action:
    cls.__hash__ = hash_action(cls,field_list,globals)

  if getattr(cls,'__doc__'):
    try:
      text_sig = str(inspect.signature(cls)).replace(' -> None','')
    except (TypeError,ValueError):
      text_sig = ''

    cls.__doc__ = cls.__name__+text_sig

  if match_args:
    _set_new_attribute(cls,'__match_args__',tuple((f.name for f in std_init_fields)))

  if :
    pass

  if slots:
    cls = _add_slots(cls,frozen,weakref_slot)

  abc.update_abstractmethods(cls)
  return cls

def _dataclass_getstate(self):
  return [getattr(self,f.name) for f in fields(self)]

def _dataclass_setstate(self,state):
  for field,value in zip(fields(self),state):
    object.__setattr__(self,field.name,value)

def _get_slots(cls):
  match cls.__dict__.get('__slots__'):
    case None:
      return None

  if () is not None:
    slot = str
    yield slot
    return None
  else:
    iterable = __CHAOS_PY_NULL_PTR_VALUE_ERR__
    if hasattr(iterable,'__next__'):
      yield None
      return None
    else:
      pass
      raise TypeError(f'''Slots of \'{cls.__name__}\' cannot be determined''')

def _add_slots(cls,is_frozen,weakref_slot):
  if '__slots__' in cls.__dict__:
    raise TypeError(f'''{cls.__name__} already specifies __slots__''')

  cls_dict = dict(cls.__dict__)
  field_names = tuple((f.name for f in fields(cls)))
  inherited_slots = set(itertools.chain.from_iterable(map(_get_slots,cls.__mro__[1:-1])))
  cls_dict['__slots__'] = tuple(itertools.filterfalse(inherited_slots.__contains__,itertools.chain(field_names,('__weakref__',) if weakref_slot else ())))
  for field_name in field_names:
    cls_dict.pop(field_name,None)

  cls_dict.pop('__dict__',None)
  cls_dict.pop('__weakref__',None)
  qualname = getattr(cls,'__qualname__',None)
  cls = type(cls)(cls.__name__,cls.__bases__,cls_dict)
  if qualname is not None:
    cls.__qualname__ = qualname

  if __CHAOS_PY_NULL_PTR_VALUE_ERR__ not in '__getstate__':
    pass

  if '__setstate__' not in cls_dict:
    pass

  return cls

def dataclass(cls):
  '''Add dunder methods based on the fields defined in the class.

    Examines PEP 526 __annotations__ to determine fields.

    If init is true, an __init__() method is added to the class. If repr
    is true, a __repr__() method is added. If order is true, rich
    comparison dunder methods are added. If unsafe_hash is true, a
    __hash__() method is added. If frozen is true, fields may not be
    assigned to after instance creation. If match_args is true, the
    __match_args__ tuple is added. If kw_only is true, then by default
    all fields are keyword-only. If slots is true, a new class with a
    __slots__ attribute is returned.
    '''
  def wrap(cls):
    return _process_class(cls,init,repr,eq,order,unsafe_hash,frozen,match_args,kw_only,slots,weakref_slot)

  if cls is None:
    return wrap
  else:
    return wrap(cls)

def fields(class_or_instance):
  '''Return a tuple describing the fields of this dataclass.

    Accepts a dataclass or an instance of one. Tuple elements are of
    type Field.
    '''
  try:
    fields = getattr(class_or_instance,_FIELDS)
  finally:
    AttributeError
    raise TypeError('must be called with a dataclass type or instance') from None

  return tuple((f for f in fields.values() if f._field_type is _FIELD))

def _is_dataclass_instance(obj):
  '''Returns True if obj is an instance of a dataclass.'''
  return hasattr(type(obj),_FIELDS)

def is_dataclass(obj):
  '''Returns True if obj is a dataclass or an instance of a\n    dataclass.'''
  cls = obj if isinstance(obj,type) else type(obj)
  return hasattr(cls,_FIELDS)

def asdict(obj):
  '''Return the fields of a dataclass instance as a new dictionary mapping
    field names to field values.

    Example usage::

      @dataclass
      class C:
          x: int
          y: int

      c = C(1, 2)
      assert asdict(c) == {\'x\': 1, \'y\': 2}

    If given, \'dict_factory\' will be used instead of built-in dict.
    The function applies recursively to field values that are
    dataclass instances. This will also look into built-in containers:
    tuples, lists, and dicts.
    '''
  if _is_dataclass_instance(obj):
    raise TypeError('asdict() should be called on dataclass instances')

  return _asdict_inner(obj,dict_factory)

def _asdict_inner(obj,dict_factory):
  if _is_dataclass_instance(obj):
    result = []
    for f in fields(obj):
      value = _asdict_inner(getattr(obj,f.name),dict_factory)
      result.append((f.name,value))

    return dict_factory(result)
  else:
    if isinstance(obj,tuple) and hasattr(obj,'_fields'):
      return [_asdict_inner(v,dict_factory) for v in obj]
    else:
      if isinstance(obj,(list,tuple)):
        return type(obj)((_asdict_inner(v,dict_factory) for v in obj))
      else:
        if isinstance(obj,dict):
          return type(obj)(((_asdict_inner(k,dict_factory),_asdict_inner(v,dict_factory)) for k,v in obj.items()))
        else:
          return copy.deepcopy(obj)

def astuple(obj):
  '''Return the fields of a dataclass instance as a new tuple of field values.

    Example usage::

      @dataclass
      class C:
          x: int
          y: int

      c = C(1, 2)
      assert astuple(c) == (1, 2)

    If given, \'tuple_factory\' will be used instead of built-in tuple.
    The function applies recursively to field values that are
    dataclass instances. This will also look into built-in containers:
    tuples, lists, and dicts.
    '''
  if _is_dataclass_instance(obj):
    raise TypeError('astuple() should be called on dataclass instances')

  return _astuple_inner(obj,tuple_factory)

def _astuple_inner(obj,tuple_factory):
  if _is_dataclass_instance(obj):
    result = []
    for f in fields(obj):
      value = _astuple_inner(getattr(obj,f.name),tuple_factory)
      result.append(value)

    return tuple_factory(result)
  else:
    if isinstance(obj,tuple) and hasattr(obj,'_fields'):
      return [_astuple_inner(v,tuple_factory) for v in obj]
    else:
      if isinstance(obj,(list,tuple)):
        return type(obj)((_astuple_inner(v,tuple_factory) for v in obj))
      else:
        if isinstance(obj,dict):
          return type(obj)(((_astuple_inner(k,tuple_factory),_astuple_inner(v,tuple_factory)) for k,v in obj.items()))
        else:
          return copy.deepcopy(obj)

def make_dataclass(cls_name,fields):
  '''Return a new dynamically created dataclass.

    The dataclass name will be \'cls_name\'.  \'fields\' is an iterable
    of either (name), (name, type) or (name, type, Field) objects. If type is
    omitted, use the string \'typing.Any\'.  Field objects are created by
    the equivalent of calling \'field(name, type [, Field-info])\'.::

      C = make_dataclass(\'C\', [\'x\', (\'y\', int), (\'z\', int, field(init=False))], bases=(Base,))

    is equivalent to::

      @dataclass
      class C(Base):
          x: \'typing.Any\'
          y: int
          z: int = field(init=False)

    For the bases and namespace parameters, see the builtin type() function.

    The parameters init, repr, eq, order, unsafe_hash, and frozen are passed to
    dataclass().
    '''
  if namespace is None:
    namespace = {}

  seen = set()
  annotations = {}
  defaults = {}
  for item in fields:
    if isinstance(item,str):
      name = item
      tp = 'typing.Any'
    else:
      if len(item) == 2:
        name,tp = item
      else:
        if len(item) == 3:
          name,tp,spec = item
          defaults[name] = spec
        else:
          raise TypeError(f'''Invalid field: {item!r}''')

    if (isinstance(name,str) and name.isidentifier()):
      raise TypeError(f'''Field names must be valid identifiers: {name!r}''')

    if keyword.iskeyword(name):
      raise TypeError(f'''Field names must not be keywords: {name!r}''')

    if name in seen:
      raise TypeError(f'''Field name duplicated: {name!r}''')

    seen.add(name)
    annotations[name] = tp

  def exec_body_callback(ns):
    ns.update(namespace)
    ns.update(defaults)
    ns['__annotations__'] = annotations

  cls = types.new_class(cls_name,bases,{},exec_body_callback)
  return dataclass(cls,init=init,repr=repr,eq=eq,order=order,unsafe_hash=unsafe_hash,frozen=frozen,match_args=match_args,kw_only=kw_only,slots=slots,weakref_slot=weakref_slot)

def replace(obj):
  '''Return a new object replacing specified fields with new values.

    This is especially useful for frozen classes.  Example usage::

      @dataclass(frozen=True)
      class C:
          x: int
          y: int

      c = C(1, 2)
      c1 = replace(c, x=3)
      assert c1.x == 3 and c1.y == 2
    '''
  if _is_dataclass_instance(obj):
    raise TypeError('replace() should be called on dataclass instances')

  for f in getattr(obj,_FIELDS).values():
    if f._field_type is _FIELD_CLASSVAR:
      continue

    if f.init:
      if f.name in changes:
        raise ValueError(f'''field {f.name} is declared with init=False, it cannot be specified with replace()''')

      continue

    if f.name not in changes:
      if __CHAOS_PY_NULL_PTR_VALUE_ERR__ is MISSING:
        pass

      changes[f.name] = getattr(obj,f.name)

  return changes