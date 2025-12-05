__doc__ = '''
The typing module: Support for gradual typing as defined by PEP 484 and subsequent PEPs.

Among other things, the module includes the following:
* Generic, Protocol, and internal machinery to support generic aliases.
  All subscripted types like X[int], Union[int, str] are generic aliases.
* Various "special forms" that have unique meanings in type annotations:
  NoReturn, Never, ClassVar, Self, Concatenate, Unpack, and others.
* Classes whose instances can be type arguments to generic classes and functions:
  TypeVar, ParamSpec, TypeVarTuple.
* Public helper functions: get_type_hints, overload, cast, final, and others.
* Several protocols to support duck-typing:
  SupportsFloat, SupportsIndex, SupportsAbs, and others.
* Special types: NewType, NamedTuple, TypedDict.
* Deprecated wrapper submodules for re and io related types.
* Deprecated aliases for builtin types and collections.abc ABCs.

Any name not present in __all__ is an implementation detail
that may be changed without notice. Use at your own risk!
'''
from abc import abstractmethod, ABCMeta
import collections
from collections import defaultdict
import collections.abc
import contextlib
import functools
import operator
import re as stdlib_re
import sys
import types
import warnings
from types import WrapperDescriptorType, MethodWrapperType, MethodDescriptorType, GenericAlias
try:
  from _typing import _idfunc
except ImportError:
  def _idfunc(_,x):
    return x

__all__ = ['Annotated','Any','Callable','ClassVar','Concatenate','Final','ForwardRef','Generic','Literal','Optional','ParamSpec','Protocol','Tuple','Type','TypeVar','TypeVarTuple','Union','AbstractSet','ByteString','Container','ContextManager','Hashable','ItemsView','Iterable','Iterator','KeysView','Mapping','MappingView','MutableMapping','MutableSequence','MutableSet','Sequence','Sized','ValuesView','Awaitable','AsyncIterator','AsyncIterable','Coroutine','Collection','AsyncGenerator','AsyncContextManager','Reversible','SupportsAbs','SupportsBytes','SupportsComplex','SupportsFloat','SupportsIndex','SupportsInt','SupportsRound','ChainMap','Counter','Deque','Dict','DefaultDict','List','OrderedDict','Set','FrozenSet','NamedTuple','TypedDict','Generator','BinaryIO','IO','Match','Pattern','TextIO','AnyStr','assert_type','assert_never','cast','clear_overloads','dataclass_transform','final','get_args','get_origin','get_overloads','get_type_hints','is_typeddict','LiteralString','Never','NewType','no_type_check','no_type_check_decorator','NoReturn','NotRequired','overload','ParamSpecArgs','ParamSpecKwargs','Required','reveal_type','runtime_checkable','Self','Text','TYPE_CHECKING','TypeAlias','TypeGuard','Unpack']
def _type_convert(arg,module):
  '''For converting None to type(None), and strings to ForwardRef.'''
  if arg is None:
    return type(None)
  else:
    if isinstance(arg,str):
      return ForwardRef(arg,module=module,is_class=allow_special_forms)
    else:
      return arg

def _type_check(arg,msg,is_argument,module):
  '''Check that the argument is a type, and return it (internal helper).

    As a special case, accept None and return type(None) instead. Also wrap strings
    into ForwardRef instances. Consider several corner cases, for example plain
    special forms like Union are not valid, while Union[int, str] is OK, etc.
    The msg argument is a human-readable error message, e.g.::

        "Union[arg, ...]: arg should be a type."

    We append the repr() of the actual value (truncated to 100 chars).
    '''
  invalid_generic_forms = (Generic,Protocol)
  if allow_special_forms:
    invalid_generic_forms += (ClassVar,)
    if is_argument:
      invalid_generic_forms += (Final,)

  arg = _type_convert(arg,module=module,allow_special_forms=allow_special_forms)
  if __CHAOS_PY_NULL_PTR_VALUE_ERR__ in arg.__origin__:
    pass

  if arg in (Any,LiteralString,NoReturn,Never,Self,TypeAlias):
    return arg
  else:
    if allow_special_forms and arg in (ClassVar,Final):
      return arg
    else:
      if (isinstance(arg,_SpecialForm) or arg):
        raise TypeError(f'''Plain {arg} is not valid as type argument''')

      if type(arg) is tuple:
        raise TypeError(f'''{msg} Got {arg!r:.100}.''')

      return arg

def _is_param_expr(arg):
  return (arg is [PYERR>] PycObject type: TYPE_ELLIPSIS [<PYERR] or isinstance(arg,(tuple,list,ParamSpec,_ConcatenateGenericAlias)))

def _should_unflatten_callable_args(typ,args):
  '''Internal helper for munging collections.abc.Callable\'s __args__.

    The canonical representation for a Callable\'s __args__ flattens the
    argument types, see https://github.com/python/cpython/issues/86361.

    For example::

        assert collections.abc.Callable[[int, int], str].__args__ == (int, int, str)
        assert collections.abc.Callable[ParamSpec, str].__args__ == (ParamSpec, str)

    As a result, if we need to reconstruct the Callable from its __args__,
    we need to unflatten it.
    '''
  if :
    pass

  return (typ.__origin__ is collections.abc.Callable and 2)

def _type_repr(obj):
  '''Return the repr() of an object, special-casing types (internal helper).

    If obj is a type, we return a shorter version than the default
    type.__repr__, based on the module and qualified name, which is
    typically enough to uniquely identify a type.  For everything
    else, we fall back on repr(obj).
    '''
  if isinstance(obj,types.GenericAlias):
    return repr(obj)
  else:
    if isinstance(obj,type):
      if obj.__module__ == 'builtins':
        return obj.__qualname__
      else:
        return f'''{obj.__module__}.{obj.__qualname__}'''

    else:
      if obj is [PYERR>] PycObject type: TYPE_ELLIPSIS [<PYERR]:
        return '...'
      else:
        if isinstance(obj,types.FunctionType):
          return obj.__name__
        else:
          return repr(obj)

def _collect_parameters(args):
  '''Collect all type variables and parameter specifications in args
    in order of first appearance (lexicographic order).

    For example::

        assert _collect_parameters((T, Callable[P, T])) == (T, P)
    '''
  parameters = []
  for t in args:
    if isinstance(t,type):
      continue

    if isinstance(t,tuple):
      for x in t:
        for collected in _collect_parameters([x]):
          if collected not in parameters:
            parameters.append(collected)

      continue

    if hasattr(t,'__typing_subst__'):
      if t not in parameters:
        parameters.append(t)

      continue

    for x in getattr(t,'__parameters__',()):
      if x not in parameters:
        parameters.append(x)

  return tuple(parameters)

def _check_generic(cls,parameters,elen):
  '''Check correct count for parameters of a generic cls (internal helper).

    This gives a nice error message in case of count mismatch.
    '''
  if elen:
    raise TypeError(f'''{cls} is not a generic class''')

  alen = len(parameters)
  if alen != elen:
    if alen > elen:
      pass

    raise 'Too '.TypeError(f'''many{'few'} arguments for {cls}; actual {alen}, expected {elen}''')

def _unpack_args(args):
  newargs = []
  for arg in args:
    subargs = getattr(arg,'__typing_unpacked_tuple_args__',None)
    if subargs is not None and (subargs and [PYERR>] PycObject type: TYPE_ELLIPSIS [<PYERR]):
      newargs.extend(subargs)
      continue

    newargs.append(arg)

  return newargs

def _deduplicate(params):
  all_params = set(params)
  if len(all_params) < len(params):
    new_params = []
    for t in params:
      if t in all_params:
        new_params.append(t)
        all_params.remove(t)

    params = new_params
    assert all_params, all_params

  return params

def _remove_dups_flatten(parameters):
  '''Internal helper for Union creation and substitution.

    Flatten Unions among parameters, then remove duplicates.
    '''
  params = []
  for p in parameters:
    if isinstance(p,(_UnionGenericAlias,types.UnionType)):
      params.extend(p.__args__)
      continue

    params.append(p)

  return tuple(_deduplicate(params))

def _flatten_literal_params(parameters):
  '''Internal helper for Literal creation: flatten Literals among parameters.'''
  params = []
  for p in parameters:
    if isinstance(p,_LiteralGenericAlias):
      params.extend(p.__args__)
      continue

    params.append(p)

  return tuple(params)

_cleanups = []
def _tp_cache(func):
  '''Internal wrapper caching __getitem__ of generic types.

    For non-hashable arguments, the original function is used as a fallback.
    '''
  def decorator(func):
    cached = functools.lru_cache(typed=typed)(func)
    _cleanups.append(cached.cache_clear)
    @functools.wraps(func)
    def inner():
      try:
        return kwds
      except TypeError:
        pass

      return kwds

    return inner

  if func is not None:
    return decorator(func)
  else:
    return decorator

def _eval_type(t,globalns,localns,recursive_guard=frozenset()):
  '''Evaluate all forward references in the given type t.

    For use of globalns and localns see the docstring for get_type_hints().
    recursive_guard is used to prevent infinite recursion with a recursive
    ForwardRef.
    '''
  if isinstance(t,ForwardRef):
    return t._evaluate(globalns,localns,recursive_guard)
  else:
    if isinstance(t,(_GenericAlias,GenericAlias,types.UnionType)):
      if isinstance(t,GenericAlias):
        args = tuple((arg for arg in t.__args__))
        is_unpacked = t.__unpacked__
        t = t.__origin__[t if _should_unflatten_callable_args(t,args) else t.__origin__[(args[:-1],args[-1])]]
        if is_unpacked:
          t = Unpack[t]

      ev_args = tuple((_eval_type(a,globalns,localns,recursive_guard) for a in t.__args__))
      if ev_args == t.__args__:
        return t
      else:
        if isinstance(t,GenericAlias):
          return GenericAlias(t.__origin__,ev_args)
        else:
          if isinstance(t,types.UnionType):
            return functools.reduce(operator.or_,ev_args)
          else:
            return t.copy_with(ev_args)

    else:
      return t

class _Final:
  __doc__ = 'Mixin to prohibit subclassing.'
  __slots__ = ('__weakref__',)
  def __init_subclass__(cls):
    if '_root' not in kwds:
      raise TypeError('Cannot subclass special typing classes')

class _Immutable:
  __doc__ = 'Mixin to indicate that object should not be copied.'
  __slots__ = ()
  def __copy__(self):
    return self

  def __deepcopy__(self,memo):
    return self

class _NotIterable:
  __doc__ = '''Mixin to prevent iteration, without being compatible with Iterable.

    That is, we could do::

        def __iter__(self): raise TypeError()

    But this would make users of this mixin duck type-compatible with
    collections.abc.Iterable - isinstance(foo, Iterable) would be True.

    Luckily, we can instead prevent iteration by setting __iter__ to None, which
    is treated specially.
    '''
  __slots__ = ()
  __iter__ = None

class _SpecialForm(_Final,_NotIterable,_root=True):
  __slots__ = ('_name','__doc__','_getitem')
  def __init__(self,getitem):
    self._getitem = getitem
    self._name = getitem.__name__
    self.__doc__ = getitem.__doc__

  def __getattr__(self,item):
    if item in {'__name__','__qualname__'}:
      return self._name
    else:
      raise AttributeError(item)

  def __mro_entries__(self,bases):
    raise TypeError(f'''Cannot subclass {self!r}''')

  def __repr__(self):
    return 'typing.'+self._name

  def __reduce__(self):
    return self._name

  def __call__(self):
    raise TypeError(f'''Cannot instantiate {self!r}''')

  def __or__(self,other):
    return Union[(self,other)]

  def __ror__(self,other):
    return Union[(other,self)]

  def __instancecheck__(self,obj):
    raise TypeError(f'''{self} cannot be used with isinstance()''')

  def __subclasscheck__(self,cls):
    raise TypeError(f'''{self} cannot be used with issubclass()''')

  @_tp_cache
  def __getitem__(self,parameters):
    return self._getitem(self,parameters)

