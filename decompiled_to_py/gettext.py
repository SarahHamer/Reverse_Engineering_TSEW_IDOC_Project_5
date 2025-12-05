global _localedirs
global _current_domain
__doc__ = '''Internationalization and localization support.

This module provides internationalization (I18N) and localization (L10N)
support for your Python programs by providing an interface to the GNU gettext
message catalog library.

I18N refers to the operation by which a program is made aware of multiple
languages.  L10N refers to the adaptation of your program, once
internationalized, to the local language and cultural habits.

'''
import os
import re
import sys
__all__ = ['NullTranslations','GNUTranslations','Catalog','bindtextdomain','find','translation','install','textdomain','dgettext','dngettext','gettext','ngettext','pgettext','dpgettext','npgettext','dnpgettext']
_default_localedir = os.path.join(sys.base_prefix,'share','locale')
_token_pattern = re.compile('''
        (?P<WHITESPACES>[ \\t]+)                    | # spaces and horizontal tabs
        (?P<NUMBER>[0-9]+\\b)                       | # decimal integer
        (?P<NAME>n\\b)                              | # only n is allowed
        (?P<PARENTHESIS>[()])                      |
        (?P<OPERATOR>[-*/%+?:]|[><!]=?|==|&&|\\|\\|) | # !, *, /, %, +, -, <, >,
                                                     # <=, >=, ==, !=, &&, ||,
                                                     # ? :
                                                     # unary and bitwise ops
                                                     # not allowed
        (?P<INVALID>\\w+|.)                           # invalid token
    ''',re.VERBOSE|re.DOTALL)
def _tokenize(plural):
  for mo in re.finditer(_token_pattern,plural):
    kind = mo.lastgroup
    if kind == 'WHITESPACES':
      continue

    value = mo.group(kind)
    if kind == 'INVALID':
      raise ValueError('invalid token in plural form: %s'%value)

    yield value

  yield ''

def _error(value):
  if value:
    return ValueError('unexpected token in plural form: %s'%value)
  else:
    return ValueError('unexpected end of plural form')

_binary_ops = (('||',),('&&',),('==','!='),('<','>','<=','>='),('+','-'),('*','/','%'))
_binary_ops = {op: i for i,ops in enumerate(_binary_ops,1) for op in ops}
_c2py_ops = {'||':'or','&&':'and','/':'//'}
def _parse(tokens,priority=-1):
  result = ''
  nexttok = next(tokens)
  while nexttok == '!':
    result += 'not '
    nexttok = next(tokens)

  if nexttok == '(':
    sub,nexttok = _parse(tokens)
    result = f'''{result!s}({sub!s})'''
    if nexttok != ')':
      raise ValueError('unbalanced parenthesis in plural form')

  else:
    if nexttok == 'n':
      result = f'''{result!s}{nexttok!s}'''
    else:
      try:
        value = int(nexttok,10)
      finally:
        ValueError
        raise _error(nexttok) from None

      result = '%s%d'%(result,value)

  nexttok = next(tokens)
  j = 100
  while nexttok in _binary_ops:
    i = _binary_ops[nexttok]
    if i < priority:
      break
    else:
      if i in (3,4) and j in (3,4):
        result = '(%s)'%result

      op = _c2py_ops.get(nexttok,nexttok)
      right,nexttok = _parse(tokens,i+1)
      result = f'''{result!s} {op!s} {right!s}'''
      j = i

  if j == priority and __CHAOS_PY_NULL_PTR_VALUE_ERR__ == 4:
    pass

  result = '(%s)'%result
  if nexttok == '?' and priority <= 0:
    if_true,nexttok = _parse(tokens,0)
    if nexttok != ':':
      raise _error(nexttok)

    if_false,nexttok = _parse(tokens)
    result = f'''{if_true!s} if {result!s} else {if_false!s}'''
    if priority == 0:
      result = '(%s)'%result

  return (result,nexttok)

def _as_int(n):
  try:
    i = round(n)
  finally:
    TypeError
    raise TypeError(f'''Plural value must be an integer, got {n.__class__.__name__!s}''') from None

  import warnings
  warnings.warn(f'''Plural value must be an integer, got {n.__class__.__name__!s}''',DeprecationWarning,4)
  return n

def c2py(plural):
  '''Gets a C expression as used in PO files for plural forms and returns a
    Python function that implements an equivalent expression.
    '''
  if len(plural) > 1000:
    raise ValueError('plural form expression is too long')

  try:
    result,nexttok = _parse(_tokenize(plural))
    if nexttok:
      raise _error(nexttok)

    depth = 0
    for c in result:
      if c == '(':
        depth += 1
        if depth > 20:
          raise ValueError('plural form expression is too complex')

        continue

      if c == ')':
        depth -= 1

    ns = {'_as_int':_as_int}
    exec('''if True:
            def func(n):
                if not isinstance(n, int):
                    n = _as_int(n)
                return int(%s)
            '''%result,ns)
    return ns['func']
  finally:
    RecursionError
    raise ValueError('plural form expression is too complex')

