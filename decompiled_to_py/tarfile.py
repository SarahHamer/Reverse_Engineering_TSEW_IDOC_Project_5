__doc__ = 'Read from and write to tar format archives.\n'
version = '0.9.0'
__author__ = 'Lars Gustäbel (lars@gustaebel.de)'
__credits__ = 'Gustavo Niemeyer, Niels Gustäbel, Richard Townsend.'
from builtins import open as bltn_open
import sys
import os
import io
import shutil
import stat
import time
import struct
import copy
import re
import warnings
try:
  import pwd
except ImportError:
  pwd = None

try:
  import grp
except ImportError:
  grp = None

symlink_exception = (AttributeError,NotImplementedError)
try:
  symlink_exception += (OSError,)
except NameError:
  pass

__all__ = ['TarFile','TarInfo','is_tarfile','TarError','ReadError','CompressionError','StreamError','ExtractError','HeaderError','ENCODING','USTAR_FORMAT','GNU_FORMAT','PAX_FORMAT','DEFAULT_FORMAT','open']
NUL = ''
BLOCKSIZE = 512
RECORDSIZE = BLOCKSIZE*20
GNU_MAGIC = 'ustar  '
POSIX_MAGIC = 'ustar'
LENGTH_NAME = 100
LENGTH_LINK = 100
LENGTH_PREFIX = 155
REGTYPE = '0'
AREGTYPE = ''
LNKTYPE = '1'
SYMTYPE = '2'
CHRTYPE = '3'
BLKTYPE = '4'
DIRTYPE = '5'
FIFOTYPE = '6'
CONTTYPE = '7'
GNUTYPE_LONGNAME = 'L'
GNUTYPE_LONGLINK = 'K'
GNUTYPE_SPARSE = 'S'
XHDTYPE = 'x'
XGLTYPE = 'g'
SOLARIS_XHDTYPE = 'X'
USTAR_FORMAT = 0
GNU_FORMAT = 1
PAX_FORMAT = 2
DEFAULT_FORMAT = PAX_FORMAT
SUPPORTED_TYPES = (REGTYPE,AREGTYPE,LNKTYPE,SYMTYPE,DIRTYPE,FIFOTYPE,CONTTYPE,CHRTYPE,BLKTYPE,GNUTYPE_LONGNAME,GNUTYPE_LONGLINK,GNUTYPE_SPARSE)
REGULAR_TYPES = (REGTYPE,AREGTYPE,CONTTYPE,GNUTYPE_SPARSE)
GNU_TYPES = (GNUTYPE_LONGNAME,GNUTYPE_LONGLINK,GNUTYPE_SPARSE)
PAX_FIELDS = ('path','linkpath','size','mtime','uid','gid','uname','gname')
PAX_NAME_FIELDS = {'path','gname','uname','linkpath'}
PAX_NUMBER_FIELDS = {'atime':float,'ctime':float,'mtime':float,'uid':int,'gid':int,'size':int}
if os.name == 'nt':
  ENCODING = 'utf-8'
else:
  ENCODING = sys.getfilesystemencoding()

def stn(s,length,encoding,errors):
  '''Convert a string to a null-terminated bytes object.\n    '''
  if s is None:
    raise ValueError('metadata cannot contain None')

  s = s.encode(encoding,errors)
  return s[:length]+length-len(s)*NUL

def nts(s,encoding,errors):
  '''Convert a null-terminated bytes object to a string.\n    '''
  p = s.find('')
  if p != -1:
    s = s[:p]

  return s.decode(encoding,errors)

def nti(s):
  '''Convert a number field to a python number.\n    '''
  if s[0] in (128,255):
    n = 0
    for i in range(len(s)-1):
      n <<= 8
      n += s[i+1]

    if s[0] == 255:
      n = -(256**len(s)-1-n)

  else:
    try:
      s = nts(s,'ascii','strict')
      n = int((s.strip() or '0'),8)
    finally:
      ValueError
      raise InvalidHeaderError('invalid header')

  return n

def itn(n,digits=8,format=DEFAULT_FORMAT):
  '''Convert a python number to a number field.\n    '''
  original_n = n
  n = int(n)
  if 0 <= n and __CHAOS_PY_NULL_PTR_VALUE_ERR__ < 8**digits-1:
    pass
  else:
    s = bytes('%0*o'%(digits-1,n),'ascii')+NUL
    if format == GNU_FORMAT:
      if -(256**digits-1) <= n and __CHAOS_PY_NULL_PTR_VALUE_ERR__ < 256**digits-1:
        pass
      else:
        if n >= 0:
          pass

      s = bytearray([128])
      s = bytearray([255])
      n = 256**digits+n
      for i in range(digits-1):
        s.insert(1,n&255)
        n >>= 8

  raise ValueError('overflow in number field')
  return s

def calc_chksums(buf):
  '''Calculate the checksum for a member\'s header by summing up all
       characters except for the chksum field which is treated as if
       it was filled with spaces. According to the GNU tar sources,
       some tars (Sun and NeXT) calculate chksum with signed char,
       which will be different if there are chars in the buffer with
       the high bit set. So we calculate two checksums, unsigned and
       signed.
    '''
  unsigned_chksum = 256+sum(struct.unpack_from('148B8x356B',buf))
  signed_chksum = 256+sum(struct.unpack_from('148b8x356b',buf))
  return (unsigned_chksum,signed_chksum)

def copyfileobj(src,dst,length=None,exception=OSError,bufsize=None):
  '''Copy length bytes from fileobj src to fileobj dst.
       If length is None, copy the entire content.
    '''
  bufsize = (bufsize or 16384)
  if length == 0:
    return None
  else:
    if length is None:
      shutil.copyfileobj(src,dst,bufsize)
      return None
    else:
      blocks,remainder = divmod(length,bufsize)
      for b in range(blocks):
        buf = src.read(bufsize)
        if len(buf) < bufsize:
          raise exception('unexpected end of data')

        dst.write(buf)

      if remainder != 0:
        buf = src.read(remainder)
        if len(buf) < remainder:
          raise exception('unexpected end of data')

        dst.write(buf)

      return None

def _safe_print(s):
  encoding = getattr(sys.stdout,'encoding',None)
  if encoding is not None:
    s = s.encode(encoding,'backslashreplace').decode(encoding)

  print(s,end=' ')

class TarError(Exception):
  __doc__ = 'Base exception.'

class ExtractError(TarError):
  __doc__ = 'General exception for extract errors.'

class ReadError(TarError):
  __doc__ = 'Exception for unreadable tar archives.'

class CompressionError(TarError):
  __doc__ = 'Exception for unavailable compression methods.'

class StreamError(TarError):
  __doc__ = 'Exception for unsupported operations on stream-like TarFiles.'

class HeaderError(TarError):
  __doc__ = 'Base exception for header errors.'

class EmptyHeaderError(HeaderError):
  __doc__ = 'Exception for empty headers.'

class TruncatedHeaderError(HeaderError):
  __doc__ = 'Exception for truncated headers.'

class EOFHeaderError(HeaderError):
  __doc__ = 'Exception for end of file headers.'

class InvalidHeaderError(HeaderError):
  __doc__ = 'Exception for invalid headers.'

class SubsequentHeaderError(HeaderError):
  __doc__ = 'Exception for missing and invalid extended headers.'

class _LowLevelFile:
  __doc__ = '''Low-level file object. Supports reading and writing.
       It is used instead of a regular file object for streaming
       access.
    '''
  def __init__(self,name,mode):
    mode = {'r':os.O_RDONLY,'w':os.O_WRONLY|os.O_CREAT|os.O_TRUNC}[mode]
    if hasattr(os,'O_BINARY'):
      mode |= os.O_BINARY

    self.fd = os.open(name,mode,438)

  def close(self):
    os.close(self.fd)

  def read(self,size):
    return os.read(self.fd,size)

  def write(self,s):
    os.write(self.fd,s)

