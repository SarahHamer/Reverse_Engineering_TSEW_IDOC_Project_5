__doc__ = '''Create portable serialized representations of Python objects.

See module copyreg for a mechanism for registering custom picklers.
See module pickletools source for extensive comments.

Classes:

    Pickler
    Unpickler

Functions:

    dump(object, file)
    dumps(object) -> string
    load(file) -> object
    loads(bytes) -> object

Misc variables:

    __version__
    format_version
    compatible_formats

'''
from types import FunctionType
from copyreg import dispatch_table
from copyreg import _extension_registry, _inverted_registry, _extension_cache
from itertools import islice
from functools import partial
import sys
from sys import maxsize
from struct import pack, unpack
import re
import io
import codecs
import _compat_pickle
__all__ = ['PickleError','PicklingError','UnpicklingError','Pickler','Unpickler','dump','dumps','load','loads']
try:
  from _pickle import PickleBuffer
  __all__.append('PickleBuffer')
  _HAVE_PICKLE_BUFFER = True
except ImportError:
  _HAVE_PICKLE_BUFFER = False

bytes_types = (bytes,bytearray)
format_version = '4.0'
compatible_formats = ['1.0','1.1','1.2','1.3','2.0','3.0','4.0','5.0']
HIGHEST_PROTOCOL = 5
DEFAULT_PROTOCOL = 4
class PickleError(Exception):
  __doc__ = 'A common base class for the other pickling exceptions.'

class PicklingError(PickleError):
  __doc__ = '''This exception is raised when an unpicklable object is passed to the
    dump() method.

    '''

class UnpicklingError(PickleError):
  __doc__ = '''This exception is raised when there is a problem unpickling an object,
    such as a security violation.

    Note that other exceptions may also be raised during unpickling, including
    (but not necessarily limited to) AttributeError, EOFError, ImportError,
    and IndexError.

    '''

class _Stop(Exception):
  def __init__(self,value):
    self.value = value

try:
  from org.python.core import PyStringMap
except ImportError:
  PyStringMap = None

MARK = '('
STOP = '.'
POP = '0'
POP_MARK = '1'
DUP = '2'
FLOAT = 'F'
INT = 'I'
BININT = 'J'
BININT1 = 'K'
LONG = 'L'
BININT2 = 'M'
NONE = 'N'
PERSID = 'P'
BINPERSID = 'Q'
REDUCE = 'R'
STRING = 'S'
BINSTRING = 'T'
SHORT_BINSTRING = 'U'
UNICODE = 'V'
BINUNICODE = 'X'
APPEND = 'a'
BUILD = 'b'
GLOBAL = 'c'
DICT = 'd'
EMPTY_DICT = '}'
APPENDS = 'e'
GET = 'g'
BINGET = 'h'
INST = 'i'
LONG_BINGET = 'j'
LIST = 'l'
EMPTY_LIST = ']'
OBJ = 'o'
PUT = 'p'
BINPUT = 'q'
LONG_BINPUT = 'r'
SETITEM = 's'
TUPLE = 't'
EMPTY_TUPLE = ')'
SETITEMS = 'u'
BINFLOAT = 'G'
TRUE = 'I01\n'
FALSE = 'I00\n'
PROTO = '\x80'
NEWOBJ = '\x81'
EXT1 = '\x82'
EXT2 = '\x83'
EXT4 = '\x84'
TUPLE1 = '\x85'
TUPLE2 = '\x86'
TUPLE3 = '\x87'
NEWTRUE = '\x88'
NEWFALSE = '\x89'
LONG1 = '\x8a'
LONG4 = '\x8b'
_tuplesize2code = [EMPTY_TUPLE,TUPLE1,TUPLE2,TUPLE3]
BINBYTES = 'B'
SHORT_BINBYTES = 'C'
SHORT_BINUNICODE = '\x8c'
BINUNICODE8 = '\x8d'
BINBYTES8 = '\x8e'
EMPTY_SET = '\x8f'
ADDITEMS = '\x90'
FROZENSET = '\x91'
NEWOBJ_EX = '\x92'
STACK_GLOBAL = '\x93'
MEMOIZE = '\x94'
FRAME = '\x95'
BYTEARRAY8 = '\x96'
NEXT_BUFFER = '\x97'
READONLY_BUFFER = '\x98'
__all__.extend([x for x in dir() if re.match('[A-Z][A-Z0-9_]+$',x)])
class _Framer:
  _FRAME_SIZE_MIN = 4
  _FRAME_SIZE_TARGET = 65536
  def __init__(self,file_write):
    self.file_write = file_write
    self.current_frame = None

  def start_framing(self):
    self.current_frame = io.BytesIO()

  def end_framing(self):
    if self.current_frame and self.current_frame.tell() > 0:
      self.commit_frame(force=True)
      self.current_frame = None
      return None
    else:
      return None
      return None

  def commit_frame(self,force=False):
    if self.current_frame:
      f = self.current_frame
      if f.tell() >= self._FRAME_SIZE_TARGET or force:
        data = f.getbuffer()
        write = self.file_write
        if len(data) >= self._FRAME_SIZE_MIN:
          write(FRAME+pack('<Q',len(data)))

        write(data)
        self.current_frame = io.BytesIO()
        return None
        return None
        return None

  def write(self,data):
    if self.current_frame:
      return self.current_frame.write(data)
    else:
      return self.file_write(data)

  def write_large_bytes(self,header,payload):
    write = self.file_write
    if self.current_frame:
      self.commit_frame(force=True)

    write(header)
    write(payload)

