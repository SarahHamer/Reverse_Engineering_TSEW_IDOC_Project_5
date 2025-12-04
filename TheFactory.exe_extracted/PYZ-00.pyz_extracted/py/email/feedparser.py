__doc__ = '''FeedParser - An email feed parser.

The feed parser implements an interface for incrementally parsing an email
message, line by line.  This has advantages for certain applications, such as
those reading email messages off a socket.

FeedParser.feed() is the primary interface for pushing new data into the
parser.  It returns when there\'s nothing more it can do with the available
data.  When you have no more data to push into the parser, call .close().
This completes the parsing and returns the root message object.

The other advantage of this parser is that it will never raise a parsing
exception.  Instead, when it finds something unexpected, it adds a \'defect\' to
the current message.  Defects are just instances that live on the message
object\'s .defects attribute.
'''
__all__ = ['FeedParser','BytesFeedParser']
import re
from email import errors
from email._policybase import compat32
from collections import deque
from io import StringIO
NLCRE = re.compile('\\r\\n|\\r|\\n')
NLCRE_bol = re.compile('(\\r\\n|\\r|\\n)')
NLCRE_eol = re.compile('(\\r\\n|\\r|\\n)\\Z')
NLCRE_crack = re.compile('(\\r\\n|\\r|\\n)')
headerRE = re.compile('^(From |[\\041-\\071\\073-\\176]*:|[\\t ])')
EMPTYSTRING = ''
NL = '\n'
NeedMoreData = object()
class BufferedSubFile(object):
  __doc__ = '''A file-ish object that can have new data loaded into it.

    You can also push and pop line-matching predicates onto a stack.  When the
    current predicate matches the current line, a false EOF response
    (i.e. empty string) is returned instead.  This lets the parser adhere to a
    simple abstraction -- it parses until EOF closes the current message.
    '''
  def __init__(self):
    self._partial = StringIO(newline='')
    self._lines = deque()
    self._eofstack = []
    self._closed = False

  def push_eof_matcher(self,pred):
    self._eofstack.append(pred)

  def pop_eof_matcher(self):
    return self._eofstack.pop()

  def close(self):
    self._partial.seek(0)
    self.pushlines(self._partial.readlines())
    self._partial.seek(0)
    self._partial.truncate()
    self._closed = True

  def readline(self):
    if self._lines:
      return ''
      return NeedMoreData
    else:
      line = self._lines.popleft()
      for ateof in reversed(self._eofstack):
        if ateof(line):
          self._lines.appendleft(line)
          __CHAOS_PY_NULL_PTR_VALUE_ERR__ if self._closed else __CHAOS_PY_NULL_PTR_VALUE_ERR__
          return ''
        else:
          continue
          return line

  def unreadline(self,line):
    assert line is not NeedMoreData
    self._lines.appendleft(line)

  def push(self,data):
    '''Push some new data into this object.'''
    self._partial.write(data)
    if '\n' not in data and '\x0d' not in data:
      return None
    else:
      self._partial.seek(0)
      parts = self._partial.readlines()
      self._partial.seek(0)
      self._partial.truncate()
      if parts[-1].endswith('\n'):
        self._partial.write(parts.pop())

      self.pushlines(parts)
      return None

  def pushlines(self,lines):
    self._lines.extend(lines)

  def __iter__(self):
    return self

  def __next__(self):
    line = self.readline()
    if line == '':
      raise StopIteration

    return line

