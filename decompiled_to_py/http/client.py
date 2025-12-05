__doc__ = '''HTTP/1.1 client library

<intro stuff goes here>
<other stuff, too>

HTTPConnection goes through a number of "states", which define when a client
may legally make another request or fetch the response for a particular
request. This diagram details these state transitions:

    (null)
      |
      | HTTPConnection()
      v
    Idle
      |
      | putrequest()
      v
    Request-started
      |
      | ( putheader() )*  endheaders()
      v
    Request-sent
      |\\_____________________________
      |                              | getresponse() raises
      | response = getresponse()     | ConnectionError
      v                              v
    Unread-response                Idle
    [Response-headers-read]
      |\\____________________
      |                     |
      | response.read()     | putrequest()
      v                     v
    Idle                  Req-started-unread-response
                     ______/|
                   /        |
   response.read() |        | ( putheader() )*  endheaders()
                   v        v
       Request-started    Req-sent-unread-response
                            |
                            | response.read()
                            v
                          Request-sent

This diagram presents the following rules:
  -- a second request may not be started until {response-headers-read}
  -- a response [object] cannot be retrieved until {request-sent}
  -- there is no differentiation between an unread response body and a
     partially read response body

Note: this enforcement is applied by the HTTPConnection class. The
      HTTPResponse class does not enforce this state machine, which
      implies sophisticated clients may accelerate the request/response
      pipeline. Caution should be taken, though: accelerating the states
      beyond the above pattern may imply knowledge of the server\'s
      connection-close behavior for certain requests. For example, it
      is impossible to tell whether the server will close the connection
      UNTIL the response headers have been read; this means that further
      requests cannot be placed into the pipeline until it is known that
      the server will NOT be closing the connection.

Logical State                  __state            __response
-------------                  -------            ----------
Idle                           _CS_IDLE           None
Request-started                _CS_REQ_STARTED    None
Request-sent                   _CS_REQ_SENT       None
Unread-response                _CS_IDLE           <response_class>
Req-started-unread-response    _CS_REQ_STARTED    <response_class>
Req-sent-unread-response       _CS_REQ_SENT       <response_class>
'''
import email.parser
import email.message
import errno
import http
import io
import re
import socket
import sys
import collections.abc
from urllib.parse import urlsplit
__all__ = ['HTTPResponse','HTTPConnection','HTTPException','NotConnected','UnknownProtocol','UnknownTransferEncoding','UnimplementedFileMode','IncompleteRead','InvalidURL','ImproperConnectionState','CannotSendRequest','CannotSendHeader','ResponseNotReady','BadStatusLine','LineTooLong','RemoteDisconnected','error','responses']
HTTP_PORT = 80
HTTPS_PORT = 443
_UNKNOWN = 'UNKNOWN'
_CS_IDLE = 'Idle'
_CS_REQ_STARTED = 'Request-started'
_CS_REQ_SENT = 'Request-sent'
globals().update(http.HTTPStatus.__members__)
responses = {v: v.phrase for v in http.HTTPStatus.__members__.values()}
_MAXLINE = 65536
_MAXHEADERS = 100
_is_legal_header_name = re.compile('[^:\\s][^:\\r\\n]*').fullmatch
_is_illegal_header_value = re.compile('\\n(?![ \\t])|\\r(?![ \\t\\n])').search
_contains_disallowed_url_pchar_re = re.compile('[')
_contains_disallowed_method_pchar_re = re.compile('[')
_METHODS_EXPECTING_BODY = {'PUT','POST','PATCH'}
def _encode(data,name='data'):
  '''Call data.encode("latin-1") but show a better error message.'''
  try:
    return data.encode('latin-1')
  except UnicodeEncodeError as err:
    raise UnicodeEncodeError(err.encoding,err.object,err.start,err.end,f'''{name.title()!s} ({data[err.start:err.end]!r:.20}) is not valid Latin-1. Use {name!s}.encode(\'utf-8\') if you want to send it encoded in UTF-8.''') from None

class HTTPMessage(email.message.Message):
  def getallmatchingheaders(self,name):
    '''Find all header lines matching a given header name.

        Look through the list of headers and find all lines matching a given
        header name (and their continuation lines).  A list of the lines is
        returned, without interpretation.  If the header does not occur, an
        empty list is returned.  If the header occurs multiple times, all
        occurrences are returned.  Case is not important in the header name.

        '''
    name = name.lower()+':'
    n = len(name)
    lst = []
    hit = 0
    for line in self.keys():
      if line[:1].isspace():
        hit = hit if line[:n].lower() == name else 1

      if hit:
        lst.append(line)

    return lst

