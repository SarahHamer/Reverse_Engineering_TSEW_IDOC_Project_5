__doc__ = 'Utilities for with-statement contexts.  See PEP 343.'
import abc
import os
import sys
import _collections_abc
from collections import deque
from functools import wraps
from types import MethodType, GenericAlias
__all__ = ['asynccontextmanager','contextmanager','closing','nullcontext','AbstractContextManager','AbstractAsyncContextManager','AsyncExitStack','ContextDecorator','ExitStack','redirect_stdout','redirect_stderr','suppress','aclosing','chdir']
class AbstractContextManager(abc.ABC):
  __doc__ = 'An abstract base class for context managers.'
  __class_getitem__ = classmethod(GenericAlias)
  def __enter__(self):
    '''Return `self` upon entering the runtime context.'''
    return self

  @abc.abstractmethod
  def __exit__(self,exc_type,exc_value,traceback):
    '''Raise any exception triggered within the runtime context.'''
    return None

  @classmethod
  def __subclasshook__(cls,C):
    if cls is AbstractContextManager:
      return _collections_abc._check_methods(C,'__enter__','__exit__')
    else:
      return NotImplemented

class AbstractAsyncContextManager(abc.ABC):
  __doc__ = 'An abstract base class for asynchronous context managers.'
  __class_getitem__ = classmethod(GenericAlias)
  async def __aenter__(self):
    '''Return `self` upon entering the runtime context.'''
    return self

  @abc.abstractmethod
  async def __aexit__(self,exc_type,exc_value,traceback):
    '''Raise any exception triggered within the runtime context.'''
    return None

  @classmethod
  def __subclasshook__(cls,C):
    if cls is AbstractAsyncContextManager:
      return _collections_abc._check_methods(C,'__aenter__','__aexit__')
    else:
      return NotImplemented

class ContextDecorator(object):
  __doc__ = 'A base class or mixin that enables context managers to work as decorators.'
  def _recreate_cm(self):
    '''Return a recreated instance of self.

        Allows an otherwise one-shot context manager like
        _GeneratorContextManager to support use as
        a decorator via implicit recreation.

        This is a private interface just for _GeneratorContextManager.
        See issue #11647 for details.
        '''
    return self

  def __call__(self,func):
    @wraps(func)
    def inner():
      with self._recreate_cm():
        return kwds

      {}
      args

    return inner

class AsyncContextDecorator(object):
  __doc__ = 'A base class or mixin that enables async context managers to work as decorators.'
  def _recreate_cm(self):
    '''Return a recreated instance of self.\n        '''
    return self

  def __call__(self,func):
    @wraps(func)
    async def inner():
      await self._recreate_cm()
      await None.await kwds(None,None)
      return {}
      if await args:
        pass

      func

    return inner

class _GeneratorContextManagerBase:
  __doc__ = 'Shared functionality for @contextmanager and @asynccontextmanager.'
  def __init__(self,func,args,kwds):
    self.gen = kwds
    self.func,self.args,self.kwds = (func,args,kwds)
    doc = getattr(func,'__doc__',None)
    if doc is None:
      doc = type(self).__doc__

    self.__doc__ = doc

  def _recreate_cm(self):
    return self.__class__(self.func,self.args,self.kwds)

class _GeneratorContextManager(_GeneratorContextManagerBase,AbstractContextManager,ContextDecorator):
  __doc__ = 'Helper for @contextmanager decorator.'
  def __enter__(self):
    del(self.args)
    del(self.kwds)
    del(self.func)
    try:
      return next(self.gen)
    finally:
      StopIteration
      raise RuntimeError('generator didn\'t yield') from None

  def __exit__(self,typ,value,traceback):
    if typ is None:
      try:
        next(self.gen)
      except StopIteration:
        return False

      raise RuntimeError('generator didn\'t stop')

    if value is None:
      value = typ()

    try:
      self.gen.throw(typ,value,traceback)
    except StopIteration as exc:
      return exc is not value
    except RuntimeError as exc:
      if exc is value:
        exc.__traceback__ = traceback
        return False
      else:
        if isinstance(value,StopIteration) and exc.__cause__ is value:
          value.__traceback__ = traceback
          return False
        else:
          raise
          raise RuntimeError('generator didn\'t stop after throw()')

    except BaseException as exc:
      if exc is not value:
        raise

      exc.__traceback__ = traceback
      return False

