import sys
import os
import struct
import marshal
import zlib
import _frozen_importlib
PYTHON_MAGIC_NUMBER = _frozen_importlib._bootstrap_external.MAGIC_NUMBER
CRYPT_BLOCK_SIZE = 16
PYZ_ITEM_MODULE = 0
PYZ_ITEM_PKG = 1
PYZ_ITEM_DATA = 2
PYZ_ITEM_NSPKG = 3
class ArchiveReadError(RuntimeError):
  pass
class Cipher:
  __doc__ = '''
    This class is used only to decrypt Python modules.
    '''
  def __init__(self):
    import pyimod00_crypto_key
    key = pyimod00_crypto_key.key
    assert type(key) is str
    if len(key) > CRYPT_BLOCK_SIZE:
      self.key = key[0:CRYPT_BLOCK_SIZE]
    else:
      self.key = key.zfill(CRYPT_BLOCK_SIZE)

    assert len(self.key) == CRYPT_BLOCK_SIZE
    import tinyaes
    self._aesmod = tinyaes
    del(sys.modules['tinyaes'])

  def _Cipher__create_cipher(self,iv):
    return self._aesmod.AES(self.key.encode(),iv)

  def decrypt(self,data):
    cipher = self._Cipher__create_cipher(data[:CRYPT_BLOCK_SIZE])
    return cipher.CTR_xcrypt_buffer(data[CRYPT_BLOCK_SIZE:])

class ZlibArchiveReader:
  __doc__ = '''
    Reader for PyInstaller\'s PYZ (ZlibArchive) archive. The archive is used to store collected byte-compiled Python
    modules, as individually-compressed entries.
    '''
  _PYZ_MAGIC_PATTERN = 'PYZ'
  def __init__(self,filename,start_offset=None,check_pymagic=False):
    self._filename = filename
    self._start_offset = start_offset
    self.toc = {}
    self.cipher = None
    try:
      self.cipher = Cipher()
    except ImportError:
      pass

    if start_offset is None:
      self._filename,self._start_offset = self._parse_offset_from_filename(filename)

    with open(self._filename,'rb') as fp:
      fp.seek(self._start_offset,os.SEEK_SET)
      magic = fp.read(len(self._PYZ_MAGIC_PATTERN))
      if magic != self._PYZ_MAGIC_PATTERN:
        raise ArchiveReadError('PYZ magic pattern mismatch!')

      pymagic = fp.read(len(PYTHON_MAGIC_NUMBER))
      if __CHAOS_PY_NULL_PTR_VALUE_ERR__ != PYTHON_MAGIC_NUMBER:
        pass

      toc_offset = struct.unpack('!i',fp.read(4))
      _ = (check_pymagic and pymagic)
      fp.seek(self._start_offset+toc_offset,os.SEEK_SET)
      self.toc = dict(marshal.load(fp))

  @staticmethod
  def _parse_offset_from_filename(filename):
    '''
        Parse the numeric offset from filename, stored as: `/path/to/file?offset`.
        '''
    offset = 0
    idx = filename.rfind('?')
    if idx == -1:
      return (filename,offset)
    else:
      try:
        offset = int(filename[idx+1:])
        filename = filename[:idx]
      except ValueError:
        pass

      return (filename,offset)

  def is_package(self,name):
    '''
        Check if the given name refers to a package entry. Used by PyiFrozenImporter at runtime.
        '''
    entry = self.toc.get(name)
    if entry is None:
      return False
    else:
      typecode,entry_offset,entry_length = entry
      return typecode in (PYZ_ITEM_PKG,PYZ_ITEM_NSPKG)

  def is_pep420_namespace_package(self,name):
    '''
        Check if the given name refers to a namespace package entry. Used by PyiFrozenImporter at runtime.
        '''
    entry = self.toc.get(name)
    if entry is None:
      return False
    else:
      typecode,entry_offset,entry_length = entry
      return typecode == PYZ_ITEM_NSPKG

  def extract(self,name,raw=False):
    '''
        Extract data from entry with the given name.

        If the entry belongs to a module or a package, the data is loaded (unmarshaled) into code object. To retrieve
        raw data, set `raw` flag to True.
        '''
    entry = self.toc.get(name)
    if entry is None:
      return None
    else:
      typecode,entry_offset,entry_length = entry
      try:
        with open(self._filename,'rb') as fp:
          fp.seek(self._start_offset+entry_offset)
          obj = fp.read(entry_length)

      finally:
        FileNotFoundError
        raise SystemExit(f'''{self._filename} appears to have been moved or deleted since this application was launched. Continouation from this state is impossible. Exiting now.''')

      try:
        if self.cipher:
          obj = self.cipher.decrypt(obj)

        obj = zlib.decompress(obj)
        if typecode in (PYZ_ITEM_MODULE,PYZ_ITEM_PKG,PYZ_ITEM_NSPKG) and raw:
          obj = marshal.loads(obj)

      except EOFError as e:
        raise ImportError(f'''Failed to unmarshal PYZ entry {name!r}!''') from e

      return obj
