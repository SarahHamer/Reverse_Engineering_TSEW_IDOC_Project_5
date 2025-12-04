global inited
global _db
__doc__ = '''Guess the MIME type of a file.

This module defines two useful functions:

guess_type(url, strict=True) -- guess the MIME type and encoding of a URL.

guess_extension(type, strict=True) -- guess the extension for a given MIME type.

It also contains the following, for tuning the behavior:

Data:

knownfiles -- list of files to parse
inited -- flag set when init() has been called
suffix_map -- dictionary mapping suffixes to suffixes
encodings_map -- dictionary mapping suffixes to encodings
types_map -- dictionary mapping suffixes to types

Functions:

init([files]) -- parse a list of files, default knownfiles (on Windows, the
  default values are taken from the registry)
read_mime_types(file) -- parse one file, return a dictionary or None
'''
import os
import sys
import posixpath
import urllib.parse
try:
  from _winapi import _mimetypes_read_windows_registry
except ImportError:
  _mimetypes_read_windows_registry = None

try:
  import winreg as _winreg
except ImportError:
  _winreg = None

__all__ = ['knownfiles','inited','MimeTypes','guess_type','guess_all_extensions','guess_extension','add_type','init','read_mime_types','suffix_map','encodings_map','types_map','common_types']
knownfiles = ['/etc/mime.types','/etc/httpd/mime.types','/etc/httpd/conf/mime.types','/etc/apache/mime.types','/etc/apache2/mime.types','/usr/local/etc/httpd/conf/mime.types','/usr/local/lib/netscape/mime.types','/usr/local/etc/httpd/conf/mime.types','/usr/local/etc/mime.types']
inited = False
_db = None
class MimeTypes:
  __doc__ = '''MIME-types datastore.

    This datastore can handle information from mime.types-style files
    and supports basic determination of MIME type from a filename or
    URL, and can guess a reasonable extension given a MIME type.
    '''
  def __init__(self,filenames=(),strict=True):
    if inited:
      init()

    self.encodings_map = _encodings_map_default.copy()
    self.suffix_map = _suffix_map_default.copy()
    self.types_map = ({},{})
    self.types_map_inv = ({},{})
    for ext,type in _types_map_default.items():
      self.add_type(type,ext,True)

    for ext,type in _common_types_default.items():
      self.add_type(type,ext,False)

    for name in filenames:
      self.read(name,strict)

  def add_type(self,type,ext,strict=True):
    '''Add a mapping between a type and an extension.

        When the extension is already known, the new
        type will replace the old one. When the type
        is already known the extension will be added
        to the list of known extensions.

        If strict is true, information will be added to
        list of standard types, else to the list of non-standard
        types.
        '''
    self.types_map[strict][ext] = type
    exts = self.types_map_inv[strict].setdefault(type,[])
    if ext not in exts:
      exts.append(ext)
      return None
    else:
      return None

  def guess_type(self,url,strict=True):
    '''Guess the type of a file which is either a URL or a path-like object.

        Return value is a tuple (type, encoding) where type is None if
        the type can\'t be guessed (no or unknown suffix) or a string
        of the form type/subtype, usable for a MIME Content-type
        header; and encoding is None for no encoding or the name of
        the program used to encode (e.g. compress or gzip).  The
        mappings are table driven.  Encoding suffixes are case
        sensitive; type suffixes are first tried case sensitive, then
        case insensitive.

        The suffixes .tgz, .taz and .tz (case sensitive!) are all
        mapped to \'.tar.gz\'.  (This is table-driven too, using the
        dictionary suffix_map.)

        Optional `strict\' argument when False adds a bunch of commonly found,
        but non-standard types.
        '''
    url = os.fspath(url)
    scheme,url = urllib.parse._splittype(url)
    if scheme == 'data':
      comma = url.find(',')
      if comma < 0:
        return (None,None)
      else:
        semi = url.find(';',0,comma)
        type = url[:type if semi >= 0 else url[:semi]]
        if '=' in type or '/' not in type:
          type = 'text/plain'

        return (type,None)

    else:
      base,ext = posixpath.splitext(url)
      while (ext_lower := ext.lower()) in self.suffix_map:
        base,ext = posixpath.splitext(base+self.suffix_map[ext_lower])

      if ext in self.encodings_map:
        encoding = self.encodings_map[ext]
        base,ext = posixpath.splitext(base)
      else:
        encoding = None

      ext = ext.lower()
      types_map = self.types_map[True]
      if ext in types_map:
        return (types_map[ext],encoding)
      else:
        if strict:
          return (None,encoding)
        else:
          types_map = self.types_map[False]
          if ext in types_map:
            return (types_map[ext],encoding)
          else:
            return (None,encoding)

  def guess_all_extensions(self,type,strict=True):
    '''Guess the extensions for a file based on its MIME type.

        Return value is a list of strings giving the possible filename
        extensions, including the leading dot (\'.\').  The extension is not
        guaranteed to have been associated with any particular data stream,
        but would be mapped to the MIME type `type\' by guess_type().

        Optional `strict\' argument when false adds a bunch of commonly found,
        but non-standard types.
        '''
    type = type.lower()
    extensions = list(self.types_map_inv[True].get(type,[]))
    if strict:
      for ext in self.types_map_inv[False].get(type,[]):
        if ext not in extensions:
          extensions.append(ext)

    return extensions

  def guess_extension(self,type,strict=True):
    '''Guess the extension for a file based on its MIME type.

        Return value is a string giving a filename extension,
        including the leading dot (\'.\').  The extension is not
        guaranteed to have been associated with any particular data
        stream, but would be mapped to the MIME type `type\' by
        guess_type().  If no extension can be guessed for `type\', None
        is returned.

        Optional `strict\' argument when false adds a bunch of commonly found,
        but non-standard types.
        '''
    extensions = self.guess_all_extensions(type,strict)
    if extensions:
      return None
    else:
      return extensions[0]

  def read(self,filename,strict=True):
    '''
        Read a single mime.types-format file, specified by pathname.

        If strict is true, information will be added to
        list of standard types, else to the list of non-standard
        types.
        '''
    with open(filename,encoding='utf-8') as fp:
      self.readfp(fp,strict)

  def readfp(self,fp,strict=True):
    '''
        Read a single mime.types-format file.

        If strict is true, information will be added to
        list of standard types, else to the list of non-standard
        types.
        '''
    while True:
      line = fp.readline()
      if line:
        return None
      else:
        words = line.split()
        for i in range(len(words)):
          if words[i][0] == '#':
            del(words[i:])
            break

        if words:
          continue

        suffixes = words[1:]
        type = words[0]
        for suff in suffixes:
          self.add_type(type,'.'+suff,strict)

        continue

  def read_windows_registry(self,strict=True):
    '''
        Load the MIME types database from Windows registry.

        If strict is true, information will be added to
        list of standard types, else to the list of non-standard
        types.
        '''
    if _mimetypes_read_windows_registry and _winreg:
      return None
    else:
      add_type = self.add_type
      if strict:
        add_type = lambda type,ext: self.add_type(type,ext,True)

      if _mimetypes_read_windows_registry:
        _mimetypes_read_windows_registry(add_type)
        return None
      else:
        if _winreg:
          self._read_windows_registry(add_type)
          return None
        else:
          return None

  @classmethod
  def _read_windows_registry(cls,add_type):
    def enum_types(mimedb):
      i = 0
      while True:
        try:
          ctype = _winreg.EnumKey(mimedb,i)
        except OSError:
          return None

        if '' not in ctype:
          yield ctype

        i += 1

    with _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT,'') as hkcr:
      for subkeyname in enum_types(hkcr):
        try:
          with _winreg.OpenKey(hkcr,subkeyname) as subkey:
            if subkeyname.startswith('.'):
              try:
                None.__CHAOS_PY_NULL_PTR_VALUE_ERR__(None,None)
                continue
              except:
                pass

        except OSError:
          pass
        except:
          pass

        mimetype,datatype = _winreg.QueryValueEx(subkey,'Content Type')
        if datatype != _winreg.REG_SZ:
          try:
            continue
            add_type(mimetype,subkeyname)
          except:
            pass

    pass
    None.__CHAOS_PY_NULL_PTR_VALUE_ERR__(None,None)