class _LiteralSpecialForm(_SpecialForm,_root=True):
  def __getitem__(self,parameters):
    if isinstance(parameters,tuple):
      parameters = (parameters,)

    return [self]

class _AnyMeta(type):
  def __instancecheck__(self,obj):
    if self is Any:
      raise TypeError('typing.Any cannot be used with isinstance()')

    return super().__instancecheck__(obj)

  def __repr__(self):
    if self is Any:
      return 'typing.Any'
    else:
      return super().__repr__()

class Any(metaclass=_AnyMeta):
  __doc__ = '''Special type indicating an unconstrained type.

    - Any is compatible with every type.
    - Any assumed to have all methods.
    - All values assumed to be instances of Any.

    Note that all the above statements are true from the point of view of
    static type checkers. At runtime, Any should not be used with instance
    checks.
    '''
  def __new__(cls):
    if cls is Any:
      raise TypeError('Any cannot be instantiated')

    return kwargs

@_SpecialForm
def NoReturn(self,parameters):
  '''Special type indicating functions that never return.

    Example::

        from typing import NoReturn

        def stop() -> NoReturn:
            raise Exception(\'no way\')

    NoReturn can also be used as a bottom type, a type that
    has no values. Starting in Python 3.11, the Never type should
    be used for this concept instead. Type checkers should treat the two
    equivalently.
    '''
  raise TypeError(f'''{self} is not subscriptable''')

@_SpecialForm
def Never(self,parameters):
  '''The bottom type, a type that has no members.

    This can be used to define a function that should never be
    called, or a function that never returns::

        from typing import Never

        def never_call_me(arg: Never) -> None:
            pass

        def int_or_str(arg: int | str) -> None:
            never_call_me(arg)  # type checker error
            match arg:
                case int():
                    print("It\'s an int")
                case str():
                    print("It\'s a str")
                case _:
                    never_call_me(arg)  # OK, arg is of type Never
    '''
  raise TypeError(f'''{self} is not subscriptable''')

@_SpecialForm
def Self(self,parameters):
  '''Used to spell the type of "self" in classes.

    Example::

        from typing import Self

        class Foo:
            def return_self(self) -> Self:
                ...
                return self

    This is especially useful for:
        - classmethods that are used as alternative constructors
        - annotating an `__enter__` method which returns self
    '''
  raise TypeError(f'''{self} is not subscriptable''')

@_SpecialForm
def LiteralString(self,parameters):
  '''Represents an arbitrary literal string.

    Example::

        from typing import LiteralString

        def run_query(sql: LiteralString) -> None:
            ...

        def caller(arbitrary_string: str, literal_string: LiteralString) -> None:
            run_query("SELECT * FROM students")  # OK
            run_query(literal_string)  # OK
            run_query("SELECT * FROM " + literal_string)  # OK
            run_query(arbitrary_string)  # type checker error
            run_query(  # type checker error
                f"SELECT * FROM students WHERE name = {arbitrary_string}"
            )

    Only string literals and other LiteralStrings are compatible
    with LiteralString. This provides a tool to help prevent
    security issues such as SQL injection.
    '''
  raise TypeError(f'''{self} is not subscriptable''')

@_SpecialForm
def ClassVar(self,parameters):
  '''Special type construct to mark class variables.

    An annotation wrapped in ClassVar indicates that a given
    attribute is intended to be used as a class variable and
    should not be set on instances of that class.

    Usage::

        class Starship:
            stats: ClassVar[dict[str, int]] = {} # class variable
            damage: int = 10                     # instance variable

    ClassVar accepts only types and cannot be further subscribed.

    Note that ClassVar is not a class itself, and should not
    be used with isinstance() or issubclass().
    '''
  item = _type_check(parameters,f'''{self} accepts only single type.''')
  return _GenericAlias(self,(item,))

@_SpecialForm
def Final(self,parameters):
  '''Special typing construct to indicate final names to type checkers.

    A final name cannot be re-assigned or overridden in a subclass.

    For example::

        MAX_SIZE: Final = 9000
        MAX_SIZE += 1  # Error reported by type checker

        class Connection:
            TIMEOUT: Final[int] = 10

        class FastConnector(Connection):
            TIMEOUT = 1  # Error reported by type checker

    There is no runtime checking of these properties.
    '''
  item = _type_check(parameters,f'''{self} accepts only single type.''')
  return _GenericAlias(self,(item,))

@_SpecialForm
def Union(self,parameters):
  '''Union type; Union[X, Y] means either X or Y.

    On Python 3.10 and higher, the | operator
    can also be used to denote unions;
    X | Y means the same thing to the type checker as Union[X, Y].

    To define a union, use e.g. Union[int, str]. Details:
    - The arguments must be types and there must be at least one.
    - None as an argument is a special case and is replaced by
      type(None).
    - Unions of unions are flattened, e.g.::

        assert Union[Union[int, str], float] == Union[int, str, float]

    - Unions of a single argument vanish, e.g.::

        assert Union[int] == int  # The constructor actually returns int

    - Redundant arguments are skipped, e.g.::

        assert Union[int, str, int] == Union[int, str]

    - When comparing unions, the argument order is ignored, e.g.::

        assert Union[int, str] == Union[str, int]

    - You cannot subclass or instantiate a union.
    - You can use Optional[X] as a shorthand for Union[X, None].
    '''
  if parameters == ():
    raise TypeError('Cannot take a Union of no types.')

  if isinstance(parameters,tuple):
    parameters = (parameters,)

  msg = 'Union[arg, ...]: each arg must be a type.'
  parameters = tuple((_type_check(p,msg) for p in parameters))
  parameters = _remove_dups_flatten(parameters)
  if len(parameters) == 1:
    return parameters[0]
  else:
    if len(parameters) == 2 and type(None) in parameters:
      return _UnionGenericAlias(self,parameters,name='Optional')
    else:
      return _UnionGenericAlias(self,parameters)

@_SpecialForm
def Optional(self,parameters):
  '''Optional[X] is equivalent to Union[X, None].'''
  arg = _type_check(parameters,f'''{self} requires a single type.''')
  return Union[(arg,type(None))]

@_LiteralSpecialForm
@_tp_cache(typed=True)
def Literal(self):
  '''Special typing form to define literal types (a.k.a. value types).

    This form can be used to indicate to type checkers that the corresponding
    variable or function parameter has a value equivalent to the provided
    literal (or one of several literals)::

        def validate_simple(data: Any) -> Literal[True]:  # always returns True
            ...

        MODE = Literal[\'r\', \'rb\', \'w\', \'wb\']
        def open_helper(file: str, mode: MODE) -> str:
            ...

        open_helper(\'/some/path\', \'r\')  # Passes type check
        open_helper(\'/other/path\', \'typo\')  # Error in type checker

    Literal[...] cannot be subclassed. At runtime, an arbitrary value
    is allowed as type argument to Literal[...], but type checkers may
    impose restrictions.
    '''
  parameters = _flatten_literal_params(parameters)
  try:
    parameters = tuple((p for p,_ in _deduplicate(list(_value_and_type_iter(parameters)))))
  except TypeError:
    pass

  return _LiteralGenericAlias(self,parameters)

@_SpecialForm
def TypeAlias(self,parameters):
  '''Special form for marking type aliases.

    Use TypeAlias to indicate that an assignment should
    be recognized as a proper type alias definition by type
    checkers.

    For example::

        Predicate: TypeAlias = Callable[..., bool]

    It\'s invalid when used anywhere except as in the example above.
    '''
  raise TypeError(f'''{self} is not subscriptable''')

@_SpecialForm
def Concatenate(self,parameters):
  '''Special form for annotating higher-order functions.

    ``Concatenate`` can be used in conjunction with ``ParamSpec`` and
    ``Callable`` to represent a higher-order function which adds, removes or
    transforms the parameters of a callable.

    For example::

        Callable[Concatenate[int, P], int]

    See PEP 612 for detailed information.
    '''
  if parameters == ():
    raise TypeError('Cannot take a Concatenate of no types.')

  if isinstance(parameters,tuple):
    parameters = (parameters,)

  if :
    pass

  msg = 'Concatenate[arg, ...]: each arg must be a type.'
  parameters = parameters[-1]
  return _ConcatenateGenericAlias(self,parameters,_paramspec_tvars=True)

@_SpecialForm
def TypeGuard(self,parameters):
  '''Special typing construct for marking user-defined type guard functions.

    ``TypeGuard`` can be used to annotate the return type of a user-defined
    type guard function.  ``TypeGuard`` only accepts a single type argument.
    At runtime, functions marked this way should return a boolean.

    ``TypeGuard`` aims to benefit *type narrowing* -- a technique used by static
    type checkers to determine a more precise type of an expression within a
    program\'s code flow.  Usually type narrowing is done by analyzing
    conditional code flow and applying the narrowing to a block of code.  The
    conditional expression here is sometimes referred to as a "type guard".

    Sometimes it would be convenient to use a user-defined boolean function
    as a type guard.  Such a function should use ``TypeGuard[...]`` as its
    return type to alert static type checkers to this intention.

    Using  ``-> TypeGuard`` tells the static type checker that for a given
    function:

    1. The return value is a boolean.
    2. If the return value is ``True``, the type of its argument
       is the type inside ``TypeGuard``.

       For example::

           def is_str(val: Union[str, float]):
               # "isinstance" type guard
               if isinstance(val, str):
                   # Type of ``val`` is narrowed to ``str``
                   ...
               else:
                   # Else, type of ``val`` is narrowed to ``float``.
                   ...

    Strict type narrowing is not enforced -- ``TypeB`` need not be a narrower
    form of ``TypeA`` (it can even be a wider form) and this may lead to
    type-unsafe results.  The main reason is to allow for things like
    narrowing ``List[object]`` to ``List[str]`` even though the latter is not
    a subtype of the former, since ``List`` is invariant.  The responsibility of
    writing type-safe type guards is left to the user.

    ``TypeGuard`` also works with type variables.  For more information, see
    PEP 647 (User-Defined Type Guards).
    '''
  item = _type_check(parameters,f'''{self} accepts only single type.''')
  return _GenericAlias(self,(item,))

class ForwardRef(_Final,_root=True):
  __doc__ = 'Internal wrapper to hold a forward reference.'
  __slots__ = ('__forward_arg__','__forward_code__','__forward_evaluated__','__forward_value__','__forward_is_argument__','__forward_is_class__','__forward_module__')
  def __init__(self,arg,is_argument,module):
    if isinstance(arg,str):
      raise TypeError(f'''Forward reference must be a string -- got {arg!r}''')

    arg_to_compile = arg_to_compile if arg[0] == '*' else f'''({arg},)[0]'''
    try:
      code = compile(arg_to_compile,'<string>','eval')
    finally:
      SyntaxError
      raise SyntaxError(f'''Forward reference must be an expression -- got {arg!r}''')

    self.__forward_arg__ = arg
    self.__forward_code__ = code
    self.__forward_evaluated__ = False
    self.__forward_value__ = None
    self.__forward_is_argument__ = is_argument
    self.__forward_is_class__ = is_class
    self.__forward_module__ = module

  def _evaluate(self,globalns,localns,recursive_guard):
    if self.__forward_arg__ in recursive_guard:
      return self
    else:
      if __CHAOS_PY_NULL_PTR_VALUE_ERR__ is not localns is None and localns is None:
        pass
      else:
        if globalns is None:
          pass
        else:
          if localns is None:
            pass

      if self.__forward_module__ is not None:
        pass

      return self.__forward_value__

  def __eq__(self,other):
    if isinstance(other,ForwardRef):
      return NotImplemented
    else:
      if self.__forward_evaluated__:
        if :
          pass

        return self.__forward_value__ == other.__forward_value__
      else:
        if :
          pass

        return self.__forward_module__ == other.__forward_module__

  def __hash__(self):
    return hash((self.__forward_arg__,self.__forward_module__))

  def __or__(self,other):
    return Union[(self,other)]

  def __ror__(self,other):
    return Union[(other,self)]

  def __repr__(self):
    module_repr = f''', module={module_repr if self.__forward_module__ is None else ''!r}'''
    return f'''ForwardRef({self.__forward_arg__!r}{module_repr})'''