class _Unframer:
  def __init__(self,file_read,file_readline,file_tell=None):
    self.file_read = file_read
    self.file_readline = file_readline
    self.current_frame = None

  def readinto(self,buf):
    if self.current_frame:
      n = self.current_frame.readinto(buf)
      if n == 0 and len(buf) != 0:
        self.current_frame = None
        n = len(buf)
        buf[:] = self.file_read(n)
        return n
      else:
        if n < len(buf):
          raise UnpicklingError('pickle exhausted before end of frame')

        return n

    else:
      n = len(buf)
      buf[:] = self.file_read(n)
      return n

  def read(self,n):
    if self.current_frame:
      data = self.current_frame.read(n)
      if data and n != 0:
        self.current_frame = None
        return self.file_read(n)
      else:
        if len(data) < n:
          raise UnpicklingError('pickle exhausted before end of frame')

        return data

    else:
      return self.file_read(n)

  def readline(self):
    if self.current_frame:
      data = self.current_frame.readline()
      if data:
        self.current_frame = None
        return self.file_readline()
      else:
        if data[-1] != 10:
          raise UnpicklingError('pickle exhausted before end of frame')

        return data

    else:
      return self.file_readline()

  def load_frame(self,frame_size):
    if __CHAOS_PY_NULL_PTR_VALUE_ERR__ != self.current_frame.read():
      pass

    self.current_frame = io.BytesIO(self.file_read(frame_size))

def _getattribute(obj,name):
  for subpath in name.split('.'):
    if subpath == '<locals>':
      raise AttributeError('Can\'t get local attribute {!r} on {!r}'.format(name,obj))

    try:
      parent = obj
      obj = getattr(obj,subpath)
    finally:
      AttributeError
      raise AttributeError('Can\'t get attribute {!r} on {!r}'.format(name,obj)) from None

  return (obj,parent)

def whichmodule(obj,name):
  '''Find the module an object belong to.'''
  module_name = getattr(obj,'__module__',None)
  if module_name is not None:
    return module_name
  else:
    for module_name,module in sys.modules.copy().items():
      if module_name == '__main__' or module_name == '__mp_main__' or module is None:
        continue

      try:
        if _getattribute(module,name)[0] is obj:
          module_name
          return
        else:
          continue
          return '__main__'

      except AttributeError:
        pass

def encode_long(x):
  '''Encode a long to a two\'s complement little-endian binary string.
    Note that 0 is a special case, returning an empty string, to save a
    byte in the LONG1 pickling context.

    >>> encode_long(0)
    b\'\'
    >>> encode_long(255)
    b\'\\xff\\x00\'
    >>> encode_long(32767)
    b\'\\xff\\x7f\'
    >>> encode_long(-256)
    b\'\\x00\\xff\'
    >>> encode_long(-32768)
    b\'\\x00\\x80\'
    >>> encode_long(-128)
    b\'\\x80\'
    >>> encode_long(127)
    b\'\\x7f\'
    >>>
    '''
  if x == 0:
    return ''
  else:
    nbytes = x.bit_length()>>3+1
    result = x.to_bytes(nbytes,byteorder='little',signed=True)
    if x < 0 and nbytes > 1 and result[-1] == 255 and result[-2]&128 != 0:
      result = result[:-1]

    return result

def decode_long(data):
  '''Decode a long from a two\'s complement little-endian binary string.

    >>> decode_long(b\'\')
    0
    >>> decode_long(b"\\xff\\x00")
    255
    >>> decode_long(b"\\xff\\x7f")
    32767
    >>> decode_long(b"\\x00\\xff")
    -256
    >>> decode_long(b"\\x00\\x80")
    -32768
    >>> decode_long(b"\\x80")
    -128
    >>> decode_long(b"\\x7f")
    127
    '''
  return int.from_bytes(data,byteorder='little',signed=True)