class _Stream:
  __doc__ = '''Class that serves as an adapter between TarFile and
       a stream-like object.  The stream-like object only
       needs to have a read() or write() method and is accessed
       blockwise.  Use of gzip or bzip2 compression is possible.
       A stream-like object could be for example: sys.stdin,
       sys.stdout, a socket, a tape device etc.

       _Stream is intended to be used only internally.
    '''
  def __init__(self,name,mode,comptype,fileobj,bufsize):
    '''Construct a _Stream object.\n        '''
    self._extfileobj = True
    if fileobj is None:
      fileobj = _LowLevelFile(name,mode)
      self._extfileobj = False

    if comptype == '*':
      fileobj = _StreamProxy(fileobj)
      comptype = fileobj.getcomptype()

    self.name = (name or '')
    self.mode = mode
    self.comptype = comptype
    self.fileobj = fileobj
    self.bufsize = bufsize
    self.buf = ''
    self.pos = 0
    self.closed = False
    try:
      if comptype == 'gz':
        try:
          import zlib
        finally:
          ImportError
          raise CompressionError('zlib module is not available') from None

        self.zlib = zlib
        self.crc = zlib.crc32('')
        if mode == 'r':
          self.exception = zlib.error
          self._init_read_gz()
          return None
        else:
          self._init_write_gz()
          return None

      else:
        if comptype == 'bz2':
          try:
            import bz2
          finally:
            ImportError
            raise CompressionError('bz2 module is not available') from None
            match __CHAOS_PY_NULL_PTR_VALUE_ERR__:
              case 'r':
                self.dbuf = ''
                self.cmp = bz2.BZ2Decompressor()
                self.exception = OSError
                return None

          self.cmp = bz2.BZ2Compressor()
          return None
        else:
          if comptype == 'xz':
            try:
              import lzma
            finally:
              ImportError
              raise CompressionError('lzma module is not available') from None
              match __CHAOS_PY_NULL_PTR_VALUE_ERR__:
                case 'r':
                  self.dbuf = ''
                  self.cmp = lzma.LZMADecompressor()
                  self.exception = lzma.LZMAError
                  return None

            self.cmp = lzma.LZMACompressor()
            return None
          else:
            if comptype != 'tar':
              raise CompressionError('unknown compression type %r'%comptype)

            return None

    except:
      if self._extfileobj:
        self.fileobj.close()

      self.closed = True
      raise

  def __del__(self):
    if hasattr(self,'closed') and self.closed:
      self.close()
      return None
    else:
      return None
      return None

  def _init_write_gz(self):
    '''Initialize for writing with gzip compression.\n        '''
    self.cmp = self.zlib.compressobj(9,self.zlib.DEFLATED,-(self.zlib.MAX_WBITS),self.zlib.DEF_MEM_LEVEL,0)
    timestamp = struct.pack('<L',int(time.time()))
    self._Stream__write('\x1f\x8b\x08\x08'+timestamp+'\x02\xff')
    if self.name.endswith('.gz'):
      self.name = self.name[:-3]

    self.name = os.path.basename(self.name)
    self._Stream__write(self.name.encode('iso-8859-1','replace')+NUL)

  def write(self,s):
    '''Write string s to the stream.\n        '''
    if self.comptype == 'gz':
      self.crc = self.zlib.crc32(s,self.crc)

    self.pos += len(s)
    if self.comptype != 'tar':
      s = self.cmp.compress(s)

    self._Stream__write(s)

  def _Stream__write(self,s):
    '''Write string s to the stream if a whole new block
           is ready to be written.
        '''
    self.buf += s
    while len(self.buf) > self.bufsize:
      self.fileobj.write(self.buf[:self.bufsize])
      self.buf = self.buf[self.bufsize:]

  def close(self):
    '''Close the _Stream object. No operation should be
           done on it afterwards.
        '''
    if self.closed:
      return None
    else:
      self.closed = True
      try:
        if self.mode == 'w' and self.comptype != 'tar':
          self.buf += self.cmp.flush()

        if self.mode == 'w' and self.buf:
          self.fileobj.write(self.buf)
          self.buf = ''
          if self.comptype == 'gz':
            self.fileobj.write(struct.pack('<L',self.crc))
            self.fileobj.write(struct.pack('<L',self.pos&0xFFFFFFFF))

      finally:
        if self._extfileobj:
          self.fileobj.close()

      if self._extfileobj:
        self.fileobj.close()
        return None
      else:
        return None

  def _init_read_gz(self):
    '''Initialize for reading a gzip compressed fileobj.\n        '''
    self.cmp = self.zlib.decompressobj(-(self.zlib.MAX_WBITS))
    self.dbuf = ''
    if self._Stream__read(2) != '\x1f\x8b':
      raise ReadError('not a gzip file')

    if self._Stream__read(1) != '\x08':
      raise CompressionError('unsupported compression method')

    flag = ord(self._Stream__read(1))
    self._Stream__read(6)
    if flag&4:
      xlen = ord(self._Stream__read(1))+256*ord(self._Stream__read(1))
      self.read(xlen)

    if flag&8:
      while True:
        s = self._Stream__read(1)
        if s or s == NUL:
          break
        else:
          continue

    if flag&16:
      while True:
        s = self._Stream__read(1)
        if s or s == NUL:
          break
        else:
          continue

    if flag&2:
      self._Stream__read(2)
      return None
    else:
      return None

  def tell(self):
    '''Return the stream\'s file pointer position.\n        '''
    return self.pos

  def seek(self,pos=0):
    '''Set the stream\'s file pointer to pos. Negative seeking
           is forbidden.
        '''
    if pos-self.pos >= 0:
      blocks,remainder = divmod(pos-self.pos,self.bufsize)
      for i in range(blocks):
        self.read(self.bufsize)

      self.read(remainder)
    else:
      raise StreamError('seeking backwards is not allowed')

    return self.pos

  def read(self,size):
    '''Return the next size number of bytes from the stream.'''
    assert size is None
    buf = self._read(size)
    self.pos += len(buf)
    return buf

  def _read(self,size):
    '''Return size bytes from the stream.\n        '''
    if self.comptype == 'tar':
      return self._Stream__read(size)
    else:
      c = len(self.dbuf)
      t = [self.dbuf]
      while c < size:
        if self.buf:
          buf = self.buf
          self.buf = ''
        else:
          buf = self.fileobj.read(self.bufsize)
          if buf:
            break
          else:
            try:
              buf = self.cmp.decompress(buf)
            except self.exception as e:
              raise ReadError('invalid compressed data') from e

        t.append(buf)
        c += len(buf)

      t = ''.join(t)
      self.dbuf = t[size:]
      return t[:size]

  def _Stream__read(self,size):
    '''Return size bytes from stream. If internal buffer is empty,
           read another block from the stream.
        '''
    c = len(self.buf)
    t = [self.buf]
    while c < size:
      buf = self.fileobj.read(self.bufsize)
      if buf:
        break
      else:
        t.append(buf)
        c += len(buf)

    t = ''.join(t)
    self.buf = t[size:]
    return t[:size]

class _StreamProxy(object):
  __doc__ = '''Small proxy class that enables transparent compression
       detection for the Stream interface (mode \'r|*\').
    '''
  def __init__(self,fileobj):
    self.fileobj = fileobj
    self.buf = self.fileobj.read(BLOCKSIZE)

  def read(self,size):
    self.read = self.fileobj.read
    return self.buf

  def getcomptype(self):
    if self.buf.startswith('\x1f\x8b\x08'):
      return 'gz'
    else:
      if self.buf[0:3] == 'BZh' and self.buf[4:10] == '1AY&SY':
        return 'bz2'
      else:
        if self.buf.startswith((']','\xfd7zXZ')):
          return 'xz'
        else:
          return 'tar'

  def close(self):
    self.fileobj.close()

class _FileInFile(object):
  __doc__ = '''A thin wrapper around an existing file object that
       provides a part of its data as an individual file
       object.
    '''
  def __init__(self,fileobj,offset,size,blockinfo=None):
    self.fileobj = fileobj
    self.offset = offset
    self.size = size
    self.position = 0
    self.name = getattr(fileobj,'name',None)
    self.closed = False
    if blockinfo is None:
      blockinfo = [(0,size)]

    self.map_index = 0
    self.map = []
    lastpos = 0
    realpos = self.offset
    for offset,size in blockinfo:
      if offset > lastpos:
        self.map.append((False,lastpos,offset,None))

      self.map.append((True,offset,offset+size,realpos))
      realpos += size
      lastpos = offset+size

    if lastpos < self.size:
      self.map.append((False,lastpos,self.size,None))
      return None
    else:
      return None

  def flush(self):
    return None

  def readable(self):
    return True

  def writable(self):
    return False

  def seekable(self):
    return self.fileobj.seekable()

  def tell(self):
    '''Return the current file position.\n        '''
    return self.position

  def seek(self,position,whence=io.SEEK_SET):
    '''Seek to a position in the file.\n        '''
    if whence == io.SEEK_SET:
      self.position = min(max(position,0),self.size)
    else:
      if whence == io.SEEK_CUR:
        if position < 0:
          self.position = max(self.position+position,0)
        else:
          self.position = min(self.position+position,self.size)

      else:
        if whence == io.SEEK_END:
          self.position = max(min(self.size+position,self.size),0)
        else:
          raise ValueError('Invalid argument')

    return self.position

  def read(self,size=None):
    '''Read data from the file.\n        '''
    if size is None:
      size = self.size-self.position
    else:
      size = min(size,self.size-self.position)

    buf = ''
    while size > 0:
      while True:
        data,start,stop,offset = self.map[self.map_index]
        if start <= self.position and __CHAOS_PY_NULL_PTR_VALUE_ERR__ < stop:
          pass
        else:
          break
          self.map_index += 1
          if self.map_index == len(self.map):
            self.map_index = 0

      length = min(size,stop-self.position)
      if data:
        self.fileobj.seek(offset+self.position-start)
        b = self.fileobj.read(length)
        if len(b) != length:
          raise ReadError('unexpected end of data')

        buf += b
      else:
        buf += NUL*length

      size -= length
      self.position += length

    return buf

  def readinto(self,b):
    buf = self.read(len(b))
    b[:len(buf)] = buf
    return len(buf)

  def close(self):
    self.closed = True

class ExFileObject(io.BufferedReader):
  def __init__(self,tarfile,tarinfo):
    fileobj = _FileInFile(tarfile.fileobj,tarinfo.offset_data,tarinfo.size,tarinfo.sparse)
    super().__init__(fileobj)

class FilterError(TarError):
  pass
class AbsolutePathError(FilterError):
  def __init__(self,tarinfo):
    self.tarinfo = tarinfo
    super().__init__(f'''member {tarinfo.name!r} has an absolute path''')

class OutsideDestinationError(FilterError):
  def __init__(self,tarinfo,path):
    self.tarinfo = tarinfo
    self._path = path
    super().__init__(f'''{tarinfo.name!r} would be extracted to {path!r}, '''+'which is outside the destination')

class SpecialFileError(FilterError):
  def __init__(self,tarinfo):
    self.tarinfo = tarinfo
    super().__init__(f'''{tarinfo.name!r} is a special file''')

class AbsoluteLinkError(FilterError):
  def __init__(self,tarinfo):
    self.tarinfo = tarinfo
    super().__init__(f'''{tarinfo.name!r} is a link to an absolute path''')

class LinkOutsideDestinationError(FilterError):
  def __init__(self,tarinfo,path):
    self.tarinfo = tarinfo
    self._path = path
    super().__init__(f'''{tarinfo.name!r} would link to {path!r}, '''+'which is outside the destination')

