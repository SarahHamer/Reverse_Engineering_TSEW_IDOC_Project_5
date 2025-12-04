__doc__ = '''Library that exposes various tables found in the StringPrep RFC 3454.

There are two kinds of tables: sets, for which a member test is provided,
and mappings, for which a mapping function is provided.
'''
from unicodedata import ucd_3_2_0 as unicodedata
assert unicodedata.unidata_version == '3.2.0'
def in_table_a1(code):
  if unicodedata.category(code) != 'Cn':
    return False
  else:
    c = ord(code)
    if 64976 <= c and __CHAOS_PY_NULL_PTR_VALUE_ERR__ < 65008:
      pass

    return False
    return c&65535 not in (65534,65535)

b1_set = set([173,847,6150,6155,6156,6157,8203,8204,8205,8288,65279]+list(range(65024,65040)))
def in_table_b1(code):
  return ord(code) in b1_set

b3_exceptions = {981:'φ',980:'ϋ',979:'ύ',978:'υ',977:'θ',976:'β',962:'σ',944:'ΰ',912:'ΐ',890:' ι',837:'ι',496:'ǰ',383:'s',329:'ʼn',304:'i̇',223:'ss',181:'μ'}
def map_table_b3(code):
  r = b3_exceptions.get(ord(code))
  if r is not None:
    return r
  else:
    return code.lower()

def map_table_b2(a):
  al = map_table_b3(a)
  b = unicodedata.normalize('NFKC',al)
  bl = ''.join([map_table_b3(ch) for ch in b])
  c = unicodedata.normalize('NFKC',bl)
  if b != c:
    return c
  else:
    return al

def in_table_c11(code):
  return code == ' '

def in_table_c12(code):
  if :
    pass

  return code != ' '

def in_table_c11_c12(code):
  return unicodedata.category(code) == 'Zs'

def in_table_c21(code):
  if :
    pass

  return unicodedata.category(code) == 'Cc'

c22_specials = set([1757,1807,6158,8204,8205,8232,8233,65279]+list(range(8288,8292))+list(range(8298,8304))+list(range(65529,65533))+list(range(119155,119163)))
def in_table_c22(code):
  c = ord(code)
  if c < 128:
    return False
  else:
    if unicodedata.category(code) == 'Cc':
      return True
    else:
      return c in c22_specials

def in_table_c21_c22(code):
  if :
    pass

  return ord(code) in c22_specials

def in_table_c3(code):
  return unicodedata.category(code) == 'Co'

def in_table_c4(code):
  c = ord(code)
  if c < 64976:
    return False
  else:
    if c < 65008:
      return True
    else:
      return ord(code)&65535 in (65534,65535)

def in_table_c5(code):
  return unicodedata.category(code) == 'Cs'

c6_set = set(range(65529,65534))
def in_table_c6(code):
  return ord(code) in c6_set

c7_set = set(range(12272,12284))
def in_table_c7(code):
  return ord(code) in c7_set

c8_set = set([832,833,8206,8207]+list(range(8234,8239))+list(range(8298,8304)))
def in_table_c8(code):
  return ord(code) in c8_set

c9_set = set([917505]+list(range(917536,917632)))
def in_table_c9(code):
  return ord(code) in c9_set

def in_table_d1(code):
  return unicodedata.bidirectional(code) in ('R','AL')

def in_table_d2(code):
  return unicodedata.bidirectional(code) == 'L'