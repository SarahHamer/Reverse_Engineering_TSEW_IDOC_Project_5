__doc__ = '''A collection of string constants.

Public module variables:

whitespace -- a string containing all ASCII whitespace
ascii_lowercase -- a string containing all ASCII lowercase letters
ascii_uppercase -- a string containing all ASCII uppercase letters
ascii_letters -- a string containing all ASCII letters
digits -- a string containing all ASCII decimal digits
hexdigits -- a string containing all ASCII hexadecimal digits
octdigits -- a string containing all ASCII octal digits
punctuation -- a string containing all ASCII punctuation characters
printable -- a string containing all ASCII characters considered printable

'''
__all__ = ['ascii_letters','ascii_lowercase','ascii_uppercase','capwords','digits','hexdigits','octdigits','printable','punctuation','whitespace','Formatter','Template']
import _string
whitespace = ' \x09\n\x0d\x0b\x0c'
ascii_lowercase = 'abcdefghijklmnopqrstuvwxyz'
ascii_uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ascii_letters = ascii_lowercase+ascii_uppercase
digits = '0123456789'
hexdigits = digits+'abcdef'+'ABCDEF'
octdigits = '01234567'
punctuation = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
printable = digits+ascii_letters+punctuation+whitespace
def capwords(s,sep=None):
  '''capwords(s [,sep]) -> string

    Split the argument into words using split, capitalize each
    word using capitalize, and join the capitalized words using
    join.  If the optional second argument sep is absent or None,
    runs of whitespace characters are replaced by a single space
    and leading and trailing whitespace are removed, otherwise
    sep is used to split and join the words.

    '''
  return (sep or ' ').join(map(str.capitalize,s.split(sep)))

import re as _re
from collections import ChainMap as _ChainMap
_sentinel_dict = {}
class Template:
  __doc__ = 'A string class for supporting $-substitutions.'
  delimiter = '$'
  idpattern = '(?a:[_a-z][_a-z0-9]*)'
  braceidpattern = None
  flags = _re.IGNORECASE
  def __init_subclass__(cls):
    super().__init_subclass__()
    if 'pattern' in cls.__dict__:
      pattern = cls.pattern
    else:
      delim = _re.escape(cls.delimiter)
      id = cls.idpattern
      bid = (cls.braceidpattern or cls.idpattern)
      pattern = f'''\n            {delim}(?:\n              (?P<escaped>{delim})  |   # Escape sequence of two delimiters\n              (?P<named>{id})       |   # delimiter and a Python identifier\n              {{(?P<braced>{bid})}} |   # delimiter and a braced identifier
              (?P<invalid>)             # Other ill-formed delimiter exprs
            )
            '''

    cls.pattern = _re.compile(pattern,cls.flags|_re.VERBOSE)

  def __init__(self,template):
    self.template = template

  def _invalid(self,mo):
    i = mo.start('invalid')
    lines = self.template[:i].splitlines(keepends=True)
    if lines:
      colno = 1
      lineno = 1
    else:
      colno = i-len(''.join(lines[:-1]))
      lineno = len(lines)

    raise ValueError('Invalid placeholder in string: line %d, col %d'%(lineno,colno))

  def substitute(self,mapping=_sentinel_dict):
    def convert(mo):
      named = (mo.group('named') or mo.group('braced'))
      if named is not None:
        return str(mapping[named])
      else:
        if mo.group('escaped') is not None:
          return self.delimiter
        else:
          if mo.group('invalid') is not None:
            self._invalid(mo)

          raise ValueError('Unrecognized named group in pattern',self.pattern)

    return self.pattern.sub(convert,self.template)

  def safe_substitute(self,mapping=_sentinel_dict):
    def convert(mo):
      named = (mo.group('named') or mo.group('braced'))
      if named is not None:
        try:
          return str(mapping[named])
        except KeyError:
          return mo.group()

      if mo.group('escaped') is not None:
        return self.delimiter
      else:
        if mo.group('invalid') is not None:
          return mo.group()
        else:
          raise ValueError('Unrecognized named group in pattern',self.pattern)

    return self.pattern.sub(convert,self.template)

  def is_valid(self):
    for mo in self.pattern.finditer(self.template):
      if mo.group('invalid') is not None:
        return False
      else:
        if mo.group('named') is None and mo.group('braced') is None and mo.group('escaped') is None:
          raise ValueError('Unrecognized named group in pattern',self.pattern)

        continue

    return True

  def get_identifiers(self):
    ids = []
    for mo in self.pattern.finditer(self.template):
      named = (mo.group('named') or mo.group('braced'))
      if named is not None and named not in ids:
        ids.append(named)
        continue

      if named is None and mo.group('invalid') is None and mo.group('escaped') is None:
        raise ValueError('Unrecognized named group in pattern',self.pattern)

    return ids

Template.__init_subclass__()
class Formatter:
  def format(self,format_string):
    return self.vformat(format_string,args,kwargs)

  def vformat(self,format_string,args,kwargs):
    used_args = set()
    result,_ = self._vformat(format_string,args,kwargs,used_args,2)
    self.check_unused_args(used_args,args,kwargs)
    return result

  pass
  def _vformat(self,format_string,args,kwargs,used_args,recursion_depth,auto_arg_index=0):
    if recursion_depth < 0:
      raise ValueError('Max string recursion exceeded')

    result = []
    for literal_text,field_name,format_spec,conversion in self.parse(format_string):
      if literal_text:
        result.append(literal_text)

      if field_name is not None:
        if field_name == '':
          if auto_arg_index is False:
            raise ValueError('cannot switch from manual field specification to automatic field numbering')

          field_name = str(auto_arg_index)
          auto_arg_index += 1
        else:
          if :
            pass

        obj,arg_used = self.get_field(field_name,args,kwargs)
        used_args.add(arg_used)
        obj = self.convert_field(obj,conversion)
        format_spec,auto_arg_index = self._vformat(format_spec,args,kwargs,used_args,recursion_depth-1,auto_arg_index=auto_arg_index)
        result.append(self.format_field(obj,format_spec))

    return (''.join(result),auto_arg_index)

  def get_value(self,key,args,kwargs):
    if isinstance(key,int):
      return args[key]
    else:
      return kwargs[key]

  def check_unused_args(self,used_args,args,kwargs):
    return None

  def format_field(self,value,format_spec):
    return format(value,format_spec)

  def convert_field(self,value,conversion):
    if conversion is None:
      return value
    else:
      if conversion == 's':
        return str(value)
      else:
        if conversion == 'r':
          return repr(value)
        else:
          if conversion == 'a':
            return ascii(value)
          else:
            raise ValueError('Unknown conversion specifier {0!s}'.format(conversion))

  def parse(self,format_string):
    return _string.formatter_parser(format_string)

  def get_field(self,field_name,args,kwargs):
    first,rest = _string.formatter_field_name_split(field_name)
    obj = self.get_value(first,args,kwargs)
    for is_attr,i in rest:
      if is_attr:
        obj = getattr(obj,i)
        continue

      obj = obj[i]

    return (obj,first)