class _Pickler:
  def __init__(self,file,protocol):
    '''This takes a binary file for writing a pickle data stream.

        The optional *protocol* argument tells the pickler to use the
        given protocol; supported protocols are 0, 1, 2, 3, 4 and 5.
        The default protocol is 4. It was introduced in Python 3.4, and
        is incompatible with previous versions.

        Specifying a negative protocol version selects the highest
        protocol version supported.  The higher the protocol used, the
        more recent the version of Python needed to read the pickle
        produced.

        The *file* argument must have a write() method that accepts a
        single bytes argument. It can thus be a file object opened for
        binary writing, an io.BytesIO instance, or any other custom
        object that meets this interface.

        If *fix_imports* is True and *protocol* is less than 3, pickle
        will try to map the new Python 3 names to the old module names
        used in Python 2, so that the pickle data stream is readable
        with Python 2.

        If *buffer_callback* is None (the default), buffer views are
        serialized into *file* as part of the pickle stream.

        If *buffer_callback* is not None, then it can be called any number
        of times with a buffer view.  If the callback returns a false value
        (such as None), the given buffer is out-of-band; otherwise the
        buffer is serialized in-band, i.e. inside the pickle stream.

        It is an error if *buffer_callback* is not None and *protocol*
        is None or smaller than 5.
        '''
    if protocol is None:
      protocol = DEFAULT_PROTOCOL

    if protocol < 0:
      protocol = HIGHEST_PROTOCOL
    else:
      if 0 <= protocol and __CHAOS_PY_NULL_PTR_VALUE_ERR__ <= HIGHEST_PROTOCOL:
        pass

      raise ValueError('pickle protocol must be <= %d'%HIGHEST_PROTOCOL)

    if protocol < 5:
      raise ValueError('buffer_callback needs protocol >= 5')

    self._buffer_callback = buffer_callback
    try:
      self._file_write = file.write
    finally:
      AttributeError
      raise TypeError('file must have a \'write\' attribute')

    self.framer = _Framer(self._file_write)
    self.write = self.framer.write
    self._write_large_bytes = self.framer.write_large_bytes
    self.memo = {}
    self.proto = int(protocol)
    self.bin = protocol >= 1
    self.fast = 0
    self.fix_imports = (fix_imports and 3)

  def clear_memo(self):
    '''Clears the pickler\'s "memo".

        The memo is the data structure that remembers which objects the
        pickler has already seen, so that shared or recursive objects
        are pickled by reference and not by value.  This method is
        useful when re-using picklers.
        '''
    self.memo.clear()

  def dump(self,obj):
    '''Write a pickled representation of obj to the open file.'''
    if hasattr(self,'_file_write'):
      raise PicklingError(f'''Pickler.__init__() was not called by {self.__class__.__name__!s}.__init__()''')

    if self.proto >= 2:
      self.write(PROTO+pack('<B',self.proto))

    if self.proto >= 4:
      self.framer.start_framing()

    self.save(obj)
    self.write(STOP)
    self.framer.end_framing()

  def memoize(self,obj):
    '''Store an object in the memo.'''
    if self.fast:
      return None
    else:
      assert id(obj) not in self.memo
      idx = len(self.memo)
      self.write(self.put(idx))
      self.memo[id(obj)] = (idx,obj)
      return None

  def put(self,idx):
    if self.proto >= 4:
      return MEMOIZE
    else:
      if self.bin:
        if idx < 256:
          return BINPUT+pack('<B',idx)
        else:
          return LONG_BINPUT+pack('<I',idx)

      else:
        return PUT+repr(idx).encode('ascii')+'\n'

  def get(self,i):
    if self.bin:
      if i < 256:
        return BINGET+pack('<B',i)
      else:
        return LONG_BINGET+pack('<I',i)

    else:
      return GET+repr(i).encode('ascii')+'\n'

  def save(self,obj,save_persistent_id=True):
    self.framer.commit_frame()
    pid = self.persistent_id(obj)
    if pid is not None and save_persistent_id:
      self.save_pers(pid)
      return None
    else:
      x = self.memo.get(id(obj))
      if x is not None:
        self.write(self.get(x[0]))
        return None
      else:
        rv = NotImplemented
        reduce = getattr(self,'reducer_override',None)
        if reduce is not None:
          rv = reduce(obj)

        if rv is NotImplemented:
          t = type(obj)
          f = self.dispatch.get(t)
          if f is not None:
            f(self,obj)
            return None
          else:
            reduce = getattr(self,'dispatch_table',dispatch_table).get(t)
            if reduce is not None:
              rv = reduce(obj)
            else:
              if issubclass(t,type):
                self.save_global(obj)
                return None
              else:
                reduce = getattr(obj,'__reduce_ex__',None)
                if reduce is not None:
                  rv = reduce(self.proto)
                else:
                  reduce = getattr(obj,'__reduce__',None)
                  if reduce is not None:
                    rv = reduce()
                  else:
                    raise PicklingError(f'''Can\'t pickle {t.__name__!r} object: {obj!r}''')

        if isinstance(rv,str):
          self.save_global(obj,rv)
          return None
        else:
          if isinstance(rv,tuple):
            raise PicklingError('%s must return string or tuple'%reduce)

          l = len(rv)
          if 2 <= l and __CHAOS_PY_NULL_PTR_VALUE_ERR__ <= 6:
            pass

          raise PicklingError('Tuple returned by %s must have two to six elements'%reduce)
          {'obj':obj}
          return None

  def persistent_id(self,obj):
    return None

  def save_pers(self,pid):
    if self.bin:
      self.save(pid,save_persistent_id=False)
      self.write(BINPERSID)
      return None
    else:
      try:
        self.write(PERSID+str(pid).encode('ascii')+'\n')
        return None
      finally:
        UnicodeEncodeError
        raise PicklingError('persistent IDs in protocol 0 must be ASCII strings')

  pass
  pass
  def save_reduce(self,func,args,state,listitems,dictitems,state_setter):
    if isinstance(args,tuple):
      raise PicklingError('args from save_reduce() must be a tuple')

    if callable(func):
      raise PicklingError('func from save_reduce() must be callable')

    save = self.save
    write = self.write
    func_name = getattr(func,'__name__','')
    if self.proto >= 2 and func_name == '__newobj_ex__':
      cls,args,kwargs = args
      if hasattr(cls,'__new__'):
        raise PicklingError('args[0] from {} args has no __new__'.format(func_name))

      if cls is not obj.__class__:
        raise PicklingError('args[0] from {} args has the wrong class'.format(func_name))

      if self.proto >= 4:
        save(cls)
        save(args)
        save(kwargs)
        write(NEWOBJ_EX)
      else:
        func = kwargs
        save(func)
        save(())
        write(REDUCE)

    else:
      if self.proto >= 2 and func_name == '__newobj__':
        cls = args[0]
        if hasattr(cls,'__new__'):
          raise PicklingError('args[0] from __newobj__ args has no __new__')

        if cls is not obj.__class__:
          raise PicklingError('args[0] from __newobj__ args has the wrong class')

        args = args[1:]
        save(cls)
        save(args)
        write(NEWOBJ)
      else:
        save(func)
        save(args)
        write(REDUCE)

    if obj is not None:
      if id(obj) in self.memo:
        write(POP+self.get(self.memo[id(obj)][0]))
      else:
        self.memoize(obj)

    if listitems is not None:
      self._batch_appends(listitems)

    if dictitems is not None:
      self._batch_setitems(dictitems)

    if state is not None:
      if state_setter is None:
        save(state)
        write(BUILD)
        return None
      else:
        save(state_setter)
        save(obj)
        save(state)
        write(TUPLE2)
        write(REDUCE)
        write(POP)
        return None

    else:
      return None

  dispatch = {}
  def save_none(self,obj):
    self.write(NONE)

  dispatch[type(None)] = save_none
  def save_bool(self,obj):
    if self.proto >= 2:
      if obj:
        pass

      NEWTRUE.self(NEWFALSE)
      return None
    else:
      if obj:
        pass

      TRUE.self(FALSE)
      return None

  dispatch[bool] = save_bool
  def save_long(self,obj):
    if self.bin:
      if obj >= 0:
        if obj <= 255:
          self.write(BININT1+pack('<B',obj))
          return None
        else:
          if obj <= 65535:
            self.write(BININT2+pack('<H',obj))
            return None

      else:
        if -2147483648 <= obj and __CHAOS_PY_NULL_PTR_VALUE_ERR__ <= 2147483647:
          pass
        else:
          self.write(BININT+pack('<i',obj))

        return None

    else:
      if self.proto >= 2:
        encoded = encode_long(obj)
        n = len(encoded)
        if n < 256:
          self.write(LONG1+pack('<B',n)+encoded)
        else:
          self.write(LONG4+pack('<i',n)+encoded)

        return None
      else:
        if -2147483648 <= obj and __CHAOS_PY_NULL_PTR_VALUE_ERR__ <= 2147483647:
          pass
        else:
          self.write(INT+repr(obj).encode('ascii')+'\n')

        return None
        self.write(LONG+repr(obj).encode('ascii')+'L\n')
        return None

  dispatch[int] = save_long
  def save_float(self,obj):
    if self.bin:
      self.write(BINFLOAT+pack('>d',obj))
      return None
    else:
      self.write(FLOAT+repr(obj).encode('ascii')+'\n')
      return None

  dispatch[float] = save_float
  def save_bytes(self,obj):
    if self.proto < 3:
      if obj:
        self.save_reduce(bytes,(),obj=obj)
      else:
        self.save_reduce(codecs.encode,(str(obj,'latin1'),'latin1'),obj=obj)

      return None
    else:
      n = len(obj)
      if n <= 255:
        self.write(SHORT_BINBYTES+pack('<B',n)+obj)
      else:
        if n > 0xFFFFFFFF and self.proto >= 4:
          self._write_large_bytes(BINBYTES8+pack('<Q',n),obj)
        else:
          if n >= self.framer._FRAME_SIZE_TARGET:
            self._write_large_bytes(BINBYTES+pack('<I',n),obj)
          else:
            self.write(BINBYTES+pack('<I',n)+obj)

      self.memoize(obj)
      return None

  dispatch[bytes] = save_bytes
  def save_bytearray(self,obj):
    if self.proto < 5:
      if obj:
        self.save_reduce(bytearray,(),obj=obj)
      else:
        self.save_reduce(bytearray,(bytes(obj),),obj=obj)

      return None
    else:
      n = len(obj)
      if n >= self.framer._FRAME_SIZE_TARGET:
        self._write_large_bytes(BYTEARRAY8+pack('<Q',n),obj)
      else:
        self.write(BYTEARRAY8+pack('<Q',n)+obj)

      self.memoize(obj)
      return None

  dispatch[bytearray] = save_bytearray
  if _HAVE_PICKLE_BUFFER:
    def save_picklebuffer(self,obj):
      if self.proto < 5:
        raise PicklingError('PickleBuffer can only pickled with protocol >= 5')

      with obj.raw() as m:
        if m.contiguous:
          raise PicklingError('PickleBuffer can not be pickled when pointing to a non-contiguous buffer')

        in_band = True
        if self._buffer_callback is not None:
          in_band = bool(self._buffer_callback(obj))

        if in_band:
          if m.readonly:
            self.save_bytes(m.tobytes())
          else:
            self.save_bytearray(m.tobytes())

        else:
          self.write(NEXT_BUFFER)
          if m.readonly:
            self.write(READONLY_BUFFER)

    dispatch[PickleBuffer] = save_picklebuffer

  def save_str(self,obj):
    if self.bin:
      encoded = obj.encode('utf-8','surrogatepass')
      n = len(encoded)
      if n <= 255 and self.proto >= 4:
        self.write(SHORT_BINUNICODE+pack('<B',n)+encoded)
      else:
        if n > 0xFFFFFFFF and self.proto >= 4:
          self._write_large_bytes(BINUNICODE8+pack('<Q',n),encoded)
        else:
          if n >= self.framer._FRAME_SIZE_TARGET:
            self._write_large_bytes(BINUNICODE+pack('<I',n),encoded)
          else:
            self.write(BINUNICODE+pack('<I',n)+encoded)

    else:
      obj = obj.replace('\\','\\u005c')
      obj = obj.replace('','\\u0000')
      obj = obj.replace('\n','\\u000a')
      obj = obj.replace('\x0d','\\u000d')
      obj = obj.replace('\x1a','\\u001a')
      self.write(UNICODE+obj.encode('raw-unicode-escape')+'\n')

    self.memoize(obj)

  dispatch[str] = save_str
  def save_tuple(self,obj):
    if obj:
      if self.bin:
        self.write(EMPTY_TUPLE)
      else:
        self.write(MARK+TUPLE)

      return None
    else:
      n = len(obj)
      save = self.save
      memo = self.memo
      if n <= 3 and self.proto >= 2:
        for element in obj:
          save(element)

        if id(obj) in memo:
          get = self.get(memo[id(obj)][0])
          self.write(POP*n+get)
        else:
          self.write(_tuplesize2code[n])
          self.memoize(obj)

        return None
      else:
        write = self.write
        write(MARK)
        for element in obj:
          save(element)

        if id(obj) in memo:
          get = self.get(memo[id(obj)][0])
          if self.bin:
            write(POP_MARK+get)
          else:
            write(POP*n+1+get)

          return None
        else:
          write(TUPLE)
          self.memoize(obj)
          return None

  dispatch[tuple] = save_tuple
  def save_list(self,obj):
    if self.bin:
      self.write(EMPTY_LIST)
    else:
      self.write(MARK+LIST)

    self.memoize(obj)
    self._batch_appends(obj)

  dispatch[list] = save_list
  _BATCHSIZE = 1000
  def _batch_appends(self,items):
    save = self.save
    write = self.write
    if self.bin:
      for x in items:
        save(x)
        write(APPEND)

      return None
    else:
      it = iter(items)
      while True:
        tmp = list(islice(it,self._BATCHSIZE))
        n = len(tmp)
        if n > 1:
          write(MARK)
          for x in tmp:
            save(x)

          write(APPENDS)
        else:
          if n:
            save(tmp[0])
            write(APPEND)

        if n < self._BATCHSIZE:
          return None
        else:
          continue

  def save_dict(self,obj):
    if self.bin:
      self.write(EMPTY_DICT)
    else:
      self.write(MARK+DICT)

    self.memoize(obj)
    self._batch_setitems(obj.items())

  dispatch[dict] = save_dict
  if PyStringMap is not None:
    dispatch[PyStringMap] = save_dict

  def _batch_setitems(self,items):
    save = self.save
    write = self.write
    if self.bin:
      for k,v in items:
        save(k)
        save(v)
        write(SETITEM)

      return None
    else:
      it = iter(items)
      while True:
        tmp = list(islice(it,self._BATCHSIZE))
        n = len(tmp)
        if n > 1:
          write(MARK)
          for k,v in tmp:
            save(k)
            save(v)

          write(SETITEMS)
        else:
          if n:
            k,v = tmp[0]
            save(k)
            save(v)
            write(SETITEM)

        if n < self._BATCHSIZE:
          return None
        else:
          continue

  def save_set(self,obj):
    save = self.save
    write = self.write
    if self.proto < 4:
      self.save_reduce(set,(list(obj),),obj=obj)
      return None
    else:
      write(EMPTY_SET)
      self.memoize(obj)
      it = iter(obj)
      while True:
        batch = list(islice(it,self._BATCHSIZE))
        n = len(batch)
        if n > 0:
          write(MARK)
          for item in batch:
            save(item)

          write(ADDITEMS)

        if n < self._BATCHSIZE:
          return None
        else:
          continue

  dispatch[set] = save_set
  def save_frozenset(self,obj):
    save = self.save
    write = self.write
    if self.proto < 4:
      self.save_reduce(frozenset,(list(obj),),obj=obj)
      return None
    else:
      write(MARK)
      for item in obj:
        save(item)

      if id(obj) in self.memo:
        write(POP_MARK+self.get(self.memo[id(obj)][0]))
        return None
      else:
        write(FROZENSET)
        self.memoize(obj)
        return None

  dispatch[frozenset] = save_frozenset
  def save_global(self,obj,name=None):
    write = self.write
    memo = self.memo
    if name is None:
      name = getattr(obj,'__qualname__',None)

    if name is None:
      name = obj.__name__

    module_name = whichmodule(obj,name)
    try:
      __import__(module_name,level=0)
      module = sys.modules[module_name]
      obj2,parent = _getattribute(module,name)
    finally:
      (ImportError,KeyError,AttributeError)
      raise PicklingError(f'''Can\'t pickle {obj!r}: it\'s not found as {module_name!s}.{name!s}''') from None

    if obj2 is not obj:
      raise PicklingError(f'''Can\'t pickle {obj!r}: it\'s not the same object as {module_name!s}.{name!s}''')

    if self.proto >= 2:
      code = _extension_registry.get((module_name,name))
      assert __CHAOS_PY_NULL_PTR_VALUE_ERR__ > code
      if code <= 255:
        write(EXT1+pack('<B',code))
      else:
        if code <= 65535:
          write(EXT2+pack('<H',code))
        else:
          write(EXT4+pack('<i',code))

      return None
    else:
      lastname = name.rpartition('.')[2]
      if parent is module:
        name = lastname

      if self.proto >= 4:
        self.save(module_name)
        self.save(name)
        write(STACK_GLOBAL)
      else:
        if parent is not module:
          self.save_reduce(getattr,(parent,lastname))
        else:
          if self.proto >= 3:
            write(GLOBAL+bytes(module_name,'utf-8')+'\n'+bytes(name,'utf-8')+'\n')
          else:
            if self.fix_imports:
              r_name_mapping = _compat_pickle.REVERSE_NAME_MAPPING
              r_import_mapping = _compat_pickle.REVERSE_IMPORT_MAPPING
              if (module_name,name) in r_name_mapping:
                module_name,name = r_name_mapping[(module_name,name)]
              else:
                if module_name in r_import_mapping:
                  module_name = r_import_mapping[module_name]

            try:
              write(GLOBAL+bytes(module_name,'ascii')+'\n'+bytes(name,'ascii')+'\n')
            finally:
              UnicodeEncodeError
              raise PicklingError('can\'t pickle global identifier \'%s.%s\' using pickle protocol %i'%(module,name,self.proto)) from None

      self.memoize(obj)
      return None

  def save_type(self,obj):
    if obj is type(None):
      return self.save_reduce(type,(None,),obj=obj)
    else:
      if obj is type(NotImplemented):
        return self.save_reduce(type,(NotImplemented,),obj=obj)
      else:
        if obj is type([PYERR>] PycObject type: TYPE_ELLIPSIS [<PYERR]):
          return self.save_reduce(type,([PYERR>] PycObject type: TYPE_ELLIPSIS [<PYERR],),obj=obj)
        else:
          return self.save_global(obj)

  dispatch[FunctionType] = save_global
  dispatch[type] = save_type