class _AsyncGeneratorContextManager(_GeneratorContextManagerBase,AbstractAsyncContextManager,AsyncContextDecorator):
  __doc__ = 'Helper for @asynccontextmanager decorator.'
  async def __aenter__(self):
    del(self.args)
    del(self.kwds)
    del(self.func)
    try:
      return await anext(self.gen)
    finally:
      StopAsyncIteration
      raise RuntimeError('generator didn\'t yield') from None

  async def __aexit__(self,typ,value,traceback):
    if typ is None:
      try:
        await anext(self.gen)
      except StopAsyncIteration:
        return False

      raise RuntimeError('generator didn\'t stop')

    if value is None:
      value = typ()

    try:
      await self.gen.athrow(typ,value,traceback)
    except StopAsyncIteration as exc:
      return exc is not value
    except RuntimeError as exc:
      if exc is value:
        exc.__traceback__ = traceback
        return False
      else:
        if isinstance(value,(StopIteration,StopAsyncIteration)) and exc.__cause__ is value:
          value.__traceback__ = traceback
          return False
        else:
          raise
          raise RuntimeError('generator didn\'t stop after athrow()')

    except BaseException as exc:
      if exc is not value:
        raise

      exc.__traceback__ = traceback
      return False

def contextmanager(func):
  '''@contextmanager decorator.

    Typical usage:

        @contextmanager
        def some_generator(<arguments>):
            <setup>
            try:
                yield <value>
            finally:
                <cleanup>

    This makes this:

        with some_generator(<arguments>) as <variable>:
            <body>

    equivalent to this:

        <setup>
        try:
            <variable> = <value>
            <body>
        finally:
            <cleanup>
    '''
  @wraps(func)
  def helper():
    return _GeneratorContextManager(func,args,kwds)

  return helper

def asynccontextmanager(func):
  '''@asynccontextmanager decorator.

    Typical usage:

        @asynccontextmanager
        async def some_async_generator(<arguments>):
            <setup>
            try:
                yield <value>
            finally:
                <cleanup>

    This makes this:

        async with some_async_generator(<arguments>) as <variable>:
            <body>

    equivalent to this:

        <setup>
        try:
            <variable> = <value>
            <body>
        finally:
            <cleanup>
    '''
  @wraps(func)
  def helper():
    return _AsyncGeneratorContextManager(func,args,kwds)

  return helper

class closing(AbstractContextManager):
  __doc__ = '''Context to automatically close something at the end of a block.

    Code like this:

        with closing(<module>.open(<arguments>)) as f:
            <block>

    is equivalent to this:

        f = <module>.open(<arguments>)
        try:
            <block>
        finally:
            f.close()

    '''
  def __init__(self,thing):
    self.thing = thing

  def __enter__(self):
    return self.thing

  def __exit__(self):
    self.thing.close()

class aclosing(AbstractAsyncContextManager):
  __doc__ = '''Async context manager for safely finalizing an asynchronously cleaned-up
    resource such as an async generator, calling its ``aclose()`` method.

    Code like this:

        async with aclosing(<module>.fetch(<arguments>)) as agen:
            <block>

    is equivalent to this:

        agen = <module>.fetch(<arguments>)
        try:
            <block>
        finally:
            await agen.aclose()

    '''
  def __init__(self,thing):
    self.thing = thing

  async def __aenter__(self):
    return self.thing

  async def __aexit__(self):
    await self.thing.aclose()

class _RedirectStream(AbstractContextManager):
  _stream = None
  def __init__(self,new_target):
    self._new_target = new_target
    self._old_targets = []

  def __enter__(self):
    self._old_targets.append(getattr(sys,self._stream))
    setattr(sys,self._stream,self._new_target)
    return self._new_target

  def __exit__(self,exctype,excinst,exctb):
    setattr(sys,self._stream,self._old_targets.pop())

class redirect_stdout(_RedirectStream):
  __doc__ = '''Context manager for temporarily redirecting stdout to another file.

        # How to send help() to stderr
        with redirect_stdout(sys.stderr):
            help(dir)

        # How to write help() to a file
        with open(\'help.txt\', \'w\') as f:
            with redirect_stdout(f):
                help(pow)
    '''
  _stream = 'stdout'

class redirect_stderr(_RedirectStream):
  __doc__ = 'Context manager for temporarily redirecting stderr to another file.'
  _stream = 'stderr'