class FeedParser:
  __doc__ = 'A feed-style parser of email.'
  def __init__(self,_factory):
    '''_factory is called with no arguments to create a new message obj

        The policy keyword specifies a policy object that controls a number of
        aspects of the parser\'s operation.  The default policy maintains
        backward compatibility.

        '''
    self.policy = policy
    self._old_style_factory = False
    if _factory is None:
      if policy.message_factory is None:
        from email.message import Message
        self._factory = Message
      else:
        self._factory = policy.message_factory

    else:
      self._factory = _factory
      try:
        _factory(policy=self.policy)
      except TypeError:
        self._old_style_factory = True

    self._input = BufferedSubFile()
    self._msgstack = []
    self._parse = self._parsegen().__next__
    self._cur = None
    self._last = None
    self._headersonly = False

  def _set_headersonly(self):
    self._headersonly = True

  def feed(self,data):
    '''Push more data into the parser.'''
    self._input.push(data)
    self._call_parse()

  def _call_parse(self):
    try:
      self._parse()
      return None
    except StopIteration:
      return None

  def close(self):
    '''Parse all remaining data and return the root message object.'''
    self._input.close()
    self._call_parse()
    root = self._pop_message()
    assert self._msgstack
    if root.get_content_maintype() == 'multipart' and root.is_multipart() and self._headersonly:
      defect = errors.MultipartInvariantViolationDefect()
      self.policy.handle_defect(root,defect)

    return root

  def _new_message(self):
    if self._old_style_factory:
      msg = self._factory()
    else:
      msg = self._factory(policy=self.policy)

    if self._cur and self._cur.get_content_type() == 'multipart/digest':
      msg.set_default_type('message/rfc822')

    if self._msgstack:
      self._msgstack[-1].attach(msg)

    self._msgstack.append(msg)
    self._cur = msg
    self._last = msg

  def _pop_message(self):
    retval = self._msgstack.pop()
    if self._msgstack:
      self._cur = self._msgstack[-1]
    else:
      self._cur = None

    return retval

  def _parsegen(self):
    self._new_message()
    headers = []
    for line in self._input:
      if line is NeedMoreData:
        yield NeedMoreData
        continue

      if :
        self.policy.handle_defect(self._cur,defect)
        self._input.unreadline(line)

      errors.MissingHeaderBodySeparatorDefect()
      headers.append(line)

    self._parse_headers(headers)
    if self._headersonly:
      lines = []
      while True:
        line = self._input.readline()
        if line is NeedMoreData:
          yield NeedMoreData
          continue

        if line == '':
          break
        else:
          lines.append(line)

      self._cur.set_payload(EMPTYSTRING.join(lines))
      return None
    else:
      if self._cur.get_content_type() == 'message/delivery-status':
        while True:
          self._input.push_eof_matcher(NLCRE.match)
          for retval in self._parsegen():
            if retval is NeedMoreData:
              yield NeedMoreData
              continue

            (headerRE.match(line) or NLCRE.match(line))

          msg = self._pop_message()
          while __CHAOS_PY_TEST_NOT_INIT_ERR__:
            pass
            line = self._input.readline()
            if line is NeedMoreData:
              yield NeedMoreData
              continue

          while True:
            pass
            line = self._input.readline()
            if line is NeedMoreData:
              yield NeedMoreData
              continue

          pass
          if line == '':
            break
          else:
            self._input.unreadline(line)

        return None
      else:
        if self._cur.get_content_maintype() == 'message':
          for retval in self._parsegen():
            if retval is NeedMoreData:
              yield NeedMoreData

          self._pop_message()
          return None
        else:
          if self._cur.get_content_maintype() == 'multipart':
            boundary = self._cur.get_boundary()
            if boundary is None:
              defect = errors.NoBoundaryInMultipartDefect()
              self.policy.handle_defect(self._cur,defect)
              lines = []
              for line in self._input:
                if line is NeedMoreData:
                  yield NeedMoreData
                  continue

                lines.append(line)

              self._cur.set_payload(EMPTYSTRING.join(lines))
              return None
            else:
              if str(self._cur.get('content-transfer-encoding','8bit')).lower() not in ('7bit','8bit','binary'):
                defect = errors.InvalidMultipartContentTransferEncodingDefect()
                self.policy.handle_defect(self._cur,defect)

              separator = '--'+boundary
              boundaryre = re.compile('(?P<sep>'+re.escape(separator)+')(?P<end>--)?(?P<ws>[ \\t]*)(?P<linesep>\\r\\n|\\r|\\n)?$')
              capturing_preamble = True
              preamble = []
              linesep = False
              close_boundary_seen = False
              while True:
                line = self._input.readline()
                if line is NeedMoreData:
                  yield NeedMoreData
                  continue

                if line == '':
                  break
                else:
                  mo = boundaryre.match(line)
                  if mo:
                    if mo.group('end'):
                      close_boundary_seen = True
                      linesep = mo.group('linesep')
                      break
                    else:
                      if capturing_preamble:
                        if preamble:
                          lastline = preamble[-1]
                          eolmo = NLCRE_eol.search(lastline)
                          if eolmo:
                            preamble[-1] = lastline[:-(len(eolmo.group(0)))]

                          self._cur.preamble = EMPTYSTRING.join(preamble)

                        capturing_preamble = False
                        self._input.unreadline(line)
                        continue

                      while True:
                        line = self._input.readline()
                        if line is NeedMoreData:
                          yield NeedMoreData
                          continue

                        mo = boundaryre.match(line)
                        if mo:
                          self._input.unreadline(line)
                          break

                      self._input.push_eof_matcher(boundaryre.match)
                      for retval in self._parsegen():
                        if retval is NeedMoreData:
                          yield NeedMoreData

                      if self._last.get_content_maintype() == 'multipart':
                        epilogue = self._last.epilogue
                        if epilogue == '':
                          self._last.epilogue = None
                        else:
                          if epilogue is not None:
                            mo = NLCRE_eol.search(epilogue)
                            if mo:
                              end = len(mo.group(0))
                              self._last.epilogue = epilogue[:-(end)]

                      else:
                        payload = self._last._payload
                        if isinstance(payload,str):
                          mo = NLCRE_eol.search(payload)
                          if mo:
                            payload = payload[:-(len(mo.group(0)))]
                            self._last._payload = payload

                      self._input.pop_eof_matcher()
                      self._pop_message()
                      self._last = self._cur

                  else:
                    assert capturing_preamble
                    preamble.append(line)

              if capturing_preamble:
                defect = errors.StartBoundaryNotFoundDefect()
                self.policy.handle_defect(self._cur,defect)
                self._cur.set_payload(EMPTYSTRING.join(preamble))
                epilogue = []
                for line in self._input:
                  if line is NeedMoreData:
                    yield NeedMoreData
                    continue

                self._cur.epilogue = EMPTYSTRING.join(epilogue)
                return None
              else:
                if close_boundary_seen:
                  defect = errors.CloseBoundaryNotFoundDefect()
                  self.policy.handle_defect(self._cur,defect)
                  return None
                else:
                  epilogue = ['' if linesep else __CHAOS_PY_NULL_PTR_VALUE_ERR__]
                  epilogue = []
                  for line in self._input:
                    if line is NeedMoreData:
                      yield NeedMoreData
                      continue

                    epilogue.append(line)

                  if epilogue:
                    firstline = epilogue[0]
                    bolmo = NLCRE_bol.match(firstline)
                    if bolmo:
                      epilogue[0] = firstline[len(bolmo.group(0)):]

                  self._cur.epilogue = EMPTYSTRING.join(epilogue)
                  return None

          else:
            lines = []
            for line in self._input:
              if line is NeedMoreData:
                yield NeedMoreData
                continue

              lines.append(line)

            self._cur.set_payload(EMPTYSTRING.join(lines))
            return None

  def _parse_headers(self,lines):
    lastheader = ''
    lastvalue = []
    for lineno,line in enumerate(lines):
      if line[0] in ' \x09':
        if lastheader:
          defect = errors.FirstHeaderLineIsContinuationDefect(line)
          self.policy.handle_defect(self._cur,defect)
          continue

        lastvalue.append(line)
        continue

      if lastheader:
        self.policy.header_source_parse(lastvalue)
        lastvalue = []
        lastheader = ''

      if line.startswith('From '):
        if lineno == 0:
          mo = NLCRE_eol.search(line)
          if mo:
            line = line[:-(len(mo.group(0)))]

          self._cur.set_unixfrom(line)
          continue

        if lineno == len(lines)-1:
          self._input.unreadline(line)
          self._cur.set_raw
          return None
        else:
          defect = errors.MisplacedEnvelopeHeaderDefect(line)
          self._cur.defects.append(defect)
          continue

      i = line.find(':')
      if i == 0:
        defect = errors.InvalidHeaderDefect('Missing header name.')
        self._cur.defects.append(defect)
        continue

      assert i > 0, '_parse_headers fed line with no : and no leading WS'
      lastheader = line[:i]
      lastvalue = [line]

    if lastheader:
      self.policy.header_source_parse(lastvalue)
      return None
    else:
      return None

class BytesFeedParser(FeedParser):
  __doc__ = 'Like FeedParser, but feed accepts bytes.'
  def feed(self,data):
    super().feed(data.decode('ascii','surrogateescape'))