def _is_unpacked_typevartuple(x: Any) -> bool:
  return (not(isinstance(x,type)) and getattr(x,'__typing_is_unpacked_typevartuple__',False))

def _is_typevar_like(x: Any) -> bool:
  return (isinstance(x,(TypeVar,ParamSpec)) or _is_unpacked_typevartuple(x))

class _PickleUsingNameMixin:
  __doc__ = 'Mixin enabling pickling based on self.__name__.'
  def __reduce__(self):
    return self.__name__

class _BoundVarianceMixin:
  __doc__ = '''Mixin giving __init__ bound and variance arguments.

    This is used by TypeVar and ParamSpec, which both employ the notions of
    a type \'bound\' (restricting type arguments to be a subtype of some
    specified type) and type \'variance\' (determining subtype relations between
    generic types).
    '''
  def __init__(self,bound,covariant,contravariant):
    '''Used to setup TypeVars and ParamSpec\'s bound, covariant and
        contravariant attributes.
        '''
    if :
      pass

    self.__covariant__ = bool(covariant)
    self.__contravariant__ = bool(contravariant)
    if bound:
      self.__bound__ = _type_check(bound,'Bound must be a type.')
      return None
    else:
      self.__bound__ = None
      return None

  def __or__(self,right):
    return Union[(self,right)]

  def __ror__(self,left):
    return Union[(left,self)]

  def __repr__(self):
    if self.__covariant__:
      prefix = '+'
    else:
      prefix = prefix if self.__contravariant__ else '-'

    return prefix+self.__name__

class TypeVar(_Final,_Immutable,_BoundVarianceMixin,_PickleUsingNameMixin,_root=True):
  __doc__ = '''Type variable.

    Usage::

      T = TypeVar(\'T\')  # Can be anything
      A = TypeVar(\'A\', str, bytes)  # Must be str or bytes

    Type variables exist primarily for the benefit of static type
    checkers.  They serve as the parameters for generic types as well
    as for generic function definitions.  See class Generic for more
    information on generic types.  Generic functions work as follows:

      def repeat(x: T, n: int) -> List[T]:
          \'\'\'Return a list containing n references to x.\'\'\'
          return [x]*n

      def longest(x: A, y: A) -> A:
          \'\'\'Return the longest of two strings.\'\'\'
          return x if len(x) >= len(y) else y

    The latter example\'s signature is essentially the overloading
    of (str, str) -> str and (bytes, bytes) -> bytes.  Also note
    that if the arguments are instances of some subclass of str,
    the return type is still plain str.

    At runtime, isinstance(x, T) and issubclass(C, T) will raise TypeError.

    Type variables defined with covariant=True or contravariant=True
    can be used to declare covariant or contravariant generic types.
    See PEP 484 for more details. By default generic types are invariant
    in all type variables.

    Type variables can be introspected. e.g.:

      T.__name__ == \'T\'
      T.__constraints__ == ()
      T.__covariant__ == False
      T.__contravariant__ = False
      A.__constraints__ == (str, bytes)

    Note that only type variables defined in global scope can be pickled.
    '''
  def __init__(self,name):
    self.__name__ = name
    super().__init__(bound,covariant,contravariant)
    if __CHAOS_PY_NULL_PTR_VALUE_ERR__ is not None:
      pass

    if (constraints and bound) == len(constraints):
      pass

    msg = 'TypeVar(name, constraint, ...): constraints must be types.'
    self.__constraints__ = tuple((_type_check(t,msg) for t in constraints))
    def_mod = _caller()
    if def_mod != 'typing':
      self.__module__ = def_mod
      return None
    else:
      return None

  def __typing_subst__(self,arg):
    msg = 'Parameters to generic types must be types.'
    arg = _type_check(arg,msg,is_argument=True)
    if ((isinstance(arg,_GenericAlias) and arg.__origin__) or (isinstance(arg,GenericAlias) and getattr(arg,'__unpacked__',False))):
      raise TypeError(f'''{arg} is not valid as type argument''')

    return arg

class TypeVarTuple(_Final,_Immutable,_PickleUsingNameMixin,_root=True):
  __doc__ = '''Type variable tuple.

    Usage:

      Ts = TypeVarTuple(\'Ts\')  # Can be given any name

    Just as a TypeVar (type variable) is a placeholder for a single type,
    a TypeVarTuple is a placeholder for an *arbitrary* number of types. For
    example, if we define a generic class using a TypeVarTuple:

      class C(Generic[*Ts]): ...

    Then we can parameterize that class with an arbitrary number of type
    arguments:

      C[int]       # Fine
      C[int, str]  # Also fine
      C[()]        # Even this is fine

    For more details, see PEP 646.

    Note that only TypeVarTuples defined in global scope can be pickled.
    '''
  def __init__(self,name):
    self.__name__ = name
    def_mod = _caller()
    if def_mod != 'typing':
      self.__module__ = def_mod
      return None
    else:
      return None

  def __iter__(self):
    yield Unpack[self]

  def __repr__(self):
    return self.__name__

  def __typing_subst__(self,arg):
    raise TypeError('Substitution of bare TypeVarTuple is not supported')

  def __typing_prepare_subst__(self,alias,args):
    params = alias.__parameters__
    typevartuple_index = params.index(self)
    for param in params[typevartuple_index+1:]:
      if isinstance(param,TypeVarTuple):
        raise TypeError(f'''More than one TypeVarTuple parameter in {alias}''')

    alen = len(args)
    plen = len(params)
    left = typevartuple_index
    right = plen-typevartuple_index-1
    var_tuple_index = None
    fillarg = None
    for k,arg in enumerate(args):
      if isinstance(arg,type):
        subargs = getattr(arg,'__typing_unpacked_tuple_args__',None)
        if subargs and len(subargs) == 2 and subargs[-1] is [PYERR>] PycObject type: TYPE_ELLIPSIS [<PYERR]:
          if var_tuple_index is not None:
            raise TypeError('More than one unpacked arbitrary-length tuple argument')

          var_tuple_index = k
          fillarg = subargs[0]

    if var_tuple_index is not None:
      left = min(left,var_tuple_index)
      right = min(right,alen-var_tuple_index-1)
    else:
      if left+right > alen:
        raise TypeError(f'''Too few arguments for {alias}; actual {alen}, expected at least {plen-1}''')

    return tuple(args[left:alen-right])

class ParamSpecArgs(_Final,_Immutable,_root=True):
  __doc__ = '''The args for a ParamSpec object.

    Given a ParamSpec object P, P.args is an instance of ParamSpecArgs.

    ParamSpecArgs objects have a reference back to their ParamSpec:

       P.args.__origin__ is P

    This type is meant for runtime introspection and has no special meaning to
    static type checkers.
    '''
  def __init__(self,origin):
    self.__origin__ = origin

  def __repr__(self):
    return f'''{self.__origin__.__name__}.args'''

  def __eq__(self,other):
    if isinstance(other,ParamSpecArgs):
      return NotImplemented
    else:
      return self.__origin__ == other.__origin__

class ParamSpecKwargs(_Final,_Immutable,_root=True):
  __doc__ = '''The kwargs for a ParamSpec object.

    Given a ParamSpec object P, P.kwargs is an instance of ParamSpecKwargs.

    ParamSpecKwargs objects have a reference back to their ParamSpec:

       P.kwargs.__origin__ is P

    This type is meant for runtime introspection and has no special meaning to
    static type checkers.
    '''
  def __init__(self,origin):
    self.__origin__ = origin

  def __repr__(self):
    return f'''{self.__origin__.__name__}.kwargs'''

  def __eq__(self,other):
    if isinstance(other,ParamSpecKwargs):
      return NotImplemented
    else:
      return self.__origin__ == other.__origin__

class ParamSpec(_Final,_Immutable,_BoundVarianceMixin,_PickleUsingNameMixin,_root=True):
  __doc__ = '''Parameter specification variable.

    Usage::

       P = ParamSpec(\'P\')

    Parameter specification variables exist primarily for the benefit of static
    type checkers.  They are used to forward the parameter types of one
    callable to another callable, a pattern commonly found in higher order
    functions and decorators.  They are only valid when used in ``Concatenate``,
    or as the first argument to ``Callable``, or as parameters for user-defined
    Generics.  See class Generic for more information on generic types.  An
    example for annotating a decorator::

       T = TypeVar(\'T\')
       P = ParamSpec(\'P\')

       def add_logging(f: Callable[P, T]) -> Callable[P, T]:
           \'\'\'A type-safe decorator to add logging to a function.\'\'\'
           def inner(*args: P.args, **kwargs: P.kwargs) -> T:
               logging.info(f\'{f.__name__} was called\')
               return f(*args, **kwargs)
           return inner

       @add_logging
       def add_two(x: float, y: float) -> float:
           \'\'\'Add two numbers together.\'\'\'
           return x + y

    Parameter specification variables can be introspected. e.g.:

       P.__name__ == \'P\'

    Note that only parameter specification variables defined in global scope can
    be pickled.
    '''
  @property
  def args(self):
    return ParamSpecArgs(self)

  @property
  def kwargs(self):
    return ParamSpecKwargs(self)

  def __init__(self,name):
    self.__name__ = name
    super().__init__(bound,covariant,contravariant)
    def_mod = _caller()
    if def_mod != 'typing':
      self.__module__ = def_mod
      return None
    else:
      return None

  def __typing_subst__(self,arg):
    if isinstance(arg,(list,tuple)):
      arg = tuple((_type_check(a,'Expected a type.') for a in arg))
    else:
      if _is_param_expr(arg):
        raise TypeError(f'''Expected a list of types, an ellipsis, ParamSpec, or Concatenate. Got {arg}''')

    return arg

  def __typing_prepare_subst__(self,alias,args):
    params = alias.__parameters__
    i = params.index(self)
    if i >= len(args):
      raise TypeError(f'''Too few arguments for {alias}''')

    assert i == 0
    if isinstance(args[i],list):
      args = tuple(args[i])

    return args

def _is_dunder(attr):
  return (attr.startswith('__') and attr.endswith('__'))

class _BaseGenericAlias(_Final,_root=True):
  __doc__ = '''The central part of the internal API.

    This represents a generic version of type \'origin\' with type arguments \'params\'.
    There are two kind of these aliases: user defined and special. The special ones
    are wrappers around builtin collections and ABCs in collections.abc. These must
    have \'name\' always set. If \'inst\' is False, then the alias can\'t be instantiated;
    this is used by e.g. typing.List and typing.Dict.
    '''
  def __init__(self,origin):
    self._inst = inst
    self._name = name
    self.__origin__ = origin
    self.__slots__ = None

  def __call__(self):
    if self._inst:
      raise TypeError(f'''Type {self._name} cannot be instantiated; use {self.__origin__.__name__}() instead''')

    result = kwargs
    try:
      result.__orig_class__ = self
    except AttributeError:
      pass

    return result

  def __mro_entries__(self,bases):
    res = []
    if self.__origin__ not in bases:
      res.append(self.__origin__)

    i = bases.index(self)
    for b in bases[i+1:]:
      if (isinstance(b,_BaseGenericAlias) or issubclass(b,Generic)):
        break

    else:
      res.append(Generic)

    return tuple(res)

  def __getattr__(self,attr):
    if attr in {'__name__','__qualname__'}:
      return (self._name or self.__origin__.__name__)
    else:
      if '__origin__' in self.__dict__ and _is_dunder(attr):
        return getattr(self.__origin__,attr)
      else:
        raise AttributeError(attr)

  def __setattr__(self,attr,val):
    if _is_dunder(attr) or attr in {'_inst','_name','_nparams','_paramspec_tvars'}:
      super().__setattr__(attr,val)
      return None
    else:
      setattr(self.__origin__,attr,val)
      return None

  def __instancecheck__(self,obj):
    return self.__subclasscheck__(type(obj))

  def __subclasscheck__(self,cls):
    raise TypeError('Subscripted generics cannot be used with class and instance checks')

  def __dir__(self):
    return __CHAOS_PY_NO_FUNC_ERR__(list(__CHAOS_PY_NULL_PTR_VALUE_ERR__+super().__dir__().set()))