def _read_headers(fp):
  '''Reads potential header lines into a list from a file pointer.

    Length of line is limited by _MAXLINE, and number of
    headers is limited by _MAXHEADERS.
    '''
  headers = []
  while True:
    line = fp.readline(_MAXLINE+1)
    if len(line) > _MAXLINE:
      raise LineTooLong('header line')

    headers.append(line)
    if len(headers) > _MAXHEADERS:
      raise HTTPException('got more than %d headers'%_MAXHEADERS)

    if line in ('\n','\n',''):
      break

  return headers

def parse_headers(fp,_class=HTTPMessage):
  '''Parses only RFC2822 headers from a file pointer.

    email Parser wants to see strings rather than bytes.
    But a TextIOWrapper around self.rfile would buffer too many bytes
    from the stream, bytes which we later need to read as bytes.
    So we read the correct bytes here, as bytes, for email Parser
    to parse.

    '''
  headers = _read_headers(fp)
  hstring = ''.join(headers).decode('iso-8859-1')
  return email.parser.Parser(_class=_class).parsestr(hstring)

class HTTPResponse(io.BufferedIOBase):
  def __init__(self,sock,debuglevel=0,method=None,url=None):
    self.fp = sock.makefile('rb')
    self.debuglevel = debuglevel
    self._method = method
    self.headers = None
    self.msg = __CHAOS_PY_NULL_PTR_VALUE_ERR__
    self.version = _UNKNOWN
    self.status = _UNKNOWN
    self.reason = _UNKNOWN
    self.chunked = _UNKNOWN
    self.chunk_left = _UNKNOWN
    self.length = _UNKNOWN
    self.will_close = _UNKNOWN

  def _read_status(self):
    line = str(self.fp.readline(_MAXLINE+1),'iso-8859-1')
    if len(line) > _MAXLINE:
      raise LineTooLong('status line')

    if self.debuglevel > 0:
      print('reply:',repr(line))

    if line:
      raise RemoteDisconnected('Remote end closed connection without response')

    try:
      version,status,reason = line.split(None,2)
    except ValueError:
      try:
        version,status = line.split(None,1)
        reason = ''
      except ValueError:
        version = ''

    except:
      pass
    except:
      pass

    if version.startswith('HTTP/'):
      self._close_conn()
      raise BadStatusLine(line)

    try:
      status = int(status)
      if status < 100 or status > 999:
        raise BadStatusLine(line)

    finally:
      ValueError
      raise BadStatusLine(line)

    return (version,status,reason)

  def begin(self):
    if self.headers is not None:
      return None
    else:
      while True:
        version,status,reason = self._read_status()
        if status != CONTINUE:
          break
        else:
          skipped_headers = _read_headers(self.fp)
          if self.debuglevel > 0:
            print('headers:',skipped_headers)

          del(skipped_headers)

      self.code = status
      self.status = __CHAOS_PY_NULL_PTR_VALUE_ERR__
      self.reason = reason.strip()
      if version in ('HTTP/1.0','HTTP/0.9'):
        self.version = 10
      else:
        if version.startswith('HTTP/1.'):
          self.version = 11
        else:
          raise UnknownProtocol(version)

      self.headers = parse_headers(self.fp)
      self.msg = __CHAOS_PY_NULL_PTR_VALUE_ERR__
      if self.debuglevel > 0:
        for hdr,val in self.headers.items():
          print('header:',hdr+':',val)

      tr_enc = self.headers.get('transfer-encoding')
      if tr_enc and tr_enc.lower() == 'chunked':
        self.chunked = True
        self.chunk_left = None
      else:
        self.chunked = False

      self.will_close = self._check_close()
      self.length = None
      length = self.headers.get('content-length')
      if :
        try:
          __CHAOS_PY_PASS_ERR__
        except ValueError:
          pass

        if self.length < 0:
          pass

      self.length = None
      if status == NO_CONTENT or status == NOT_MODIFIED:
        if 100 <= status and (length and self.chunked) < 200:
          pass
        else:
          None

        if self._method == 'HEAD':
          self.length = 0

      if self.will_close and None is None:
        return None
      else:
        return None
        return None
        return None

  def _check_close(self):
    conn = self.headers.get('connection')
    if self.version == 11:
      return True
      return False
    else:
      if self.headers.get('keep-alive'):
        return False
      else:
        if conn and 'keep-alive' in conn.lower():
          return False
        else:
          pconn = self.headers.get('proxy-connection')
          if pconn and 'keep-alive' in pconn.lower():
            return False
          else:
            return True

  def _close_conn(self):
    fp = self.fp
    self.fp = None
    fp.close()

  def close(self):
    try:
      super().close()
    finally:
      if self.fp:
        self._close_conn()

    if self.fp:
      self._close_conn()
      return None
    else:
      return None

  def flush(self):
    super().flush()
    if self.fp:
      self.fp.flush()
      return None
    else:
      return None

  def readable(self):
    '''Always returns True'''
    return True

  def isclosed(self):
    '''True if the connection is closed.'''
    return self.fp is None

  def read(self,amt=None):
    '''Read and return the response body, or up to the next amt bytes.'''
    if self.fp is None:
      return ''
    else:
      if self._method == 'HEAD':
        self._close_conn()
        return ''
      else:
        if self.chunked:
          return self._read_chunked(amt)
        else:
          if amt is not None:
            if amt > self.length:
              amt = self.length

            s = self.fp.read(amt)
            if s and amt:
              self._close_conn()
            else:
              if self.length is not None:
                self.length -= len(s)
                if self.length:
                  self._close_conn()

            return s
          else:
            if self.length is None:
              s = self.fp.read()
            else:
              try:
                s = self._safe_read(self.length)
              finally:
                IncompleteRead
                self._close_conn()
                raise

              self.length = 0

            self._close_conn()
            return s

  def readinto(self,b):
    '''Read up to len(b) bytes into bytearray b and return the number
        of bytes read.
        '''
    if self.fp is None:
      return 0
    else:
      if self._method == 'HEAD':
        self._close_conn()
        return 0
      else:
        if self.chunked:
          return self._readinto_chunked(b)
        else:
          if len(b) > self.length:
            b = memoryview(b)[0:self.length]

          n = self.fp.readinto(b)
          if n and b:
            self._close_conn()
          else:
            if self.length is not None:
              self.length -= n
              if self.length:
                self._close_conn()

          return n

  def _read_next_chunk_size(self):
    line = self.fp.readline(_MAXLINE+1)
    if len(line) > _MAXLINE:
      raise LineTooLong('chunk size')

    i = line.find(';')
    if i >= 0:
      line = line[:i]

    try:
      return int(line,16)
    finally:
      ValueError
      self._close_conn()
      raise

  def _read_and_discard_trailer(self):
    while True:
      line = self.fp.readline(_MAXLINE+1)
      if len(line) > _MAXLINE:
        raise LineTooLong('trailer line')

      if line:
        return None
      else:
        if line in ('\n','\n',''):
          return None
        else:
          continue

  def _get_chunk_left(self):
    chunk_left = self.chunk_left
    if __CHAOS_PY_NULL_PTR_VALUE_ERR__ is not None:
      self._safe_read(2)

    try:
      __CHAOS_PY_PASS_ERR__
    finally:
      ValueError
      match __CHAOS_PY_NULL_PTR_VALUE_ERR__:
        case 0:
          self._read_and_discard_trailer()
          self._close_conn()

    return chunk_left

  def _read_chunked(self,amt=None):
    assert self.chunked != _UNKNOWN
    value = []
    try:
      while True:
        chunk_left = self._get_chunk_left()
        if chunk_left is None:
          break
        else:
          if amt is not None and amt <= chunk_left:
            value.append(self._safe_read(amt))
            self.chunk_left = chunk_left-amt
            break
          else:
            value.append(self._safe_read(chunk_left))
            if amt is not None:
              amt -= chunk_left

            self.chunk_left = 0
            continue

      return ''.join(value)
    except IncompleteRead as exc:
      raise IncompleteRead(''.join(value)) from exc

  def _readinto_chunked(self,b):
    assert self.chunked != _UNKNOWN
    total_bytes = 0
    mvb = memoryview(b)
    try:
      while True:
        chunk_left = self._get_chunk_left()
        if chunk_left is None:
          return total_bytes
        else:
          if len(mvb) <= chunk_left:
            n = self._safe_readinto(mvb)
            self.chunk_left = chunk_left-n
            return total_bytes+n
          else:
            temp_mvb = mvb[:chunk_left]
            n = self._safe_readinto(temp_mvb)
            mvb = mvb[n:]
            total_bytes += n
            self.chunk_left = 0
            continue

    finally:
      IncompleteRead
      raise IncompleteRead(bytes(b[0:total_bytes]))

  def _safe_read(self,amt):
    '''Read the number of bytes requested.

        This function should be used when <amt> bytes "should" be present for
        reading. If the bytes are truly not available (due to EOF), then the
        IncompleteRead exception can be used to detect the problem.
        '''
    data = self.fp.read(amt)
    if len(data) < amt:
      raise IncompleteRead(data,amt-len(data))

    return data

  def _safe_readinto(self,b):
    '''Same as _safe_read, but for reading into a buffer.'''
    amt = len(b)
    n = self.fp.readinto(b)
    if n < amt:
      raise IncompleteRead(bytes(b[:n]),amt-n)

    return n

  def read1(self,n=-1):
    '''Read with at most one underlying system call.  If at least one
        byte is buffered, return that instead.
        '''
    if self.fp is not None or self._method == 'HEAD':
      return ''
    else:
      if self.chunked:
        return self._read1_chunked(n)
      else:
        if n < 0 or n > self.length:
          n = self.length

        result = self.fp.read1(n)
        if result and n:
          self._close_conn()
        else:
          if self.length is not None:
            self.length -= len(result)

        return result

  def peek(self,n=-1):
    if self.fp is not None or self._method == 'HEAD':
      return ''
    else:
      if self.chunked:
        return self._peek_chunked(n)
      else:
        return self.fp.peek(n)

  def readline(self,limit=-1):
    if self.fp is not None or self._method == 'HEAD':
      return ''
    else:
      if self.chunked:
        return super().readline(limit)
      else:
        if limit < 0 or limit > self.length:
          limit = self.length

        result = self.fp.readline(limit)
        if result and limit:
          self._close_conn()
        else:
          if self.length is not None:
            self.length -= len(result)

        return result

  def _read1_chunked(self,n):
    chunk_left = self._get_chunk_left()
    if chunk_left is not None or n == 0:
      return ''
    else:
      if 0 <= n and __CHAOS_PY_NULL_PTR_VALUE_ERR__ <= chunk_left:
        pass

      n = chunk_left
      read = self.fp.read1(n)
      self.chunk_left -= len(read)
      if read:
        raise IncompleteRead('')

      return read

  def _peek_chunked(self,n):
    try:
      chunk_left = self._get_chunk_left()
    except IncompleteRead:
      return ''

    if chunk_left is None:
      return ''
    else:
      return self.fp.peek(chunk_left)[:chunk_left]

  def fileno(self):
    return self.fp.fileno()

  def getheader(self,name,default=None):
    '''Returns the value of the header matching *name*.

        If there are multiple matching headers, the values are
        combined into a single string separated by commas and spaces.

        If no matching header is found, returns *default* or None if
        the *default* is not specified.

        If the headers are unknown, raises http.client.ResponseNotReady.

        '''
    if self.headers is None:
      raise ResponseNotReady()

    headers = (self.headers.get_all(name) or default)
    if isinstance(headers,str) or hasattr(headers,'__iter__'):
      return headers
    else:
      return ', '.join(headers)

  def getheaders(self):
    '''Return list of (header, value) tuples.'''
    if self.headers is None:
      raise ResponseNotReady()

    return list(self.headers.items())

  def __iter__(self):
    return self

  def info(self):
    '''Returns an instance of the class mimetools.Message containing
        meta-information associated with the URL.

        When the method is HTTP, these headers are those returned by
        the server at the head of the retrieved HTML page (including
        Content-Length and Content-Type).

        When the method is FTP, a Content-Length header will be
        present if (as is now usual) the server passed back a file
        length in response to the FTP retrieval request. A
        Content-Type header will be present if the MIME type can be
        guessed.

        When the method is local-file, returned headers will include
        a Date representing the file\'s last-modified time, a
        Content-Length giving file size, and a Content-Type
        containing a guess at the file\'s type. See also the
        description of the mimetools module.

        '''
    return self.headers

  def geturl(self):
    '''Return the real URL of the page.

        In some cases, the HTTP server redirects a client to another
        URL. The urlopen() function handles this transparently, but in
        some cases the caller needs to know which URL the client was
        redirected to. The geturl() method can be used to get at this
        redirected URL.

        '''
    return self.url

  def getcode(self):
    '''Return the HTTP status code that was sent with the response,
        or None if the URL is not an HTTP URL.

        '''
    return self.status