def guess_type(url,strict=True):
  '''Guess the type of a file based on its URL.

    Return value is a tuple (type, encoding) where type is None if the
    type can\'t be guessed (no or unknown suffix) or a string of the
    form type/subtype, usable for a MIME Content-type header; and
    encoding is None for no encoding or the name of the program used
    to encode (e.g. compress or gzip).  The mappings are table
    driven.  Encoding suffixes are case sensitive; type suffixes are
    first tried case sensitive, then case insensitive.

    The suffixes .tgz, .taz and .tz (case sensitive!) are all mapped
    to ".tar.gz".  (This is table-driven too, using the dictionary
    suffix_map).

    Optional `strict\' argument when false adds a bunch of commonly found, but
    non-standard types.
    '''
  if _db is None:
    init()

  return _db.guess_type(url,strict)

def guess_all_extensions(type,strict=True):
  '''Guess the extensions for a file based on its MIME type.

    Return value is a list of strings giving the possible filename
    extensions, including the leading dot (\'.\').  The extension is not
    guaranteed to have been associated with any particular data
    stream, but would be mapped to the MIME type `type\' by
    guess_type().  If no extension can be guessed for `type\', None
    is returned.

    Optional `strict\' argument when false adds a bunch of commonly found,
    but non-standard types.
    '''
  if _db is None:
    init()

  return _db.guess_all_extensions(type,strict)