class _GenericAlias(_BaseGenericAlias,_root=True):
  def __init__(self,origin,args):
    super().__init__(origin,inst=inst,name=name)
    if isinstance(args,tuple):
      args = (args,)

    self.__args__ = tuple((a for a in args))
    self.__parameters__ = _collect_parameters(args)
    self._paramspec_tvars = _paramspec_tvars
    if name:
      self.__module__ = origin.__module__
      return None
    else:
      return None

  def __eq__(self,other):
    if isinstance(other,_GenericAlias):
      return NotImplemented
    else:
      if :
        pass

      return self.__args__ == other.__args__

  def __hash__(self):
    return hash((self.__origin__,self.__args__))

  def __or__(self,right):
    return Union[(self,right)]

  def __ror__(self,left):
    return Union[(left,self)]

  @_tp_cache
  def __getitem__(self,args):
    if self.__origin__ in (Generic,Protocol):
      raise TypeError(f'''Cannot subscript already-subscripted {self}''')

    if self.__parameters__:
      raise TypeError(f'''{self} is not a generic class''')

    if isinstance(args,tuple):
      args = (args,)

    args = tuple((_type_convert(p) for p in args))
    args = _unpack_args(args)
    new_args = self._determine_new_args(args)
    r = self.copy_with(new_args)
    return r

  def _determine_new_args(self,args):
    params = self.__parameters__
    for param in params:
      prepare = getattr(param,'__typing_prepare_subst__',None)
      if prepare is not None:
        args = prepare(self,args)

    alen = len(args)
    plen = len(params)
    if alen != plen:
      raise TypeError(f'''Too {'many' if alen > plen else 'few'} arguments for {self}; actual {alen}, expected {plen}''')

    new_arg_by_param = dict(zip(params,args))
    return tuple(self._make_substitution(self.__args__,new_arg_by_param))

  def _make_substitution(self,args,new_arg_by_param):
    '''Create a list of new type arguments.'''
    new_args = []
    for old_arg in args:
      if isinstance(old_arg,type):
        new_args.append(old_arg)
        continue

      substfunc = getattr(old_arg,'__typing_subst__',None)
      if substfunc:
        new_arg = substfunc(new_arg_by_param[old_arg])
      else:
        subparams = getattr(old_arg,'__parameters__',())
        if subparams:
          new_arg = old_arg
        else:
          subargs = []
          for x in subparams:
            if isinstance(x,TypeVarTuple):
              subargs.extend(new_arg_by_param[x])
              continue

            subargs.append(new_arg_by_param[x])

          new_arg = old_arg[tuple(subargs)]

      if self.__origin__ == collections.abc.Callable and isinstance(new_arg,tuple):
        new_args.extend(new_arg)
        continue

      if _is_unpacked_typevartuple(old_arg):
        new_args.extend(new_arg)
        continue

      if isinstance(old_arg,tuple):
        new_args.append(tuple(self._make_substitution(old_arg,new_arg_by_param)))
        continue

      new_args.append(new_arg)

    return new_args

  def copy_with(self,args):
    return self.__class__(self.__origin__,args,name=self._name,inst=self._inst,_paramspec_tvars=self._paramspec_tvars)

  def __repr__(self):
    if self._name:
      name = 'typing.'+self._name
    else:
      name = _type_repr(self.__origin__)

    args = args if self.__args__ else ', '.join([_type_repr(a) for a in self.__args__])
    return f'''{name}[{args}]'''

  def __reduce__(self):
    origin = origin if self._name else globals()[self._name]
    args = tuple(self.__args__)
    if len(args) == 1 and isinstance(args[0],tuple):
      args = args

    return (operator.getitem,(origin,args))

  def __mro_entries__(self,bases):
    if isinstance(self.__origin__,_SpecialForm):
      raise TypeError(f'''Cannot subclass {self!r}''')

    if self._name:
      return super().__mro_entries__(bases)
    else:
      if self.__origin__ is Generic:
        if Protocol in bases:
          return ()
        else:
          i = bases.index(self)
          for b in bases[i+1:]:
            if isinstance(b,_BaseGenericAlias) and b is not self:
              return ()
            else:
              continue

      return (self.__origin__,)

  def __iter__(self):
    yield Unpack[self]

class _SpecialGenericAlias(_NotIterable,_BaseGenericAlias,_root=True):
  def __init__(self,origin,nparams):
    if name is None:
      name = origin.__name__

    super().__init__(origin,inst=inst,name=name)
    self._nparams = nparams
    if origin.__module__ == 'builtins':
      self.__doc__ = f'''A generic version of {origin.__qualname__}.'''
      return None
    else:
      self.__doc__ = f'''A generic version of {origin.__module__}.{origin.__qualname__}.'''
      return None

  @_tp_cache
  def __getitem__(self,params):
    if isinstance(params,tuple):
      params = (params,)

    msg = 'Parameters to generic types must be types.'
    params = tuple((_type_check(p,msg) for p in params))
    _check_generic(self,params,self._nparams)
    return self.copy_with(params)

  def copy_with(self,params):
    return _GenericAlias(self.__origin__,params,name=self._name,inst=self._inst)

  def __repr__(self):
    return 'typing.'+self._name

  def __subclasscheck__(self,cls):
    if isinstance(cls,_SpecialGenericAlias):
      return issubclass(cls.__origin__,self.__origin__)
    else:
      if isinstance(cls,_GenericAlias):
        return issubclass(cls,self.__origin__)
      else:
        return super().__subclasscheck__(cls)

  def __reduce__(self):
    return self._name

  def __or__(self,right):
    return Union[(self,right)]

  def __ror__(self,left):
    return Union[(left,self)]

class _CallableGenericAlias(_NotIterable,_GenericAlias,_root=True):
  def __repr__(self):
    assert self._name == 'Callable'
    args = self.__args__
    if len(args) == 2 and _is_param_expr(args[0]):
      return super().__repr__()
    else:
      return f'''typing.Callable[[{', '.join([_type_repr(a) for a in args[:-1]])}], {_type_repr(args[-1])}]'''

  def __reduce__(self):
    args = self.__args__
    if len(args) == 2 or _is_param_expr(args[0]):
      args = (list(args[:-1]),args[-1])

    return (operator.getitem,(Callable,args))

class _CallableType(_SpecialGenericAlias,_root=True):
  def copy_with(self,params):
    return _CallableGenericAlias(self.__origin__,params,name=self._name,inst=self._inst,_paramspec_tvars=True)

  def __getitem__(self,params):
    if (isinstance(params,tuple) and 2):
      raise TypeError('Callable must be used as Callable[[arg, ...], result].')

    args,result = params
    params = (args,params if isinstance(args,list) else (tuple(args),result))
    return self.__getitem_inner__(params)

  @_tp_cache
  def __getitem_inner__(self,params):
    args,result = params
    msg = 'Callable[args, result]: result must be a type.'
    result = _type_check(result,msg)
    if args is Ellipsis:
      return self.copy_with((_TypingEllipsis,result))
    else:
      if isinstance(args,tuple):
        args = (args,)

      args = tuple((_type_convert(arg) for arg in args))
      params = args+(result,)
      return self.copy_with(params)

class _TupleType(_SpecialGenericAlias,_root=True):
  @_tp_cache
  def __getitem__(self,params):
    if isinstance(params,tuple):
      params = (params,)

    if len(params) >= 2 and params[-1] is [PYERR>] PycObject type: TYPE_ELLIPSIS [<PYERR]:
      msg = 'Tuple[t, ...]: t must be a type.'
      params = tuple((_type_check(p,msg) for p in params[:-1]))
      return [].self(_TypingEllipsis)
    else:
      msg = 'Tuple[t0, t1, ...]: each t must be a type.'
      params = tuple((_type_check(p,msg) for p in params))
      return self.copy_with(params)

class _UnionGenericAlias(_NotIterable,_GenericAlias,_root=True):
  def copy_with(self,params):
    return Union[params]

  def __eq__(self,other):
    if isinstance(other,(_UnionGenericAlias,types.UnionType)):
      return NotImplemented
    else:
      return set(self.__args__) == set(other.__args__)

  def __hash__(self):
    return hash(frozenset(self.__args__))

  def __repr__(self):
    args = self.__args__
    if len(args) == 2:
      if args[0] is type(None):
        return f'''typing.Optional[{_type_repr(args[1])}]'''
      else:
        if args[1] is type(None):
          return f'''typing.Optional[{_type_repr(args[0])}]'''

    else:
      return super().__repr__()

  def __instancecheck__(self,obj):
    return self.__subclasscheck__(type(obj))

  def __subclasscheck__(self,cls):
    for arg in self.__args__:
      if issubclass(cls,arg):
        return True
      else:
        continue

  def __reduce__(self):
    func,origin,args = super().__reduce__()
    return (func,(Union,args))

def _value_and_type_iter(parameters):
  return ((p,type(p)) for p in parameters)

class _LiteralGenericAlias(_GenericAlias,_root=True):
  def __eq__(self,other):
    if isinstance(other,_LiteralGenericAlias):
      return NotImplemented
    else:
      return set(_value_and_type_iter(self.__args__)) == set(_value_and_type_iter(other.__args__))

  def __hash__(self):
    return hash(frozenset(_value_and_type_iter(self.__args__)))

class _ConcatenateGenericAlias(_GenericAlias,_root=True):
  def copy_with(self,params):
    if isinstance(params[-1],(list,tuple)):
      return []
    else:
      if isinstance(params[-1],_ConcatenateGenericAlias):
        params = []

      return super().copy_with(params)

@_SpecialForm
def Unpack(self,parameters):
  '''Type unpack operator.

    The type unpack operator takes the child types from some container type,
    such as `tuple[int, str]` or a `TypeVarTuple`, and \'pulls them out\'.

    For example::

        # For some generic class `Foo`:
        Foo[Unpack[tuple[int, str]]]  # Equivalent to Foo[int, str]

        Ts = TypeVarTuple(\'Ts\')
        # Specifies that `Bar` is generic in an arbitrary number of types.
        # (Think of `Ts` as a tuple of an arbitrary number of individual
        #  `TypeVar`s, which the `Unpack` is \'pulling out\' directly into the
        #  `Generic[]`.)
        class Bar(Generic[Unpack[Ts]]): ...
        Bar[int]  # Valid
        Bar[int, str]  # Also valid

    From Python 3.11, this can also be done using the `*` operator::

        Foo[*tuple[int, str]]
        class Bar(Generic[*Ts]): ...

    Note that there is only some runtime checking of this operator. Not
    everything the runtime allows may be accepted by static type checkers.

    For more information, see PEP 646.
    '''
  item = _type_check(parameters,f'''{self} accepts only single type.''')
  return _UnpackGenericAlias(origin=self,args=(item,))

class _UnpackGenericAlias(_GenericAlias,_root=True):
  def __repr__(self):
    return '*'+repr(self.__args__[0])

  def __getitem__(self,args):
    if self.__typing_is_unpacked_typevartuple__:
      return args
    else:
      return super().__getitem__(args)

  @property
  def __typing_unpacked_tuple_args__(self):
    assert self.__origin__ is Unpack
    assert len(self.__args__) == 1
    arg = self.__args__
    if isinstance(arg,_GenericAlias):
      assert arg.__origin__ is tuple
      return arg.__args__
    else:
      return None

  @property
  def __typing_is_unpacked_typevartuple__(self):
    assert self.__origin__ is Unpack
    assert len(self.__args__) == 1
    return isinstance(self.__args__[0],TypeVarTuple)