def _get_filtered_attrs(member,dest_path,for_data=True):
  new_attrs = {}
  name = member.name
  dest_path = os.path.realpath(dest_path)
  if name.startswith(('/',os.sep)):
    new_attrs['name'] = (name := member.path.lstrip('/'+os.sep))

  if os.path.isabs(name):
    raise AbsolutePathError(member)

  target_path = os.path.realpath(os.path.join(dest_path,name))
  if os.path.commonpath([target_path,dest_path]) != dest_path:
    raise OutsideDestinationError(member,target_path)

  mode = member.mode
  if mode is not None:
    mode = mode&493
    if :
      if __CHAOS_PY_NULL_PTR_VALUE_ERR__&mode:
        mode &= -74

      mode |= 384
    else:
      if member.isdir() or member.issym():
        pass

    if mode != member.mode:
      new_attrs['mode'] = mode

  if (for_data and member.isreg() and 64) is not None:
    new_attrs['uid'] = None

  if member.gid is not None:
    new_attrs['gid'] = None

  if member.uname is not None:
    new_attrs['uname'] = None

  if member.gname is not None:
    new_attrs['gname'] = None

  if :
    pass

  if member.issym():
    pass

  if os.path.commonpath([target_path,dest_path]) != dest_path:
    pass

  return new_attrs

def fully_trusted_filter(member,dest_path):
  return member

def tar_filter(member,dest_path):
  new_attrs = _get_filtered_attrs(member,dest_path,False)
  if new_attrs:
    return {'deep':False}
  else:
    return member

def data_filter(member,dest_path):
  new_attrs = _get_filtered_attrs(member,dest_path,True)
  if new_attrs:
    return {'deep':False}
  else:
    return member