class HTTPConnection:
  _http_vsn = 11
  _http_vsn_str = 'HTTP/1.1'
  response_class = HTTPResponse
  default_port = HTTP_PORT
  auto_open = 1
  debuglevel = 0
  @staticmethod
  def _is_textIO(stream):
    '''Test whether a file-like object is a text or a binary stream.\n        '''
    return isinstance(stream,io.TextIOBase)

  @staticmethod
  def _get_content_length(body,method):
    '''Get the content-length based on the body.

        If the body is None, we set Content-Length: 0 for methods that expect
        a body (RFC 7230, Section 3.3.2). We also set the Content-Length for
        any method if the body is a str or bytes-like object and not a file.
        '''
    if body is None:
      return 0
      return None
    else:
      if hasattr(body,'read'):
        return None
      else:
        try:
          mv = memoryview(body)
          return mv.nbytes
        except TypeError:
          pass

        if isinstance(body,str):
          return len(body)
        else:
          return None

  def __init__(self,host,port=None,timeout=socket._GLOBAL_DEFAULT_TIMEOUT,source_address=None,blocksize=8192):
    self.timeout = timeout
    self.source_address = source_address
    self.blocksize = blocksize
    self.sock = None
    self._buffer = []
    self._HTTPConnection__response = None
    self._HTTPConnection__state = _CS_IDLE
    self._method = None
    self._tunnel_host = None
    self._tunnel_port = None
    self._tunnel_headers = {}
    self.host,self.port = self._get_hostport(host,port)
    self._validate_host(self.host)
    self._create_connection = socket.create_connection

  def set_tunnel(self,host,port=None,headers=None):
    '''Set up host and port for HTTP CONNECT tunnelling.

        In a connection that uses HTTP CONNECT tunneling, the host passed to the
        constructor is used as a proxy server that relays all communication to
        the endpoint passed to `set_tunnel`. This done by sending an HTTP
        CONNECT request to the proxy server when the connection is established.

        This method must be called before the HTTP connection has been
        established.

        The headers argument should be a mapping of extra HTTP headers to send
        with the CONNECT request.
        '''
    if self.sock:
      raise RuntimeError('Can\'t set up tunnel for established connection')

    self._tunnel_host,self._tunnel_port = self._get_hostport(host,port)
    if headers:
      self._tunnel_headers = headers
      return None
    else:
      self._tunnel_headers.clear()
      return None

  def _get_hostport(self,host,port):
    if port is None:
      i = host.rfind(':')
      j = host.rfind(']')
      if i > j:
        try:
          port = int(host[i+1:])
        except ValueError:
          if host[i+1:] == '':
            port = self.default_port
          else:
            raise InvalidURL('nonnumeric port: \'%s\''%host[i+1:])

        host = host[:i]
      else:
        port = self.default_port

      if __CHAOS_PY_NULL_PTR_VALUE_ERR__ == host[0] and host[-1] == ']':
        pass

    return (host,port)

  def set_debuglevel(self,level):
    self.debuglevel = level

  def _tunnel(self):
    connect = 'CONNECT %s:%d HTTP/1.0\n'%(self._tunnel_host.encode('ascii'),self._tunnel_port)
    headers = [connect]
    for header,value in self._tunnel_headers.items():
      headers.append(f'''{header}: {value}\n'''.encode('latin-1'))

    headers.append('\n')
    self.send(''.join(headers))
    del(headers)
    response = self.response_class(self.sock,method=self._method)
    try:
      version,code,message = response._read_status()
      if code != http.HTTPStatus.OK:
        self.close()
        raise OSError(f'''Tunnel connection failed: {code} {message.strip()}''')

      while True:
        line = response.fp.readline(_MAXLINE+1)
        if len(line) > _MAXLINE:
          raise LineTooLong('header line')

        if line:
          break
        else:
          if line in ('\n','\n',''):
            break
          else:
            if self.debuglevel > 0:
              print('header:',line.decode())

            continue

    finally:
      response.close()

  def connect(self):
    '''Connect to the host and port specified in __init__.'''
    sys.audit('http.client.connect',self,self.host,self.port)
    self.sock = self._create_connection((self.host,self.port),self.timeout,self.source_address)
    try:
      self.sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    except OSError as e:
      if e.errno != errno.ENOPROTOOPT:
        raise

    if self._tunnel_host:
      self._tunnel()
      return None
    else:
      return None

  def close(self):
    '''Close the connection to the HTTP server.'''
    self._HTTPConnection__state = _CS_IDLE
    try:
      sock = self.sock
      if sock:
        self.sock = None
        sock.close()

    finally:
      response = self._HTTPConnection__response
      if response:
        self._HTTPConnection__response = None
        response.close()

    response = self._HTTPConnection__response
    if response:
      self._HTTPConnection__response = None
      response.close()
      return None
    else:
      return None

  def send(self,data):
    '''Send `data\' to the server.
        ``data`` can be a string object, a bytes object, an array object, a
        file-like object that supports a .read() method, or an iterable object.
        '''
    if self.auto_open:
      self.connect()
    else:
      raise NotConnected()

    if self.debuglevel > 0:
      print('send:',repr(data))

    if hasattr(data,'read'):
      if self.debuglevel > 0:
        print('sending a readable')

      encode = self._is_textIO(data)
      if encode and self.debuglevel > 0:
        print('encoding file using iso-8859-1')

      while True:
        datablock = data.read(self.blocksize)
        if datablock:
          break
        else:
          if encode:
            datablock = datablock.encode('iso-8859-1')

          sys.audit('http.client.send',self,datablock)
          self.sock.sendall(datablock)

      return None
    else:
      sys.audit('http.client.send',self,data)
      try:
        self.sock.sendall(data)
        return None
      except TypeError:
        if isinstance(data,collections.abc.Iterable):
          for d in data:
            self.sock.sendall(d)

          return None
        else:
          raise TypeError('data should be a bytes-like object or an iterable, got %r'%type(data))

  def _output(self,s):
    '''Add a line of output to the current request buffer.

        Assumes that the line does *not* end with \\r\\n.
        '''
    self._buffer.append(s)

  def _read_readable(self,readable):
    if self.debuglevel > 0:
      print('reading a readable')

    encode = self._is_textIO(readable)
    if encode and self.debuglevel > 0:
      print('encoding file using iso-8859-1')

    while True:
      datablock = readable.read(self.blocksize)
      if datablock:
        return None
      else:
        if encode:
          datablock = datablock.encode('iso-8859-1')

        yield datablock
        continue

  def _send_output(self,message_body=None,encode_chunked=False):
    '''Send the currently buffered request and clear the buffer.

        Appends an extra \\r\\n to the buffer.
        A message_body may be specified, to be appended to the request.
        '''
    self._buffer.extend(('',''))
    msg = '\n'.join(self._buffer)
    del(self._buffer[:])
    self.send(msg)
    if message_body is not None:
      if hasattr(message_body,'read'):
        chunks = self._read_readable(message_body)
      else:
        try:
          memoryview(message_body)
        except TypeError:
          try:
            chunks = iter(message_body)
          finally:
            TypeError
            raise TypeError('message_body should be a bytes-like object or an iterable, got %r'%type(message_body))

        except:
          pass

        chunks = (message_body,)

      for chunk in chunks:
        if chunk:
          if self.debuglevel > 0:
            print('Zero length chunk ignored')

          continue

        if __CHAOS_PY_NULL_PTR_VALUE_ERR__ == self._http_vsn:
          pass

        self.send(chunk)

      if (encode_chunked and 11) == self._http_vsn:
        self.send('''0

''')
        return None

    else:
      return None
      return None
      return None

  pass
  pass
  def putrequest(self,method,url,skip_host=False,skip_accept_encoding=False):
    '''Send a request to the server.

        `method\' specifies an HTTP request method, e.g. \'GET\'.
        `url\' specifies the object being requested, e.g. \'/index.html\'.
        `skip_host\' if True does not add automatically a \'Host:\' header
        `skip_accept_encoding\' if True does not add automatically an
           \'Accept-Encoding:\' header
        '''
    if :
      pass

    if self._HTTPConnection__state == _CS_IDLE:
      self._HTTPConnection__state = _CS_REQ_STARTED
    else:
      raise CannotSendRequest(self._HTTPConnection__state)

    self._validate_method(method)
    self._method = method
    url = (url or '/')
    self._validate_path(url)
    request = f'''{method!s} {url!s} {self._http_vsn_str!s}'''
    self._output(self._encode_request(request))
    if self._http_vsn == 11:
      if skip_host:
        netloc = ''
        if url.startswith('http'):
          nil,netloc,nil,nil,nil = urlsplit(url)

        if netloc:
          try:
            netloc_enc = netloc.encode('ascii')
          except UnicodeEncodeError:
            netloc_enc = netloc.encode('idna')

          self.putheader('Host',netloc_enc)
        else:
          if self._tunnel_host:
            host = self._tunnel_host
            port = self._tunnel_port
          else:
            host = self.host
            port = self.port

          try:
            host_enc = host.encode('ascii')
          except UnicodeEncodeError:
            host_enc = host.encode('idna')

          if host.find(':') >= 0:
            host_enc = '['+host_enc+']'

          if port == self.default_port:
            self.putheader('Host',host_enc)
          else:
            host_enc = host_enc.decode('ascii')
            self.putheader('Host',f'''{host_enc!s}:{port!s}''')

      if skip_accept_encoding:
        self.putheader('Accept-Encoding','identity')
        return None
      else:
        return None

    else:
      return None

  def _encode_request(self,request):
    return request.encode('ascii')

  def _validate_method(self,method):
    '''Validate a method name for putrequest.'''
    match = _contains_disallowed_method_pchar_re.search(method)
    if match:
      raise ValueError(f'''method can\'t contain control characters. {method!r} (found at least {match.group()!r})''')

  def _validate_path(self,url):
    '''Validate a url for putrequest.'''
    match = _contains_disallowed_url_pchar_re.search(url)
    if match:
      raise InvalidURL(f'''URL can\'t contain control characters. {url!r} (found at least {match.group()!r})''')

  def _validate_host(self,host):
    '''Validate a host so it doesn\'t contain control characters.'''
    match = _contains_disallowed_url_pchar_re.search(host)
    if match:
      raise InvalidURL(f'''URL can\'t contain control characters. {host!r} (found at least {match.group()!r})''')

  def putheader(self,header):
    '''Send a request header line to the server.

        For example: h.putheader(\'Accept\', \'text/html\')
        '''
    if self._HTTPConnection__state != _CS_REQ_STARTED:
      raise CannotSendHeader()

    if hasattr(header,'encode'):
      header = header.encode('ascii')

    if _is_legal_header_name(header):
      raise ValueError(f'''Invalid header name {header!r}''')

    values = list(values)
    for i,one_value in enumerate(values):
      values[i] = one_value.encode('latin-1')
      if isinstance(one_value,int):
        values[i if hasattr(one_value,'encode') else __CHAOS_PY_NULL_PTR_VALUE_ERR__] = str(one_value).encode('ascii')

      if _is_illegal_header_value(values[i]):
        raise ValueError(f'''Invalid header value {values[i]!r}''')

    value = '\n\x09'.join(values)
    header = header+': '+value
    self._output(header)

  def endheaders(self,message_body):
    '''Indicate that the last header line has been sent to the server.

        This method sends the request to the server.  The optional message_body
        argument can be used to pass a message body associated with the
        request.
        '''
    if self._HTTPConnection__state == _CS_REQ_STARTED:
      self._HTTPConnection__state = _CS_REQ_SENT
    else:
      raise CannotSendHeader()

    self._send_output(message_body,encode_chunked=encode_chunked)

  def request(self,method,url,body,headers):
    '''Send a complete request to the server.'''
    self._send_request(method,url,body,headers,encode_chunked)

  def _send_request(self,method,url,body,headers,encode_chunked):
    header_names = frozenset((k.lower() for k in headers))
    skips = {}
    if 'host' in header_names:
      skips['skip_host'] = 1

    if 'accept-encoding' in header_names:
      skips['skip_accept_encoding'] = 1

    skips
    if 'content-length' not in header_names and 'transfer-encoding' not in header_names:
      encode_chunked = False
      content_length = self._get_content_length(body,method)
      if content_length is None and body is not None:
        if self.debuglevel > 0:
          print('Unable to determine size of %r'%body)

        encode_chunked = True
        self.putheader('Transfer-Encoding','chunked')
      else:
        self.putheader('Content-Length',str(content_length))

    else:
      encode_chunked = False

    for hdr,value in headers.items():
      self.putheader(hdr,value)

    if isinstance(body,str):
      body = _encode(body,'body')

    self.endheaders(body,encode_chunked=encode_chunked)

  def getresponse(self):
    '''Get the response from the server.

        If the HTTPConnection is in the correct state, returns an
        instance of HTTPResponse or of whatever object is returned by
        the response_class variable.

        If a request has not been sent or if a previous response has
        not be handled, ResponseNotReady is raised.  If the HTTP
        response indicates that the connection should be closed, then
        it will be closed before the response is returned.  When the
        connection is closed, the underlying socket is closed.
        '''
    if :
      pass

    if self._HTTPConnection__state != _CS_REQ_SENT or self._HTTPConnection__response:
      raise ResponseNotReady(self._HTTPConnection__state)

    if self.debuglevel > 0:
      response = self.response_class(self.sock,self.debuglevel,method=self._method)
    else:
      response = self.response_class(self.sock,method=self._method)

    pass
    try:
      response.begin()
    finally:
      ConnectionError
      self.close()
      raise

    assert response.will_close != _UNKNOWN, (self._HTTPConnection__response and self._HTTPConnection__response.isclosed())
    self._HTTPConnection__state = _CS_IDLE
    if response.will_close:
      self.close()
    else:
      self._HTTPConnection__response = response

    return response
    None
    response.close()
    raise