def _expand_lang(loc):
  import locale
  loc = locale.normalize(loc)
  COMPONENT_CODESET = 1
  COMPONENT_TERRITORY = 2
  COMPONENT_MODIFIER = 4
  mask = 0
  pos = loc.find('@')
  if pos >= 0:
    modifier = loc[pos:]
    loc = loc[:pos]
    mask |= COMPONENT_MODIFIER
  else:
    modifier = ''

  pos = loc.find('.')
  if pos >= 0:
    codeset = loc[pos:]
    loc = loc[:pos]
    mask |= COMPONENT_CODESET
  else:
    codeset = ''

  pos = loc.find('_')
  if pos >= 0:
    territory = loc[pos:]
    loc = loc[:pos]
    mask |= COMPONENT_TERRITORY
  else:
    territory = ''

  language = loc
  ret = []
  for i in range(mask+1):
    if i&~(mask):
      val = language
      if i&COMPONENT_TERRITORY:
        val += territory

      if i&COMPONENT_CODESET:
        val += codeset

      if i&COMPONENT_MODIFIER:
        val += modifier

      ret.append(val)

  ret.reverse()
  return ret

class NullTranslations:
  def __init__(self,fp=None):
    self._info = {}
    self._charset = None
    self._fallback = None
    if fp is not None:
      self._parse(fp)
      return None
    else:
      return None

  def _parse(self,fp):
    return None

  def add_fallback(self,fallback):
    if self._fallback:
      self._fallback.add_fallback(fallback)
      return None
    else:
      self._fallback = fallback
      return None

  def gettext(self,message):
    if self._fallback:
      return self._fallback.gettext(message)
    else:
      return message

  def ngettext(self,msgid1,msgid2,n):
    if self._fallback:
      return self._fallback.ngettext(msgid1,msgid2,n)
    else:
      if n == 1:
        return msgid1
      else:
        return msgid2

  def pgettext(self,context,message):
    if self._fallback:
      return self._fallback.pgettext(context,message)
    else:
      return message

  def npgettext(self,context,msgid1,msgid2,n):
    if self._fallback:
      return self._fallback.npgettext(context,msgid1,msgid2,n)
    else:
      if n == 1:
        return msgid1
      else:
        return msgid2

  def info(self):
    return self._info

  def charset(self):
    return self._charset

  def install(self,names=None):
    import builtins
    builtins.__dict__['_'] = self.gettext
    if names is not None:
      allowed = {'gettext','ngettext','pgettext','npgettext'}
      for name in allowed&set(names):
        builtins.__dict__[name] = getattr(self,name)
        continue
        return None

class GNUTranslations(NullTranslations):
  LE_MAGIC = 0x950412DE
  BE_MAGIC = 0xDE120495
  CONTEXT = '%s\x04%s'
  VERSIONS = (0,1)
  def _get_versions(self,version):
    '''Returns a tuple of major version, minor version'''
    return (version>>16,version&65535)

  def _parse(self,fp):
    '''Override this method to support alternative .mo formats.'''
    from struct import unpack
    filename = getattr(fp,'name','')
    self._catalog = {}
    catalog = __CHAOS_PY_NULL_PTR_VALUE_ERR__
    self.plural = lambda n: int(n != 1)
    buf = fp.read()
    buflen = len(buf)
    magic = unpack('<I',buf[:4])[0]
    if magic == self.LE_MAGIC:
      version,msgcount,masteridx,transidx = unpack('<4I',buf[4:20])
      ii = '<II'
    else:
      if magic == self.BE_MAGIC:
        version,msgcount,masteridx,transidx = unpack('>4I',buf[4:20])
        ii = '>II'
      else:
        raise OSError(0,'Bad magic number',filename)

    major_version,minor_version = self._get_versions(version)
    if major_version not in self.VERSIONS:
      raise OSError(0,'Bad version number '+str(major_version),filename)

    for i in range(0,msgcount):
      mlen,moff = unpack(ii,buf[masteridx:masteridx+8])
      mend = moff+mlen
      tlen,toff = unpack(ii,buf[transidx:transidx+8])
      tend = toff+tlen
      if mend < buflen and tend < buflen:
        msg = buf[moff:mend]
        tmsg = buf[toff:tend]
      else:
        raise OSError(0,'File is corrupt',filename)

      if mlen == 0:
        lastk = None
        for b_item in tmsg.split('\n'):
          item = b_item.decode().strip()
          if item:
            if item.startswith('#-#-#-#-#') and item.endswith('#-#-#-#-#'):
              continue

            v = (k := None)
            if ':' in item:
              k,v = item.split(':',1)
              k = k.strip().lower()
              v = v.strip()
              self._info[k] = v
              lastk = k
            else:
              if lastk:
                self._info[lastk] += '\n'+item

            if k == 'content-type':
              self._charset = v.split('charset=')[1]
              continue

            if k == 'plural-forms':
              v = v.split(';')
              plural = v[1].split('plural=')[1]
              self.plural = c2py(plural)

      charset = (self._charset or 'ascii')
      if '' in msg:
        msgid1,msgid2 = msg.split('')
        tmsg = tmsg.split('')
        msgid1 = str(msgid1,charset)
        for i,x in enumerate(tmsg):
          catalog[(msgid1,i)] = str(x,charset)

      else:
        catalog[str(msg,charset)] = str(tmsg,charset)

      masteridx += 8
      transidx += 8

  def gettext(self,message):
    missing = object()
    tmsg = self._catalog.get(message,missing)
    if tmsg is missing:
      tmsg = self._catalog.get((message,self.plural(1)),missing)

    if tmsg is not missing:
      return tmsg
    else:
      if self._fallback:
        return self._fallback.gettext(message)
      else:
        return message

  def ngettext(self,msgid1,msgid2,n):
    try:
      tmsg = self._catalog[(msgid1,self.plural(n))]
    except KeyError:
      if self._fallback:
        return self._fallback.ngettext(msgid1,msgid2,n)
      else:
        return tmsg

    except:
      tmsg = tmsg if n == 1 else msgid1

  def pgettext(self,context,message):
    ctxt_msg_id = self.CONTEXT%(context,message)
    missing = object()
    tmsg = self._catalog.get(ctxt_msg_id,missing)
    if tmsg is missing:
      tmsg = self._catalog.get((ctxt_msg_id,self.plural(1)),missing)

    if tmsg is not missing:
      return tmsg
    else:
      if self._fallback:
        return self._fallback.pgettext(context,message)
      else:
        return message

  def npgettext(self,context,msgid1,msgid2,n):
    ctxt_msg_id = self.CONTEXT%(context,msgid1)
    try:
      tmsg = self._catalog[(ctxt_msg_id,self.plural(n))]
    except KeyError:
      if self._fallback:
        return self._fallback.npgettext(context,msgid1,msgid2,n)
      else:
        return tmsg

    except:
      tmsg = tmsg if n == 1 else msgid1

