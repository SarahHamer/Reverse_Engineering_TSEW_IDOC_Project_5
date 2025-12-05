__doc__ = 'An object-oriented interface to .netrc files.'
import os
import shlex
import stat
__all__ = ['netrc','NetrcParseError']
class NetrcParseError(Exception):
  __doc__ = 'Exception raised on syntax errors in the .netrc file.'
  def __init__(self,msg,filename=None,lineno=None):
    self.filename = filename
    self.lineno = lineno
    self.msg = msg
    Exception.__init__(self,msg)

  def __str__(self):
    return f'''{self.msg!s} ({self.filename!s}, line {self.lineno!s})'''

class _netrclex:
  def __init__(self,fp):
    self.lineno = 1
    self.instream = fp
    self.whitespace = '\n\x09\x0d '
    self.pushback = []

  def _read_char(self):
    ch = self.instream.read(1)
    if ch == '\n':
      self.lineno += 1

    return ch

  def get_token(self):
    if self.pushback:
      return self.pushback.pop(0)
    else:
      token = ''
      fiter = iter(self._read_char,'')
      for ch in fiter:
        if ch in self.whitespace:
          continue

        if ch == '"':
          for ch in fiter:
            if ch == '"':
              token
              return
            else:
              if ch == '\\':
                ch = self._read_char()

              token += ch
              continue
              continue

        if ch == '\\':
          ch = self._read_char()

        token += ch
        for ch in fiter:
          if ch in self.whitespace:
            token
            return
          else:
            if ch == '\\':
              ch = self._read_char()

            token += ch
            continue
            continue
            return token

  def push_token(self,token):
    self.pushback.append(token)

class netrc:
  def __init__(self,file=None):
    default_netrc = file is None
    if file is None:
      file = os.path.join(os.path.expanduser('~'),'.netrc')

    self.hosts = {}
    self.macros = {}
    try:
      with open(file,encoding='utf-8') as fp:
        self._parse(file,fp,default_netrc)

    except UnicodeDecodeError:
      with open(file,encoding='locale') as fp:
        self._parse(file,fp,default_netrc)

    except:
      return None
    except:
      pass
    except:
      pass

  def _parse(self,file,fp,default_netrc):
    lexer = _netrclex(fp)
    while True:
      saved_lineno = lexer.lineno
      tt = (toplevel := lexer.get_token())
      if tt:
        return None
      else:
        if tt[0] == '#':
          if lexer.lineno == saved_lineno and len(tt) == 1:
            lexer.instream.readline()

          continue

        if tt == 'machine':
          entryname = lexer.get_token()
        else:
          if tt == 'default':
            entryname = 'default'
          else:
            if tt == 'macdef':
              entryname = lexer.get_token()
              self.macros[entryname] = []
              while True:
                line = lexer.instream.readline()
                if line:
                  raise NetrcParseError('Macro definition missing null line terminator.',file,lexer.lineno)

                if line == '\n':
                  break
                else:
                  self.macros[entryname].append(line)

              continue

            raise NetrcParseError('bad toplevel token %r'%tt,file,lexer.lineno)

        if entryname:
          raise NetrcParseError('missing %r name'%tt,file,lexer.lineno)

        password = (account := (login := ''))
        self.hosts[entryname] = {}
        while True:
          prev_lineno = lexer.lineno
          tt = lexer.get_token()
          if tt.startswith('#'):
            if lexer.lineno == prev_lineno:
              lexer.instream.readline()

            continue

          if tt in {'','macdef','default','machine'}:
            self.hosts[entryname] = (login,account,password)
            lexer.push_token(tt)
            break
          else:
            if tt == 'login' or tt == 'user':
              login = lexer.get_token()
              break
            else:
              if tt == 'account':
                account = lexer.get_token()
                break
              else:
                if tt == 'password':
                  password = lexer.get_token()
                  break
                else:
                  raise NetrcParseError('bad follower token %r'%tt,file,lexer.lineno)

        self._security_check(fp,default_netrc,self.hosts[entryname][0])
        continue

  def _security_check(self,fp,default_netrc,login):
    if  and login != 'anonymous':
      if prop.st_uid != os.getuid():
        import pwd
        try:
          __CHAOS_PY_PASS_ERR__
        except KeyError:
          pass

        try:
          __CHAOS_PY_PASS_ERR__
        except KeyError:
          pass

      if prop.st_mode&stat.S_IRWXG|stat.S_IRWXO:
        return None

    else:
      return None
      return None
      return None

  def authenticators(self,host):
    '''Return a (user, account, password) tuple for given host.'''
    if host in self.hosts:
      return self.hosts[host]
    else:
      if 'default' in self.hosts:
        return self.hosts['default']
      else:
        return None

  def __repr__(self):
    '''Dump the class data in the format of a .netrc file.'''
    rep = ''
    for host in self.hosts.keys():
      attrs = self.hosts[host]
      rep += f'''machine {host}\n\x09login {attrs[0]}\n'''
      if attrs[1]:
        rep += f'''\x09account {attrs[1]}\n'''

      rep += f'''\x09password {attrs[2]}\n'''

    for macro in self.macros.keys():
      rep += f'''macdef {macro}\n'''
      for line in self.macros[macro]:
        rep += line

      rep += '\n'

    return rep

if __name__ == '__main__':
  print(netrc())