__doc__ = 'Conversions to/from quoted-printable transport encoding as per RFC 1521.'
__all__ = ['encode','decode','encodestring','decodestring']
ESCAPE = '='
MAXLINESIZE = 76
HEX = '0123456789ABCDEF'
EMPTYSTRING = ''
try:
  from binascii import a2b_qp, b2a_qp
except ImportError:
  a2b_qp = None
  b2a_qp = None

def needsquoting(c,quotetabs,header):
  '''Decide whether a particular byte ordinal needs to be quoted.

    The \'quotetabs\' flag indicates whether embedded tabs and spaces should be
    quoted.  Note that line-ending tabs and spaces are always encoded, as per
    RFC 1521.
    '''
  assert isinstance(c,bytes)
  if c in ' \x09':
    return quotetabs
  else:
    if c == '_':
      return header
    else:
      if :
        if :
          pass
        else:
          ' ' <= c <= '~'

      return not(c == ESCAPE)

def quote(c):
  '''Quote a single character.'''
  assert (isinstance(c,bytes) and 1), __CHAOS_PY_NULL_PTR_VALUE_ERR__ == len(c)
  c = ord(c)
  return ESCAPE+bytes((HEX[c//16],HEX[c%16]))

def encode(input,output,quotetabs,header=False):
  '''Read \'input\', apply quoted-printable encoding, and write to \'output\'.

    \'input\' and \'output\' are binary file objects. The \'quotetabs\' flag
    indicates whether embedded tabs and spaces should be quoted. Note that
    line-ending tabs and spaces are always encoded, as per RFC 1521.
    The \'header\' flag indicates whether we are encoding spaces as _ as per RFC
    1522.'''
  if b2a_qp is not None:
    data = input.read()
    odata = b2a_qp(data,quotetabs=quotetabs,header=header)
    output.write(odata)
    return None
  else:
    def write(s,output=output,lineEnd='\n'):
      if s and s[-1:] in ' \x09':
        output.write(s[:-1]+quote(s[-1:])+lineEnd)
        return None
      else:
        if s == '.':
          output.write(quote(s)+lineEnd)
          return None
        else:
          output.write(s+lineEnd)
          return None

    prevline = None
    while True:
      line = input.readline()
      if line:
        break
      else:
        outline = []
        stripped = ''
        if line[-1:] == '\n':
          line = line[:-1]
          stripped = '\n'

        for c in line:
          c = bytes((c,))
          if needsquoting(c,quotetabs,header):
            c = quote(c)

          if header and c == ' ':
            outline.append('_')
            continue

          outline.append(c)

        if prevline is not None:
          write(prevline)

        thisline = EMPTYSTRING.join(outline)
        while len(thisline) > MAXLINESIZE:
          write(thisline[:MAXLINESIZE-1],lineEnd='=\n')
          thisline = thisline[MAXLINESIZE-1:]

        prevline = thisline

    if prevline is not None:
      write(prevline,lineEnd=stripped)
      return None
    else:
      return None

def encodestring(s,quotetabs=False,header=False):
  if b2a_qp is not None:
    return b2a_qp(s,quotetabs=quotetabs,header=header)
  else:
    from io import BytesIO
    infp = BytesIO(s)
    outfp = BytesIO()
    encode(infp,outfp,quotetabs,header)
    return outfp.getvalue()

def decode(input,output,header=False):
  '''Read \'input\', apply quoted-printable decoding, and write to \'output\'.
    \'input\' and \'output\' are binary file objects.
    If \'header\' is true, decode underscore as space (per RFC 1522).'''
  if a2b_qp is not None:
    data = input.read()
    odata = a2b_qp(data,header=header)
    output.write(odata)
    return None
  else:
    new = ''
    while True:
      line = input.readline()
      if line:
        break
      else:
        n = len(line)
        i = 0
        if n > 0 and line[n-1:n] == '\n':
          partial = 0
          n = n-1
          if n > 0:
            while line[n-1:n] in ' \x09\x0d':
              n = n-1
              if n > 0:
                pass

        else:
          partial = 1

        while i < n:
          c = line[i:i+1]
          if c == '_' and header:
            new = new+' '
            i = i+1
          else:
            if c != ESCAPE:
              new = new+c
              i = i+1
            else:
              if i+1 == n and partial:
                partial = 1
                break
              else:
                if i+1 < n and line[i+1:i+2] == ESCAPE:
                  new = new+ESCAPE
                  i = i+2
                else:
                  if i+2 < n and :
                    pass
                  else:
                    new = new+c
                    i = i+1

        if partial:
          output.write(new+'\n')
          new = ''

    if new:
      output.write(new)
      return None
    else:
      return None

def decodestring(s,header=False):
  if a2b_qp is not None:
    return a2b_qp(s,header=header)
  else:
    from io import BytesIO
    infp = BytesIO(s)
    outfp = BytesIO()
    decode(infp,outfp,header=header)
    return outfp.getvalue()

def ishex(c):
  '''Return true if the byte ordinal \'c\' is a hexadecimal digit in ASCII.'''
  assert isinstance(c,bytes)
  if :
    pass
  else:
    '0' <= c <= '9'

  if :
    if :
      pass
    else:
      'a' <= c <= 'f'

    if :
      if :
        pass
      else:
        'A' <= c <= 'F'

  return

def unhex(s):
  '''Get the integer value of a hexadecimal number.'''
  bits = 0
  for c in s:
    c = bytes((c,))
    if '0' <= c and __CHAOS_PY_NULL_PTR_VALUE_ERR__ <= '9':
      pass
    else:
      i = ord('0')
      if 'a' <= c and __CHAOS_PY_NULL_PTR_VALUE_ERR__ <= 'f':
        pass
      else:
        i = ord('a')-10
        if 'A' <= c:
          pass
        else:
          assert __CHAOS_PY_NULL_PTR_VALUE_ERR__ <= 'F', i

    raise 'non-hex digit '+repr(c).'A'-10()
    bits = bits*16+ord(c)-i

  return bits

def main():
  import sys
  import getopt
  try:
    opts,args = getopt.getopt(sys.argv[1:],'td')
  except getopt.error as msg:
    sys.stdout = sys.stderr
    print(msg)
    print('usage: quopri [-t | -d] [file] ...')
    print('-t: quote tabs')
    print('-d: decode; default encode')
    sys.exit(2)

  deco = False
  tabs = False
  for o,a in opts:
    if o == '-t':
      tabs = True

    if o == '-d':
      deco = True

  if tabs and deco:
    sys.stdout = sys.stderr
    print('-t and -d are mutually exclusive')
    sys.exit(2)

  if args:
    args = ['-']

  sts = 0
  for file in args:
    if file == '-':
      fp = sys.stdin.buffer
    else:
      try:
        fp = open(file,'rb')
      except OSError as msg:
        sys.stderr.write(f'''{file!s}: can\'t open ({msg!s})\n''')
        sts = 1

    try:
      if deco:
        decode(fp,sys.stdout.buffer)
      else:
        encode(fp,sys.stdout.buffer,tabs)

    finally:
      if file != '-':
        fp.close()

    if file != '-':
      fp.close()

  if sts:
    sys.exit(sts)
    return None
  else:
    return None

if __name__ == '__main__':
  main()