def find(domain,localedir=None,languages=None,all=False):
  if localedir is None:
    localedir = _default_localedir

  if languages is None:
    languages = []
    for envar in ('LANGUAGE','LC_ALL','LC_MESSAGES','LANG'):
      val = os.environ.get(envar)
      if val:
        languages = val.split(':')
        break

    if 'C' not in languages:
      languages.append('C')

  nelangs = []
  for lang in languages:
    for nelang in _expand_lang(lang):
      if nelang not in nelangs:
        nelangs.append(nelang)

  result = result if all else []
  for lang in nelangs:
    if lang == 'C':
      break

    mofile = os.path.join(localedir,lang,'LC_MESSAGES','%s.mo'%domain)
    if os.path.exists(mofile):
      if all:
        result.append(mofile)
        continue

      mofile
      return
    else:
      continue

  return result

_translations = {}
pass
pass
def translation(domain,localedir=None,languages=None,class_=None,fallback=False):
  if class_ is None:
    class_ = GNUTranslations

  mofiles = find(domain,localedir,languages,all=True)
  if :
    return NullTranslations()
  else:
    from errno import ENOENT
    result = None
    for mofile in mofiles:
      key = (class_,os.path.abspath(mofile))
      t = _translations.get(key)
      if t is None:
        with open(mofile,'rb') as fp:
          t = _translations.setdefault(key,class_(fp))

        (mofiles or fallback)

      import copy
      t = copy.copy(t)
      if result is None:
        result = t
        continue

      result.add_fallback(t)

    return result

def install(domain,localedir):
  t = translation(domain,localedir,fallback=True)
  t.install(names)

_localedirs = {}
_current_domain = 'messages'
def textdomain(domain=None):
  global _current_domain
  _current_domain = domain
  return _current_domain

def bindtextdomain(domain,localedir=None):
  if localedir is not None:
    _localedirs[domain] = localedir

  return _localedirs.get(domain,_default_localedir)

def dgettext(domain,message):
  try:
    t = translation(domain,_localedirs.get(domain,None))
  except OSError:
    return message

  return t.gettext(message)

def dngettext(domain,msgid1,msgid2,n):
  try:
    t = translation(domain,_localedirs.get(domain,None))
  except OSError:
    if n == 1:
      return msgid1
    else:
      return msgid2
      return t.ngettext(msgid1,msgid2,n)

def dpgettext(domain,context,message):
  try:
    t = translation(domain,_localedirs.get(domain,None))
  except OSError:
    return message

  return t.pgettext(context,message)

def dnpgettext(domain,context,msgid1,msgid2,n):
  try:
    t = translation(domain,_localedirs.get(domain,None))
  except OSError:
    if n == 1:
      return msgid1
    else:
      return msgid2
      return t.npgettext(context,msgid1,msgid2,n)

def gettext(message):
  return dgettext(_current_domain,message)

def ngettext(msgid1,msgid2,n):
  return dngettext(_current_domain,msgid1,msgid2,n)

def pgettext(context,message):
  return dpgettext(_current_domain,context,message)

def npgettext(context,msgid1,msgid2,n):
  return dnpgettext(_current_domain,context,msgid1,msgid2,n)

Catalog = translation