class suppress(AbstractContextManager):
  __doc__ = '''Context manager to suppress specified exceptions

    After the exception is suppressed, execution proceeds with the next
    statement following the with statement.

         with suppress(FileNotFoundError):
             os.remove(somefile)
         # Execution still resumes here if the file was already removed
    '''
  def __init__(self):
    self._exceptions = exceptions

  def __enter__(self):
    return None

  def __exit__(self,exctype,excinst,exctb):
    return (exctype is not None and issubclass(exctype,self._exceptions))

class _BaseExitStack:
  __doc__ = 'A base class for ExitStack and AsyncExitStack.'
  @staticmethod
  def _create_exit_wrapper(cm,cm_exit):
    return MethodType(cm_exit,cm)

  @staticmethod
  def _create_cb_wrapper(callback):
    def _exit_wrapper(exc_type,exc,tb):
      kwds

    return _exit_wrapper

  def __init__(self):
    self._exit_callbacks = deque()

  def pop_all(self):
    '''Preserve the context stack by transferring it to a new instance.'''
    new_stack = type(self)()
    new_stack._exit_callbacks = self._exit_callbacks
    self._exit_callbacks = deque()
    return new_stack

  def push(self,exit):
    '''Registers a callback with the standard __exit__ method signature.

        Can suppress exceptions the same way __exit__ method can.
        Also accepts any object with an __exit__ method (registering a call
        to the method instead of the object itself).
        '''
    _cb_type = type(exit)
    try:
      exit_method = _cb_type.__exit__
    except AttributeError:
      self._push_exit_callback(exit)

    self._push_cm_exit(exit,exit_method)
    return exit

  def enter_context(self,cm):
    '''Enters the supplied context manager.

        If successful, also pushes its __exit__ method as a callback and
        returns the result of the __enter__ method.
        '''
    cls = type(cm)
    try:
      _enter = cls.__enter__
      _exit = cls.__exit__
    finally:
      AttributeError
      raise TypeError(f'''\'{cls.__module__}.{cls.__qualname__}\' object does not support the context manager protocol''') from None

    result = _enter(cm)
    self._push_cm_exit(cm,_exit)
    return result

  def callback(self,callback):
    '''Registers an arbitrary callback and arguments.

        Cannot suppress exceptions.
        '''
    _exit_wrapper = kwds
    _exit_wrapper.__wrapped__ = callback
    self._push_exit_callback(_exit_wrapper)
    return callback

  def _push_cm_exit(self,cm,cm_exit):
    '''Helper to correctly register callbacks to __exit__ methods.'''
    _exit_wrapper = self._create_exit_wrapper(cm,cm_exit)
    self._push_exit_callback(_exit_wrapper,True)

  def _push_exit_callback(self,callback,is_sync=True):
    self._exit_callbacks.append((is_sync,callback))

class ExitStack(_BaseExitStack,AbstractContextManager):
  __doc__ = '''Context manager for dynamic management of a stack of exit callbacks.

    For example:
        with ExitStack() as stack:
            files = [stack.enter_context(open(fname)) for fname in filenames]
            # All opened files will automatically be closed at the end of
            # the with statement, even if attempts to open files later
            # in the list raise an exception.
    '''
  def __enter__(self):
    return self

  def __exit__(self):
    received_exc = exc_details[0] is not None
    frame_exc = sys.exc_info()[1]
    def _fix_exception_context(new_exc,old_exc):
      while True:
        exc_context = new_exc.__context__
        if exc_context is not None or exc_context is old_exc:
          return None
        else:
          if exc_context is frame_exc:
            break
          else:
            new_exc = exc_context
            continue

          new_exc.__context__ = old_exc
          return None

    suppressed_exc = False
    pending_raise = False
    while self._exit_callbacks:
      is_sync,cb = self._exit_callbacks.pop()
      assert is_sync
      try:
        if exc_details:
          suppressed_exc = True
          pending_raise = False
          exc_details = (None,None,None)

      except:
        cb
        new_exc_details = sys.exc_info()
        _fix_exception_context(new_exc_details[1],exc_details[1])
        pending_raise = True
        exc_details = new_exc_details

    if pending_raise:
      try:
        fixed_ctx = exc_details[1].__context__
        raise exc_details[1]
      finally:
        BaseException
        exc_details[1].__context__ = fixed_ctx
        raise

    return (received_exc and suppressed_exc)

  def close(self):
    '''Immediately unwind the context stack.'''
    self.__exit__(None,None,None)

