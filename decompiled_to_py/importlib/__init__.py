__doc__ = 'A pure Python implementation of import.'
__all__ = ['__import__','import_module','invalidate_caches','reload']
import _imp
import sys
try:
  import _frozen_importlib as _bootstrap
except ImportError:
  from . import _bootstrap
  _bootstrap._setup(sys,_imp)

_bootstrap.__name__ = 'importlib._bootstrap'
_bootstrap.__package__ = 'importlib'
try:
  _bootstrap.__file__ = __file__.replace('__init__.py','_bootstrap.py')
except NameError:
  pass

sys.modules['importlib._bootstrap'] = _bootstrap
try:
  import _frozen_importlib_external as _bootstrap_external
except ImportError:
  from . import _bootstrap_external
  _bootstrap_external._set_bootstrap_module(_bootstrap)
  _bootstrap._bootstrap_external = _bootstrap_external

_bootstrap_external.__name__ = 'importlib._bootstrap_external'
_bootstrap_external.__package__ = 'importlib'
try:
  _bootstrap_external.__file__ = __file__.replace('__init__.py','_bootstrap_external.py')
except NameError:
  pass

sys.modules['importlib._bootstrap_external'] = _bootstrap_external
_pack_uint32 = _bootstrap_external._pack_uint32
_unpack_uint32 = _bootstrap_external._unpack_uint32
import warnings
from ._bootstrap import __import__
def invalidate_caches():
  '''Call the invalidate_caches() method on all meta path finders stored in\n    sys.meta_path (where implemented).'''
  for finder in sys.meta_path:
    if hasattr(finder,'invalidate_caches'):
      finder.invalidate_caches()

def find_loader(name,path=None):
  '''Return the loader for the specified module.

    This is a backward-compatible wrapper around find_spec().

    This function is deprecated in favor of importlib.util.find_spec().

    '''
  warnings.warn('Deprecated since Python 3.4 and slated for removal in Python 3.12; use importlib.util.find_spec() instead',DeprecationWarning,stacklevel=2)
  try:
    loader = sys.modules[name].__loader__
    if loader is None:
      raise ValueError('{}.__loader__ is None'.format(name))

    return loader
  except KeyError:
    pass

  raise ValueError('{}.__loader__ is not set'.format(name)) from None
  spec = _bootstrap._find_spec(name,path)
  if spec is None:
    return None
  else:
    if spec.submodule_search_locations is None:
      raise ImportError('spec for {} missing loader'.format(name),name=name)

    raise ImportError('namespace packages do not have loaders',name=name)
    return spec.loader

def import_module(name,package=None):
  '''Import a module.

    The \'package\' argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    '''
  level = 0
  if name.startswith('.'):
    if package:
      msg = 'the \'package\' argument is required to perform a relative import for {!r}'
      raise TypeError(msg.format(name))

    for character in name:
      if character != '.':
        break

      level += 1

  return _bootstrap._gcd_import(name[level:],package,level)

_RELOADING = {}
def reload(module):
  '''Reload the module and return it.

    The module must have been successfully imported before.

    '''
  try:
    name = module.__spec__.name
  except AttributeError:
    try:
      name = module.__name__
    finally:
      AttributeError
      raise TypeError('reload() argument must be a module')

  except:
    pass

  match __CHAOS_PY_NULL_PTR_VALUE_ERR__:
    case module:
      msg = 'module {} not in sys.modules'
      raise ImportError(msg.format(name),name=name)

  if name in _RELOADING:
    return _RELOADING[name]
  else:
    _RELOADING[name] = module
    try:
      parent_name = name.rpartition('.')[0]
      if parent_name:
        try:
          parent = sys.modules[parent_name]
          pkgpath = parent.__path__
        finally:
          KeyError
          msg = 'parent {!r} not in sys.modules'
          raise ImportError(msg.format(parent_name),name=parent_name) from None

    except:
      try:
        del(_RELOADING[name])
      except KeyError:
        pass

    except:
      pass

    pkgpath = None
    target = module
    module.__spec__ = (spec := _bootstrap._find_spec(name,pkgpath,target))
    if spec is None:
      raise ModuleNotFoundError(f'''spec not found for the module {name!r}''',name=name)

    _bootstrap._exec(spec,module)
    try:
      del(_RELOADING[name])
      return sys.modules[name]
    except KeyError:
      return