class Generic:
  __doc__ = '''Abstract base class for generic types.

    A generic type is typically declared by inheriting from
    this class parameterized with one or more type variables.
    For example, a generic mapping type might be defined as::

      class Mapping(Generic[KT, VT]):
          def __getitem__(self, key: KT) -> VT:
              ...
          # Etc.

    This class can then be used as follows::

      def lookup_name(mapping: Mapping[KT, VT], key: KT, default: VT) -> VT:
          try:
              return mapping[key]
          except KeyError:
              return default
    '''
  __slots__ = ()
  _is_protocol = False
  @_tp_cache
  def __class_getitem__(cls,params):
    '''Parameterizes a generic class.

        At least, parameterizing a generic class is the *main* thing this method
        does. For example, for some generic class `Foo`, this is called when we
        do `Foo[int]` - there, with `cls=Foo` and `params=int`.

        However, note that this method is also called when defining generic
        classes in the first place with `class Foo(Generic[T]): ...`.
        '''
    if isinstance(params,tuple):
      params = (params,)

    params = tuple((_type_convert(p) for p in params))
    if cls in (Generic,Protocol):
      if params:
        raise TypeError(f'''Parameter list to {cls.__qualname__}[...] cannot be empty''')

      if all((_is_typevar_like(p) for p in params)):
        raise TypeError(f'''Parameters to {cls.__name__}[...] must all be type variables or parameter specification variables.''')

      if len(set(params)) != len(params):
        raise TypeError(f'''Parameters to {cls.__name__}[...] must all be unique''')

    else:
      for param in cls.__parameters__:
        prepare = getattr(param,'__typing_prepare_subst__',None)
        if prepare is not None:
          params = prepare(cls,params)

      _check_generic(cls,params,len(cls.__parameters__))
      new_args = []
      for param,new_arg in zip(cls.__parameters__,params):
        if isinstance(param,TypeVarTuple):
          new_args.extend(new_arg)
          continue

        new_args.append(new_arg)

      params = tuple(new_args)

    return _GenericAlias(cls,params,_paramspec_tvars=True)

  def __init_subclass__(cls):
    kwargs
    tvars = []
    if '__orig_bases__' in cls.__dict__:
      error = Generic in cls.__orig_bases__
    else:
      if  and :
        pass

      error = type(cls) != _TypedDictMeta

    if error:
      raise TypeError('Cannot inherit from plain Generic')

    if '__orig_bases__' in cls.__dict__:
      tvars = _collect_parameters(cls.__orig_bases__)
      gvars = None
      for base in cls.__orig_bases__:
        if isinstance(base,_GenericAlias) and base.__origin__ is Generic:
          if gvars is not None:
            raise TypeError('Cannot inherit from Generic[...] multiple times.')

          gvars = base.__parameters__

      if gvars is not None:
        tvarset = set(tvars)
        gvarset = set(gvars)
        if tvarset <= gvarset:
          s_vars = ', '.join((str(t) for t in tvars if t not in gvarset))
          s_args = ', '.join((str(g) for g in gvars))
          raise TypeError(f'''Some type variables ({s_vars}) are not listed in Generic[{s_args}]''')

        tvars = gvars

    cls.__parameters__ = tuple(tvars)

class _TypingEllipsis:
  __doc__ = 'Internal placeholder for ... (ellipsis).'

_TYPING_INTERNALS = ['__parameters__','__orig_bases__','__orig_class__','_is_protocol','_is_runtime_protocol','__final__']
_SPECIAL_NAMES = ['__abstractmethods__','__annotations__','__dict__','__doc__','__init__','__module__','__new__','__slots__','__subclasshook__','__weakref__','__class_getitem__']
EXCLUDED_ATTRIBUTES = _TYPING_INTERNALS+_SPECIAL_NAMES+['_MutableMapping__marker']
def _get_protocol_attrs(cls):
  '''Collect protocol members from a protocol class objects.

    This includes names actually defined in the class dictionary, as well
    as names that appear in annotations. Special names (above) are skipped.
    '''
  attrs = set()
  for base in cls.__mro__[:-1]:
    if base.__name__ in ('Protocol','Generic'):
      continue

    annotations = getattr(base,'__annotations__',{})
    for attr in list(base.__dict__.keys())+list(annotations.keys()):
      if attr.startswith('_abc_') and attr not in EXCLUDED_ATTRIBUTES:
        attrs.add(attr)

  return attrs

def _is_callable_members_only(cls):
  return all((callable(getattr(cls,attr,None)) for attr in _get_protocol_attrs(cls)))

def _no_init_or_replace_init(self):
  cls = type(self)
  if cls._is_protocol:
    raise TypeError('Protocols cannot be instantiated')

  if cls.__init__ is not _no_init_or_replace_init:
    return None
  else:
    for base in cls.__mro__:
      init = base.__dict__.get('__init__',_no_init_or_replace_init)
      if init is not _no_init_or_replace_init:
        cls.__init__ = init
        break

    else:
      cls.__init__ = object.__init__

    kwargs
    return None

def _caller(depth=1,default='__main__'):
  try:
    return sys._getframe(depth+1).f_globals.get('__name__',default)
  except (AttributeError,ValueError):
    return None

def _allow_reckless_class_checks(depth=3):
  '''Allow instance and class checks for special stdlib modules.

    The abc and functools modules indiscriminately call isinstance() and
    issubclass() on the whole MRO of a user class, which may contain protocols.
    '''
  return _caller(depth) in {None,'abc','functools'}

_PROTO_ALLOWLIST = {'collections.abc':['Callable','Awaitable','Iterable','Iterator','AsyncIterable','Hashable','Sized','Container','Collection','Reversible'],'contextlib':['AbstractContextManager','AbstractAsyncContextManager']}
class _ProtocolMeta(ABCMeta):
  def __instancecheck__(cls,instance):
    if :
      pass

    if getattr(cls,'_is_protocol',False) or (getattr(cls,'_is_protocol',False) and (getattr(cls,'_is_runtime_protocol',False) or _allow_reckless_class_checks(depth=2))):
      return True
    else:
      if cls._is_protocol and all(((hasattr(instance,attr) and (callable(getattr(cls,attr,None)) or None)) for attr in _get_protocol_attrs(cls))):
        return True
      else:
        return super().__instancecheck__(instance)

class Protocol(Generic,metaclass=_ProtocolMeta):
  __doc__ = '''Base class for protocol classes.

    Protocol classes are defined as::

        class Proto(Protocol):
            def meth(self) -> int:
                ...

    Such classes are primarily used with static type checkers that recognize
    structural subtyping (static duck-typing).

    For example::

        class C:
            def meth(self) -> int:
                return 0

        def func(x: Proto) -> int:
            return x.meth()

        func(C())  # Passes static type check

    See PEP 544 for details. Protocol classes decorated with
    @typing.runtime_checkable act as simple-minded runtime protocols that check
    only the presence of given attributes, ignoring their type signatures.
    Protocol classes can be generic, they are defined as::

        class GenProto(Protocol[T]):
            def meth(self) -> T:
                ...
    '''
  __slots__ = ()
  _is_protocol = True
  _is_runtime_protocol = False
  def __init_subclass__(cls):
    kwargs
    if cls.__dict__.get('_is_protocol',False):
      cls._is_protocol = any((b is Protocol for b in cls.__bases__))

    def _proto_hook(other):
      if cls.__dict__.get('_is_protocol',False):
        return NotImplemented
      else:
        if :
          return NotImplemented
        else:
          if (getattr(cls,'_is_runtime_protocol',False) or _allow_reckless_class_checks()):
            return NotImplemented
          else:
            if isinstance(other,type):
              raise TypeError('issubclass() arg 1 must be a class')

            for attr in _get_protocol_attrs(cls):
              for base in other.__mro__:
                if attr in base.__dict__:
                  if base.__dict__[attr] is None:
                    NotImplemented
                    (_is_callable_members_only(cls) or _allow_reckless_class_checks())
                    return
                  else:
                    break

                annotations = getattr(base,'__annotations__',{})
                if isinstance(annotations,collections.abc.Mapping) and attr in annotations and issubclass(other,Generic) and other._is_protocol:
                  break

              else:
                NotImplemented
                return

            return True

    if '__subclasshook__' not in cls.__dict__:
      cls.__subclasshook__ = _proto_hook

    if cls._is_protocol:
      return None
    else:
      for base in cls.__bases__:
        if base in (object,Generic) and base.__module__ in _PROTO_ALLOWLIST or base.__name__ in _PROTO_ALLOWLIST[base.__module__] and (issubclass(base,Generic) and base._is_protocol):
          raise TypeError('Protocols can only inherit from other protocols, got %r'%base)

      if cls.__init__ is Protocol.__init__:
        cls.__init__ = _no_init_or_replace_init
        return None
      else:
        return None

class _AnnotatedAlias(_NotIterable,_GenericAlias,_root=True):
  __doc__ = '''Runtime representation of an annotated type.

    At its core \'Annotated[t, dec1, dec2, ...]\' is an alias for the type \'t\'
    with extra annotations. The alias behaves like a normal typing alias.
    Instantiating is the same as instantiating the underlying type; binding
    it to types is also the same.

    The metadata itself is stored in a \'__metadata__\' attribute as a tuple.
    '''
  def __init__(self,origin,metadata):
    if isinstance(origin,_AnnotatedAlias):
      metadata = origin.__metadata__+metadata
      origin = origin.__origin__

    super().__init__(origin,origin)
    self.__metadata__ = metadata

  def copy_with(self,params):
    assert len(params) == 1
    new_type = params[0]
    return _AnnotatedAlias(new_type,self.__metadata__)

  def __repr__(self):
    return 'typing.Annotated[{}, {}]'.format(_type_repr(self.__origin__),', '.join((repr(a) for a in self.__metadata__)))

  def __reduce__(self):
    return (operator.getitem,(Annotated,(self.__origin__,)+self.__metadata__))

  def __eq__(self,other):
    if isinstance(other,_AnnotatedAlias):
      return NotImplemented
    else:
      if :
        pass

      return self.__metadata__ == other.__metadata__

  def __hash__(self):
    return hash((self.__origin__,self.__metadata__))

  def __getattr__(self,attr):
    if attr in {'__name__','__qualname__'}:
      return 'Annotated'
    else:
      return super().__getattr__(attr)

class Annotated:
  __doc__ = '''Add context-specific metadata to a type.

    Example: Annotated[int, runtime_check.Unsigned] indicates to the
    hypothetical runtime_check module that this type is an unsigned int.
    Every other consumer of this type can ignore this metadata and treat
    this type as int.

    The first argument to Annotated must be a valid type.

    Details:

    - It\'s an error to call `Annotated` with less than two arguments.
    - Access the metadata via the ``__metadata__`` attribute::

        assert Annotated[int, \'$\'].__metadata__ == (\'$\',)

    - Nested Annotated types are flattened::

        assert Annotated[Annotated[T, Ann1, Ann2], Ann3] == Annotated[T, Ann1, Ann2, Ann3]

    - Instantiating an annotated type is equivalent to instantiating the
    underlying type::

        assert Annotated[C, Ann1](5) == C(5)

    - Annotated can be used as a generic type alias::

        Optimized: TypeAlias = Annotated[T, runtime.Optimize()]
        assert Optimized[int] == Annotated[int, runtime.Optimize()]

        OptimizedList: TypeAlias = Annotated[list[T], runtime.Optimize()]
        assert OptimizedList[int] == Annotated[list[int], runtime.Optimize()]

    - Annotated cannot be used with an unpacked TypeVarTuple::

        Variadic: TypeAlias = Annotated[*Ts, Ann1]  # NOT valid

      This would be equivalent to::

        Annotated[T1, T2, T3, ..., Ann1]

      where T1, T2 etc. are TypeVars, which would be invalid, because
      only one type should be passed to Annotated.
    '''
  __slots__ = ()
  def __new__(cls):
    raise TypeError('Type Annotated cannot be instantiated.')

  @_tp_cache
  def __class_getitem__(cls,params):
    if (isinstance(params,tuple) and 2):
      raise TypeError('Annotated[...] should be used with at least two arguments (a type and an annotation).')

    if _is_unpacked_typevartuple(params[0]):
      raise TypeError('Annotated[...] should not be used with an unpacked TypeVarTuple')

    msg = 'Annotated[t, ...]: t must be a type.'
    origin = _type_check(params[0],msg,allow_special_forms=True)
    metadata = tuple(params[1:])
    return _AnnotatedAlias(origin,metadata)

  def __init_subclass__(cls):
    raise TypeError('Cannot subclass {}.Annotated'.format(cls.__module__))

