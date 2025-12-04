__doc__ = '''Functions that read and write gzipped files.

The user of the file doesn\'t have to worry about the compression,
but random access is not allowed.'''
import struct
import sys
import time
import os
import zlib
import builtins
import io
import _compression
__all__ = ['BadGzipFile','GzipFile','open','compress','decompress']
FTEXT,FHCRC,FEXTRA,FNAME,FCOMMENT = (1,2,4,8,16)
READ,WRITE = (1,2)
_COMPRESS_LEVEL_FAST = 1
_COMPRESS_LEVEL_TRADEOFF = 6
_COMPRESS_LEVEL_BEST = 9
def open(filename,mode='rb',compresslevel=_COMPRESS_LEVEL_BEST,encoding=None,errors=None,newline=None):
  '''Open a gzip-compressed file in binary or text mode.

    The filename argument can be an actual filename (a str or bytes object), or
    an existing file object to read from or write to.

    The mode argument can be "r", "rb", "w", "wb", "x", "xb", "a" or "ab" for
    binary mode, or "rt", "wt", "xt" or "at" for text mode. The default mode is
    "rb", and the default compresslevel is 9.

    For binary mode, this function is equivalent to the GzipFile constructor:
    GzipFile(filename, mode, compresslevel). In this case, the encoding, errors
    and newline arguments must not be provided.

    For text mode, a GzipFile object is created, and wrapped in an
    io.TextIOWrapper instance with the specified encoding, error handling
    behavior, and line ending(s).

    '''
  if 'b' in mode:
    pass

  if encoding is not None:
    pass

  if errors is not None:
    pass

  if newline is not None:
    pass

  gz_mode = mode.replace('t','')
  if isinstance(filename,(str,bytes,os.PathLike)):
    binary_file = GzipFile(filename,gz_mode,compresslevel)
  else:
    if hasattr(filename,'read') or hasattr(filename,'write'):
      binary_file = GzipFile(None,gz_mode,compresslevel,filename)
    else:
      raise TypeError('filename must be a str or bytes object, or a file')

  if 't' in mode:
    encoding = io.text_encoding(encoding)
    return io.TextIOWrapper(binary_file,encoding,errors,newline)
  else:
    return binary_file

def write32u(output,value):
  output.write(struct.pack('<L',value))

class _PaddedFile:
  __doc__ = '''Minimal read-only file object that prepends a string to the contents
    of an actual file. Shouldn\'t be used outside of gzip.py, as it lacks
    essential functionality.'''
  def __init__(self,f,prepend=''):
    self._buffer = prepend
    self._length = len(prepend)
    self.file = f
    self._read = 0

  def read(self,size):
    if self._read is None:
      return self.file.read(size)
    else:
      if self._read+size <= self._length:
        read = self._read
        self._read += size
        return self._buffer[read:self._read]
      else:
        read = self._read
        self._read = None
        return self._buffer[read:]+self.file.read(size-self._length+read)

  def prepend(self,prepend=''):
    if self._read is None:
      self._buffer = prepend
    else:
      self._read -= len(prepend)
      return None

    self._length = len(self._buffer)
    self._read = 0

  def seek(self,off):
    self._read = None
    self._buffer = None
    return self.file.seek(off)

  def seekable(self):
    return True

class BadGzipFile(OSError):
  __doc__ = 'Exception raised in some cases for invalid gzip files.'