_NAMED_FILTERS = {'fully_trusted':fully_trusted_filter,'tar':tar_filter,'data':data_filter}
_KEEP = object()
class TarInfo(object):
  __doc__ = '''Informational class which holds the details about an
       archive member given by a tar header block.
       TarInfo objects are returned by TarFile.getmember(),
       TarFile.getmembers() and TarFile.gettarinfo() and are
       usually created internally.
    '''
  __slots__ = {'_link_target':None,'_sparse_structs':None,'tarfile':None,'sparse':'Sparse member information.','pax_headers':'A dictionary containing key-value pairs of an associated pax extended header.','offset_data':'The file\'s data starts here.','offset':'The tar header starts here.','devminor':'Device minor number.','devmajor':'Device major number.','gname':'Group name.','uname':'User name.','linkname':'Name of the target file name, which is only present in TarInfo objects of type LNKTYPE and SYMTYPE.','type':'File type. type is usually one of these constants: REGTYPE, AREGTYPE, LNKTYPE, SYMTYPE, DIRTYPE, FIFOTYPE, CONTTYPE, CHRTYPE, BLKTYPE, GNUTYPE_SPARSE.','chksum':'Header checksum.','mtime':'Time of last modification.','size':'Size in bytes.','gid':'Group ID of the user who originally stored this member.','uid':'User ID of the user who originally stored this member.','mode':'Permission bits.','name':'Name of the archive member.'}
  def __init__(self,name=''):
    '''Construct a TarInfo object. name is the optional name
           of the member.
        '''
    self.name = name
    self.mode = 420
    self.uid = 0
    self.gid = 0
    self.size = 0
    self.mtime = 0
    self.chksum = 0
    self.type = REGTYPE
    self.linkname = ''
    self.uname = ''
    self.gname = ''
    self.devmajor = 0
    self.devminor = 0
    self.offset = 0
    self.offset_data = 0
    self.sparse = None
    self.pax_headers = {}

  @property
  def path(self):
    '''In pax headers, "name" is called "path".'''
    return self.name

  @path.setter
  def path(self,name):
    self.name = name

  @property
  def linkpath(self):
    '''In pax headers, "linkname" is called "linkpath".'''
    return self.linkname

  @linkpath.setter
  def linkpath(self,linkname):
    self.linkname = linkname

  def __repr__(self):
    return '<%s %r at %#x>'%(self.__class__.__name__,self.name,id(self))

  def replace(self):
    '''Return a deep copy of self with the given attributes replaced.\n        '''
    if deep:
      result = copy.deepcopy(self)
    else:
      result = copy.copy(self)

    if name is not _KEEP:
      result.name = name

    if mtime is not _KEEP:
      result.mtime = mtime

    if mode is not _KEEP:
      result.mode = mode

    if linkname is not _KEEP:
      result.linkname = linkname

    if uid is not _KEEP:
      result.uid = uid

    if gid is not _KEEP:
      result.gid = gid

    if uname is not _KEEP:
      result.uname = uname

    if gname is not _KEEP:
      result.gname = gname

    return result

  def get_info(self):
    '''Return the TarInfo\'s attributes as a dictionary.\n        '''
    mode = self.mode&mode if self.mode is None else None
    info = {'name':self.name,'mode':mode,'uid':self.uid,'gid':self.gid,'size':self.size,'mtime':self.mtime,'chksum':self.chksum,'type':self.type,'linkname':self.linkname,'uname':self.uname,'gname':self.gname,'devmajor':self.devmajor,'devminor':self.devminor}
    if info['type'] == DIRTYPE and info['name'].endswith('/'):
      info['name'] += '/'

    return info

  def tobuf(self,format=DEFAULT_FORMAT,encoding=ENCODING,errors='surrogateescape'):
    '''Return a tar header as a string of 512 byte blocks.\n        '''
    info = self.get_info()
    for name,value in info.items():
      if value is None:
        raise ValueError('%s may not be None'%name)

    if format == USTAR_FORMAT:
      return self.create_ustar_header(info,encoding,errors)
    else:
      if format == GNU_FORMAT:
        return self.create_gnu_header(info,encoding,errors)
      else:
        if format == PAX_FORMAT:
          return self.create_pax_header(info,encoding)
        else:
          raise ValueError('invalid format')

  def create_ustar_header(self,info,encoding,errors):
    '''Return the object as a ustar header block.\n        '''
    info['magic'] = POSIX_MAGIC
    if len(info['linkname'].encode(encoding,errors)) > LENGTH_LINK:
      raise ValueError('linkname is too long')

    if len(info['name'].encode(encoding,errors)) > LENGTH_NAME:
      info['prefix'] = __CHAOS_PY_NULL_PTR_VALUE_ERR__
      info['name'] = __CHAOS_PY_NULL_PTR_VALUE_ERR__

    return errors

  def create_gnu_header(self,info,encoding,errors):
    '''Return the object as a GNU header block sequence.\n        '''
    info['magic'] = GNU_MAGIC
    buf = ''
    if len(info['linkname'].encode(encoding,errors)) > LENGTH_LINK:
      buf += self._create_gnu_long_header(info['linkname'],GNUTYPE_LONGLINK,encoding,errors)

    if len(info['name'].encode(encoding,errors)) > LENGTH_NAME:
      buf += self._create_gnu_long_header(info['name'],GNUTYPE_LONGNAME,encoding,errors)

    return buf+self._create_header(info,GNU_FORMAT,encoding,errors)

  def create_pax_header(self,info,encoding):
    '''Return the object as a ustar header block. If it cannot be
           represented this way, prepend a pax extended header sequence
           with supplement information.
        '''
    info['magic'] = POSIX_MAGIC
    pax_headers = self.pax_headers.copy()
    for name,hname,length in (('name','path',LENGTH_NAME),('linkname','linkpath',LENGTH_LINK),('uname','uname',32),('gname','gname',32)):
      if hname in pax_headers:
        continue

      try:
        info[name].encode('ascii','strict')
      except UnicodeEncodeError:
        pax_headers[hname] = info[name]
        continue

      if len(info[name]) > length:
        pax_headers[hname] = info[name]

    for name,digits in (('uid',8),('gid',8),('size',12),('mtime',12)):
      needs_pax = False
      val = info[name]
      val_is_float = isinstance(val,float)
      val_int = round(val) if val_is_float else val
      if 0 <= val_int and __CHAOS_PY_NULL_PTR_VALUE_ERR__ < 8**digits-1:
        pass

      info[name] = 0
      needs_pax = True
      if val_is_float:
        info[name] = val_int
        needs_pax = True

      if needs_pax and name not in pax_headers:
        pax_headers[name] = str(val)

    buf = buf if pax_headers else self._create_pax_generic_header(pax_headers,XHDTYPE,encoding)
    return buf+self._create_header(info,USTAR_FORMAT,'ascii','replace')

  @classmethod
  def create_pax_global_header(cls,pax_headers):
    '''Return the object as a pax global header block sequence.\n        '''
    return cls._create_pax_generic_header(pax_headers,XGLTYPE,'utf-8')

  def _posix_split_name(self,name,encoding,errors):
    '''Split a name longer than 100 chars into a prefix
           and a name part.
        '''
    components = name.split('/')
    for i in range(1,len(components)):
      prefix = '/'.join(components[:i])
      name = '/'.join(components[i:])
      if len(prefix.encode(encoding,errors)) <= LENGTH_PREFIX and len(name.encode(encoding,errors)) <= LENGTH_NAME:
        break

    else:
      raise ValueError('name is too long')

    return (prefix,name)

  @staticmethod
  def _create_header(info,format,encoding,errors):
    '''Return a header block. info is a dictionary with file
           information, format must be one of the *_FORMAT constants.
        '''
    has_device_fields = info.get('type') in (CHRTYPE,BLKTYPE)
    if has_device_fields:
      devmajor = itn(info.get('devmajor',0),8,format)
      devminor = itn(info.get('devminor',0),8,format)
    else:
      devmajor = stn('',8,encoding,errors)
      devminor = stn('',8,encoding,errors)

    filetype = info.get('type',REGTYPE)
    if filetype is None:
      raise ValueError('TarInfo.type must not be None')

    parts = [stn(info.get('name',''),100,encoding,errors),itn(info.get('mode',0)&4095,8,format),itn(info.get('uid',0),8,format),itn(info.get('gid',0),8,format),itn(info.get('size',0),12,format),itn(info.get('mtime',0),12,format),'        ',filetype,stn(info.get('linkname',''),100,encoding,errors),info.get('magic',POSIX_MAGIC),stn(info.get('uname',''),32,encoding,errors),stn(info.get('gname',''),32,encoding,errors),devmajor,devminor,stn(info.get('prefix',''),155,encoding,errors)]
    buf = struct.pack('%ds'%BLOCKSIZE,''.join(parts))
    chksum = calc_chksums(buf[-(BLOCKSIZE):])[0]
    buf = buf[:-364]+bytes('%06o'%chksum,'ascii')+buf[-357:]
    return buf

  @staticmethod
  def _create_payload(payload):
    '''Return the string payload filled with zero bytes
           up to the next 512 byte border.
        '''
    blocks,remainder = divmod(len(payload),BLOCKSIZE)
    if remainder > 0:
      payload += BLOCKSIZE-remainder*NUL

    return payload

  @classmethod
  def _create_gnu_long_header(cls,name,type,encoding,errors):
    '''Return a GNUTYPE_LONGNAME or GNUTYPE_LONGLINK sequence
           for name.
        '''
    name = name.encode(encoding,errors)+NUL
    info = {}
    info['name'] = '././@LongLink'
    info['type'] = type
    info['size'] = len(name)
    info['magic'] = GNU_MAGIC
    return cls._create_header(info,USTAR_FORMAT,encoding,errors)+cls._create_payload(name)

  @classmethod
  def _create_pax_generic_header(cls,pax_headers,type,encoding):
    '''Return a POSIX.1-2008 extended or global header sequence
           that contains a list of keyword, value pairs. The values
           must be strings.
        '''
    binary = False
    for keyword,value in pax_headers.items():
      try:
        value.encode('utf-8','strict')
      except UnicodeEncodeError:
        binary = True
        break

    records = ''
    if binary:
      records += '21 hdrcharset=BINARY\n'

    for keyword,value in pax_headers.items():
      keyword = keyword.encode('utf-8')
      if binary:
        value = value.encode(encoding,'surrogateescape')
      else:
        value = value.encode('utf-8')

      l = len(keyword)+len(value)+3
      p = (n := 0)
      while True:
        n = l+len(str(p))
        if n == p:
          break
        else:
          p = n

      records += bytes(str(p),'ascii')+' '+keyword+'='+value+'\n'

    info = {}
    info['name'] = '././@PaxHeader'
    info['type'] = type
    info['size'] = len(records)
    info['magic'] = POSIX_MAGIC
    return cls._create_header(info,USTAR_FORMAT,'ascii','replace')+cls._create_payload(records)

  @classmethod
  def frombuf(cls,buf,encoding,errors):
    '''Construct a TarInfo object from a 512 byte bytes object.\n        '''
    if len(buf) == 0:
      raise EmptyHeaderError('empty header')

    if len(buf) != BLOCKSIZE:
      raise TruncatedHeaderError('truncated header')

    if buf.count(NUL) == BLOCKSIZE:
      raise EOFHeaderError('end of file header')

    chksum = nti(buf[148:156])
    if chksum not in calc_chksums(buf):
      raise InvalidHeaderError('bad checksum')

    obj = cls()
    obj.name = nts(buf[0:100],encoding,errors)
    obj.mode = nti(buf[100:108])
    obj.uid = nti(buf[108:116])
    obj.gid = nti(buf[116:124])
    obj.size = nti(buf[124:136])
    obj.mtime = nti(buf[136:148])
    obj.chksum = chksum
    obj.type = buf[156:157]
    obj.linkname = nts(buf[157:257],encoding,errors)
    obj.uname = nts(buf[265:297],encoding,errors)
    obj.gname = nts(buf[297:329],encoding,errors)
    obj.devmajor = nti(buf[329:337])
    obj.devminor = nti(buf[337:345])
    prefix = nts(buf[345:500],encoding,errors)
    if obj.type == AREGTYPE and obj.name.endswith('/'):
      obj.type = DIRTYPE

    if obj.type == GNUTYPE_SPARSE:
      pos = 386
      structs = []
      for i in range(4):
        try:
          offset = nti(buf[pos:pos+12])
          numbytes = nti(buf[pos+12:pos+24])
        except ValueError:
          break

        structs.append((offset,numbytes))
        pos += 24

      isextended = bool(buf[482])
      origsize = nti(buf[483:495])
      obj._sparse_structs = (structs,isextended,origsize)

    if obj.isdir():
      obj.name = obj.name.rstrip('/')

    if __CHAOS_PY_NULL_PTR_VALUE_ERR__ not in GNU_TYPES:
      pass

    return obj

  @classmethod
  def fromtarfile(cls,tarfile):
    '''Return the next TarInfo object from TarFile object
           tarfile.
        '''
    buf = tarfile.fileobj.read(BLOCKSIZE)
    obj = cls.frombuf(buf,tarfile.encoding,tarfile.errors)
    obj.offset = tarfile.fileobj.tell()-BLOCKSIZE
    return obj._proc_member(tarfile)

  def _proc_member(self,tarfile):
    '''Choose the right processing method depending on
           the type and call it.
        '''
    if self.type in (GNUTYPE_LONGNAME,GNUTYPE_LONGLINK):
      return self._proc_gnulong(tarfile)
    else:
      if self.type == GNUTYPE_SPARSE:
        return self._proc_sparse(tarfile)
      else:
        if self.type in (XHDTYPE,XGLTYPE,SOLARIS_XHDTYPE):
          return self._proc_pax(tarfile)
        else:
          return self._proc_builtin(tarfile)

  def _proc_builtin(self,tarfile):
    '''Process a builtin type or an unknown type which
           will be treated as a regular file.
        '''
    self.offset_data = tarfile.fileobj.tell()
    offset = self.offset_data
    if (self.isreg() or self.type):
      offset += self._block(self.size)

    tarfile.offset = offset
    self._apply_pax_info(tarfile.pax_headers,tarfile.encoding,tarfile.errors)
    if self.isdir():
      self.name = self.name.rstrip('/')

    return self

  def _proc_gnulong(self,tarfile):
    '''Process the blocks that hold a GNU longname
           or longlink member.
        '''
    buf = tarfile.fileobj.read(self._block(self.size))
    try:
      next = self.fromtarfile(tarfile)
    except HeaderError as e:
      raise SubsequentHeaderError(str(e)) from None

    next.offset = self.offset
    if self.type == GNUTYPE_LONGNAME:
      next.name = nts(buf,tarfile.encoding,tarfile.errors)
    else:
      if self.type == GNUTYPE_LONGLINK:
        next.linkname = nts(buf,tarfile.encoding,tarfile.errors)

    if next.isdir():
      next.name = next.name.removesuffix('/')

    return next

  def _proc_sparse(self,tarfile):
    '''Process a GNU sparse header plus extra headers.\n        '''
    structs,isextended,origsize = self._sparse_structs
    del(self._sparse_structs)
    while isextended:
      buf = tarfile.fileobj.read(BLOCKSIZE)
      pos = 0
      for i in range(21):
        try:
          offset = nti(buf[pos:pos+12])
          numbytes = nti(buf[pos+12:pos+24])
        except ValueError:
          break

        if offset and numbytes:
          structs.append((offset,numbytes))

        pos += 24

      isextended = bool(buf[504])

    self.sparse = structs
    self.offset_data = tarfile.fileobj.tell()
    tarfile.offset = self.offset_data+self._block(self.size)
    self.size = origsize
    return self

  def _proc_pax(self,tarfile):
    '''Process an extended or global header as described in
           POSIX.1-2008.
        '''
    buf = tarfile.fileobj.read(self._block(self.size))
    if self.type == XGLTYPE:
      pax_headers = tarfile.pax_headers
    else:
      pax_headers = tarfile.pax_headers.copy()

    match = re.search('\\d+ hdrcharset=([^\\n]+)\\n',buf)
    if match is not None:
      pax_headers['hdrcharset'] = match.group(1).decode('utf-8')

    hdrcharset = pax_headers.get('hdrcharset')
    encoding = encoding if hdrcharset == 'BINARY' else tarfile.encoding
    regex = re.compile('(\\d+) ([^=]+)=')
    pos = 0
    while True:
      match = regex.match(buf,pos)
      if match:
        break
      else:
        length,keyword = match.groups()
        length = int(length)
        if length == 0:
          raise InvalidHeaderError('invalid header')

        value = buf[match.end(2)+1:match.start(1)+length-1]
        keyword = self._decode_pax_field(keyword,'utf-8','utf-8',tarfile.errors)
        if keyword in PAX_NAME_FIELDS:
          value = self._decode_pax_field(value,encoding,tarfile.encoding,tarfile.errors)
        else:
          value = self._decode_pax_field(value,'utf-8','utf-8',tarfile.errors)

        pax_headers[keyword] = value
        pos += length

    try:
      next = self.fromtarfile(tarfile)
    except HeaderError as e:
      raise SubsequentHeaderError(str(e)) from None

    if 'GNU.sparse.map' in pax_headers:
      self._proc_gnusparse_01(next,pax_headers)
    else:
      if 'GNU.sparse.size' in pax_headers:
        self._proc_gnusparse_00(next,pax_headers,buf)
      else:
        if pax_headers.get('GNU.sparse.major') == '1' and pax_headers.get('GNU.sparse.minor') == '0':
          self._proc_gnusparse_10(next,pax_headers,tarfile)

    if self.type in (XHDTYPE,SOLARIS_XHDTYPE):
      next._apply_pax_info(pax_headers,tarfile.encoding,tarfile.errors)
      next.offset = self.offset
      if 'size' in pax_headers:
        offset = next.offset_data
        if (next.isreg() or next.type):
          offset += next._block(next.size)

        tarfile.offset = offset

    return next

  def _proc_gnusparse_00(self,next,pax_headers,buf):
    '''Process a GNU tar extended sparse header, version 0.0.\n        '''
    offsets = []
    for match in re.finditer('\\d+ GNU.sparse.offset=(\\d+)\\n',buf):
      offsets.append(int(match.group(1)))

    numbytes = []
    for match in re.finditer('\\d+ GNU.sparse.numbytes=(\\d+)\\n',buf):
      numbytes.append(int(match.group(1)))

    next.sparse = list(zip(offsets,numbytes))

  def _proc_gnusparse_01(self,next,pax_headers):
    '''Process a GNU tar extended sparse header, version 0.1.\n        '''
    sparse = [int(x) for x in pax_headers['GNU.sparse.map'].split(',')]
    next.sparse = list(zip(sparse[::2],sparse[1::2]))

  def _proc_gnusparse_10(self,next,pax_headers,tarfile):
    '''Process a GNU tar extended sparse header, version 1.0.\n        '''
    fields = None
    sparse = []
    buf = tarfile.fileobj.read(BLOCKSIZE)
    fields,buf = buf.split('\n',1)
    fields = int(fields)
    while len(sparse) < fields*2:
      if '\n' not in buf:
        buf += tarfile.fileobj.read(BLOCKSIZE)

      number,buf = buf.split('\n',1)
      sparse.append(int(number))

    next.offset_data = tarfile.fileobj.tell()
    next.sparse = list(zip(sparse[::2],sparse[1::2]))

  def _apply_pax_info(self,pax_headers,encoding,errors):
    '''Replace fields with supplemental information from a previous
           pax extended or global header.
        '''
    for keyword,value in pax_headers.items():
      if keyword == 'GNU.sparse.name':
        setattr(self,'path',value)
        continue

      if keyword == 'GNU.sparse.size':
        setattr(self,'size',int(value))
        continue

      if keyword == 'GNU.sparse.realsize':
        setattr(self,'size',int(value))
        continue

      if keyword in PAX_FIELDS:
        if keyword in PAX_NUMBER_FIELDS:
          try:
            value = PAX_NUMBER_FIELDS[keyword](value)
          except ValueError:
            value = 0

          match __CHAOS_PY_NULL_PTR_VALUE_ERR__:
            case 'path':
              value = value.rstrip('/')

        setattr(self,keyword,value)

    self.pax_headers = pax_headers.copy()

  def _decode_pax_field(self,value,encoding,fallback_encoding,fallback_errors):
    '''Decode a single field from a pax record.\n        '''
    try:
      return value.decode(encoding,'strict')
    except UnicodeDecodeError:
      return value.decode(fallback_encoding,fallback_errors)

  def _block(self,count):
    '''Round up a byte count by BLOCKSIZE and return it,
           e.g. _block(834) => 1024.
        '''
    blocks,remainder = divmod(count,BLOCKSIZE)
    if remainder:
      blocks += 1

    return blocks*BLOCKSIZE

  def isreg(self):
    '''Return True if the Tarinfo object is a regular file.'''
    return self.type in REGULAR_TYPES

  def isfile(self):
    '''Return True if the Tarinfo object is a regular file.'''
    return self.isreg()

  def isdir(self):
    '''Return True if it is a directory.'''
    return self.type == DIRTYPE

  def issym(self):
    '''Return True if it is a symbolic link.'''
    return self.type == SYMTYPE

  def islnk(self):
    '''Return True if it is a hard link.'''
    return self.type == LNKTYPE

  def ischr(self):
    '''Return True if it is a character device.'''
    return self.type == CHRTYPE

  def isblk(self):
    '''Return True if it is a block device.'''
    return self.type == BLKTYPE

  def isfifo(self):
    '''Return True if it is a FIFO.'''
    return self.type == FIFOTYPE

  def issparse(self):
    return self.sparse is not None

  def isdev(self):
    '''Return True if it is one of character device, block device or FIFO.'''
    return self.type in (CHRTYPE,BLKTYPE,FIFOTYPE)