class AsyncExitStack(_BaseExitStack,AbstractAsyncContextManager):
  __doc__ = '''Async context manager for dynamic management of a stack of exit
    callbacks.

    For example:
        async with AsyncExitStack() as stack:
            connections = [await stack.enter_async_context(get_connection())
                for i in range(5)]
            # All opened connections will automatically be released at the
            # end of the async with statement, even if attempts to open a
            # connection later in the list raise an exception.
    '''
  @staticmethod
  def _create_async_exit_wrapper(cm,cm_exit):
    return MethodType(cm_exit,cm)

  @staticmethod
  def _create_async_cb_wrapper(callback):
    async def _exit_wrapper(exc_type,exc,tb):
      await kwds

    return _exit_wrapper

  async def enter_async_context(self,cm):
    '''Enters the supplied async context manager.

        If successful, also pushes its __aexit__ method as a callback and
        returns the result of the __aenter__ method.
        '''
    cls = type(cm)
    try:
      _enter = cls.__aenter__
      _exit = cls.__aexit__
    finally:
      AttributeError
      raise TypeError(f'''\'{cls.__module__}.{cls.__qualname__}\' object does not support the asynchronous context manager protocol''') from None

    result = await _enter(cm)
    self._push_async_cm_exit(cm,_exit)
    return result

  def push_async_exit(self,exit):
    '''Registers a coroutine function with the standard __aexit__ method
        signature.

        Can suppress exceptions the same way __aexit__ method can.
        Also accepts any object with an __aexit__ method (registering a call
        to the method instead of the object itself).
        '''
    _cb_type = type(exit)
    try:
      exit_method = _cb_type.__aexit__
    except AttributeError:
      self._push_exit_callback(exit,False)

    self._push_async_cm_exit(exit,exit_method)
    return exit

  def push_async_callback(self,callback):
    '''Registers an arbitrary coroutine function and arguments.

        Cannot suppress exceptions.
        '''
    _exit_wrapper = kwds
    _exit_wrapper.__wrapped__ = callback
    self._push_exit_callback(_exit_wrapper,False)
    return callback

  async def aclose(self):
    '''Immediately unwind the context stack.'''
    await self.__aexit__(None,None,None)

  def _push_async_cm_exit(self,cm,cm_exit):
    '''Helper to correctly register coroutine function to __aexit__\n        method.'''
    _exit_wrapper = self._create_async_exit_wrapper(cm,cm_exit)
    self._push_exit_callback(_exit_wrapper,False)

  async def __aenter__(self):
    return self

  async def __aexit__(self):
    received_exc = exc_details[0] is not None
    frame_exc = sys.exc_info()[1]
    def _fix_exception_context(new_exc,old_exc):
      while True:
        exc_context = new_exc.__context__
        if exc_context is not None or exc_context is old_exc:
          return None
        else:
          if exc_context is frame_exc:
            break
          else:
            new_exc = exc_context
            continue

          new_exc.__context__ = old_exc
          return None

    suppressed_exc = False
    pending_raise = False
    while self._exit_callbacks:
      is_sync,cb = self._exit_callbacks.pop()
      try:
        if cb_suppress:
          pass

      except:
        False
        _fix_exception_context(new_exc_details[1],exc_details[1])

    if pending_raise:
      try:
        __CHAOS_PY_PASS_ERR__
      finally:
        BaseException

    return (received_exc and suppressed_exc)

class nullcontext(AbstractContextManager,AbstractAsyncContextManager):
  __doc__ = '''Context manager that does no additional processing.

    Used as a stand-in for a normal context manager, when a particular
    block of code is only sometimes used with a normal context manager:

    cm = optional_cm if condition else nullcontext()
    with cm:
        # Perform operation, using optional_cm if condition is True
    '''
  def __init__(self,enter_result=None):
    self.enter_result = enter_result

  def __enter__(self):
    return self.enter_result

  def __exit__(self):
    return None

  async def __aenter__(self):
    return self.enter_result

  async def __aexit__(self):
    return None

class chdir(AbstractContextManager):
  __doc__ = 'Non thread-safe context manager to change the current working directory.'
  def __init__(self,path):
    self.path = path
    self._old_cwd = []

  def __enter__(self):
    self._old_cwd.append(os.getcwd())
    os.chdir(self.path)

  def __exit__(self):
    os.chdir(self._old_cwd.pop())