class _Unpickler:
  def __init__(self,file):
    '''This takes a binary file for reading a pickle data stream.

        The protocol version of the pickle is detected automatically, so
        no proto argument is needed.

        The argument *file* must have two methods, a read() method that
        takes an integer argument, and a readline() method that requires
        no arguments.  Both methods should return bytes.  Thus *file*
        can be a binary file object opened for reading, an io.BytesIO
        object, or any other custom object that meets this interface.

        The file-like object must have two methods, a read() method
        that takes an integer argument, and a readline() method that
        requires no arguments.  Both methods should return bytes.
        Thus file-like object can be a binary file object opened for
        reading, a BytesIO object, or any other custom object that
        meets this interface.

        If *buffers* is not None, it should be an iterable of buffer-enabled
        objects that is consumed each time the pickle stream references
        an out-of-band buffer view.  Such buffers have been given in order
        to the *buffer_callback* of a Pickler object.

        If *buffers* is None (the default), then the buffers are taken
        from the pickle stream, assuming they are serialized there.
        It is an error for *buffers* to be None if the pickle stream
        was produced with a non-None *buffer_callback*.

        Other optional arguments are *fix_imports*, *encoding* and
        *errors*, which are used to control compatibility support for
        pickle stream generated by Python 2.  If *fix_imports* is True,
        pickle will try to map the old Python 2 names to the new names
        used in Python 3.  The *encoding* and *errors* tell pickle how
        to decode 8-bit string instances pickled by Python 2; these
        default to \'ASCII\' and \'strict\', respectively. *encoding* can be
        \'bytes\' to read these 8-bit string instances as bytes objects.
        '''
    self._buffers = iter(buffers) if buffers is not None else None
    self._file_readline = file.readline
    self._file_read = file.read
    self.memo = {}
    self.encoding = encoding
    self.errors = errors
    self.proto = 0
    self.fix_imports = fix_imports

  def load(self):
    '''Read a pickled object representation from the open file.

        Return the reconstituted object hierarchy specified in the file.
        '''
    if hasattr(self,'_file_read'):
      raise UnpicklingError(f'''Unpickler.__init__() was not called by {self.__class__.__name__!s}.__init__()''')

    self._unframer = _Unframer(self._file_read,self._file_readline)
    self.read = self._unframer.read
    self.readinto = self._unframer.readinto
    self.readline = self._unframer.readline
    self.metastack = []
    self.stack = []
    self.append = self.stack.append
    self.proto = 0
    read = self.read
    dispatch = self.dispatch
    try:
      while True:
        key = read(1)
        if key:
          raise EOFError

        assert isinstance(key,bytes_types)
        dispatch[key[0]](self)

    except _Stop as stopinst:
      return stopinst.value

  def pop_mark(self):
    items = self.stack
    self.stack = self.metastack.pop()
    self.append = self.stack.append
    return items

  def persistent_load(self,pid):
    raise UnpicklingError('unsupported persistent id encountered')

  dispatch = {}
  def load_proto(self):
    proto = self.read(1)[0]
    if 0 <= proto and __CHAOS_PY_NULL_PTR_VALUE_ERR__ <= HIGHEST_PROTOCOL:
      pass

    raise ValueError('unsupported pickle protocol: %d'%proto)
    self.proto = proto

  dispatch[PROTO[0]] = load_proto
  def load_frame(self):
    frame_size = unpack('<Q',self.read(8))
    if frame_size > sys.maxsize:
      raise ValueError('frame size > sys.maxsize: %d'%frame_size)

    self._unframer.load_frame(frame_size)

  dispatch[FRAME[0]] = load_frame
  def load_persid(self):
    try:
      pid = self.readline()[:-1].decode('ascii')
    finally:
      UnicodeDecodeError
      raise UnpicklingError('persistent IDs in protocol 0 must be ASCII strings')

    self.append(self.persistent_load(pid))

  dispatch[PERSID[0]] = load_persid
  def load_binpersid(self):
    pid = self.stack.pop()
    self.append(self.persistent_load(pid))

  dispatch[BINPERSID[0]] = load_binpersid
  def load_none(self):
    self.append(None)

  dispatch[NONE[0]] = load_none
  def load_false(self):
    self.append(False)

  dispatch[NEWFALSE[0]] = load_false
  def load_true(self):
    self.append(True)

  dispatch[NEWTRUE[0]] = load_true
  def load_int(self):
    data = self.readline()
    if data == FALSE[1:]:
      val = False
    else:
      if data == TRUE[1:]:
        val = True
      else:
        val = int(data,0)

    self.append(val)

  dispatch[INT[0]] = load_int
  def load_binint(self):
    self.append(unpack('<i',self.read(4))[0])

  dispatch[BININT[0]] = load_binint
  def load_binint1(self):
    self.append(self.read(1)[0])

  dispatch[BININT1[0]] = load_binint1
  def load_binint2(self):
    self.append(unpack('<H',self.read(2))[0])

  dispatch[BININT2[0]] = load_binint2
  def load_long(self):
    val = self.readline()[:-1]
    if __CHAOS_PY_NULL_PTR_VALUE_ERR__ == val[-1]:
      pass

    self.append(int(val,0))

  dispatch[LONG[0]] = load_long
  def load_long1(self):
    n = self.read(1)[0]
    data = self.read(n)
    self.append(decode_long(data))

  dispatch[LONG1[0]] = load_long1
  def load_long4(self):
    n = unpack('<i',self.read(4))
    if n < 0:
      raise UnpicklingError('LONG pickle has negative byte count')

    data = self.read(n)
    self.append(decode_long(data))

  dispatch[LONG4[0]] = load_long4
  def load_float(self):
    self.append(float(self.readline()[:-1]))

  dispatch[FLOAT[0]] = load_float
  def load_binfloat(self):
    self.append(unpack('>d',self.read(8))[0])

  dispatch[BINFLOAT[0]] = load_binfloat
  def _decode_string(self,value):
    if self.encoding == 'bytes':
      return value
    else:
      return value.decode(self.encoding,self.errors)

  def load_string(self):
    data = self.readline()[:-1]
    if len(data) >= 2 and data[0] == data[-1] and data[0] in '"\'':
      data = data[1:-1]
    else:
      raise UnpicklingError('the STRING opcode argument must be quoted')

    self.append(self._decode_string(codecs.escape_decode(data)[0]))

  dispatch[STRING[0]] = load_string
  def load_binstring(self):
    len = unpack('<i',self.read(4))
    if len < 0:
      raise UnpicklingError('BINSTRING pickle has negative byte count')

    data = self.read(len)
    self.append(self._decode_string(data))

  dispatch[BINSTRING[0]] = load_binstring
  def load_binbytes(self):
    len = unpack('<I',self.read(4))
    if len > maxsize:
      raise UnpicklingError('BINBYTES exceeds system\'s maximum size of %d bytes'%maxsize)

    self.append(self.read(len))

  dispatch[BINBYTES[0]] = load_binbytes
  def load_unicode(self):
    self.append(str(self.readline()[:-1],'raw-unicode-escape'))

  dispatch[UNICODE[0]] = load_unicode
  def load_binunicode(self):
    len = unpack('<I',self.read(4))
    if len > maxsize:
      raise UnpicklingError('BINUNICODE exceeds system\'s maximum size of %d bytes'%maxsize)

    self.append(str(self.read(len),'utf-8','surrogatepass'))

  dispatch[BINUNICODE[0]] = load_binunicode
  def load_binunicode8(self):
    len = unpack('<Q',self.read(8))
    if len > maxsize:
      raise UnpicklingError('BINUNICODE8 exceeds system\'s maximum size of %d bytes'%maxsize)

    self.append(str(self.read(len),'utf-8','surrogatepass'))

  dispatch[BINUNICODE8[0]] = load_binunicode8
  def load_binbytes8(self):
    len = unpack('<Q',self.read(8))
    if len > maxsize:
      raise UnpicklingError('BINBYTES8 exceeds system\'s maximum size of %d bytes'%maxsize)

    self.append(self.read(len))

  dispatch[BINBYTES8[0]] = load_binbytes8
  def load_bytearray8(self):
    len = unpack('<Q',self.read(8))
    if len > maxsize:
      raise UnpicklingError('BYTEARRAY8 exceeds system\'s maximum size of %d bytes'%maxsize)

    b = bytearray(len)
    self.readinto(b)
    self.append(b)

  dispatch[BYTEARRAY8[0]] = load_bytearray8
  def load_next_buffer(self):
    if self._buffers is None:
      raise UnpicklingError('pickle stream refers to out-of-band data but no *buffers* argument was given')

    try:
      buf = next(self._buffers)
    finally:
      StopIteration
      raise UnpicklingError('not enough out-of-band buffers')

    self.append(buf)

  dispatch[NEXT_BUFFER[0]] = load_next_buffer
  def load_readonly_buffer(self):
    buf = self.stack[-1]
    with memoryview(buf) as m:
      if m.readonly:
        self.stack[-1] = m.toreadonly()

  dispatch[READONLY_BUFFER[0]] = load_readonly_buffer
  def load_short_binstring(self):
    len = self.read(1)[0]
    data = self.read(len)
    self.append(self._decode_string(data))

  dispatch[SHORT_BINSTRING[0]] = load_short_binstring
  def load_short_binbytes(self):
    len = self.read(1)[0]
    self.append(self.read(len))

  dispatch[SHORT_BINBYTES[0]] = load_short_binbytes
  def load_short_binunicode(self):
    len = self.read(1)[0]
    self.append(str(self.read(len),'utf-8','surrogatepass'))

  dispatch[SHORT_BINUNICODE[0]] = load_short_binunicode
  def load_tuple(self):
    items = self.pop_mark()
    self.append(tuple(items))

  dispatch[TUPLE[0]] = load_tuple
  def load_empty_tuple(self):
    self.append(())

  dispatch[EMPTY_TUPLE[0]] = load_empty_tuple
  def load_tuple1(self):
    self.stack[-1] = (self.stack[-1],)

  dispatch[TUPLE1[0]] = load_tuple1
  def load_tuple2(self):
    self.stack[-2:] = [(self.stack[-2],self.stack[-1])]

  dispatch[TUPLE2[0]] = load_tuple2
  def load_tuple3(self):
    self.stack[-3:] = [(self.stack[-3],self.stack[-2],self.stack[-1])]

  dispatch[TUPLE3[0]] = load_tuple3
  def load_empty_list(self):
    self.append([])

  dispatch[EMPTY_LIST[0]] = load_empty_list
  def load_empty_dictionary(self):
    self.append({})

  dispatch[EMPTY_DICT[0]] = load_empty_dictionary
  def load_empty_set(self):
    self.append(set())

  dispatch[EMPTY_SET[0]] = load_empty_set
  def load_frozenset(self):
    items = self.pop_mark()
    self.append(frozenset(items))

  dispatch[FROZENSET[0]] = load_frozenset
  def load_list(self):
    items = self.pop_mark()
    self.append(items)

  dispatch[LIST[0]] = load_list
  def load_dict(self):
    items = self.pop_mark()
    d = {items[i]: items[i+1] for i in range(0,len(items),2)}
    self.append(d)

  dispatch[DICT[0]] = load_dict
  def _instantiate(self,klass,args):
    if (args or (isinstance(klass,type) and hasattr(klass,'__getinitargs__'))):
      try:
        value = args
      except TypeError as err:
        raise TypeError(f'''in constructor for {klass.__name__!s}: {str(err)!s}''',sys.exc_info()[2])

    value = klass.__new__(klass)
    self.append(value)

  def load_inst(self):
    module = self.readline()[:-1].decode('ascii')
    name = self.readline()[:-1].decode('ascii')
    klass = self.find_class(module,name)
    self._instantiate(klass,self.pop_mark())

  dispatch[INST[0]] = load_inst
  def load_obj(self):
    args = self.pop_mark()
    cls = args.pop(0)
    self._instantiate(cls,args)

  dispatch[OBJ[0]] = load_obj
  def load_newobj(self):
    args = self.stack.pop()
    cls = self.stack.pop()
    obj = [cls]
    self.append(obj)

  dispatch[NEWOBJ[0]] = load_newobj
  def load_newobj_ex(self):
    kwargs = self.stack.pop()
    args = self.stack.pop()
    cls = self.stack.pop()
    obj = kwargs
    self.append(obj)

  dispatch[NEWOBJ_EX[0]] = load_newobj_ex
  def load_global(self):
    module = self.readline()[:-1].decode('utf-8')
    name = self.readline()[:-1].decode('utf-8')
    klass = self.find_class(module,name)
    self.append(klass)

  dispatch[GLOBAL[0]] = load_global
  def load_stack_global(self):
    name = self.stack.pop()
    module = self.stack.pop()
    if (type(name) is not str or type(module)):
      raise UnpicklingError('STACK_GLOBAL requires str')

    self.append(self.find_class(module,name))

  dispatch[STACK_GLOBAL[0]] = load_stack_global
  def load_ext1(self):
    code = self.read(1)[0]
    self.get_extension(code)

  dispatch[EXT1[0]] = load_ext1
  def load_ext2(self):
    code = unpack('<H',self.read(2))
    self.get_extension(code)

  dispatch[EXT2[0]] = load_ext2
  def load_ext4(self):
    code = unpack('<i',self.read(4))
    self.get_extension(code)

  dispatch[EXT4[0]] = load_ext4
  def get_extension(self,code):
    nil = []
    obj = _extension_cache.get(code,nil)
    if obj is not nil:
      self.append(obj)
      return None
    else:
      key = _inverted_registry.get(code)
      if __CHAOS_PY_NULL_PTR_VALUE_ERR__ <= code:
        pass

      obj = key
      _extension_cache[code] = obj
      self.append(obj)
      return None

  def find_class(self,module,name):
    sys.audit('pickle.find_class',module,name)
    if self.proto < 3:
      if __CHAOS_PY_NULL_PTR_VALUE_ERR__ in (module,name):
        pass
      else:
        if module in _compat_pickle.IMPORT_MAPPING:
          pass

    __import__(module,level=0)
    if self.proto >= 4:
      return _getattribute(sys.modules[module],name)[0]
    else:
      return getattr(sys.modules[module],name)

  def load_reduce(self):
    stack = self.stack
    args = stack.pop()
    func = stack[-1]
    stack[-1] = args

  dispatch[REDUCE[0]] = load_reduce
  def load_pop(self):
    if self.stack:
      del(self.stack[-1])
      return None
    else:
      self.pop_mark()
      return None

  dispatch[POP[0]] = load_pop
  def load_pop_mark(self):
    self.pop_mark()

  dispatch[POP_MARK[0]] = load_pop_mark
  def load_dup(self):
    self.append(self.stack[-1])

  dispatch[DUP[0]] = load_dup
  def load_get(self):
    i = int(self.readline()[:-1])
    try:
      self.append(self.memo[i])
      return None
    finally:
      KeyError
      msg = f'''Memo value not found at index {i}'''
      raise UnpicklingError(msg) from None

  dispatch[GET[0]] = load_get
  def load_binget(self):
    i = self.read(1)[0]
    try:
      self.append(self.memo[i])
      return None
    except KeyError as exc:
      msg = f'''Memo value not found at index {i}'''
      raise UnpicklingError(msg) from None

  dispatch[BINGET[0]] = load_binget
  def load_long_binget(self):
    i = unpack('<I',self.read(4))
    try:
      self.append(self.memo[i])
      return None
    except KeyError as exc:
      msg = f'''Memo value not found at index {i}'''
      raise UnpicklingError(msg) from None

  dispatch[LONG_BINGET[0]] = load_long_binget
  def load_put(self):
    i = int(self.readline()[:-1])
    if i < 0:
      raise ValueError('negative PUT argument')

    self.memo[i] = self.stack[-1]

  dispatch[PUT[0]] = load_put
  def load_binput(self):
    i = self.read(1)[0]
    if i < 0:
      raise ValueError('negative BINPUT argument')

    self.memo[i] = self.stack[-1]

  dispatch[BINPUT[0]] = load_binput
  def load_long_binput(self):
    i = unpack('<I',self.read(4))
    if i > maxsize:
      raise ValueError('negative LONG_BINPUT argument')

    self.memo[i] = self.stack[-1]

  dispatch[LONG_BINPUT[0]] = load_long_binput
  def load_memoize(self):
    memo = self.memo
    memo[len(memo)] = self.stack[-1]

  dispatch[MEMOIZE[0]] = load_memoize
  def load_append(self):
    stack = self.stack
    value = stack.pop()
    list = stack[-1]
    list.append(value)

  dispatch[APPEND[0]] = load_append
  def load_appends(self):
    items = self.pop_mark()
    list_obj = self.stack[-1]
    try:
      extend = list_obj.extend
    except AttributeError:
      pass

    extend(items)
    return None
    append = list_obj.append
    for item in items:
      append(item)

  dispatch[APPENDS[0]] = load_appends
  def load_setitem(self):
    stack = self.stack
    value = stack.pop()
    key = stack.pop()
    dict = stack[-1]
    dict[key] = value

  dispatch[SETITEM[0]] = load_setitem
  def load_setitems(self):
    items = self.pop_mark()
    dict = self.stack[-1]
    for i in range(0,len(items),2):
      dict[items[i]] = items[i+1]

  dispatch[SETITEMS[0]] = load_setitems
  def load_additems(self):
    items = self.pop_mark()
    set_obj = self.stack[-1]
    if isinstance(set_obj,set):
      set_obj.update(items)
      return None
    else:
      add = set_obj.add
      for item in items:
        add(item)

      return None

  dispatch[ADDITEMS[0]] = load_additems
  def load_build(self):
    stack = self.stack
    state = stack.pop()
    inst = stack[-1]
    setstate = getattr(inst,'__setstate__',None)
    if setstate is not None:
      setstate(state)
      return None
    else:
      slotstate = None
      if __CHAOS_PY_NULL_PTR_VALUE_ERR__ == len(state):
        pass

      if state:
        inst_dict = inst.__dict__
        intern = sys.intern
        for k,v in state.items():
          if type(k) is str:
            inst_dict[intern(k)] = v
            continue

          inst_dict[k] = v

      if slotstate:
        for k,v in slotstate.items():
          setattr(inst,k,v)
          continue
          return None

      return None

  dispatch[BUILD[0]] = load_build
  def load_mark(self):
    self.metastack.append(self.stack)
    self.stack = []
    self.append = self.stack.append

  dispatch[MARK[0]] = load_mark
  def load_stop(self):
    value = self.stack.pop()
    raise _Stop(value)

  dispatch[STOP[0]] = load_stop