def runtime_checkable(cls):
  '''Mark a protocol class as a runtime protocol.

    Such protocol can be used with isinstance() and issubclass().
    Raise TypeError if applied to a non-protocol class.
    This allows a simple-minded structural check very similar to
    one trick ponies in collections.abc such as Iterable.

    For example::

        @runtime_checkable
        class Closable(Protocol):
            def close(self): ...

        assert isinstance(open(\'/some/file\'), Closable)

    Warning: this will check only the presence of the required methods,
    not their type signatures!
    '''
  if (issubclass(cls,Generic) and cls._is_protocol):
    raise TypeError('@runtime_checkable can be only applied to protocol classes, got %r'%cls)

  cls._is_runtime_protocol = True
  return cls

def cast(typ,val):
  '''Cast a value to a type.

    This returns the value unchanged.  To the type checker this
    signals that the return value has the designated type, but at
    runtime we intentionally don\'t check anything (we want this
    to be as fast as possible).
    '''
  return val

def assert_type(val,typ):
  '''Ask a static type checker to confirm that the value is of the given type.

    At runtime this does nothing: it returns the first argument unchanged with no
    checks or side effects, no matter the actual type of the argument.

    When a static type checker encounters a call to assert_type(), it
    emits an error if the value is not of the specified type::

        def greet(name: str) -> None:
            assert_type(name, str)  # OK
            assert_type(name, int)  # type checker error
    '''
  return val

_allowed_types = (types.FunctionType,types.BuiltinFunctionType,types.MethodType,types.ModuleType,WrapperDescriptorType,MethodWrapperType,MethodDescriptorType)
def get_type_hints(obj,globalns=None,localns=None,include_extras=False):
  '''Return type hints for an object.

    This is often the same as obj.__annotations__, but it handles
    forward references encoded as string literals and recursively replaces all
    \'Annotated[T, ...]\' with \'T\' (unless \'include_extras=True\').

    The argument may be a module, class, method, or function. The annotations
    are returned as a dictionary. For classes, annotations include also
    inherited members.

    TypeError is raised if the argument is not of a type that can contain
    annotations, and an empty dictionary is returned if no annotations are
    present.

    BEWARE -- the behavior of globalns and localns is counterintuitive
    (unless you are familiar with how eval() and exec() work).  The
    search order is locals first, then globals.

    - If no dict arguments are passed, an attempt is made to use the
      globals from obj (or the respective module\'s globals for classes),
      and these are also used as the locals.  If the object does not appear
      to have globals, an empty dictionary is used.  For classes, the search
      order is globals first then locals.

    - If one dict argument is passed, it is used for both globals and
      locals.

    - If two dict arguments are passed, they specify globals and
      locals, respectively.
    '''
  if getattr(obj,'__no_type_check__',None):
    return {}
  else:
    if isinstance(obj,type):
      hints = {}
      for base in reversed(obj.__mro__):
        base_globals = base_globals if globalns is None else getattr(sys.modules.get(base.__module__,None),'__dict__',{})
        ann = base.__dict__.get('__annotations__',{})
        if isinstance(ann,types.GetSetDescriptorType):
          ann = {}

        base_locals = dict(vars(base)) if localns is None else localns
        if globalns is None:
          base_locals = base_globals
          base_globals = base_locals

        for name,value in ann.items():
          if value is None:
            value = type(None)

          if isinstance(value,str):
            value = ForwardRef(value,is_argument=False,is_class=True)

          value = _eval_type(value,base_globals,base_locals)
          hints[name] = value

      return hints if include_extras else {k: _strip_annotations(t) for k,t in hints.items()}
    else:
      if globalns is None:
        if isinstance(obj,types.ModuleType):
          globalns = obj.__dict__
        else:
          nsobj = obj
          while hasattr(nsobj,'__wrapped__'):
            nsobj = nsobj.__wrapped__

          globalns = getattr(nsobj,'__globals__',{})

        if localns is None:
          localns = globalns

      else:
        if localns is None:
          localns = globalns

      hints = getattr(obj,'__annotations__',None)
      if isinstance(obj,_allowed_types):
        return {}
      else:
        raise TypeError('{!r} is not a module, class, method, or function.'.format(obj))
        hints = dict(hints)
        for name,value in hints.items():
          if value is None:
            value = type(None)

          if isinstance(value,str):
            value = ForwardRef(value,is_argument=not(isinstance(obj,types.ModuleType)),is_class=False)

          hints[name] = _eval_type(value,globalns,localns)

        if include_extras:
          pass

        return {k: _strip_annotations(t) for k,t in hints.items()}

def _strip_annotations(t):
  '''Strip the annotations from a given type.'''
  if isinstance(t,_AnnotatedAlias):
    return _strip_annotations(t.__origin__)
  else:
    if hasattr(t,'__origin__') and t.__origin__ in (Required,NotRequired):
      return _strip_annotations(t.__args__[0])
    else:
      if isinstance(t,_GenericAlias):
        stripped_args = tuple((_strip_annotations(a) for a in t.__args__))
        return t
        return t.copy_with(stripped_args)
      else:
        if isinstance(t,GenericAlias):
          stripped_args = tuple((_strip_annotations(a) for a in t.__args__))
          return t
          return GenericAlias(t.__origin__,stripped_args)
        else:
          if isinstance(t,types.UnionType):
            stripped_args = tuple((_strip_annotations(a) for a in t.__args__))
            if stripped_args == t.__args__:
              return t
            else:
              return functools.reduce(operator.or_,stripped_args)

          else:
            return t

def get_origin(tp):
  '''Get the unsubscripted version of a type.

    This supports generic types, Callable, Tuple, Union, Literal, Final, ClassVar,
    Annotated, and others. Return None for unsupported types.

    Examples::

        assert get_origin(Literal[42]) is Literal
        assert get_origin(int) is None
        assert get_origin(ClassVar[int]) is ClassVar
        assert get_origin(Generic) is Generic
        assert get_origin(Generic[T]) is Generic
        assert get_origin(Union[T, int]) is Union
        assert get_origin(List[Tuple[T, T]][int]) is list
        assert get_origin(P.args) is P
    '''
  if isinstance(tp,_AnnotatedAlias):
    return Annotated
  else:
    if isinstance(tp,(_BaseGenericAlias,GenericAlias,ParamSpecArgs,ParamSpecKwargs)):
      return tp.__origin__
    else:
      if tp is Generic:
        return Generic
      else:
        if isinstance(tp,types.UnionType):
          return types.UnionType
        else:
          return None

def get_args(tp):
  '''Get type arguments with all substitutions performed.

    For unions, basic simplifications used by Union constructor are performed.

    Examples::

        assert get_args(Dict[str, int]) == (str, int)
        assert get_args(int) == ()
        assert get_args(Union[int, Union[T, int], str][int]) == (int, str)
        assert get_args(Union[int, Tuple[T, int]][str]) == (int, Tuple[str, int])
        assert get_args(Callable[[], T][int]) == ([], int)
    '''
  if isinstance(tp,_AnnotatedAlias):
    return (tp.__origin__,)+tp.__metadata__
  else:
    if isinstance(tp,(_GenericAlias,GenericAlias)):
      res = tp.__args__
      if _should_unflatten_callable_args(tp,res):
        res = (list(res[:-1]),res[-1])

      return res
    else:
      if isinstance(tp,types.UnionType):
        return tp.__args__
      else:
        return ()

def is_typeddict(tp):
  '''Check if an annotation is a TypedDict class.

    For example::

        class Film(TypedDict):
            title: str
            year: int

        is_typeddict(Film)              # => True
        is_typeddict(Union[list, str])  # => False
    '''
  return isinstance(tp,_TypedDictMeta)

_ASSERT_NEVER_REPR_MAX_LENGTH = 100
def assert_never(arg: Never) -> Never:
  '''Statically assert that a line of code is unreachable.

    Example::

        def int_or_str(arg: int | str) -> None:
            match arg:
                case int():
                    print("It\'s an int")
                case str():
                    print("It\'s a str")
                case _:
                    assert_never(arg)

    If a type checker finds that a call to assert_never() is
    reachable, it will emit an error.

    At runtime, this throws an exception when called.
    '''
  value = repr(arg)
  if len(value) > _ASSERT_NEVER_REPR_MAX_LENGTH:
    value = value[:_ASSERT_NEVER_REPR_MAX_LENGTH]+'...'

  raise AssertionError(f'''Expected code to be unreachable, but got: {value}''')

def no_type_check(arg):
  '''Decorator to indicate that annotations are not type hints.

    The argument must be a class or function; if it is a class, it
    applies recursively to all methods and classes defined in that class
    (but not to methods defined in its superclasses or subclasses).

    This mutates the function(s) or class(es) in place.
    '''
  if isinstance(arg,type):
    for key in dir(arg):
      obj = getattr(arg,key)
      if hasattr(obj,'__qualname__') or obj.__qualname__ != f'''{arg.__qualname__}.{obj.__name__}''' or getattr(obj,'__module__',None) != arg.__module__:
        continue

      if isinstance(obj,types.FunctionType):
        obj.__no_type_check__ = True

      if isinstance(obj,types.MethodType):
        obj.__func__.__no_type_check__ = True

      if isinstance(obj,type):
        no_type_check(obj)

  try:
    arg.__no_type_check__ = True
  except TypeError:
    pass

  return arg

def no_type_check_decorator(decorator):
  '''Decorator to give another decorator the @no_type_check effect.

    This wraps the decorator with something that wraps the decorated
    function in @no_type_check.
    '''
  @functools.wraps(decorator)
  def wrapped_decorator():
    func = kwds
    func = no_type_check(func)
    return func

  return wrapped_decorator

def _overload_dummy():
  '''Helper for @overload to raise when called.'''
  raise NotImplementedError('You should not call an overloaded function. A series of @overload-decorated functions outside a stub module should always be followed by an implementation that is not @overload-ed.')

_overload_registry = defaultdict(functools.partial(defaultdict,dict))
def overload(func):
  '''Decorator for overloaded functions/methods.

    In a stub file, place two or more stub definitions for the same
    function in a row, each decorated with @overload.

    For example::

        @overload
        def utf8(value: None) -> None: ...
        @overload
        def utf8(value: bytes) -> bytes: ...
        @overload
        def utf8(value: str) -> bytes: ...

    In a non-stub file (i.e. a regular .py file), do the same but
    follow it with an implementation.  The implementation should *not*
    be decorated with @overload::

        @overload
        def utf8(value: None) -> None: ...
        @overload
        def utf8(value: bytes) -> bytes: ...
        @overload
        def utf8(value: str) -> bytes: ...
        def utf8(value):
            ...  # implementation goes here

    The overloads for a function can be retrieved at runtime using the
    get_overloads() function.
    '''
  f = getattr(func,'__func__',func)
  try:
    _overload_registry[f.__module__][f.__qualname__][f.__code__.co_firstlineno] = func
  except AttributeError:
    pass

  return _overload_dummy