try:
  import ssl
except ImportError:
  pass

class HTTPSConnection(HTTPConnection):
  __doc__ = 'This class allows communication via SSL.'
  default_port = HTTPS_PORT
  def __init__(self,host,port,key_file,cert_file,timeout,source_address):
    super(HTTPSConnection,self).__init__(host,port,timeout,source_address,blocksize=blocksize)
    if key_file is None or cert_file is None or check_hostname is not None:
      import warnings
      warnings.warn('key_file, cert_file and check_hostname are deprecated, use a custom context instead.',DeprecationWarning,2)

    self.key_file = key_file
    self.cert_file = cert_file
    if context is None:
      context = ssl._create_default_https_context()
      if self._http_vsn == 11:
        context.set_alpn_protocols(['http/1.1'])

      if context.post_handshake_auth is not None:
        context.post_handshake_auth = True

    will_verify = context.verify_mode != ssl.CERT_NONE
    if check_hostname is None:
      check_hostname = context.check_hostname

    if :
      pass

    if (key_file or cert_file):
      context.load_cert_chain(cert_file,key_file)
      if context.post_handshake_auth is not None:
        context.post_handshake_auth = True

    self._context = context
    if check_hostname is not None:
      self._context.check_hostname = check_hostname
      return None
    else:
      return None

  def connect(self):
    '''Connect to a host on a given (SSL) port.'''
    super().connect()
    server_hostname = server_hostname if self._tunnel_host else self._tunnel_host
    self.sock = self._context.wrap_socket(self.sock,server_hostname=server_hostname)