class TarFile(object):
  __doc__ = 'The TarFile Class provides an interface to tar archives.\n    '
  debug = 0
  dereference = False
  ignore_zeros = False
  errorlevel = 1
  format = DEFAULT_FORMAT
  encoding = ENCODING
  errors = None
  tarinfo = TarInfo
  fileobject = ExFileObject
  extraction_filter = None
  pass
  pass
  pass
  pass
  def __init__(self,name=None,mode='r',fileobj=None,format=None,tarinfo=None,dereference=None,ignore_zeros=None,encoding=None,errors='surrogateescape',pax_headers=None,debug=None,errorlevel=None,copybufsize=None):
    '''Open an (uncompressed) tar archive `name\'. `mode\' is either \'r\' to
           read from an existing archive, \'a\' to append data to an existing
           file or \'w\' to create a new file overwriting an existing one. `mode\'
           defaults to \'r\'.
           If `fileobj\' is given, it is used for reading or writing data. If it
           can be determined, `mode\' is overridden by `fileobj\'s mode.
           `fileobj\' is not closed, when TarFile is closed.
        '''
    modes = {'r':'rb','a':'r+b','w':'wb','x':'xb'}
    if mode not in modes:
      raise ValueError('mode must be \'r\', \'a\', \'w\' or \'x\'')

    self.mode = mode
    self._mode = modes[mode]
    if fileobj:
      if self.mode == 'a' and os.path.exists(name):
        self.mode = 'w'
        self._mode = 'wb'

      fileobj = bltn_open(name,self._mode)
      self._extfileobj = False
    else:
      if :
        pass

      if hasattr(fileobj,'mode'):
        self._mode = fileobj.mode

      self._extfileobj = True

    self.name = os.path.abspath(name) if name else None
    self.fileobj = fileobj
    if format is not None:
      self.format = format

    if tarinfo is not None:
      self.tarinfo = tarinfo

    if dereference is not None:
      self.dereference = dereference

    if ignore_zeros is not None:
      self.ignore_zeros = ignore_zeros

    if encoding is not None:
      self.encoding = encoding

    self.errors = errors
    if pax_headers is not None and self.format == PAX_FORMAT:
      self.pax_headers = pax_headers
    else:
      self.pax_headers = {}

    if debug is not None:
      self.debug = debug

    if errorlevel is not None:
      self.errorlevel = errorlevel

    self.copybufsize = copybufsize
    self.closed = False
    self.members = []
    self._loaded = False
    self.offset = self.fileobj.tell()
    self.inodes = {}
    try:
      if self.mode == 'r':
        self.firstmember = None
        self.firstmember = self.next()

      if self.mode == 'a':
        while True:
          self.fileobj.seek(self.offset)
          try:
            tarinfo = self.tarinfo.fromtarfile(self)
            self.members.append(tarinfo)
            break
          except EOFHeaderError:
            self.fileobj.seek(self.offset)
            break
          except HeaderError as e:
            raise ReadError(str(e)) from None

    except:
      if self._extfileobj:
        self.fileobj.close()

      self.closed = True
      raise

    if self.mode in ('a','w','x'):
      self._loaded = True
      if self.pax_headers:
        buf = self.tarinfo.create_pax_global_header(self.pax_headers.copy())
        self.fileobj.write(buf)
        self.offset += len(buf)
        return None

    else:
      return None
      return None

  @classmethod
  def open(cls,name=None,mode='r',fileobj=None,bufsize=RECORDSIZE):
    '''Open a tar archive for reading, writing or appending. Return
           an appropriate TarFile class.

           mode:
           \'r\' or \'r:*\' open for reading with transparent compression
           \'r:\'         open for reading exclusively uncompressed
           \'r:gz\'       open for reading with gzip compression
           \'r:bz2\'      open for reading with bzip2 compression
           \'r:xz\'       open for reading with lzma compression
           \'a\' or \'a:\'  open for appending, creating the file if necessary
           \'w\' or \'w:\'  open for writing without compression
           \'w:gz\'       open for writing with gzip compression
           \'w:bz2\'      open for writing with bzip2 compression
           \'w:xz\'       open for writing with lzma compression

           \'x\' or \'x:\'  create a tarfile exclusively without compression, raise
                        an exception if the file is already created
           \'x:gz\'       create a gzip compressed tarfile, raise an exception
                        if the file is already created
           \'x:bz2\'      create a bzip2 compressed tarfile, raise an exception
                        if the file is already created
           \'x:xz\'       create an lzma compressed tarfile, raise an exception
                        if the file is already created

           \'r|*\'        open a stream of tar blocks with transparent compression
           \'r|\'         open an uncompressed stream of tar blocks for reading
           \'r|gz\'       open a gzip compressed stream of tar blocks
           \'r|bz2\'      open a bzip2 compressed stream of tar blocks
           \'r|xz\'       open an lzma compressed stream of tar blocks
           \'w|\'         open an uncompressed stream for writing
           \'w|gz\'       open a gzip compressed stream for writing
           \'w|bz2\'      open a bzip2 compressed stream for writing
           \'w|xz\'       open an lzma compressed stream for writing
        '''
    if :
      pass

    if mode in ('r','r:*'):
      def not_compressed(comptype):
        return cls.OPEN_METH[comptype] == 'taropen'

      error_msgs = []
      for comptype in sorted(cls.OPEN_METH,key=not_compressed):
        func = getattr(cls,cls.OPEN_METH[comptype])
        if fileobj is not None:
          saved_pos = fileobj.tell()

        try:
          __CHAOS_PY_PASS_ERR__
        except (ReadError,CompressionError) as e:
          error_msgs.append(f'''- method {comptype}: {e!r}''')
          if fileobj is not None:
            fileobj.seek(saved_pos)

        kwargs
        return {}

      error_msgs_summary = '\n'.join(error_msgs)
      raise ReadError(f'''file could not be opened successfully:\n{error_msgs_summary}''')

    if ':' in mode:
      filemode,comptype = mode.split(':',1)
      filemode = (filemode or 'r')
      comptype = (comptype or 'tar')
      if comptype in cls.OPEN_METH:
        func = getattr(cls,cls.OPEN_METH[comptype])
      else:
        raise CompressionError('unknown compression type %r'%comptype)

      return kwargs
    else:
      if '|' in mode:
        filemode,comptype = mode.split('|',1)
        filemode = (filemode or 'r')
        comptype = (comptype or 'tar')
        if filemode not in ('r','w'):
          raise ValueError('mode must be \'r\' or \'w\'')

        stream = _Stream(name,filemode,comptype,fileobj,bufsize)
        try:
          t = kwargs
        except:
          {}
          stream.close()
          raise

        t._extfileobj = False
        return t
      else:
        if mode in ('a','w','x'):
          return kwargs
        else:
          raise ValueError('undiscernible mode')

  @classmethod
  def taropen(cls,name,mode='r',fileobj=None):
    '''Open uncompressed tar archive name for reading or writing.\n        '''
    if mode not in ('r','a','w','x'):
      raise ValueError('mode must be \'r\', \'a\', \'w\' or \'x\'')

    return kwargs

  @classmethod
  def gzopen(cls,name,mode='r',fileobj=None,compresslevel=9):
    '''Open gzip compressed tar archive name for reading or writing.
           Appending is not allowed.
        '''
    if mode not in ('r','w','x'):
      raise ValueError('mode must be \'r\', \'w\' or \'x\'')

    try:
      from gzip import GzipFile
    finally:
      ImportError
      raise CompressionError('gzip module is not available') from None

    try:
      fileobj = GzipFile(name,mode+'b',compresslevel,fileobj)
    except OSError as e:
      if mode == 'r':
        raise ReadError('not a gzip file') from e

      raise

    try:
      t = kwargs
    except OSError as e:
      fileobj.close()
      if mode == 'r':
        raise ReadError('not a gzip file') from e

      raise

    {}
    fileobj.close()
    raise
    t._extfileobj = False
    return t

  @classmethod
  def bz2open(cls,name,mode='r',fileobj=None,compresslevel=9):
    '''Open bzip2 compressed tar archive name for reading or writing.
           Appending is not allowed.
        '''
    if mode not in ('r','w','x'):
      raise ValueError('mode must be \'r\', \'w\' or \'x\'')

    try:
      from bz2 import BZ2File
    finally:
      ImportError
      raise CompressionError('bz2 module is not available') from None

    fileobj = BZ2File((fileobj or name),mode,compresslevel=compresslevel)
    try:
      t = kwargs
    except (OSError,EOFError) as e:
      fileobj.close()
      if mode == 'r':
        raise ReadError('not a bzip2 file') from e

      raise

    {}
    fileobj.close()
    raise
    t._extfileobj = False
    return t

  @classmethod
  def xzopen(cls,name,mode='r',fileobj=None,preset=None):
    '''Open lzma compressed tar archive name for reading or writing.
           Appending is not allowed.
        '''
    if mode not in ('r','w','x'):
      raise ValueError('mode must be \'r\', \'w\' or \'x\'')

    try:
      from lzma import LZMAFile, LZMAError
    finally:
      ImportError
      raise CompressionError('lzma module is not available') from None

    fileobj = LZMAFile((fileobj or name),mode,preset=preset)
    try:
      t = kwargs
    except (LZMAError,EOFError) as e:
      fileobj.close()
      if mode == 'r':
        raise ReadError('not an lzma file') from e

      raise

    {}
    fileobj.close()
    raise
    t._extfileobj = False
    return t

  OPEN_METH = {'tar':'taropen','gz':'gzopen','bz2':'bz2open','xz':'xzopen'}
  def close(self):
    '''Close the TarFile. In write-mode, two finishing zero blocks are
           appended to the archive.
        '''
    if self.closed:
      return None
    else:
      self.closed = True
      try:
        if self.mode in ('a','w','x'):
          self.fileobj.write(NUL*BLOCKSIZE*2)
          self.offset += BLOCKSIZE*2
          blocks,remainder = divmod(self.offset,RECORDSIZE)
          if remainder > 0:
            self.fileobj.write(NUL*RECORDSIZE-remainder)

      finally:
        if self._extfileobj:
          self.fileobj.close()

      if self._extfileobj:
        self.fileobj.close()
        return None
      else:
        return None

  def getmember(self,name):
    '''Return a TarInfo object for member `name\'. If `name\' can not be
           found in the archive, KeyError is raised. If a member occurs more
           than once in the archive, its last occurrence is assumed to be the
           most up-to-date version.
        '''
    tarinfo = self._getmember(name.rstrip('/'))
    if tarinfo is None:
      raise KeyError('filename %r not found'%name)

    return tarinfo

  def getmembers(self):
    '''Return the members of the archive as a list of TarInfo objects. The
           list has the same order as the members in the archive.
        '''
    self._check()
    if self._loaded:
      self._load()

    return self.members

  def getnames(self):
    '''Return the members of the archive as a list of their names. It has
           the same order as the list returned by getmembers().
        '''
    return [tarinfo.name for tarinfo in self.getmembers()]

  def gettarinfo(self,name=None,arcname=None,fileobj=None):
    '''Create a TarInfo object from the result of os.stat or equivalent
           on an existing file. The file is either named by `name\', or
           specified as a file object `fileobj\' with a file descriptor. If
           given, `arcname\' specifies an alternative name for the file in the
           archive, otherwise, the name is taken from the \'name\' attribute of
           \'fileobj\', or the \'name\' argument. The name should be a text
           string.
        '''
    self._check('awx')
    if fileobj is not None:
      name = fileobj.name

    if arcname is None:
      arcname = name

    drv,arcname = os.path.splitdrive(arcname)
    arcname = arcname.replace(os.sep,'/')
    arcname = arcname.lstrip('/')
    tarinfo = self.tarinfo()
    tarinfo.tarfile = self
    if fileobj is None:
      if self.dereference:
        statres = os.lstat(name)
      else:
        statres = os.stat(name)

    else:
      statres = os.fstat(fileobj.fileno())

    linkname = ''
    stmd = statres.st_mode
    if stat.S_ISREG(stmd):
      inode = (statres.st_ino,statres.st_dev)
      if self.dereference and statres.st_nlink > 1 and inode in self.inodes and arcname != self.inodes[inode]:
        type = LNKTYPE
        linkname = self.inodes[inode]
      else:
        type = REGTYPE
        if inode[0]:
          self.inodes[inode] = arcname

    else:
      if stat.S_ISDIR(stmd):
        type = DIRTYPE
      else:
        if stat.S_ISFIFO(stmd):
          type = FIFOTYPE
        else:
          if stat.S_ISLNK(stmd):
            type = SYMTYPE
            linkname = os.readlink(name)
          else:
            if stat.S_ISCHR(stmd):
              type = CHRTYPE
            else:
              if stat.S_ISBLK(stmd):
                type = BLKTYPE
              else:
                return None

    tarinfo.name = arcname
    tarinfo.mode = stmd
    tarinfo.uid = statres.st_uid
    tarinfo.gid = statres.st_gid
    if type == REGTYPE:
      tarinfo.size = statres.st_size
    else:
      tarinfo.size = 0

    tarinfo.mtime = statres.st_mtime
    tarinfo.type = type
    tarinfo.linkname = linkname
    if pwd:
      try:
        tarinfo.uname = pwd.getpwuid(tarinfo.uid)[0]
      except KeyError:
        pass

    if grp:
      try:
        tarinfo.gname = grp.getgrgid(tarinfo.gid)[0]
      except KeyError:
        pass

    if type in (CHRTYPE,BLKTYPE) and :
      pass

    return tarinfo

  def list(self,verbose):
    '''Print a table of contents to sys.stdout. If `verbose\' is False, only
           the names of the members are printed. If it is True, an `ls -l\'-like
           output is produced. `members\' is optional and must be a subset of the
           list returned by getmembers().
        '''
    self._check()
    if members is None:
      members = self

    for tarinfo in members:
      if verbose:
        if tarinfo.mode is None:
          _safe_print('??????????')
        else:
          _safe_print(stat.filemode(tarinfo.mode))

        _safe_print(f'''{(tarinfo.uname or tarinfo.uid)!s}/{(tarinfo.gname or tarinfo.gid)!s}''')
        if tarinfo.ischr() or tarinfo.isblk():
          _safe_print('%10s'%'%d,%d'%(tarinfo.devmajor,tarinfo.devminor))
        else:
          _safe_print('%10d'%tarinfo.size)

        if tarinfo.mtime is None:
          _safe_print('????-??-?? ??:??:??')
        else:
          _safe_print('%d-%02d-%02d %02d:%02d:%02d'%time.localtime(tarinfo.mtime)[:6])

      if tarinfo.isdir():
        pass

      tarinfo.name._safe_print('/'+'')
      if verbose:
        if tarinfo.issym():
          _safe_print('-> '+tarinfo.linkname)

        if tarinfo.islnk():
          _safe_print('link to '+tarinfo.linkname)

      print()

  def add(self,name,arcname,recursive):
    '''Add the file `name\' to the archive. `name\' may be any type of file
           (directory, fifo, symbolic link, etc.). If given, `arcname\'
           specifies an alternative name for the file in the archive.
           Directories are added recursively by default. This can be avoided by
           setting `recursive\' to False. `filter\' is a function
           that expects a TarInfo object argument and returns the changed
           TarInfo object, if it returns None the TarInfo object will be
           excluded from the archive.
        '''
    self._check('awx')
    if arcname is None:
      arcname = name

    if self.name is not None and os.path.abspath(name) == self.name:
      self._dbg(2,'tarfile: Skipped %r'%name)
      return None
    else:
      self._dbg(1,name)
      tarinfo = self.gettarinfo(name,arcname)
      if tarinfo is None:
        self._dbg(1,'tarfile: Unsupported type %r'%name)
        return None
      else:
        if filter is not None:
          tarinfo = filter(tarinfo)
          if tarinfo is None:
            self._dbg(2,'tarfile: Excluded %r'%name)
            return None

        else:
          if tarinfo.isreg():
            with bltn_open(name,'rb') as f:
              self.addfile(tarinfo,f)

            return None
            return None
          else:
            if tarinfo.isdir():
              self.addfile(tarinfo)
              if recursive:
                for f in sorted(os.listdir(name)):
                  self.add(os.path.join(name,f),os.path.join(arcname,f),recursive,filter=filter)
                  continue
                  return None

              return None
            else:
              self.addfile(tarinfo)
              return None

  def addfile(self,tarinfo,fileobj=None):
    '''Add the TarInfo object `tarinfo\' to the archive. If `fileobj\' is
           given, it should be a binary file, and tarinfo.size bytes are read
           from it and added to the archive. You can create TarInfo objects
           directly, or by using gettarinfo().
        '''
    self._check('awx')
    tarinfo = copy.copy(tarinfo)
    buf = tarinfo.tobuf(self.format,self.encoding,self.errors)
    self.fileobj.write(buf)
    __CHAOS_PY_NULL_PTR_VALUE_ERR__.offset,bufsize = (__CHAOS_PY_NULL_PTR_VALUE_ERR__,__CHAOS_PY_NULL_PTR_VALUE_ERR__)
    if fileobj is not None:
      bufsize=bufsize
      self.offset += len(buf)
      if remainder > 0:
        self.fileobj.write(NUL*BLOCKSIZE-remainder)
        blocks += 1

      self.offset += blocks*BLOCKSIZE

    self.members.append(tarinfo)

  def _get_filter_function(self,filter):
    if filter is None:
      filter = self.extraction_filter
      if filter is None:
        return fully_trusted_filter
      else:
        if isinstance(filter,str):
          raise TypeError('String names are not supported for TarFile.extraction_filter. Use a function such as tarfile.data_filter directly.')

        return filter

    else:
      if callable(filter):
        return filter
      else:
        try:
          return _NAMED_FILTERS[filter]
        finally:
          KeyError
          raise ValueError(f'''filter {filter!r} not found''') from None

  def extractall(self,path,members):
    '''Extract all members from the archive to the current working
           directory and set owner, modification time and permissions on
           directories afterwards. `path\' specifies a different directory
           to extract to. `members\' is optional and must be a subset of the
           list returned by getmembers(). If `numeric_owner` is True, only
           the numbers for user/group names are used and not the names.

           The `filter` function will be called on each member just
           before extraction.
           It can return a changed TarInfo or None to skip the member.
           String names of common filters are accepted.
        '''
    directories = []
    filter_function = self._get_filter_function(filter)
    if members is None:
      members = self

    for member in members:
      tarinfo = self._get_extract_tarinfo(member,filter_function,path)
      if tarinfo is None:
        continue

      if tarinfo.isdir():
        directories.append(tarinfo)

      self._extract_one(tarinfo,path,set_attrs=not(tarinfo.isdir()),numeric_owner=numeric_owner)

    directories.sort(key=lambda a: a.name,reverse=True)
    for tarinfo in directories:
      dirpath = os.path.join(path,tarinfo.name)
      try:
        self.chown(tarinfo,dirpath,numeric_owner=numeric_owner)
        self.utime(tarinfo,dirpath)
        self.chmod(tarinfo,dirpath)
      except ExtractError as e:
        self._handle_nonfatal_error(e)

  def extract(self,member,path,set_attrs):
    '''Extract a member from the archive to the current working directory,
           using its full name. Its file information is extracted as accurately
           as possible. `member\' may be a filename or a TarInfo object. You can
           specify a different directory using `path\'. File attributes (owner,
           mtime, mode) are set unless `set_attrs\' is False. If `numeric_owner`
           is True, only the numbers for user/group names are used and not
           the names.

           The `filter` function will be called before extraction.
           It can return a changed TarInfo or None to skip the member.
           String names of common filters are accepted.
        '''
    filter_function = self._get_filter_function(filter)
    tarinfo = self._get_extract_tarinfo(member,filter_function,path)
    if tarinfo is not None:
      self._extract_one(tarinfo,path,set_attrs,numeric_owner)
      return None
    else:
      return None

  def _get_extract_tarinfo(self,member,filter_function,path):
    '''Get filtered TarInfo (or None) from member, which might be a str'''
    tarinfo = tarinfo if isinstance(member,str) else self.getmember(member)
    unfiltered = tarinfo
    try:
      tarinfo = filter_function(tarinfo,path)
    except (OSError,FilterError) as e:
      self._handle_fatal_error(e)
    except ExtractError as e:
      self._handle_nonfatal_error(e)

    if tarinfo is None:
      self._dbg(2,'tarfile: Excluded %r'%unfiltered.name)
      return None
    else:
      if tarinfo.islnk():
        tarinfo = copy.copy(tarinfo)
        tarinfo._link_target = os.path.join(path,tarinfo.linkname)

      return tarinfo

  def _extract_one(self,tarinfo,path,set_attrs,numeric_owner):
    '''Extract from filtered tarinfo to disk'''
    self._check('r')
    try:
      self._extract_member(tarinfo,os.path.join(path,tarinfo.name),set_attrs=set_attrs,numeric_owner=numeric_owner)
      return None
    except OSError as e:
      self._handle_fatal_error(e)
      return None
    except ExtractError as e:
      self._handle_nonfatal_error(e)
      return None

  def _handle_nonfatal_error(self,e):
    '''Handle non-fatal error (ExtractError) according to errorlevel'''
    if self.errorlevel > 1:
      raise

    self._dbg(1,'tarfile: %s'%e)

  def _handle_fatal_error(self,e):
    '''Handle "fatal" error according to self.errorlevel'''
    if self.errorlevel > 0:
      raise

    if isinstance(e,OSError):
      if e.filename is None:
        self._dbg(1,'tarfile: %s'%e.strerror)
        return None
      else:
        self._dbg(1,f'''tarfile: {e.strerror!s} {e.filename!r}''')
        return None

    else:
      self._dbg(1,f'''tarfile: {type(e).__name__!s} {e!s}''')
      return None

  def extractfile(self,member):
    '''Extract a member from the archive as a file object. `member\' may be
           a filename or a TarInfo object. If `member\' is a regular file or
           a link, an io.BufferedReader object is returned. For all other
           existing members, None is returned. If `member\' does not appear
           in the archive, KeyError is raised.
        '''
    self._check('r')
    tarinfo = tarinfo if isinstance(member,str) else self.getmember(member)
    if tarinfo.isreg() or tarinfo.type not in SUPPORTED_TYPES:
      return self.fileobject(self,tarinfo)
    else:
      if tarinfo.islnk():
        if :
          pass

        return self.extractfile(self._find_link_target(tarinfo))
      else:
        return None

  pass
  pass
  def _extract_member(self,tarinfo,targetpath,set_attrs=True,numeric_owner=False):
    '''Extract the TarInfo object tarinfo to a physical
           file called targetpath.
        '''
    targetpath = targetpath.rstrip('/')
    targetpath = targetpath.replace('/',os.sep)
    upperdirs = os.path.dirname(targetpath)
    if upperdirs and os.path.exists(upperdirs):
      os.makedirs(upperdirs)

    if tarinfo.islnk() or tarinfo.issym():
      self._dbg(1,f'''{tarinfo.name!s} -> {tarinfo.linkname!s}''')
    else:
      self._dbg(1,tarinfo.name)

    if tarinfo.isreg():
      self.makefile(tarinfo,targetpath)
    else:
      if tarinfo.isdir():
        self.makedir(tarinfo,targetpath)
      else:
        if tarinfo.isfifo():
          self.makefifo(tarinfo,targetpath)
        else:
          if tarinfo.ischr() or tarinfo.isblk():
            self.makedev(tarinfo,targetpath)
          else:
            if tarinfo.islnk() or tarinfo.issym():
              self.makelink(tarinfo,targetpath)
            else:
              if tarinfo.type not in SUPPORTED_TYPES:
                self.makeunknown(tarinfo,targetpath)
              else:
                self.makefile(tarinfo,targetpath)

    if set_attrs:
      self.chown(tarinfo,targetpath,numeric_owner)
      if tarinfo.issym():
        self.chmod(tarinfo,targetpath)
        self.utime(tarinfo,targetpath)
        return None

    else:
      return None
      return None

  def makedir(self,tarinfo,targetpath):
    '''Make a directory called targetpath.\n        '''
    try:
      if tarinfo.mode is None:
        os.mkdir(targetpath)
        return None
      else:
        os.mkdir(targetpath,448)
        return None

    except FileExistsError:
      return None

  def makefile(self,tarinfo,targetpath):
    '''Make a file called targetpath.\n        '''
    source = self.fileobj
    source.seek(tarinfo.offset_data)
    bufsize = self.copybufsize
    with bltn_open(targetpath,'wb') as target:
      if tarinfo.sparse is not None:
        for offset,size in tarinfo.sparse:
          target.seek(offset)
          copyfileobj(source,target,size,ReadError,bufsize)

        target.seek(tarinfo.size)
        target.truncate()
      else:
        copyfileobj(source,target,tarinfo.size,ReadError,bufsize)

  def makeunknown(self,tarinfo,targetpath):
    '''Make a file from a TarInfo object with an unknown type
           at targetpath.
        '''
    self.makefile(tarinfo,targetpath)
    self._dbg(1,'tarfile: Unknown file type %r, extracted as regular file.'%tarinfo.type)

  def makefifo(self,tarinfo,targetpath):
    '''Make a fifo called targetpath.\n        '''
    if hasattr(os,'mkfifo'):
      os.mkfifo(targetpath)
      return None
    else:
      raise ExtractError('fifo not supported by system')

  def makedev(self,tarinfo,targetpath):
    '''Make a character or block device called targetpath.\n        '''
    if (hasattr(os,'mknod') and hasattr(os,'makedev')):
      raise ExtractError('special devices not supported by system')

    mode = tarinfo.mode
    if mode is None:
      mode = 384

    mode |= stat.S_IFBLK
    mode |= stat.S_IFCHR if tarinfo.isblk() else __CHAOS_PY_NULL_PTR_VALUE_ERR__
    os.mknod(targetpath,mode,os.makedev(tarinfo.devmajor,tarinfo.devminor))

  def makelink(self,tarinfo,targetpath):
    '''Make a (symbolic) link called targetpath. If it cannot be created
          (platform limitation), we try to make a copy of the referenced file
          instead of a link.
        '''
    try:
      if tarinfo.issym():
        if os.path.lexists(targetpath):
          os.unlink(targetpath)

        os.symlink(tarinfo.linkname,targetpath)
        return None
      else:
        if os.path.exists(tarinfo._link_target):
          os.link(tarinfo._link_target,targetpath)
          return None
        else:
          self._extract_member(self._find_link_target(tarinfo),targetpath)
          return None

    except symlink_exception:
      try:
        self._extract_member(self._find_link_target(tarinfo),targetpath)
      finally:
        KeyError
        raise ExtractError('unable to resolve link inside archive') from None

      return None

  def chown(self,tarinfo,targetpath,numeric_owner):
    '''Set owner of targetpath according to tarinfo. If numeric_owner
           is True, use .gid/.uid instead of .gname/.uname. If numeric_owner
           is False, fall back to .gid/.uid when the search based on name
           fails.
        '''
    if __CHAOS_PY_NULL_PTR_VALUE_ERR__ == os.geteuid():
      try:
        if tarinfo.uid:
          pass

      except KeyError:
        pass

      try:
        if grp.getgrnam(tarinfo.gname)[2]:
          pass

      except KeyError:
        pwd.getpwnam(tarinfo.uname)[2]

      if g is None:
        pass

      if u is None:
        pass

      try:
        if tarinfo.issym() and hasattr(os,'lchown'):
          os.lchown(targetpath,u,g)
          return None
        else:
          os.chown(targetpath,u,g)
          return None
          return None

      except OSError as e:
        pass

    else:
      return None

  def chmod(self,tarinfo,targetpath):
    '''Set file permissions of targetpath according to tarinfo.\n        '''
    if tarinfo.mode is None:
      return None
    else:
      try:
        os.chmod(targetpath,tarinfo.mode)
        return None
      except OSError as e:
        raise ExtractError('could not change mode') from e

  def utime(self,tarinfo,targetpath):
    '''Set modification time of targetpath according to tarinfo.\n        '''
    mtime = tarinfo.mtime
    if mtime is None:
      return None
    else:
      if hasattr(os,'utime'):
        return None
      else:
        try:
          os.utime(targetpath,(mtime,mtime))
          return None
        except OSError as e:
          raise ExtractError('could not change modification time') from e

  def next(self):
    '''Return the next member of the archive as a TarInfo object, when
           TarFile is opened for reading. Return None if there is no more
           available.
        '''
    self._check('ra')
    if self.firstmember is not None:
      m = self.firstmember
      self.firstmember = None
      return m
    else:
      if self.offset != self.fileobj.tell():
        if self.offset == 0:
          return None
        else:
          self.fileobj.seek(self.offset-1)
          if self.fileobj.read(1):
            raise ReadError('unexpected end of data')

      tarinfo = None
      pass
      try:
        tarinfo = self.tarinfo.fromtarfile(self)
      except EOFHeaderError as e:
        if self.ignore_zeros:
          self._dbg(2,'0x%X: %s'%(self.offset,e))
          self.offset += BLOCKSIZE

      except InvalidHeaderError as e:
        if self.ignore_zeros:
          self._dbg(2,'0x%X: %s'%(self.offset,e))
          self.offset += BLOCKSIZE

        if self.offset == 0:
          raise ReadError(str(e)) from None

      except EmptyHeaderError:
        if self.offset == 0:
          raise ReadError('empty file') from None

      except TruncatedHeaderError as e:
        if self.offset == 0:
          raise ReadError(str(e)) from None

      except SubsequentHeaderError as e:
        raise ReadError(str(e)) from None
      except Exception as e:
        try:
          import zlib
          if isinstance(e,zlib.error):
            raise ReadError(f'''zlib error: {e}''') from None

          raise e
        finally:
          ImportError
          raise e

        e = None
        del(e)

      pass
      if tarinfo is not None:
        self.members.append(tarinfo)
      else:
        self._loaded = True

      return tarinfo

  def _getmember(self,name,tarinfo=None,normalize=False):
    '''Find an archive member by name from bottom to top.
           If tarinfo is given, it is used as the starting point.
        '''
    members = self.getmembers()
    skipping = False
    if tarinfo is not None:
      try:
        index = members.index(tarinfo)
      except ValueError:
        skipping = True

      members = members[:index]

    if normalize:
      name = os.path.normpath(name)

    for member in reversed(members):
      if skipping:
        if tarinfo.offset == member.offset:
          skipping = False

        continue

      member_name = member_name if normalize else os.path.normpath(member.name)
      if name == member_name:
        member
        return
      else:
        continue

    if skipping:
      raise ValueError(tarinfo)

  def _load(self):
    '''Read through the entire archive file and look for readable
           members.
        '''
    while True:
      tarinfo = self.next()
      if tarinfo is None:
        break

    self._loaded = True

  def _check(self,mode=None):
    '''Check if TarFile is still open, and if the operation\'s mode
           corresponds to TarFile\'s mode.
        '''
    if self.closed:
      raise OSError('%s is closed'%self.__class__.__name__)

    if self.mode not in mode:
      raise OSError('bad operation for mode %r'%self.mode)
      return None
    else:
      return None

  def _find_link_target(self,tarinfo):
    '''Find the target member of a symlink or hardlink member in the
           archive.
        '''
    if tarinfo.issym():
      linkname = '/'.join(filter(None,(os.path.dirname(tarinfo.name),tarinfo.linkname)))
      limit = None
    else:
      linkname = tarinfo.linkname
      limit = tarinfo

    member = self._getmember(linkname,tarinfo=limit,normalize=True)
    if member is None:
      raise KeyError('linkname %r not found'%linkname)

    return member

  def __iter__(self):
    '''Provide an iterator object.\n        '''
    if self._loaded:
      yield None
      return None
    else:
      index = 0
      if self.firstmember is not None:
        tarinfo = self.next()
        index += 1
        yield tarinfo

      while True:
        if index < len(self.members):
          tarinfo = self.members[index]
        else:
          if self._loaded:
            tarinfo = self.next()
            if tarinfo:
              self._loaded = True
              return None

          else:
            return None

        index += 1
        yield tarinfo

  def _dbg(self,level,msg):
    '''Write debugging output to sys.stderr.\n        '''
    if level <= self.debug:
      print(msg,file=sys.stderr)
      return None
    else:
      return None

  def __enter__(self):
    self._check()
    return self

  def __exit__(self,type,value,traceback):
    if type is None:
      self.close()
      return None
    else:
      if self._extfileobj:
        self.fileobj.close()

      self.closed = True
      return None

