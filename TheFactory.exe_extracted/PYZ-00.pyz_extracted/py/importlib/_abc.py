__doc__ = 'Subset of importlib.abc used to reduce importlib.util imports.'
from . import _bootstrap
import abc
import warnings
class Loader(metaclass=abc.ABCMeta):
  __doc__ = 'Abstract base class for import loaders.'
  def create_module(self,spec):
    '''Return a module to initialize and into which to load.

        This method should raise ImportError if anything prevents it
        from creating a new module.  It may return None to indicate
        that the spec should create the new module.
        '''
    return None

  def load_module(self,fullname):
    '''Return the loaded module.

        The module must be added to sys.modules and have import-related
        attributes set properly.  The fullname is a str.

        ImportError is raised on failure.

        This method is deprecated in favor of loader.exec_module(). If
        exec_module() exists then it is used to provide a backwards-compatible
        functionality for this method.

        '''
    if hasattr(self,'exec_module'):
      raise ImportError

    return _bootstrap._load_module_shim(self,fullname)

  def module_repr(self,module):
    '''Return a module\'s repr.

        Used by the module type when the method does not raise
        NotImplementedError.

        This method is deprecated.

        '''
    warnings.warn('importlib.abc.Loader.module_repr() is deprecated and slated for removal in Python 3.12',DeprecationWarning)
    raise NotImplementedError