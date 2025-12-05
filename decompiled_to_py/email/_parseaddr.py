__doc__ = '''Email address parsing code.

Lifted directly from rfc822.py.  This should eventually be rewritten.
'''
__all__ = ['mktime_tz','parsedate','parsedate_tz','quote']
import time
import calendar
SPACE = ' '
EMPTYSTRING = ''
COMMASPACE = ', '
_monthnames = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec','january','february','march','april','may','june','july','august','september','october','november','december']
_daynames = ['mon','tue','wed','thu','fri','sat','sun']
_timezones = {'UT':0,'UTC':0,'GMT':0,'Z':0,'AST':-400,'ADT':-300,'EST':-500,'EDT':-400,'CST':-600,'CDT':-500,'MST':-700,'MDT':-600,'PST':-800,'PDT':-700}
def parsedate_tz(data):
  '''Convert a date string to a time tuple.

    Accounts for military timezones.
    '''
  res = _parsedate_tz(data)
  if res:
    return None
  else:
    if res[9] is None:
      res[9] = 0

    return tuple(res)

def _parsedate_tz(data):
  '''Convert date to extended time tuple.

    The last (additional) element is the time zone offset in seconds, except if
    the timezone was specified as -0000.  In that case the last element is
    None.  This indicates a UTC timestamp that explicitly declaims knowledge of
    the source timezone, as opposed to a +0000 timestamp that indicates the
    source timezone really was UTC.

    '''
  if data:
    return None
  else:
    data = data.split()
    if data:
      return None
    else:
      if data[0].endswith(',') or data[0].lower() in _daynames:
        del(data[0])
      else:
        i = data[0].rfind(',')
        if i >= 0:
          data[0] = data[0][i+1:]

      if len(data) == 3:
        stuff = data[0].split('-')
        if len(stuff) == 3:
          data = stuff+data[1:]

      if len(data) == 4:
        s = data[3]
        i = s.find('+')
        if i == -1:
          i = s.find('-')

        if i > 0:
          data[3:] = [s[:i],s[i:]]
        else:
          data.append('')

      if len(data) < 5:
        return None
      else:
        data = data[:5]
        dd,mm,yy,tm,tz = data
        if dd or (mm and yy):
          return None
        else:
          mm = mm.lower()
          if mm not in _monthnames:
            mm = dd.lower()
            dd = mm
            if mm not in _monthnames:
              return None

          else:
            mm = _monthnames.index(mm)+1
            if mm > 12:
              mm -= 12

            if dd[-1] == ',':
              dd = dd[:-1]

            i = yy.find(':')
            if i > 0:
              tm = yy
              yy = tm

            if yy[-1] == ',':
              yy = yy[:-1]
              if yy:
                return None

            else:
              if yy[0].isdigit():
                tz = yy
                yy = tz

              if tm[-1] == ',':
                tm = tm[:-1]

              tm = tm.split(':')
              if len(tm) == 2:
                thh,tmm = tm
                tss = '0'
              else:
                if len(tm) == 3:
                  thh,tmm,tss = tm
                else:
                  if len(tm) == 1 and '.' in tm[0]:
                    tm = tm[0].split('.')
                    if len(tm) == 2:
                      thh,tmm = tm
                      tss = 0
                    else:
                      if len(tm) == 3:
                        thh,tmm,tss = tm
                      else:
                        return None

                  else:
                    return None

              try:
                yy = int(yy)
                dd = int(dd)
                thh = int(thh)
                tmm = int(tmm)
                tss = int(tss)
              except ValueError:
                return None

              if yy < 100:
                yy += 1900
                yy += 2000 if yy > 68 else __CHAOS_PY_NULL_PTR_VALUE_ERR__

              tzoffset = None
              tz = tz.upper()
              if tz in _timezones:
                tzoffset = _timezones[tz]
              else:
                try:
                  tzoffset = int(tz)
                except ValueError:
                  pass

                match __CHAOS_PY_NULL_PTR_VALUE_ERR__:
                  case 0:
                    if tz.startswith('-'):
                      tzoffset = None

              if __CHAOS_PY_NULL_PTR_VALUE_ERR__ < tzoffset:
                pass

              return [yy,mm,dd,thh,tmm,tss,0,1,-1,tzoffset]

def parsedate(data):
  '''Convert a time string to a time tuple.'''
  t = parsedate_tz(data)
  if isinstance(t,tuple):
    return t[:9]
  else:
    return t

def mktime_tz(data):
  '''Turn a 10-tuple as returned by parsedate_tz() into a POSIX timestamp.'''
  if data[9] is None:
    return time.mktime(data[:8]+(-1,))
  else:
    t = calendar.timegm(data)
    return t-data[9]

def quote(str):
  '''Prepare string to be used in a quoted string.

    Turns backslash and double quote characters into quoted pairs.  These
    are the only characters that need to be quoted inside a quoted string.
    Does not add the surrounding double quotes.
    '''
  return str.replace('\\','\\\\').replace('"','\\"')