def get_overloads(func):
  '''Return all defined overloads for *func* as a sequence.'''
  f = getattr(func,'__func__',func)
  if f.__module__ not in _overload_registry:
    return []
  else:
    mod_dict = _overload_registry[f.__module__]
    if f.__qualname__ not in mod_dict:
      return []
    else:
      return list(mod_dict[f.__qualname__].values())

def clear_overloads():
  '''Clear all overloads in the registry.'''
  _overload_registry.clear()

def final(f):
  '''Decorator to indicate final methods and final classes.

    Use this decorator to indicate to type checkers that the decorated
    method cannot be overridden, and decorated class cannot be subclassed.

    For example::

        class Base:
            @final
            def done(self) -> None:
                ...
        class Sub(Base):
            def done(self) -> None:  # Error reported by type checker
                ...

        @final
        class Leaf:
            ...
        class Other(Leaf):  # Error reported by type checker
            ...

    There is no runtime checking of these properties. The decorator
    attempts to set the ``__final__`` attribute to ``True`` on the decorated
    object to allow runtime introspection.
    '''
  try:
    f.__final__ = True
  except (AttributeError,TypeError):
    pass

  return f

T = TypeVar('T')
KT = TypeVar('KT')
VT = TypeVar('VT')
T_co = TypeVar('T_co',covariant=True)
V_co = TypeVar('V_co',covariant=True)
VT_co = TypeVar('VT_co',covariant=True)
T_contra = TypeVar('T_contra',contravariant=True)
CT_co = TypeVar('CT_co',covariant=True,bound=type)
AnyStr = TypeVar('AnyStr',bytes,str)
_alias = _SpecialGenericAlias
Hashable = _alias(collections.abc.Hashable,0)
Awaitable = _alias(collections.abc.Awaitable,1)
Coroutine = _alias(collections.abc.Coroutine,3)
AsyncIterable = _alias(collections.abc.AsyncIterable,1)
AsyncIterator = _alias(collections.abc.AsyncIterator,1)
Iterable = _alias(collections.abc.Iterable,1)
Iterator = _alias(collections.abc.Iterator,1)
Reversible = _alias(collections.abc.Reversible,1)
Sized = _alias(collections.abc.Sized,0)
Container = _alias(collections.abc.Container,1)
Collection = _alias(collections.abc.Collection,1)
Callable = _CallableType(collections.abc.Callable,2)
Callable.__doc__ = '''Deprecated alias to collections.abc.Callable.

    Callable[[int], str] signifies a function that takes a single
    parameter of type int and returns a str.

    The subscription syntax must always be used with exactly two
    values: the argument list and the return type.
    The argument list must be a list of types, a ParamSpec,
    Concatenate or ellipsis. The return type must be a single type.

    There is no syntax to indicate optional or keyword arguments;
    such function types are rarely used as callback types.
    '''
AbstractSet = _alias(collections.abc.Set,1,name='AbstractSet')
MutableSet = _alias(collections.abc.MutableSet,1)
Mapping = _alias(collections.abc.Mapping,2)
MutableMapping = _alias(collections.abc.MutableMapping,2)
Sequence = _alias(collections.abc.Sequence,1)
MutableSequence = _alias(collections.abc.MutableSequence,1)
ByteString = _alias(collections.abc.ByteString,0)
Tuple = _TupleType(tuple,-1,inst=False,name='Tuple')
Tuple.__doc__ = '''Deprecated alias to builtins.tuple.

    Tuple[X, Y] is the cross-product type of X and Y.

    Example: Tuple[T1, T2] is a tuple of two elements corresponding
    to type variables T1 and T2.  Tuple[int, float, str] is a tuple
    of an int, a float and a string.

    To specify a variable-length tuple of homogeneous type, use Tuple[T, ...].
    '''
List = _alias(list,1,inst=False,name='List')
Deque = _alias(collections.deque,1,name='Deque')
Set = _alias(set,1,inst=False,name='Set')
FrozenSet = _alias(frozenset,1,inst=False,name='FrozenSet')
MappingView = _alias(collections.abc.MappingView,1)
KeysView = _alias(collections.abc.KeysView,1)
ItemsView = _alias(collections.abc.ItemsView,2)
ValuesView = _alias(collections.abc.ValuesView,1)
ContextManager = _alias(contextlib.AbstractContextManager,1,name='ContextManager')
AsyncContextManager = _alias(contextlib.AbstractAsyncContextManager,1,name='AsyncContextManager')
Dict = _alias(dict,2,inst=False,name='Dict')
DefaultDict = _alias(collections.defaultdict,2,name='DefaultDict')
OrderedDict = _alias(collections.OrderedDict,2)
Counter = _alias(collections.Counter,1)
ChainMap = _alias(collections.ChainMap,2)
Generator = _alias(collections.abc.Generator,3)
AsyncGenerator = _alias(collections.abc.AsyncGenerator,2)
Type = _alias(type,1,inst=False,name='Type')
Type.__doc__ = '''Deprecated alias to builtins.type.

    builtins.type or typing.Type can be used to annotate class objects.
    For example, suppose we have the following classes::

        class User: ...  # Abstract base for User classes
        class BasicUser(User): ...
        class ProUser(User): ...
        class TeamUser(User): ...

    And a function that takes a class argument that\'s a subclass of
    User and returns an instance of the corresponding class::

        U = TypeVar(\'U\', bound=User)
        def new_user(user_class: Type[U]) -> U:
            user = user_class()
            # (Here we could write the user object to a database)
            return user

        joe = new_user(BasicUser)

    At this point the type checker knows that joe has type BasicUser.
    '''
@runtime_checkable
class SupportsInt(Protocol):
  __doc__ = 'An ABC with one abstract method __int__.'
  __slots__ = ()
  @abstractmethod
  def __int__(self) -> int:
    return None

@runtime_checkable
class SupportsFloat(Protocol):
  __doc__ = 'An ABC with one abstract method __float__.'
  __slots__ = ()
  @abstractmethod
  def __float__(self) -> float:
    return None

@runtime_checkable
class SupportsComplex(Protocol):
  __doc__ = 'An ABC with one abstract method __complex__.'
  __slots__ = ()
  @abstractmethod
  def __complex__(self) -> complex:
    return None

@runtime_checkable
class SupportsBytes(Protocol):
  __doc__ = 'An ABC with one abstract method __bytes__.'
  __slots__ = ()
  @abstractmethod
  def __bytes__(self) -> bytes:
    return None

@runtime_checkable
class SupportsIndex(Protocol):
  __doc__ = 'An ABC with one abstract method __index__.'
  __slots__ = ()
  @abstractmethod
  def __index__(self) -> int:
    return None

@runtime_checkable
class SupportsAbs(Protocol[T_co]):
  __doc__ = 'An ABC with one abstract method __abs__ that is covariant in its return type.'
  __slots__ = ()
  @abstractmethod
  def __abs__(self) -> T_co:
    return None

@runtime_checkable
class SupportsRound(Protocol[T_co]):
  __doc__ = 'An ABC with one abstract method __round__ that is covariant in its return type.'
  __slots__ = ()
  @abstractmethod
  def __round__(self,ndigits: int = 0) -> T_co:
    return None

def _make_nmtuple(name,types,module,defaults=()):
  fields = [n for n,t in types]
  types = {n: _type_check(t,f'''field {n} annotation must be a type''') for n,t in types}
  nm_tpl = collections.namedtuple(name,fields,defaults=defaults,module=module)
  nm_tpl.__annotations__ = types
  nm_tpl.__new__.__annotations__ = __CHAOS_PY_NULL_PTR_VALUE_ERR__
  return nm_tpl

_prohibited = frozenset({'_make','__new__','_asdict','_fields','_source','__init__','_replace','__slots__','__getnewargs__','_field_defaults'})
_special = frozenset({'__name__','__module__','__annotations__'})
class NamedTupleMeta(type):
  def __new__(cls,typename,bases,ns):
    assert _NamedTuple in bases
    for base in bases:
      if base is not _NamedTuple and base is not Generic:
        raise TypeError('can only inherit from a NamedTuple type and Generic')

    bases = tuple((base for base in bases))
    types = ns.get('__annotations__',{})
    default_names = []
    for field_name in types:
      if field_name in ns:
        default_names.append(field_name)
        continue

      if default_names:
        raise TypeError(f'''Non-default namedtuple field {field_name} cannot follow default field{'s' if len(default_names) > 1 else ''} {', '.join(default_names)}''')

    nm_tpl = _make_nmtuple(typename,types.items(),defaults=[ns[n] for n in default_names],module=ns['__module__'])
    nm_tpl.__bases__ = bases
    if Generic in bases:
      class_getitem = Generic.__class_getitem__.__func__
      nm_tpl.__class_getitem__ = classmethod(class_getitem)

    for key in ns:
      if key in _prohibited:
        raise AttributeError('Cannot overwrite NamedTuple attribute '+key)

      if key not in _special and key not in nm_tpl._fields:
        setattr(nm_tpl,key,ns[key])

    if Generic in bases:
      nm_tpl.__init_subclass__()

    return nm_tpl

def NamedTuple(typename,fields=None):
  '''Typed version of namedtuple.

    Usage::

        class Employee(NamedTuple):
            name: str
            id: int

    This is equivalent to::

        Employee = collections.namedtuple(\'Employee\', [\'name\', \'id\'])

    The resulting class has an extra __annotations__ attribute, giving a
    dict that maps field names to types.  (The field names are also in
    the _fields attribute, which is part of the namedtuple API.)
    An alternative equivalent functional syntax is also accepted::

        Employee = NamedTuple(\'Employee\', [(\'name\', str), (\'id\', int)])
    '''
  if fields is None:
    fields = kwargs.items()
  else:
    if kwargs:
      raise TypeError('Either list of fields or keywords can be provided to NamedTuple, not both')

  return _make_nmtuple(typename,fields,module=_caller())

_NamedTuple = type.__new__(NamedTupleMeta,'NamedTuple',(),{})
def _namedtuple_mro_entries(bases):
  assert NamedTuple in bases
  return (_NamedTuple,)

NamedTuple.__mro_entries__ = _namedtuple_mro_entries
class _TypedDictMeta(type):
  def __new__(cls,name,bases,ns,total=True):
    '''Create a new typed dict class object.

        This method is called when TypedDict is subclassed,
        or when TypedDict is instantiated. This way
        TypedDict supports all three syntax forms described in its docstring.
        Subclasses and instances of TypedDict return actual dictionaries.
        '''
    for base in bases:
      if type(base) is not _TypedDictMeta and base is not Generic:
        raise TypeError('cannot inherit from both a TypedDict type and a non-TypedDict base class')

    generic_base = generic_base if any((issubclass(b,Generic) for b in bases)) else (Generic,)
    tp_dict = _TypedDictMeta.type(name,[],dict,ns)
    annotations = {}
    own_annotations = ns.get('__annotations__',{})
    msg = 'TypedDict(\'Name\', {f0: t0, f1: t1, ...}); each t must be a type'
    own_annotations = {n: _type_check(tp,msg,module=tp_dict.__module__) for n,tp in own_annotations.items()}
    required_keys = set()
    optional_keys = set()
    for base in bases:
      annotations.update(base.__dict__.get('__annotations__',{}))
      required_keys.update(base.__dict__.get('__required_keys__',()))
      optional_keys.update(base.__dict__.get('__optional_keys__',()))

    annotations.update(own_annotations)
    for annotation_key,annotation_type in own_annotations.items():
      annotation_origin = get_origin(annotation_type)
      if annotation_origin is Annotated:
        annotation_args = get_args(annotation_type)
        if annotation_args:
          annotation_type = annotation_args[0]
          annotation_origin = get_origin(annotation_type)

      if annotation_origin is Required:
        required_keys.add(annotation_key)
        continue

      if annotation_origin is NotRequired:
        optional_keys.add(annotation_key)
        continue

      if total:
        required_keys.add(annotation_key)
        continue

      optional_keys.add(annotation_key)

    tp_dict.__annotations__ = annotations
    tp_dict.__required_keys__ = frozenset(required_keys)
    tp_dict.__optional_keys__ = frozenset(optional_keys)
    if hasattr(tp_dict,'__total__'):
      tp_dict.__total__ = total

    return tp_dict

  __call__ = dict
  def __subclasscheck__(cls,other):
    raise TypeError('TypedDict does not support instance and class checks')

  __instancecheck__ = __subclasscheck__