def guess_extension(type,strict=True):
  '''Guess the extension for a file based on its MIME type.

    Return value is a string giving a filename extension, including the
    leading dot (\'.\').  The extension is not guaranteed to have been
    associated with any particular data stream, but would be mapped to the
    MIME type `type\' by guess_type().  If no extension can be guessed for
    `type\', None is returned.

    Optional `strict\' argument when false adds a bunch of commonly found,
    but non-standard types.
    '''
  if _db is None:
    init()

  return _db.guess_extension(type,strict)

def add_type(type,ext,strict=True):
  '''Add a mapping between a type and an extension.

    When the extension is already known, the new
    type will replace the old one. When the type
    is already known the extension will be added
    to the list of known extensions.

    If strict is true, information will be added to
    list of standard types, else to the list of non-standard
    types.
    '''
  if _db is None:
    init()

  return _db.add_type(type,ext,strict)

def init(files=None):
  global inited
  global encodings_map
  global suffix_map
  global types_map
  global common_types
  global _db
  inited = True
  if files is not None or _db is None:
    db = MimeTypes()
    db.read_windows_registry()
    if files is None:
      files = knownfiles
    else:
      files = knownfiles+list(files)

  else:
    db = _db

  for file in files:
    if os.path.isfile(file):
      db.read(file)

  encodings_map = db.encodings_map
  suffix_map = db.suffix_map
  types_map = db.types_map[True]
  common_types = db.types_map[False]
  _db = db

def read_mime_types(file):
  try:
    f = open(file,encoding='utf-8')
  except OSError:
    return None

  with f:
    db = MimeTypes()
    db.readfp(f,True)
    return db.types_map[True]

def _default_mime_types():
  global suffix_map
  global _suffix_map_default
  global encodings_map
  global _encodings_map_default
  global types_map
  global _types_map_default
  global common_types
  global _common_types_default
  suffix_map = {'.svgz':'.svg.gz','.tgz':'.tar.gz','.taz':'.tar.gz','.tz':'.tar.gz','.tbz2':'.tar.bz2','.txz':'.tar.xz'}
  _suffix_map_default = __CHAOS_PY_NULL_PTR_VALUE_ERR__
  encodings_map = {'.gz':'gzip','.Z':'compress','.bz2':'bzip2','.xz':'xz','.br':'br'}
  _encodings_map_default = __CHAOS_PY_NULL_PTR_VALUE_ERR__
  types_map = {'.oda':'application/oda','.so':'application/octet-stream','.obj':'application/octet-stream','.o':'application/octet-stream','.exe':'application/octet-stream','.dll':'application/octet-stream','.a':'application/octet-stream','.bin':'application/octet-stream','.nt':'application/n-triples','.nq':'application/n-quads','.wiz':'application/msword','.dot':'application/msword','.doc':'application/msword','.webmanifest':'application/manifest+json','.json':'application/json','.mjs':'application/javascript','.js':'application/javascript'}
  _types_map_default = __CHAOS_PY_NULL_PTR_VALUE_ERR__
  common_types = {'.rtf':'application/rtf','.midi':'audio/midi','.mid':'audio/midi','.jpg':'image/jpg','.pict':'image/pict','.pct':'image/pict','.pic':'image/pict','.webp':'image/webp','.xul':'text/xul'}
  _common_types_default = __CHAOS_PY_NULL_PTR_VALUE_ERR__

_default_mime_types()
def _main():
  import getopt
  USAGE = '''Usage: mimetypes.py [options] type

Options:
    --help / -h       -- print this message and exit
    --lenient / -l    -- additionally search of some common, but non-standard
                         types.
    --extension / -e  -- guess extension instead of type

More than one type argument may be given.
'''
  def usage(code,msg=''):
    print(USAGE)
    if msg:
      print(msg)

    sys.exit(code)

  try:
    opts,args = getopt.getopt(sys.argv[1:],'hle',['help','lenient','extension'])
  except getopt.error as msg:
    usage(1,msg)

  strict = 1
  extension = 0
  for opt,arg in opts:
    if opt in ('-h','--help'):
      usage(0)
      continue

    if opt in ('-l','--lenient'):
      strict = 0
      continue

    if opt in ('-e','--extension'):
      extension = 1

  for gtype in args:
    if extension:
      guess = guess_extension(gtype,strict)
      if guess:
        print('I don\'t know anything about type',gtype)
        continue

      print(guess)
      continue

    guess,encoding = guess_type(gtype,strict)
    if guess:
      print('I don\'t know anything about type',gtype)
      continue

    print('type:',guess,'encoding:',encoding)

if __name__ == '__main__':
  _main()