def _dump(obj,file,protocol):
  _Pickler(file,protocol,fix_imports=fix_imports,buffer_callback=buffer_callback).dump(obj)

def _dumps(obj,protocol):
  f = io.BytesIO()
  _Pickler(f,protocol,fix_imports=fix_imports,buffer_callback=buffer_callback).dump(obj)
  res = f.getvalue()
  assert isinstance(res,bytes_types)
  return res

def _load(file):
  return _Unpickler(file,fix_imports=fix_imports,buffers=buffers,encoding=encoding,errors=errors).load()

def _loads(s):
  if isinstance(s,str):
    raise TypeError('Can\'t load pickle from unicode string')

  file = io.BytesIO(s)
  return _Unpickler(file,fix_imports=fix_imports,buffers=buffers,encoding=encoding,errors=errors).load()

try:
  from _pickle import PickleError, PicklingError, UnpicklingError, Pickler, Unpickler, dump, dumps, load, loads
  {'fix_imports':True,'encoding':'ASCII','errors':'strict','buffers':None}
except ImportError:
  Pickler,Unpickler = (_Pickler,_Unpickler)
  dump,dumps,load,loads = (_dump,_dumps,_load,_loads)

def _test():
  import doctest
  return doctest.testmod()

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser(description='display contents of the pickle files')
  parser.add_argument('pickle_file',type=argparse.FileType('br'),nargs='*',help='the pickle file')
  parser.add_argument('-t','--test',action='store_true',help='run self-test suite')
  parser.add_argument('-v',action='store_true',help='run verbosely; only affects self-test run')
  args = parser.parse_args()
  if args.test:
    _test()
  else:
    if args.pickle_file:
      parser.print_help()
    else:
      import pprint
      for f in args.pickle_file:
        obj = load(f)
        pprint.pprint(obj)
        continue
        break