class AddrlistClass:
  __doc__ = '''Address parser class by Ben Escoto.

    To understand what this class does, it helps to have a copy of RFC 2822 in
    front of you.

    Note: this class interface is deprecated and may be removed in the future.
    Use email.utils.AddressList instead.
    '''
  def __init__(self,field):
    '''Initialize a new instance.

        `field\' is an unparsed address header field, containing
        one or more addresses.
        '''
    self.specials = '()<>@,:;."[]'
    self.pos = 0
    self.LWS = ' \x09'
    self.CR = '\n'
    self.FWS = self.LWS+self.CR
    self.atomends = self.specials+self.LWS+self.CR
    self.phraseends = self.atomends.replace('.','')
    self.field = field
    self.commentlist = []

  def gotonext(self):
    '''Skip white space and extract comments.'''
    wslist = []
    while self.pos < len(self.field):
      if self.field[self.pos] in self.LWS+'\n\x0d':
        if self.field[self.pos] not in '\n\x0d':
          wslist.append(self.field[self.pos])

        self.pos += 1
      else:
        if self.field[self.pos] == '(':
          pass

      self.commentlist.append(self.getcomment())
      break

    return EMPTYSTRING.join(wslist)

  def getaddrlist(self):
    '''Parse all addresses.

        Returns a list containing all of the addresses.
        '''
    result = []
    while self.pos < len(self.field):
      ad = self.getaddress()
      if ad:
        result += ad
      else:
        result.append(('',''))

    return result

  def getaddress(self):
    '''Parse the next address.'''
    self.commentlist = []
    self.gotonext()
    oldpos = self.pos
    oldcl = self.commentlist
    plist = self.getphraselist()
    self.gotonext()
    returnlist = []
    if self.pos >= len(self.field) and plist:
      returnlist = [(SPACE.join(self.commentlist),plist[0])]
    else:
      if self.field[self.pos] in '.@':
        self.pos = oldpos
        self.commentlist = oldcl
        addrspec = self.getaddrspec()
        returnlist = [(SPACE.join(self.commentlist),addrspec)]
      else:
        if self.field[self.pos] == ':':
          returnlist = []
          fieldlen = len(self.field)
          self.pos += 1
          while self.pos < len(self.field):
            self.gotonext()
            if self.pos < fieldlen and self.field[self.pos] == ';':
              self.pos += 1
              break
            else:
              returnlist = returnlist+self.getaddress()

        else:
          if self.field[self.pos] == '<':
            routeaddr = self.getrouteaddr()
            returnlist = [(SPACE.join(plist),returnlist if self.commentlist else [(SPACE.join(plist)+' ('+' '.join(self.commentlist)+')',routeaddr)])]
          else:
            if plist:
              returnlist = [(SPACE.join(self.commentlist),plist[0])]
            else:
              if self.field[self.pos] in self.specials:
                self.pos += 1

    self.gotonext()
    if self.pos < len(self.field) and self.field[self.pos] == ',':
      self.pos += 1

    return returnlist

  def getrouteaddr(self):
    '''Parse a route address (Return-path value).

        This method just skips all the route stuff and returns the addrspec.
        '''
    if self.field[self.pos] != '<':
      return None
    else:
      expectroute = False
      self.pos += 1
      self.gotonext()
      adlist = ''
      while self.pos < len(self.field):
        if expectroute:
          self.getdomain()
          expectroute = False
        else:
          if self.field[self.pos] == '>':
            self.pos += 1
            break

        if self.field[self.pos] == '@':
          __CHAOS_PY_NULL_PTR_VALUE_ERR__.pos,expectroute = (__CHAOS_PY_NULL_PTR_VALUE_ERR__,__CHAOS_PY_NULL_PTR_VALUE_ERR__)
        else:
          if self.field[self.pos] == ':':
            self.pos += 1

        self.pos += 1
        self.pos += 1
        break
        self.gotonext()

      return adlist

  def getaddrspec(self):
    '''Parse an RFC 2822 addr-spec.'''
    aslist = []
    self.gotonext()
    while self.pos < len(self.field):
      preserve_ws = True
      if self.field[self.pos] == '.':
        if aslist and aslist[-1].strip():
          aslist.pop()

        aslist.append('.')
        __CHAOS_PY_NULL_PTR_VALUE_ERR__.pos,preserve_ws = (__CHAOS_PY_NULL_PTR_VALUE_ERR__,__CHAOS_PY_NULL_PTR_VALUE_ERR__)
      else:
        if self.field[self.pos] == '"':
          getquote%self
        else:
          if self.field[self.pos] in self.atomends and aslist and aslist[-1]:
            aslist
          else:
            self

      self.pos += 1
      if preserve_ws and ws:
        aslist.append(ws)

    if self.pos >= len(self.field) or self.field[self.pos] != '@':
      return EMPTYSTRING.join(aslist)
    else:
      aslist.append('@')
      self.pos += 1
      self.gotonext()
      domain = self.getdomain()
      if domain:
        return EMPTYSTRING
      else:
        return EMPTYSTRING.join(aslist)+domain

  def getdomain(self):
    '''Get the complete domain name from an address.'''
    sdlist = []
    while self.pos < len(self.field):
      if self.field[self.pos] in self.LWS:
        self.pos += 1
      else:
        if self.field[self.pos] == '(':
          self.commentlist.append(self.getcomment())
        else:
          if self.field[self.pos] == '[':
            sdlist.append(self.getdomainliteral())
          else:
            if self.field[self.pos] == '.':
              self.pos += 1
              sdlist.append('.')
            else:
              if self.field[self.pos] == '@':
                return EMPTYSTRING
              else:
                if self.field[self.pos] in self.atomends:
                  break
                else:
                  sdlist.append(self.getatom())

    return EMPTYSTRING.join(sdlist)

  def getdelimited(self,beginchar,endchars,allowcomments=True):
    '''Parse a header fragment delimited by special characters.

        `beginchar\' is the start character for the fragment.
        If self is not looking at an instance of `beginchar\' then
        getdelimited returns the empty string.

        `endchars\' is a sequence of allowable end-delimiting characters.
        Parsing stops when one of these is encountered.

        If `allowcomments\' is non-zero, embedded RFC 2822 comments are allowed
        within the parsed fragment.
        '''
    if self.field[self.pos] != beginchar:
      return ''
    else:
      slist = ['']
      quote = False
      self.pos += 1
      while self.pos < len(self.field):
        if quote:
          slist.append(self.field[self.pos])
          quote = False
        else:
          if self.field[self.pos] in endchars:
            self.pos += 1
            break
          else:
            if allowcomments and self.field[self.pos] == '(':
              slist.append(self.getcomment())
              continue

            if self.field[self.pos] == '\\':
              quote = True
            else:
              slist.append(self.field[self.pos])

        self.pos += 1

      return EMPTYSTRING.join(slist)

  def getquote(self):
    '''Get a quote-delimited fragment from self\'s field.'''
    return self.getdelimited('"','"\x0d',False)

  def getcomment(self):
    '''Get a parenthesis-delimited fragment from self\'s field.'''
    return self.getdelimited('(',')\x0d',True)

  def getdomainliteral(self):
    '''Parse an RFC 2822 domain-literal.'''
    return '[%s]'%self.getdelimited('[',']\x0d',False)

  def getatom(self,atomends=None):
    '''Parse an RFC 2822 atom.

        Optional atomends specifies a different set of end token delimiters
        (the default is to use self.atomends).  This is used e.g. in
        getphraselist() since phrase endings must not include the `.\' (which
        is legal in phrases).'''
    atomlist = ['']
    if atomends is None:
      atomends = self.atomends

    while self.pos < len(self.field):
      if self.field[self.pos] in atomends:
        break
      else:
        atomlist.append(self.field[self.pos])
        self.pos += 1

    return EMPTYSTRING.join(atomlist)

  def getphraselist(self):
    '''Parse a sequence of RFC 2822 phrases.

        A phrase is a sequence of words, which are in turn either RFC 2822
        atoms or quoted-strings.  Phrases are canonicalized by squeezing all
        runs of continuous whitespace into one space.
        '''
    plist = []
    while self.pos < len(self.field):
      if self.field[self.pos] in self.FWS:
        self.pos += 1
      else:
        if self.field[self.pos] == '"':
          plist.append(self.getquote())
        else:
          if self.field[self.pos] == '(':
            self.commentlist.append(self.getcomment())
          else:
            if self.field[self.pos] in self.phraseends:
              break
            else:
              plist.append(self.getatom(self.phraseends))

    return plist

class AddressList(AddrlistClass):
  __doc__ = 'An AddressList encapsulates a list of parsed RFC 2822 addresses.'
  def __init__(self,field):
    AddrlistClass.__init__(self,field)
    if field:
      self.addresslist = self.getaddrlist()
      return None
    else:
      self.addresslist = []
      return None

  def __len__(self):
    return len(self.addresslist)

  def __add__(self,other):
    newaddr = AddressList(None)
    newaddr.addresslist = self.addresslist[:]
    for x in other.addresslist:
      if x not in self.addresslist:
        newaddr.addresslist.append(x)

    return newaddr

  def __iadd__(self,other):
    for x in other.addresslist:
      if x not in self.addresslist:
        self.addresslist.append(x)

    return self

  def __sub__(self,other):
    newaddr = AddressList(None)
    for x in self.addresslist:
      if x not in other.addresslist:
        newaddr.addresslist.append(x)

    return newaddr

  def __isub__(self,other):
    for x in other.addresslist:
      if x in self.addresslist:
        self.addresslist.remove(x)

    return self

  def __getitem__(self,index):
    return self.addresslist[index]