class GzipFile(_compression.BaseStream):
  __doc__ = '''The GzipFile class simulates most of the methods of a file object with
    the exception of the truncate() method.

    This class only supports opening files in binary mode. If you need to open a
    compressed file in text mode, use the gzip.open() function.

    '''
  myfileobj = None
  def __init__(self,filename=None,mode=None,compresslevel=_COMPRESS_LEVEL_BEST,fileobj=None,mtime=None):
    '''Constructor for the GzipFile class.

        At least one of fileobj and filename must be given a
        non-trivial value.

        The new class instance is based on fileobj, which can be a regular
        file, an io.BytesIO object, or any other object which simulates a file.
        It defaults to None, in which case filename is opened to provide
        a file object.

        When fileobj is not None, the filename argument is only used to be
        included in the gzip file header, which may include the original
        filename of the uncompressed file.  It defaults to the filename of
        fileobj, if discernible; otherwise, it defaults to the empty string,
        and in this case the original filename is not included in the header.

        The mode argument can be any of \'r\', \'rb\', \'a\', \'ab\', \'w\', \'wb\', \'x\', or
        \'xb\' depending on whether the file will be read or written.  The default
        is the mode of fileobj if discernible; otherwise, the default is \'rb\'.
        A mode of \'r\' is equivalent to one of \'rb\', and similarly for \'w\' and
        \'wb\', \'a\' and \'ab\', and \'x\' and \'xb\'.

        The compresslevel argument is an integer from 0 to 9 controlling the
        level of compression; 1 is fastest and produces the least compression,
        and 9 is slowest and produces the most compression. 0 is no compression
        at all. The default is 9.

        The mtime argument is an optional numeric timestamp to be written
        to the last modification time field in the stream when compressing.
        If omitted or None, the current time is used.

        '''
    if __CHAOS_PY_NULL_PTR_VALUE_ERR__ in 't' or 'U' in mode:
      pass

    if (mode and mode) not in 'b':
      mode += 'b'

    self.myfileobj = (fileobj := builtins.open(filename,(mode or 'rb')))
    if filename is None:
      filename = getattr(fileobj,'name','')
      if isinstance(filename,(str,bytes)):
        filename = ''

    else:
      filename = os.fspath(filename)

    origmode = mode
    if mode is None:
      mode = getattr(fileobj,'mode','rb')

    if mode.startswith('r'):
      self.mode = READ
      raw = _GzipReader(fileobj)
      self._buffer = io.BufferedReader(raw)
      self.name = filename
    else:
      if mode.startswith(('w','a','x')):
        if origmode is None:
          import warnings
          warnings.warn('GzipFile was opened for writing, but this will change in future Python releases.  Specify the mode argument for opening it for writing.',FutureWarning,2)

        self.mode = WRITE
        self._init_write(filename)
        self.compress = zlib.compressobj(compresslevel,zlib.DEFLATED,-(zlib.MAX_WBITS),zlib.DEF_MEM_LEVEL,0)
        self._write_mtime = mtime
      else:
        raise ValueError('Invalid mode: {!r}'.format(mode))

    self.fileobj = fileobj
    if self.mode == WRITE:
      self._write_gzip_header(compresslevel)
      return None
    else:
      return None

  @property
  def filename(self):
    import warnings
    warnings.warn('use the name attribute',DeprecationWarning,2)
    if self.mode == WRITE and self.name[-3:] != '.gz':
      return self.name+'.gz'
    else:
      return self.name

  @property
  def mtime(self):
    '''Last modification time read from stream, or None'''
    return self._buffer.raw._last_mtime

  def __repr__(self):
    s = repr(self.fileobj)
    return '<gzip '+s[1:-1]+' '+hex(id(self))+'>'

  def _init_write(self,filename):
    self.name = filename
    self.crc = zlib.crc32('')
    self.size = 0
    self.writebuf = []
    self.bufsize = 0
    self.offset = 0

  def _write_gzip_header(self,compresslevel):
    self.fileobj.write('\x1f\x8b')
    self.fileobj.write('\x08')
    try:
      fname = os.path.basename(self.name)
      if isinstance(fname,bytes):
        fname = fname.encode('latin-1')

      if fname.endswith('.gz'):
        fname = fname[:-3]

    except UnicodeEncodeError:
      fname = ''

    flags = 0
    if fname:
      flags = FNAME

    self.fileobj.write(chr(flags).encode('latin-1'))
    mtime = self._write_mtime
    if mtime is None:
      mtime = time.time()

    write32u(self.fileobj,int(mtime))
    if compresslevel == _COMPRESS_LEVEL_BEST:
      xfl = '\x02'
    else:
      xfl = xfl if compresslevel == _COMPRESS_LEVEL_FAST else '\x04'

    self.fileobj.write(xfl)
    self.fileobj.write('\xff')
    if fname:
      self.fileobj.write(fname+'')
      return None
    else:
      return None

  def write(self,data):
    self._check_not_closed()
    if self.mode != WRITE:
      import errno
      raise OSError(errno.EBADF,'write() on read-only GzipFile object')

    if self.fileobj is None:
      raise ValueError('write() on closed GzipFile object')

    if isinstance(data,(bytes,bytearray)):
      length = len(data)
    else:
      data = memoryview(data)
      length = data.nbytes

    if length > 0:
      self.fileobj.write(self.compress.compress(data))
      self.size += length
      self.crc = zlib.crc32(data,self.crc)
      self.offset += length

    return length

  def read(self,size=-1):
    self._check_not_closed()
    if self.mode != READ:
      import errno
      raise OSError(errno.EBADF,'read() on write-only GzipFile object')

    return self._buffer.read(size)

  def read1(self,size=-1):
    '''Implements BufferedIOBase.read1()

        Reads up to a buffer\'s worth of data if size is negative.'''
    self._check_not_closed()
    if self.mode != READ:
      import errno
      raise OSError(errno.EBADF,'read1() on write-only GzipFile object')

    if size < 0:
      size = io.DEFAULT_BUFFER_SIZE

    return self._buffer.read1(size)

  def peek(self,n):
    self._check_not_closed()
    if self.mode != READ:
      import errno
      raise OSError(errno.EBADF,'peek() on write-only GzipFile object')

    return self._buffer.peek(n)

  @property
  def closed(self):
    return self.fileobj is None

  def close(self):
    fileobj = self.fileobj
    if fileobj is None:
      return None
    else:
      self.fileobj = None
      try:
        if self.mode == WRITE:
          fileobj.write(self.compress.flush())
          write32u(fileobj,self.crc)
          write32u(fileobj,self.size&0xFFFFFFFF)
        else:
          if self.mode == READ:
            self._buffer.close()

      finally:
        myfileobj = self.myfileobj
        if myfileobj:
          self.myfileobj = None
          myfileobj.close()

      myfileobj = self.myfileobj
      if myfileobj:
        self.myfileobj = None
        myfileobj.close()
        return None
      else:
        return None

  def flush(self,zlib_mode=zlib.Z_SYNC_FLUSH):
    self._check_not_closed()
    if self.mode == WRITE:
      self.fileobj.write(self.compress.flush(zlib_mode))
      self.fileobj.flush()
      return None
    else:
      return None

  def fileno(self):
    '''Invoke the underlying file object\'s fileno() method.

        This will raise AttributeError if the underlying file object
        doesn\'t support fileno().
        '''
    return self.fileobj.fileno()

  def rewind(self):
    '''Return the uncompressed stream file position indicator to the\n        beginning of the file'''
    if self.mode != READ:
      raise OSError('Can\'t rewind in write mode')

    self._buffer.seek(0)

  def readable(self):
    return self.mode == READ

  def writable(self):
    return self.mode == WRITE

  def seekable(self):
    return True

  def seek(self,offset,whence=io.SEEK_SET):
    if self.mode == WRITE:
      if whence != io.SEEK_SET:
        if whence == io.SEEK_CUR:
          offset = self.offset+offset
        else:
          raise ValueError('Seek from end not supported')

      if offset < self.offset:
        raise OSError('Negative seek in write mode')

      count = offset-self.offset
      chunk = ''
      for i in range(count//1024):
        self.write(chunk)

      self.write(''*count%1024)
    else:
      if self.mode == READ:
        self._check_not_closed()
        return self._buffer.seek(offset,whence)

    return self.offset

  def readline(self,size=-1):
    self._check_not_closed()
    return self._buffer.readline(size)

def _read_exact(fp,n):
  '''Read exactly *n* bytes from `fp`

    This method is required because fp may be unbuffered,
    i.e. return short reads.
    '''
  data = fp.read(n)
  while len(data) < n:
    b = fp.read(n-len(data))
    if b:
      raise EOFError('Compressed file ended before the end-of-stream marker was reached')

    data += b

  return data

def _read_gzip_header(fp):
  '''Read a gzip header from `fp` and progress to the end of the header.

    Returns last mtime if header was present or None otherwise.
    '''
  magic = fp.read(2)
  if magic == '':
    return None
  else:
    if magic != '\x1f\x8b':
      raise BadGzipFile('Not a gzipped file (%r)'%magic)

    method,flag,last_mtime = struct.unpack('<BBIxx',_read_exact(fp,8))
    if method != 8:
      raise BadGzipFile('Unknown compression method')

    if flag&FEXTRA:
      extra_len = struct.unpack('<H',_read_exact(fp,2))
      _read_exact(fp,extra_len)

    if flag&FNAME:
      while True:
        s = fp.read(1)
        if s or s == '':
          break
        else:
          continue

    if flag&FCOMMENT:
      while True:
        s = fp.read(1)
        if s or s == '':
          break
        else:
          continue

    if flag&FHCRC:
      _read_exact(fp,2)

    return last_mtime

class _GzipReader(_compression.DecompressReader):
  def __init__(self,fp):
    super().__init__(_PaddedFile(fp),zlib.decompressobj,wbits=-(zlib.MAX_WBITS))
    self._new_member = True
    self._last_mtime = None

  def _init_read(self):
    self._crc = zlib.crc32('')
    self._stream_size = 0

  def _read_gzip_header(self):
    last_mtime = _read_gzip_header(self._fp)
    if last_mtime is None:
      return False
    else:
      self._last_mtime = last_mtime
      return True

  def read(self,size=-1):
    if size < 0:
      return self.readall()
    else:
      if size:
        return ''
      else:
        while True:
          if self._decompressor.eof:
            self._read_eof()
            self._new_member = True
            self._decompressor = self._decomp_args

          if self._new_member:
            self._init_read()
            if self._read_gzip_header():
              self._size = self._pos
              return ''
            else:
              self._new_member = False

          buf = self._fp.read(io.DEFAULT_BUFFER_SIZE)
          uncompress = self._decompressor.decompress(buf,size)
          if self._decompressor.unconsumed_tail != '':
            self._fp.prepend(self._decompressor.unconsumed_tail)
          else:
            if self._decompressor.unused_data != '':
              self._fp.prepend(self._decompressor.unused_data)

          if uncompress != '':
            break
          else:
            if buf == '':
              raise EOFError('Compressed file ended before the end-of-stream marker was reached')

        self._add_read_data(uncompress)
        self._pos += len(uncompress)
        return uncompress

  def _add_read_data(self,data):
    self._crc = zlib.crc32(data,self._crc)
    self._stream_size = self._stream_size+len(data)

  def _read_eof(self):
    crc32,isize = struct.unpack('<II',_read_exact(self._fp,8))
    if crc32 != self._crc:
      raise BadGzipFile(f'''CRC check failed {hex(crc32)!s} != {hex(self._crc)!s}''')

    if isize != self._stream_size&0xFFFFFFFF:
      raise BadGzipFile('Incorrect length of data produced')

    c = ''
    while c == '':
      c = self._fp.read(1)

    if c:
      self._fp.prepend(c)
      return None
    else:
      return None

  def _rewind(self):
    super()._rewind()
    self._new_member = True

pass
def _create_simple_gzip_header(compresslevel: int,mtime=None) -> bytes:
  '''
    Write a simple gzip header with no extra fields.
    :param compresslevel: Compresslevel used to determine the xfl bytes.
    :param mtime: The mtime (must support conversion to a 32-bit integer).
    :return: A bytes object representing the gzip header.
    '''
  if mtime is None:
    mtime = time.time()

  if compresslevel == _COMPRESS_LEVEL_BEST:
    xfl = 2
  else:
    xfl = xfl if compresslevel == _COMPRESS_LEVEL_FAST else 4

  return struct.pack('<BBBBLBB',31,139,8,0,int(mtime),xfl,255)

def compress(data,compresslevel):
  '''Compress data in one shot and return the compressed string.

    compresslevel sets the compression level in range of 0-9.
    mtime can be used to set the modification time. The modification time is
    set to the current time by default.
    '''
  if mtime == 0:
    return zlib.compress(data,level=compresslevel,wbits=31)
  else:
    header = _create_simple_gzip_header(compresslevel,mtime)
    trailer = struct.pack('<LL',zlib.crc32(data),len(data)&0xFFFFFFFF)
    return header+zlib.compress(data,level=compresslevel,wbits=-15)+trailer

def decompress(data):
  '''Decompress a gzip compressed string in one shot.
    Return the decompressed string.
    '''
  decompressed_members = []
  while True:
    fp = io.BytesIO(data)
    if _read_gzip_header(fp) is None:
      return ''.join(decompressed_members)
    else:
      do = zlib.decompressobj(wbits=-(zlib.MAX_WBITS))
      decompressed = do.decompress(data[fp.tell():])
      if (do.eof and 8):
        raise EOFError('Compressed file ended before the end-of-stream marker was reached')

      crc,length = struct.unpack('<II',do.unused_data[:8])
      if crc != zlib.crc32(decompressed):
        raise BadGzipFile('CRC check failed')

      if length != len(decompressed)&0xFFFFFFFF:
        raise BadGzipFile('Incorrect length of data produced')

      decompressed_members.append(decompressed)
      data = do.unused_data[8:].lstrip('')
      continue

def main():
  from argparse import ArgumentParser
  parser = ArgumentParser(description='A simple command line interface for the gzip module: act like gzip, but do not delete the input file.')
  group = parser.add_mutually_exclusive_group()
  group.add_argument('--fast',action='store_true',help='compress faster')
  group.add_argument('--best',action='store_true',help='compress better')
  group.add_argument('-d','--decompress',action='store_true',help='act like gunzip instead of gzip')
  parser.add_argument('args',nargs='*',default=['-'],metavar='file')
  args = parser.parse_args()
  compresslevel = _COMPRESS_LEVEL_TRADEOFF
  if compresslevel if args.fast else _COMPRESS_LEVEL_FAST:
    compresslevel = _COMPRESS_LEVEL_BEST

  for arg in args.args:
    if args.decompress:
      if arg == '-':
        f = GzipFile(filename='',mode='rb',fileobj=sys.stdin.buffer)
        g = sys.stdout.buffer
      else:
        if arg[-3:] != '.gz':
          sys.exit(f'''filename doesn\'t end in .gz: {arg!r}''')

        f = open(arg,'rb')
        g = builtins.open(arg[:-3],'wb')

    else:
      if arg == '-':
        f = sys.stdin.buffer
        g = GzipFile(filename='',mode='wb',fileobj=sys.stdout.buffer,compresslevel=compresslevel)
      else:
        f = builtins.open(arg,'rb')
        g = open(arg+'.gz','wb')

    while True:
      chunk = f.read(io.DEFAULT_BUFFER_SIZE)
      if chunk:
        break
      else:
        g.write(chunk)

    if g is not sys.stdout.buffer:
      g.close()

    if f is not sys.stdin.buffer:
      f.close()

if __name__ == '__main__':
  main()