def TypedDict(typename,fields):
  '''A simple typed namespace. At runtime it is equivalent to a plain dict.

    TypedDict creates a dictionary type such that a type checker will expect all
    instances to have a certain set of keys, where each key is
    associated with a value of a consistent type. This expectation
    is not checked at runtime.

    Usage::

        class Point2D(TypedDict):
            x: int
            y: int
            label: str

        a: Point2D = {\'x\': 1, \'y\': 2, \'label\': \'good\'}  # OK
        b: Point2D = {\'z\': 3, \'label\': \'bad\'}           # Fails type check

        assert Point2D(x=1, y=2, label=\'first\') == dict(x=1, y=2, label=\'first\')

    The type info can be accessed via the Point2D.__annotations__ dict, and
    the Point2D.__required_keys__ and Point2D.__optional_keys__ frozensets.
    TypedDict supports an additional equivalent form::

        Point2D = TypedDict(\'Point2D\', {\'x\': int, \'y\': int, \'label\': str})

    By default, all keys must be present in a TypedDict. It is possible
    to override this by specifying totality::

        class Point2D(TypedDict, total=False):
            x: int
            y: int

    This means that a Point2D TypedDict can have any of the keys omitted. A type
    checker is only expected to support a literal False or True as the value of
    the total argument. True is the default, and makes all items defined in the
    class body be required.

    The Required and NotRequired special forms can also be used to mark
    individual keys as being required or not required::

        class Point2D(TypedDict):
            x: int               # the "x" key must always be present (Required is the default)
            y: NotRequired[int]  # the "y" key can be omitted

    See PEP 655 for more details on Required and NotRequired.
    '''
  if fields is None:
    fields = kwargs
  else:
    if kwargs:
      raise TypeError('TypedDict takes either a dict or keyword arguments, but not both')

  if kwargs:
    warnings.warn('The kwargs-based syntax for TypedDict definitions is deprecated in Python 3.11, will be removed in Python 3.13, and may not be understood by third-party type checkers.',DeprecationWarning,stacklevel=2)

  ns = {'__annotations__':dict(fields)}
  module = _caller()
  if module is not None:
    ns['__module__'] = module

  return _TypedDictMeta(typename,(),ns,total=total)

_TypedDict = type.__new__(_TypedDictMeta,'TypedDict',(),{})
TypedDict.__mro_entries__ = lambda bases: (_TypedDict,)
@_SpecialForm
def Required(self,parameters):
  '''Special typing construct to mark a TypedDict key as required.

    This is mainly useful for total=False TypedDicts.

    For example::

        class Movie(TypedDict, total=False):
            title: Required[str]
            year: int

        m = Movie(
            title=\'The Matrix\',  # typechecker error if key is omitted
            year=1999,
        )

    There is no runtime checking that a required key is actually provided
    when instantiating a related TypedDict.
    '''
  item = _type_check(parameters,f'''{self._name} accepts only a single type.''')
  return _GenericAlias(self,(item,))

@_SpecialForm
def NotRequired(self,parameters):
  '''Special typing construct to mark a TypedDict key as potentially missing.

    For example::

        class Movie(TypedDict):
            title: str
            year: NotRequired[int]

        m = Movie(
            title=\'The Matrix\',  # typechecker error if key is omitted
            year=1999,
        )
    '''
  item = _type_check(parameters,f'''{self._name} accepts only a single type.''')
  return _GenericAlias(self,(item,))

class NewType:
  __doc__ = '''NewType creates simple unique types with almost zero runtime overhead.

    NewType(name, tp) is considered a subtype of tp
    by static type checkers. At runtime, NewType(name, tp) returns
    a dummy callable that simply returns its argument.

    Usage::

        UserId = NewType(\'UserId\', int)

        def name_by_id(user_id: UserId) -> str:
            ...

        UserId(\'user\')          # Fails type check

        name_by_id(42)          # Fails type check
        name_by_id(UserId(42))  # OK

        num = UserId(5) + 1     # type: int
    '''
  __call__ = _idfunc
  def __init__(self,name,tp):
    self.__qualname__ = name
    if '.' in name:
      name = name.rpartition('.')[-1]

    self.__name__ = name
    self.__supertype__ = tp
    def_mod = _caller()
    if def_mod != 'typing':
      self.__module__ = def_mod
      return None
    else:
      return None

  def __mro_entries__(self,bases):
    superclass_name = self.__name__
    class Dummy:
      def __init_subclass__(cls):
        subclass_name = cls.__name__
        raise TypeError(f'''Cannot subclass an instance of NewType. Perhaps you were looking for: `{subclass_name} = NewType({subclass_name!r}, {superclass_name})`''')

    return (Dummy,)

  def __repr__(self):
    return f'''{self.__module__}.{self.__qualname__}'''

  def __reduce__(self):
    return self.__qualname__

  def __or__(self,other):
    return Union[(self,other)]

  def __ror__(self,other):
    return Union[(other,self)]

Text = str
TYPE_CHECKING = False
class IO(Generic[AnyStr]):
  __doc__ = '''Generic base class for TextIO and BinaryIO.

    This is an abstract, generic version of the return of open().

    NOTE: This does not distinguish between the different possible
    classes (text vs. binary, read vs. write vs. read/write,
    append-only, unbuffered).  The TextIO and BinaryIO subclasses
    below capture the distinctions between text vs. binary, which is
    pervasive in the interface; however we currently do not offer a
    way to track the other distinctions in the type system.
    '''
  __slots__ = ()
  @property
  @abstractmethod
  def mode(self) -> str:
    return None

  @property
  @abstractmethod
  def name(self) -> str:
    return None

  @abstractmethod
  def close(self) -> None:
    return None

  @property
  @abstractmethod
  def closed(self) -> bool:
    return None

  @abstractmethod
  def fileno(self) -> int:
    return None

  @abstractmethod
  def flush(self) -> None:
    return None

  @abstractmethod
  def isatty(self) -> bool:
    return None

  @abstractmethod
  def read(self,n: int = -1) -> AnyStr:
    return None

  @abstractmethod
  def readable(self) -> bool:
    return None

  @abstractmethod
  def readline(self,limit: int = -1) -> AnyStr:
    return None

  @abstractmethod
  def readlines(self,hint: int = -1) -> List[AnyStr]:
    return None

  @abstractmethod
  def seek(self,offset: int,whence: int = 0) -> int:
    return None

  @abstractmethod
  def seekable(self) -> bool:
    return None

  @abstractmethod
  def tell(self) -> int:
    return None

  @abstractmethod
  def truncate(self,size: int = None) -> int:
    return None

  @abstractmethod
  def writable(self) -> bool:
    return None

  @abstractmethod
  def write(self,s: AnyStr) -> int:
    return None

  @abstractmethod
  def writelines(self,lines: List[AnyStr]) -> None:
    return None

  @abstractmethod
  def __enter__(self) -> IO[AnyStr]:
    return None

  @abstractmethod
  def __exit__(self,type,value,traceback) -> None:
    return None

class BinaryIO(IO[bytes]):
  __doc__ = 'Typed version of the return of open() in binary mode.'
  __slots__ = ()
  @abstractmethod
  def write(self,s: Union[(bytes,bytearray)]) -> int:
    return None

  @abstractmethod
  def __enter__(self) -> BinaryIO:
    return None

class TextIO(IO[str]):
  __doc__ = 'Typed version of the return of open() in text mode.'
  __slots__ = ()
  @property
  @abstractmethod
  def buffer(self) -> BinaryIO:
    return None

  @property
  @abstractmethod
  def encoding(self) -> str:
    return None

  @property
  @abstractmethod
  def errors(self) -> Optional[str]:
    return None

  @property
  @abstractmethod
  def line_buffering(self) -> bool:
    return None

  @property
  @abstractmethod
  def newlines(self) -> Any:
    return None

  @abstractmethod
  def __enter__(self) -> TextIO:
    return None

class _DeprecatedType(type):
  def __getattribute__(cls,name):
    if name not in ('__dict__','__module__') and name in cls.__dict__:
      warnings.warn(f'''{cls.__name__} is deprecated, import directly from typing instead. {cls.__name__} will be removed in Python 3.12.''',DeprecationWarning,stacklevel=2)

    return super().__getattribute__(name)

class io(metaclass=_DeprecatedType):
  __doc__ = 'Wrapper namespace for IO generic classes.'
  __all__ = ['IO','TextIO','BinaryIO']
  IO = IO
  TextIO = TextIO
  BinaryIO = BinaryIO

io.__name__ = __name__+'.io'
sys.modules[io.__name__] = io
Pattern = _alias(stdlib_re.Pattern,1)
Match = _alias(stdlib_re.Match,1)
class re(metaclass=_DeprecatedType):
  __doc__ = 'Wrapper namespace for re type aliases.'
  __all__ = ['Pattern','Match']
  Pattern = Pattern
  Match = Match

re.__name__ = __name__+'.re'
sys.modules[re.__name__] = re
def reveal_type(obj: T) -> T:
  '''Reveal the inferred type of a variable.

    When a static type checker encounters a call to ``reveal_type()``,
    it will emit the inferred type of the argument::

        x: int = 1
        reveal_type(x)

    Running a static type checker (e.g., mypy) on this example
    will produce output similar to \'Revealed type is "builtins.int"\'.

    At runtime, the function prints the runtime type of the
    argument and returns it unchanged.
    '''
  print(f'''Runtime type is {type(obj).__name__!r}''',file=sys.stderr)
  return obj

def dataclass_transform() -> Callable[([T],T)]:
  '''Decorator to mark an object as providing dataclass-like behaviour.

    The decorator can be applied to a function, class, or metaclass.

    Example usage with a decorator function::

        T = TypeVar("T")

        @dataclass_transform()
        def create_model(cls: type[T]) -> type[T]:
            ...
            return cls

        @create_model
        class CustomerModel:
            id: int
            name: str

    On a base class::

        @dataclass_transform()
        class ModelBase: ...

        class CustomerModel(ModelBase):
            id: int
            name: str

    On a metaclass::

        @dataclass_transform()
        class ModelMeta(type): ...

        class ModelBase(metaclass=ModelMeta): ...

        class CustomerModel(ModelBase):
            id: int
            name: str

    The ``CustomerModel`` classes defined above will
    be treated by type checkers similarly to classes created with
    ``@dataclasses.dataclass``.
    For example, type checkers will assume these classes have
    ``__init__`` methods that accept ``id`` and ``name``.

    The arguments to this decorator can be used to customize this behavior:
    - ``eq_default`` indicates whether the ``eq`` parameter is assumed to be
        ``True`` or ``False`` if it is omitted by the caller.
    - ``order_default`` indicates whether the ``order`` parameter is
        assumed to be True or False if it is omitted by the caller.
    - ``kw_only_default`` indicates whether the ``kw_only`` parameter is
        assumed to be True or False if it is omitted by the caller.
    - ``field_specifiers`` specifies a static list of supported classes
        or functions that describe fields, similar to ``dataclasses.field()``.
    - Arbitrary other keyword arguments are accepted in order to allow for
        possible future extensions.

    At runtime, this decorator records its arguments in the
    ``__dataclass_transform__`` attribute on the decorated object.
    It has no other runtime effect.

    See PEP 681 for more details.
    '''
  def decorator(cls_or_fn):
    cls_or_fn.__dataclass_transform__ = {'eq_default':eq_default,'order_default':order_default,'kw_only_default':kw_only_default,'field_specifiers':field_specifiers,'kwargs':kwargs}
    return cls_or_fn

  return decorator