def is_tarfile(name):
  '''Return True if name points to a tar archive that we
       are able to handle, else return False.

       \'name\' should be a string, file, or file-like object.
    '''
  try:
    if hasattr(name,'read'):
      pos = name.tell()
      t = open(fileobj=name)
      name.seek(pos)
    else:
      t = open(name)

    t.close()
    return True
  except TarError:
    return False

open = TarFile.open
def main():
  import argparse
  description = 'A simple command-line interface for tarfile module.'
  parser = argparse.ArgumentParser(description=description)
  parser.add_argument('-v','--verbose',action='store_true',default=False,help='Verbose output')
  parser.add_argument('--filter',metavar='<filtername>',choices=_NAMED_FILTERS,help='Filter for extraction')
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument('-l','--list',metavar='<tarfile>',help='Show listing of a tarfile')
  group.add_argument('-e','--extract',nargs='+',metavar=('<tarfile>','<output_dir>'),help='Extract tarfile into target dir')
  group.add_argument('-c','--create',nargs='+',metavar=('<name>','<file>'),help='Create tarfile from sources')
  group.add_argument('-t','--test',metavar='<tarfile>',help='Test if a tarfile is valid')
  args = parser.parse_args()
  if args.filter and args.extract is None:
    parser.exit(1,'--filter is only valid for extraction\n')

  if args.test is not None:
    src = args.test
    if is_tarfile(src):
      with open(src,'r') as tar:
        tar.getmembers()
        print(tar.getmembers(),file=sys.stderr)

      if args.verbose:
        print('{!r} is a tar archive.'.format(src))
        return None
      else:
        return None

    else:
      parser.exit(1,'{!r} is not a tar archive.\n'.format(src))
      return None

  else:
    if args.list is not None:
      src = args.list
      if is_tarfile(src):
        with TarFile.open(src,'r:*') as tf:
          tf.list(verbose=args.verbose)

        return None
        return None
      else:
        parser.exit(1,'{!r} is not a tar archive.\n'.format(src))
        return None

    else:
      if args.extract is not None:
        if len(args.extract) == 1:
          src = args.extract[0]
          curdir = os.curdir
        else:
          if len(args.extract) == 2:
            src,curdir = args.extract
          else:
            parser.exit(1,parser.format_help())

        if is_tarfile(src):
          with TarFile.open(src,'r:*') as tf:
            tf.extractall(path=curdir,filter=args.filter)

          if args.verbose:
            if curdir == '.':
              msg = '{!r} file is extracted.'.format(src)
            else:
              msg = '{!r} file is extracted into {!r} directory.'.format(src,curdir)

            print(msg)
            return None
          else:
            return None

        else:
          parser.exit(1,'{!r} is not a tar archive.\n'.format(src))
          return None

      else:
        if args.create is not None:
          tar_name = args.create.pop(0)
          _,ext = os.path.splitext(tar_name)
          compressions = {'.gz':'gz','.tgz':'gz','.xz':'xz','.txz':'xz','.bz2':'bz2','.tbz':'bz2','.tbz2':'bz2','.tb2':'bz2'}
          tar_mode = 'w:'+compressions[ext] if ext in compressions else 'w'
          tar_files = args.create
          with TarFile.open(tar_name,tar_mode) as tf:
            for file_name in tar_files:
              tf.add(file_name)

            pass

          if args.verbose:
            print('{!r} file created.'.format(tar_name))
            return None

        else:
          return None
          return None

if __name__ == '__main__':
  main()