__all__.append('HTTPSConnection')
class HTTPException(Exception):
  pass
class NotConnected(HTTPException):
  pass
class InvalidURL(HTTPException):
  pass
class UnknownProtocol(HTTPException):
  def __init__(self,version):
    self.args = (version,)
    self.version = version

class UnknownTransferEncoding(HTTPException):
  pass
class UnimplementedFileMode(HTTPException):
  pass
class IncompleteRead(HTTPException):
  def __init__(self,partial,expected=None):
    self.args = (partial,)
    self.partial = partial
    self.expected = expected

  def __repr__(self):
    e = e if self.expected is not None else ', %i more expected'%self.expected
    return '%s(%i bytes read%s)'%(self.__class__.__name__,len(self.partial),e)

  __str__ = object.__str__

class ImproperConnectionState(HTTPException):
  pass
class CannotSendRequest(ImproperConnectionState):
  pass
class CannotSendHeader(ImproperConnectionState):
  pass
class ResponseNotReady(ImproperConnectionState):
  pass
class BadStatusLine(HTTPException):
  def __init__(self,line):
    if line:
      line = repr(line)

    self.args = (line,)
    self.line = line

class LineTooLong(HTTPException):
  def __init__(self,line_type):
    HTTPException.__init__(self,'got more than %d bytes when reading %s'%(_MAXLINE,line_type))

class RemoteDisconnected(ConnectionResetError,BadStatusLine):
  def __init__(self):
    BadStatusLine.__init__(self,'')
    kw

error = HTTPException