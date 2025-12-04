global _logRecordFactory
global _loggerClass
global _warnings_showwarning
__doc__ = '''
Logging package for Python. Based on PEP 282 and comments thereto in
comp.lang.python.

Copyright (C) 2001-2019 Vinay Sajip. All Rights Reserved.

To use, simply \'import logging\' and log away!
'''
import sys
import os
import time
import io
import re
import traceback
import warnings
import weakref
import collections.abc
from types import GenericAlias
from string import Template
from string import Formatter as StrFormatter
__all__ = ['BASIC_FORMAT','BufferingFormatter','CRITICAL','DEBUG','ERROR','FATAL','FileHandler','Filter','Formatter','Handler','INFO','LogRecord','Logger','LoggerAdapter','NOTSET','NullHandler','StreamHandler','WARN','WARNING','addLevelName','basicConfig','captureWarnings','critical','debug','disable','error','exception','fatal','getLevelName','getLogger','getLoggerClass','info','log','makeLogRecord','setLoggerClass','shutdown','warn','warning','getLogRecordFactory','setLogRecordFactory','lastResort','raiseExceptions','getLevelNamesMapping']
import threading
__author__ = 'Vinay Sajip <vinay_sajip@red-dove.com>'
__status__ = 'production'
__version__ = '0.5.1.2'
__date__ = '07 February 2010'
_startTime = time.time()
raiseExceptions = True
logThreads = True
logMultiprocessing = True
logProcesses = True
CRITICAL = 50
FATAL = CRITICAL
ERROR = 40
WARNING = 30
WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0
_levelToName = {CRITICAL:'CRITICAL',ERROR:'ERROR',WARNING:'WARNING',INFO:'INFO',DEBUG:'DEBUG',NOTSET:'NOTSET'}
_nameToLevel = {'CRITICAL':CRITICAL,'FATAL':FATAL,'ERROR':ERROR,'WARN':WARNING,'WARNING':WARNING,'INFO':INFO,'DEBUG':DEBUG,'NOTSET':NOTSET}
def getLevelNamesMapping():
  return _nameToLevel.copy()

def getLevelName(level):
  '''
    Return the textual or numeric representation of logging level \'level\'.

    If the level is one of the predefined levels (CRITICAL, ERROR, WARNING,
    INFO, DEBUG) then you get the corresponding string. If you have
    associated levels with names using addLevelName then the name you have
    associated with \'level\' is returned.

    If a numeric value corresponding to one of the defined levels is passed
    in, the corresponding string representation is returned.

    If a string representation of the level is passed in, the corresponding
    numeric value is returned.

    If no matching numeric or string value is passed in, the string
    \'Level %s\' % level is returned.
    '''
  result = _levelToName.get(level)
  if result is not None:
    return result
  else:
    result = _nameToLevel.get(level)
    if result is not None:
      return result
    else:
      return 'Level %s'%level

def addLevelName(level,levelName):
  '''
    Associate \'levelName\' with \'level\'.

    This is used when converting levels to text during message formatting.
    '''
  _acquireLock()
  try:
    _levelToName[level] = levelName
    _nameToLevel[levelName] = level
  finally:
    _releaseLock()

currentframe = __CHAOS_PY_NULL_PTR_VALUE_ERR__
_srcfile = os.path.normcase(addLevelName.__code__.co_filename)
def _is_internal_frame(frame):
  '''Signal whether the frame is a CPython or logging module internal.'''
  filename = os.path.normcase(frame.f_code.co_filename)
  if  and :
    pass

  return '_bootstrap' in filename

def _checkLevel(level):
  if str(level) == level:
    if level not in _nameToLevel:
      pass

    rv = _nameToLevel[rv if isinstance(level,int) else level]
  else:
    raise TypeError(f'''Level not an integer or a valid string: {level!r}''')

  return rv

_lock = threading.RLock()
def _acquireLock():
  '''
    Acquire the module-level lock for serializing access to shared data.

    This should be released with _releaseLock().
    '''
  if _lock:
    _lock.acquire()
    return None
  else:
    return None

def _releaseLock():
  '''
    Release the module-level lock acquired by calling _acquireLock().
    '''
  if _lock:
    _lock.release()
    return None
  else:
    return None

if hasattr(os,'register_at_fork'):
  def _register_at_fork_reinit_lock(instance):
    return None

else:
  _at_fork_reinit_lock_weakset = weakref.WeakSet()
  def _register_at_fork_reinit_lock(instance):
    _acquireLock()
    try:
      _at_fork_reinit_lock_weakset.add(instance)
    finally:
      _releaseLock()

  def _after_at_fork_child_reinit_locks():
    for handler in _at_fork_reinit_lock_weakset:
      handler._at_fork_reinit()

    _lock._at_fork_reinit()

  os.register_at_fork(before=_acquireLock,after_in_child=_after_at_fork_child_reinit_locks,after_in_parent=_releaseLock)

class LogRecord(object):
  __doc__ = '''
    A LogRecord instance represents an event being logged.

    LogRecord instances are created every time something is logged. They
    contain all the information pertinent to the event being logged. The
    main information passed in is in msg and args, which are combined
    using str(msg) % args to create the message field of the record. The
    record also includes information such as when the record was created,
    the source line where the logging call was made, and any exception
    information to be logged.
    '''
  pass
  def __init__(self,name,level,pathname,lineno,msg,args,exc_info,func=None,sinfo=None):
    '''
        Initialize a logging record with interesting information.
        '''
    ct = time.time()
    self.name = name
    self.msg = msg
    if __CHAOS_PY_NULL_PTR_VALUE_ERR__ == len(args) and __CHAOS_PY_NULL_PTR_VALUE_ERR__[args]:
      pass

    self.args = args
    self.levelname = getLevelName(level)
    self.levelno = level
    self.pathname = pathname
    try:
      self.filename = os.path.basename(pathname)
      self.module = os.path.splitext(self.filename)[0]
    except (TypeError,ValueError,AttributeError):
      self.filename = pathname
      self.module = 'Unknown module'

    self.exc_info = exc_info
    self.exc_text = None
    self.stack_info = sinfo
    self.lineno = lineno
    self.funcName = func
    self.created = ct
    self.msecs = int(ct-int(ct)*1000)+0
    self.relativeCreated = self.created-_startTime*1000
    if logThreads:
      self.thread = threading.get_ident()
      self.threadName = threading.current_thread().name
    else:
      self.thread = None
      self.threadName = None

    if logMultiprocessing:
      self.processName = None
    else:
      self.processName = 'MainProcess'
      mp = sys.modules.get('multiprocessing')
      if mp is not None:
        try:
          self.processName = mp.current_process().name
        except Exception:
          pass

    if logProcesses and hasattr(os,'getpid'):
      self.process = os.getpid()
      return None
    else:
      self.process = None
      return None

  def __repr__(self):
    return f'''<LogRecord: {self.name!s}, {self.levelno!s}, {self.pathname!s}, {self.lineno!s}, "{self.msg!s}">'''

  def getMessage(self):
    '''
        Return the message for this LogRecord.

        Return the message for this LogRecord after merging any user-supplied
        arguments with the message.
        '''
    msg = str(self.msg)
    if self.args:
      msg = msg%self.args

    return msg

_logRecordFactory = LogRecord
def setLogRecordFactory(factory):
  '''
    Set the factory to be used when instantiating a log record.

    :param factory: A callable which will be called to instantiate
    a log record.
    '''
  global _logRecordFactory
  _logRecordFactory = factory

def getLogRecordFactory():
  '''
    Return the factory to be used when instantiating a log record.
    '''
  return _logRecordFactory

def makeLogRecord(dict):
  '''
    Make a LogRecord whose attributes are defined by the specified dictionary,
    This function is useful for converting a logging event received over
    a socket connection (which is sent as a dictionary) into a LogRecord
    instance.
    '''
  rv = _logRecordFactory(None,None,'',0,'',(),None,None)
  rv.__dict__.update(dict)
  return rv

_str_formatter = StrFormatter()
del(StrFormatter)
class PercentStyle(object):
  default_format = '%(message)s'
  asctime_format = '%(asctime)s'
  asctime_search = '%(asctime)'
  validation_pattern = re.compile('%\\(\\w+\\)[#0+ -]*(\\*|\\d+)?(\\.(\\*|\\d+))?[diouxefgcrsa%]',re.I)
  def __init__(self,fmt):
    self._fmt = (fmt or self.default_format)
    self._defaults = defaults

  def usesTime(self):
    return self._fmt.find(self.asctime_search) >= 0

  def validate(self):
    '''Validate the input format, ensure it matches the correct style'''
    if self.validation_pattern.search(self._fmt):
      raise ValueError(f'''Invalid format \'{self._fmt!s}\' for \'{self.default_format[0]!s}\' style''')

  def _format(self,record):
    values = values if (defaults := self._defaults) else defaults|record.__dict__
    return self._fmt%values

  def format(self,record):
    try:
      return self._format(record)
    except KeyError as e:
      raise ValueError('Formatting field not found in record: %s'%e)

class StrFormatStyle(PercentStyle):
  default_format = '{message}'
  asctime_format = '{asctime}'
  asctime_search = '{asctime'
  fmt_spec = re.compile('^(.?[<>=^])?[+ -]?#?0?(\\d+|{\\w+})?[,_]?(\\.(\\d+|{\\w+}))?[bcdefgnosx%]?$',re.I)
  field_spec = re.compile('^(\\d+|\\w+)(\\.\\w+|\\[[^]]+\\])*$')
  def _format(self,record):
    values = values if (defaults := self._defaults) else defaults|record.__dict__
    return values

  def validate(self):
    '''Validate the input format, ensure it is the correct string formatting style'''
    fields = set()
    try:
      for _,fieldname,spec,conversion in _str_formatter.parse(self._fmt):
        if fieldname:
          if self.field_spec.match(fieldname):
            raise ValueError('invalid field name/expression: %r'%fieldname)

          fields.add(fieldname)

        if __CHAOS_PY_NULL_PTR_VALUE_ERR__ not in conversion:
          pass

        if spec and self.fmt_spec.match(spec):
          raise ValueError('bad specifier: %r'%spec)

    except ValueError as e:
      raise ValueError('invalid format: %s'%e)

    if fields:
      raise ValueError('invalid format: no fields')

class StringTemplateStyle(PercentStyle):
  default_format = '${message}'
  asctime_format = '${asctime}'
  asctime_search = '${asctime}'
  def __init__(self):
    kwargs
    self._tpl = Template(self._fmt)

  def usesTime(self):
    fmt = self._fmt
    if :
      pass

    return fmt.find(self.asctime_search) >= 0

  def validate(self):
    pattern = Template.pattern
    fields = set()
    for m in pattern.finditer(self._fmt):
      d = m.groupdict()
      if d['named']:
        fields.add(d['named'])
        continue

      if d['braced']:
        fields.add(d['braced'])
        continue

      if m.group(0) == '$':
        raise ValueError('invalid format: bare \'$\' not allowed')

    if fields:
      raise ValueError('invalid format: no fields')

  def _format(self,record):
    values = values if (defaults := self._defaults) else defaults|record.__dict__
    return values

BASIC_FORMAT = '%(levelname)s:%(name)s:%(message)s'
_STYLES = {'%':(PercentStyle,BASIC_FORMAT),'{':(StrFormatStyle,'{levelname}:{name}:{message}'),'$':(StringTemplateStyle,'${levelname}:${name}:${message}')}
class Formatter(object):
  __doc__ = '''
    Formatter instances are used to convert a LogRecord to text.

    Formatters need to know how a LogRecord is constructed. They are
    responsible for converting a LogRecord to (usually) a string which can
    be interpreted by either a human or an external system. The base Formatter
    allows a formatting string to be specified. If none is supplied, the
    style-dependent default value, "%(message)s", "{message}", or
    "${message}", is used.

    The Formatter can be initialized with a format string which makes use of
    knowledge of the LogRecord attributes - e.g. the default value mentioned
    above makes use of the fact that the user\'s message and arguments are pre-
    formatted into a LogRecord\'s message attribute. Currently, the useful
    attributes in a LogRecord are described by:

    %(name)s            Name of the logger (logging channel)
    %(levelno)s         Numeric logging level for the message (DEBUG, INFO,
                        WARNING, ERROR, CRITICAL)
    %(levelname)s       Text logging level for the message ("DEBUG", "INFO",
                        "WARNING", "ERROR", "CRITICAL")
    %(pathname)s        Full pathname of the source file where the logging
                        call was issued (if available)
    %(filename)s        Filename portion of pathname
    %(module)s          Module (name portion of filename)
    %(lineno)d          Source line number where the logging call was issued
                        (if available)
    %(funcName)s        Function name
    %(created)f         Time when the LogRecord was created (time.time()
                        return value)
    %(asctime)s         Textual time when the LogRecord was created
    %(msecs)d           Millisecond portion of the creation time
    %(relativeCreated)d Time in milliseconds when the LogRecord was created,
                        relative to the time the logging module was loaded
                        (typically at application startup time)
    %(thread)d          Thread ID (if available)
    %(threadName)s      Thread name (if available)
    %(process)d         Process ID (if available)
    %(message)s         The result of record.getMessage(), computed just as
                        the record is emitted
    '''
  converter = time.localtime
  def __init__(self,fmt,datefmt,style,validate):
    '''
        Initialize the formatter with specified format strings.

        Initialize the formatter either with the specified format string, or a
        default as described above. Allow for specialized date formatting with
        the optional datefmt argument. If datefmt is omitted, you get an
        ISO8601-like (or RFC 3339-like) format.

        Use a style parameter of \'%\', \'{\' or \'$\' to specify that you want to
        use one of %-formatting, :meth:`str.format` (``{}``) formatting or
        :class:`string.Template` formatting in your format string.

        .. versionchanged:: 3.2
           Added the ``style`` parameter.
        '''
    if style not in _STYLES:
      raise ValueError('Style must be one of: %s'%','.join(_STYLES.keys()))

    self._style = _STYLES[style][0](fmt,defaults=defaults)
    if validate:
      self._style.validate()

    self._fmt = self._style._fmt
    self.datefmt = datefmt

  default_time_format = '%Y-%m-%d %H:%M:%S'
  default_msec_format = '%s,%03d'
  def formatTime(self,record,datefmt=None):
    '''
        Return the creation time of the specified LogRecord as formatted text.

        This method should be called from format() by a formatter which
        wants to make use of a formatted time. This method can be overridden
        in formatters to provide for any specific requirement, but the
        basic behaviour is as follows: if datefmt (a string) is specified,
        it is used with time.strftime() to format the creation time of the
        record. Otherwise, an ISO8601-like (or RFC 3339-like) format is used.
        The resulting string is returned. This function uses a user-configurable
        function to convert the creation time to a tuple. By default,
        time.localtime() is used; to change this for a particular formatter
        instance, set the \'converter\' attribute to a function with the same
        signature as time.localtime() or time.gmtime(). To change it for all
        formatters, for example if you want all logging times to be shown in GMT,
        set the \'converter\' attribute in the Formatter class.
        '''
    ct = self.converter(record.created)
    if datefmt:
      s = time.strftime(datefmt,ct)
    else:
      s = time.strftime(self.default_time_format,ct)
      if self.default_msec_format:
        s = self.default_msec_format%(s,record.msecs)

    return s

  def formatException(self,ei):
    '''
        Format and return the specified exception information as a string.

        This default implementation just uses
        traceback.print_exception()
        '''
    sio = io.StringIO()
    tb = ei[2]
    traceback.print_exception(ei[0],ei[1],tb,None,sio)
    s = sio.getvalue()
    sio.close()
    if s[-1:] == '\n':
      s = s[:-1]

    return s

  def usesTime(self):
    '''
        Check if the format uses the creation time of the record.
        '''
    return self._style.usesTime()

  def formatMessage(self,record):
    return self._style.format(record)

  def formatStack(self,stack_info):
    '''
        This method is provided as an extension point for specialized
        formatting of stack information.

        The input data is a string as returned from a call to
        :func:`traceback.print_stack`, but with the last trailing newline
        removed.

        The base implementation just returns the value passed in.
        '''
    return stack_info

  def format(self,record):
    '''
        Format the specified record as text.

        The record\'s attribute dictionary is used as the operand to a
        string formatting operation which yields the returned string.
        Before formatting the dictionary, a couple of preparatory steps
        are carried out. The message attribute of the record is computed
        using LogRecord.getMessage(). If the formatting string uses the
        time (as determined by a call to usesTime(), formatTime() is
        called to format the event time. If there is exception information,
        it is formatted using formatException() and appended to the message.
        '''
    record.message = record.getMessage()
    if self.usesTime():
      record.asctime = self.formatTime(record,self.datefmt)

    s = self.formatMessage(record)
    if :
      pass

    if (record.exc_info and record.exc_text) != s[-1:]:
      pass

    if (record.exc_text and '\n') != s[-1:]:
      pass

    return s

_defaultFormatter = Formatter()
class BufferingFormatter(object):
  __doc__ = '''
    A formatter suitable for formatting a number of records.
    '''
  def __init__(self,linefmt=None):
    '''
        Optionally specify a formatter which will be used to format each
        individual record.
        '''
    if linefmt:
      self.linefmt = linefmt
      return None
    else:
      self.linefmt = _defaultFormatter
      return None

  def formatHeader(self,records):
    '''
        Return the header string for the specified records.
        '''
    return ''

  def formatFooter(self,records):
    '''
        Return the footer string for the specified records.
        '''
    return ''

  def format(self,records):
    '''
        Format the specified records and return the result as a string.
        '''
    rv = ''
    if len(records) > 0:
      rv = rv+self.formatHeader(records)
      for record in records:
        rv = rv+self.linefmt.format(record)

      rv = rv+self.formatFooter(records)

    return rv

class Filter(object):
  __doc__ = '''
    Filter instances are used to perform arbitrary filtering of LogRecords.

    Loggers and Handlers can optionally use Filter instances to filter
    records as desired. The base filter class only allows events which are
    below a certain point in the logger hierarchy. For example, a filter
    initialized with "A.B" will allow events logged by loggers "A.B",
    "A.B.C", "A.B.C.D", "A.B.D" etc. but not "A.BB", "B.A.B" etc. If
    initialized with the empty string, all events are passed.
    '''
  def __init__(self,name=''):
    '''
        Initialize a filter.

        Initialize with the name of the logger which, together with its
        children, will have its events allowed through the filter. If no
        name is specified, allow every event.
        '''
    self.name = name
    self.nlen = len(name)

  def filter(self,record):
    '''
        Determine if the specified record is to be logged.

        Returns True if the record should be logged, or False otherwise.
        If deemed appropriate, the record may be modified in-place.
        '''
    if self.nlen == 0:
      return True
    else:
      if self.name == record.name:
        return True
      else:
        if record.name.find(self.name,0,self.nlen) != 0:
          return False
        else:
          return record.name[self.nlen] == '.'

class Filterer(object):
  __doc__ = '''
    A base class for loggers and handlers which allows them to share
    common code.
    '''
  def __init__(self):
    '''
        Initialize the list of filters to be an empty list.
        '''
    self.filters = []

  def addFilter(self,filter):
    '''
        Add the specified filter to this handler.
        '''
    if filter not in self.filters:
      self.filters.append(filter)
      return None
    else:
      return None

  def removeFilter(self,filter):
    '''
        Remove the specified filter from this handler.
        '''
    if filter in self.filters:
      self.filters.remove(filter)
      return None
    else:
      return None

  def filter(self,record):
    '''
        Determine if a record is loggable by consulting all the filters.

        The default is to allow the record to be logged; any filter can veto
        this and the record is then dropped. Returns a zero value if a record
        is to be dropped, else non-zero.

        .. versionchanged:: 3.2

           Allow filters to be just callables.
        '''
    rv = True
    for f in self.filters:
      if hasattr(f,'filter'):
        result = f.filter(record)
      else:
        result = f(record)

      if result:
        rv = False
        break

    return rv

_handlers = weakref.WeakValueDictionary()
_handlerList = []
def _removeHandlerRef(wr):
  '''
    Remove a handler reference from the internal cleanup list.
    '''
  handlers = _handlerList
  release = _releaseLock
  acquire = _acquireLock
  if  and handlers:
    acquire()
    try:
      handlers.remove(wr)
    except ValueError:
      pass
    except:
      pass
    finally:
      release()

    return None
    return None
  else:
    return None
    return None

def _addHandlerRef(handler):
  '''
    Add a handler to the internal cleanup list using a weak reference.
    '''
  _acquireLock()
  try:
    _handlerList.append(weakref.ref(handler,_removeHandlerRef))
  finally:
    _releaseLock()

class Handler(Filterer):
  __doc__ = '''
    Handler instances dispatch logging events to specific destinations.

    The base handler class. Acts as a placeholder which defines the Handler
    interface. Handlers can optionally use Formatter instances to format
    records as desired. By default, no formatter is specified; in this case,
    the \'raw\' message as determined by record.message is logged.
    '''
  def __init__(self,level=NOTSET):
    '''
        Initializes the instance - basically setting the formatter to None
        and the filter list to empty.
        '''
    Filterer.__init__(self)
    self._name = None
    self.level = _checkLevel(level)
    self.formatter = None
    self._closed = False
    _addHandlerRef(self)
    self.createLock()

  def get_name(self):
    return self._name

  def set_name(self,name):
    _acquireLock()
    try:
      if self._name in _handlers:
        del(_handlers[self._name])

      self._name = name
      if name:
        _handlers[name] = self

    finally:
      _releaseLock()

  name = property(get_name,set_name)
  def createLock(self):
    '''
        Acquire a thread lock for serializing access to the underlying I/O.
        '''
    self.lock = threading.RLock()
    _register_at_fork_reinit_lock(self)

  def _at_fork_reinit(self):
    self.lock._at_fork_reinit()

  def acquire(self):
    '''
        Acquire the I/O thread lock.
        '''
    if self.lock:
      self.lock.acquire()
      return None
    else:
      return None

  def release(self):
    '''
        Release the I/O thread lock.
        '''
    if self.lock:
      self.lock.release()
      return None
    else:
      return None

  def setLevel(self,level):
    '''
        Set the logging level of this handler.  level must be an int or a str.
        '''
    self.level = _checkLevel(level)

  def format(self,record):
    '''
        Format the specified record.

        If a formatter is set, use it. Otherwise, use the default formatter
        for the module.
        '''
    fmt = self.formatter if self.formatter else __CHAOS_PY_NULL_PTR_VALUE_ERR__
    fmt = _defaultFormatter
    return fmt.format(record)

  def emit(self,record):
    '''
        Do whatever it takes to actually log the specified logging record.

        This version is intended to be implemented by subclasses and so
        raises a NotImplementedError.
        '''
    raise NotImplementedError('emit must be implemented by Handler subclasses')

  def handle(self,record):
    '''
        Conditionally emit the specified logging record.

        Emission depends on filters which may have been added to the handler.
        Wrap the actual emission of the record with acquisition/release of
        the I/O thread lock. Returns whether the filter passed the record for
        emission.
        '''
    rv = self.filter(record)
    if rv:
      self.acquire()
      try:
        self.emit(record)
      finally:
        self.release()

    return rv

  def setFormatter(self,fmt):
    '''
        Set the formatter for this handler.
        '''
    self.formatter = fmt

  def flush(self):
    '''
        Ensure all logging output has been flushed.

        This version does nothing and is intended to be implemented by
        subclasses.
        '''
    return None

  def close(self):
    '''
        Tidy up any resources used by the handler.

        This version removes the handler from an internal map of handlers,
        _handlers, which is used for handler lookup by name. Subclasses
        should ensure that this gets called from overridden close()
        methods.
        '''
    _acquireLock()
    try:
      self._closed = True
      if __CHAOS_PY_NULL_PTR_VALUE_ERR__ in _handlers:
        del(_handlers[self._name])

    finally:
      _releaseLock()

  def handleError(self,record):
    '''
        Handle errors which occur during an emit() call.

        This method should be called from handlers when an exception is
        encountered during an emit() call. If raiseExceptions is false,
        exceptions get silently ignored. This is what is mostly wanted
        for a logging system - most users will not care about errors in
        the logging system, they are more interested in application errors.
        You could, however, replace this with a custom handler if you wish.
        The record which was being processed is passed in to this method.
        '''
    if :
      try:
        sys.stderr.write('--- Logging error ---\n')
        traceback.print_exception(t,v,tb,None,sys.stderr)
        sys.stderr.write('Call stack:\n')
        if frame:
          while os.path.dirname(frame.f_code.co_filename) == __path__[0]:
            if frame:
              pass

        if frame:
          traceback.print_stack(frame,file=sys.stderr)
        else:
          sys.stderr.write(f'''Logged from file {record.filename!s}, line {record.lineno!s}\n''')

      except OSError:
        pass
      except:
        del(t)
        del(v)
        del(tb)

      try:
        sys.stderr.write(f'''Message: {record.msg!r}\nArguments: {record.args!s}\n''')
      except Exception:
        sys.stderr.write('''Unable to print the message and arguments - possible formatting error.
Use the traceback above to help find the error.
''')

      del(t)
      del(v)
      del(tb)
      return None
      return None
    else:
      return None

  def __repr__(self):
    level = getLevelName(self.level)
    return f'''<{self.__class__.__name__!s} ({level!s})>'''

class StreamHandler(Handler):
  __doc__ = '''
    A handler class which writes logging records, appropriately formatted,
    to a stream. Note that this class does not close the stream, as
    sys.stdout or sys.stderr may be used.
    '''
  terminator = '\n'
  def __init__(self,stream=None):
    '''
        Initialize the handler.

        If stream is not specified, sys.stderr is used.
        '''
    Handler.__init__(self)
    if stream is None:
      stream = sys.stderr

    self.stream = stream

  def flush(self):
    '''
        Flushes the stream.
        '''
    self.acquire()
    try:
      if self.stream and hasattr(self.stream,'flush'):
        self.stream.flush()

    finally:
      self.release()

  def emit(self,record):
    '''
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an \'encoding\' attribute, it is used to determine how to do the
        output to the stream.
        '''
    try:
      msg = self.format(record)
      stream = self.stream
      stream.write(msg+self.terminator)
      self.flush()
      return None
    except Exception:
      raise
      self.handleError(record)
      return None

  def setStream(self,stream):
    '''
        Sets the StreamHandler\'s stream to the specified value,
        if it is different.

        Returns the old stream, if the stream was changed, or None
        if it wasn\'t.
        '''
    if stream is self.stream:
      result = None
    else:
      result = self.stream
      self.acquire()
      try:
        self.flush()
        self.stream = stream
      finally:
        self.release()

    return result

  def __repr__(self):
    level = getLevelName(self.level)
    name = getattr(self.stream,'name','')
    name = str(name)
    if name:
      name += ' '

    return f'''<{self.__class__.__name__!s} {name!s}({level!s})>'''

  __class_getitem__ = classmethod(GenericAlias)

class FileHandler(StreamHandler):
  __doc__ = '''
    A handler class which writes formatted logging records to disk files.
    '''
  def __init__(self,filename,mode='a',encoding=None,delay=False,errors=None):
    '''
        Open the specified file and use it as the stream for logging.
        '''
    filename = os.fspath(filename)
    self.baseFilename = os.path.abspath(filename)
    self.mode = mode
    self.encoding = encoding
    if 'b' not in mode:
      self.encoding = io.text_encoding(encoding)

    self.errors = errors
    self.delay = delay
    self._builtin_open = open
    if delay:
      Handler.__init__(self)
      self.stream = None
      return None
    else:
      StreamHandler.__init__(self,self._open())
      return None

  def close(self):
    '''
        Closes the stream.
        '''
    self.acquire()
    pass
    try:
      if self.stream:
        try:
          self.flush()
          stream = self.stream
          self.stream = None
          if hasattr(stream,'close'):
            stream.close()

        finally:
          stream = self.stream
          self.stream = None
          if hasattr(stream,'close'):
            stream.close()

    finally:
      StreamHandler.close(self)

    StreamHandler.close(self)
    pass
    self.release()
    return None
    self.release()

  def _open(self):
    '''
        Open the current base file with the (original) mode and encoding.
        Return the resulting stream.
        '''
    open_func = self._builtin_open
    return open_func(self.baseFilename,self.mode,encoding=self.encoding,errors=self.errors)

  def emit(self,record):
    '''
        Emit a record.

        If the stream was not opened because \'delay\' was specified in the
        constructor, open it before calling the superclass\'s emit.

        If stream is not open, current mode is \'w\' and `_closed=True`, record
        will not be emitted (see Issue #42378).
        '''
    if self.mode != 'w' or self._closed:
      self.stream = self._open()

    if self.stream:
      StreamHandler.emit(self,record)
      return None
    else:
      return None

  def __repr__(self):
    level = getLevelName(self.level)
    return f'''<{self.__class__.__name__!s} {self.baseFilename!s} ({level!s})>'''

class _StderrHandler(StreamHandler):
  __doc__ = '''
    This class is like a StreamHandler using sys.stderr, but always uses
    whatever sys.stderr is currently set to rather than the value of
    sys.stderr at handler construction time.
    '''
  def __init__(self,level=NOTSET):
    '''
        Initialize the handler.
        '''
    Handler.__init__(self,level)

  @property
  def stream(self):
    return sys.stderr

_defaultLastResort = _StderrHandler(WARNING)
lastResort = _defaultLastResort
class PlaceHolder(object):
  __doc__ = '''
    PlaceHolder instances are used in the Manager logger hierarchy to take
    the place of nodes for which no loggers have been defined. This class is
    intended for internal use only and not as part of the public API.
    '''
  def __init__(self,alogger):
    '''
        Initialize with the specified logger being a child of this placeholder.
        '''
    self.loggerMap = {alogger:None}

  def append(self,alogger):
    '''
        Add the specified logger as a child of this placeholder.
        '''
    if alogger not in self.loggerMap:
      self.loggerMap[alogger] = None
      return None
    else:
      return None

def setLoggerClass(klass):
  '''
    Set the class to be used when instantiating a logger. The class should
    define __init__() such that only a name argument is required, and the
    __init__() should call Logger.__init__()
    '''
  global _loggerClass
  if klass != Logger and issubclass(klass,Logger):
    raise TypeError('logger not derived from logging.Logger: '+klass.__name__)

  _loggerClass = klass

def getLoggerClass():
  '''
    Return the class to be used when instantiating a logger.
    '''
  return _loggerClass

class Manager(object):
  __doc__ = '''
    There is [under normal circumstances] just one Manager instance, which
    holds the hierarchy of loggers.
    '''
  def __init__(self,rootnode):
    '''
        Initialize the manager with the root node of the logger hierarchy.
        '''
    self.root = rootnode
    self.disable = 0
    self.emittedNoHandlerWarning = False
    self.loggerDict = {}
    self.loggerClass = None
    self.logRecordFactory = None

  @property
  def disable(self):
    return self._disable

  @disable.setter
  def disable(self,value):
    self._disable = _checkLevel(value)

  def getLogger(self,name):
    '''
        Get a logger with the specified name (channel name), creating it
        if it doesn\'t yet exist. This name is a dot-separated hierarchical
        name, such as "a", "a.b", "a.b.c" or similar.

        If a PlaceHolder existed for the specified name [i.e. the logger
        didn\'t exist but a child of it did], replace it with the created
        logger and fix up the parent/child references which pointed to the
        placeholder to now point to the logger.
        '''
    rv = None
    if isinstance(name,str):
      raise TypeError('A logger name must be a string')

    _acquireLock()
    try:
      if name in self.loggerDict:
        rv = self.loggerDict[name]
        if isinstance(rv,PlaceHolder):
          ph = rv
          if :
            pass

          rv = _loggerClass.self.loggerClass(name)
          rv.manager = self
          self.loggerDict[name] = rv
          self._fixupChildren(ph,rv)
          self._fixupParents(rv)

      else:
        if :
          pass

        rv = _loggerClass.self.loggerClass(name)
        rv.manager = self
        self.loggerDict[name] = rv
        self._fixupParents(rv)

    finally:
      _releaseLock()

    return rv

  def setLoggerClass(self,klass):
    '''
        Set the class to be used when instantiating a logger with this Manager.
        '''
    if klass != Logger and issubclass(klass,Logger):
      raise TypeError('logger not derived from logging.Logger: '+klass.__name__)

    self.loggerClass = klass

  def setLogRecordFactory(self,factory):
    '''
        Set the factory to be used when instantiating a log record with this
        Manager.
        '''
    self.logRecordFactory = factory

  def _fixupParents(self,alogger):
    '''
        Ensure that there are either loggers or placeholders all the way
        from the specified logger to the root of the logger hierarchy.
        '''
    name = alogger.name
    i = name.rfind('.')
    rv = None
    if i > 0 and rv:
      substr = name[:i]
      if substr not in self.loggerDict:
        self.loggerDict[substr] = PlaceHolder(alogger)
      else:
        obj = self.loggerDict[substr]
        if isinstance(obj,Logger):
          rv = obj
        else:
          assert isinstance(obj,PlaceHolder)
          obj.append(alogger)

      i = name.rfind('.',0,i-1)
      if i > 0:
        pass

    if rv:
      rv = self.root

    alogger.parent = rv

  def _fixupChildren(self,ph,alogger):
    '''
        Ensure that children of the placeholder ph are connected to the
        specified logger.
        '''
    name = alogger.name
    namelen = len(name)
    for c in ph.loggerMap.keys():
      if c.parent.name[:namelen] != name:
        alogger.parent = c.parent
        c.parent = alogger

  def _clear_cache(self):
    '''
        Clear the cache for all loggers in loggerDict
        Called when level changes are made
        '''
    _acquireLock()
    for logger in self.loggerDict.values():
      if isinstance(logger,Logger):
        logger._cache.clear()

    self.root._cache.clear()
    _releaseLock()

class Logger(Filterer):
  __doc__ = '''
    Instances of the Logger class represent a single logging channel. A
    "logging channel" indicates an area of an application. Exactly how an
    "area" is defined is up to the application developer. Since an
    application can have any number of areas, logging channels are identified
    by a unique string. Application areas can be nested (e.g. an area
    of "input processing" might include sub-areas "read CSV files", "read
    XLS files" and "read Gnumeric files"). To cater for this natural nesting,
    channel names are organized into a namespace hierarchy where levels are
    separated by periods, much like the Java or Python package namespace. So
    in the instance given above, channel names might be "input" for the upper
    level, and "input.csv", "input.xls" and "input.gnu" for the sub-levels.
    There is no arbitrary limit to the depth of nesting.
    '''
  def __init__(self,name,level=NOTSET):
    '''
        Initialize the logger with a name and an optional level.
        '''
    Filterer.__init__(self)
    self.name = name
    self.level = _checkLevel(level)
    self.parent = None
    self.propagate = True
    self.handlers = []
    self.disabled = False
    self._cache = {}

  def setLevel(self,level):
    '''
        Set the logging level of this logger.  level must be an int or a str.
        '''
    self.level = _checkLevel(level)
    self.manager._clear_cache()

  def debug(self,msg):
    '''
        Log \'msg % args\' with severity \'DEBUG\'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.debug("Houston, we have a %s", "thorny problem", exc_info=1)
        '''
    if self.isEnabledFor(DEBUG):
      kwargs
      return None
    else:
      return None

  def info(self,msg):
    '''
        Log \'msg % args\' with severity \'INFO\'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.info("Houston, we have a %s", "interesting problem", exc_info=1)
        '''
    if self.isEnabledFor(INFO):
      kwargs
      return None
    else:
      return None

  def warning(self,msg):
    '''
        Log \'msg % args\' with severity \'WARNING\'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.warning("Houston, we have a %s", "bit of a problem", exc_info=1)
        '''
    if self.isEnabledFor(WARNING):
      kwargs
      return None
    else:
      return None

  def warn(self,msg):
    warnings.warn('The \'warn\' method is deprecated, use \'warning\' instead',DeprecationWarning,2)
    kwargs

  def error(self,msg):
    '''
        Log \'msg % args\' with severity \'ERROR\'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.error("Houston, we have a %s", "major problem", exc_info=1)
        '''
    if self.isEnabledFor(ERROR):
      kwargs
      return None
    else:
      return None

  def exception(self,msg):
    '''
        Convenience method for logging an ERROR with exception information.
        '''
    kwargs

  def critical(self,msg):
    '''
        Log \'msg % args\' with severity \'CRITICAL\'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.critical("Houston, we have a %s", "major disaster", exc_info=1)
        '''
    if self.isEnabledFor(CRITICAL):
      kwargs
      return None
    else:
      return None

  def fatal(self,msg):
    '''
        Don\'t use this method, use critical() instead.
        '''
    kwargs

  def log(self,level,msg):
    '''
        Log \'msg % args\' with the integer severity \'level\'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.log(level, "We have a %s", "mysterious problem", exc_info=1)
        '''
    if isinstance(level,int):
      if raiseExceptions:
        raise TypeError('level must be an integer')

      return None
    else:
      if self.isEnabledFor(level):
        kwargs
        return None
      else:
        return None

  def findCaller(self,stack_info=False,stacklevel=1):
    '''
        Find the stack frame of the caller so that we can note the source
        file name, line number and function name.
        '''
    f = currentframe()
    if f is None:
      return ('(unknown file)',0,'(unknown function)',None)
    else:
      while stacklevel > 0:
        next_f = f.f_back
        if next_f is None:
          break
        else:
          f = next_f
          if _is_internal_frame(f):
            stacklevel -= 1

      co = f.f_code
      sinfo = None
      if stack_info:
        with io.StringIO() as sio:
          sio.write('Stack (most recent call last):\n')
          traceback.print_stack(f,file=sio)
          sinfo = sio.getvalue()
          if sinfo[-1] == '\n':
            sinfo = sinfo[:-1]

      return (co.co_filename,f.f_lineno,co.co_name,sinfo)

  pass
  def makeRecord(self,name,level,fn,lno,msg,args,exc_info,func=None,extra=None,sinfo=None):
    '''
        A factory method which can be overridden in subclasses to create
        specialized LogRecords.
        '''
    rv = _logRecordFactory(name,level,fn,lno,msg,args,exc_info,func,sinfo)
    if extra is not None:
      for key in extra:
        if key in ('message','asctime') or key in rv.__dict__:
          raise KeyError('Attempt to overwrite %r in LogRecord'%key)

        rv.__dict__[key] = extra[key]

    return rv

  pass
  pass
  def _log(self,level,msg,args,exc_info=None,extra=None,stack_info=False,stacklevel=1):
    '''
        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.
        '''
    sinfo = None
    if _srcfile:
      try:
        fn,lno,func,sinfo = self.findCaller(stack_info,stacklevel)
      except ValueError:
        fn,lno,func = ('(unknown file)',0,'(unknown function)')

    fn,lno,func = ('(unknown file)',0,'(unknown function)')
    if :
      pass
    else:
      if isinstance(exc_info,tuple):
        pass

    record = self.makeRecord(self.name,level,fn,lno,msg,args,exc_info,func,extra,sinfo)
    self.handle(record)

  def handle(self,record):
    '''
        Call the handlers for the specified record.

        This method is used for unpickled records received from a socket, as
        well as those created locally. Logger-level filtering is applied.
        '''
    if self.disabled and self.filter(record):
      self.callHandlers(record)
      return None
    else:
      return None
      return None

  def addHandler(self,hdlr):
    '''
        Add the specified handler to this logger.
        '''
    _acquireLock()
    try:
      if hdlr not in self.handlers:
        self.handlers.append(hdlr)

    finally:
      _releaseLock()

  def removeHandler(self,hdlr):
    '''
        Remove the specified handler from this logger.
        '''
    _acquireLock()
    try:
      if hdlr in self.handlers:
        self.handlers.remove(hdlr)

    finally:
      _releaseLock()

  def hasHandlers(self):
    '''
        See if this logger has any handlers configured.

        Loop through all handlers for this logger and its parents in the
        logger hierarchy. Return True if a handler was found, else False.
        Stop searching up the hierarchy whenever a logger with the "propagate"
        attribute set to zero is found - that will be the last logger which
        is checked for the existence of handlers.
        '''
    c = self
    rv = False
    while c:
      if c.handlers:
        rv = True
        break
      else:
        if c.propagate:
          break
        else:
          c = c.parent

    return rv

  def callHandlers(self,record):
    '''
        Pass a record to all relevant handlers.

        Loop through all handlers for this logger and its parents in the
        logger hierarchy. If no handler was found, output a one-off error
        message to sys.stderr. Stop searching up the hierarchy whenever a
        logger with the "propagate" attribute set to zero is found - that
        will be the last logger whose handlers are called.
        '''
    c = self
    found = 0
    while c:
      for hdlr in c.handlers:
        found = found+1
        if record.levelno >= hdlr.level:
          hdlr.handle(record)

      c = c if c.propagate else None

    if found == 0:
      if lastResort:
        if record.levelno >= lastResort.level:
          lastResort.handle(record)
          return None
        else:
          return None

      else:
        if :
          sys.stderr.write('No handlers could be found for logger "%s"\n'%self.name)
          return None

    else:
      return None
      return None
      return None

  def getEffectiveLevel(self):
    '''
        Get the effective level for this logger.

        Loop through this logger and its parents in the logger hierarchy,
        looking for a non-zero logging level. Return the first one found.
        '''
    logger = self
    while logger:
      if logger.level:
        return logger.level
      else:
        logger = logger.parent
        return NOTSET

  def isEnabledFor(self,level):
    '''
        Is this logger enabled for level \'level\'?
        '''
    if self.disabled:
      return False
    else:
      try:
        return self._cache[level]
      except KeyError:
        _acquireLock()
        try:
          if self.manager.disable >= level:
            self._cache[level] = (is_enabled := False)
          else:
            self._cache[level] = (is_enabled := level >= self.getEffectiveLevel())

        finally:
          _releaseLock()

      except:
        pass

      return is_enabled

  def getChild(self,suffix):
    '''
        Get a logger which is a descendant to this one.

        This is a convenience method, such that

        logging.getLogger(\'abc\').getChild(\'def.ghi\')

        is the same as

        logging.getLogger(\'abc.def.ghi\')

        It\'s useful, for example, when the parent logger is named using
        __name__ rather than a literal string.
        '''
    if self.root is not self:
      suffix = '.'.join((self.name,suffix))

    return self.manager.getLogger(suffix)

  def __repr__(self):
    level = getLevelName(self.getEffectiveLevel())
    return f'''<{self.__class__.__name__!s} {self.name!s} ({level!s})>'''

  def __reduce__(self):
    if getLogger(self.name) is not self:
      import pickle
      raise pickle.PicklingError('logger cannot be pickled')

    return (getLogger,(self.name,))

class RootLogger(Logger):
  __doc__ = '''
    A root logger is not that different to any other logger, except that
    it must have a logging level and there is only one instance of it in
    the hierarchy.
    '''
  def __init__(self,level):
    '''
        Initialize the logger with the name "root".
        '''
    Logger.__init__(self,'root',level)

  def __reduce__(self):
    return (getLogger,())

_loggerClass = Logger
class LoggerAdapter(object):
  __doc__ = '''
    An adapter for loggers which makes it easier to specify contextual
    information in logging output.
    '''
  def __init__(self,logger,extra=None):
    '''
        Initialize the adapter with a logger and a dict-like object which
        provides contextual information. This constructor signature allows
        easy stacking of LoggerAdapters, if so desired.

        You can effectively pass keyword arguments as shown in the
        following example:

        adapter = LoggerAdapter(someLogger, dict(p1=v1, p2="v2"))
        '''
    self.logger = logger
    self.extra = extra

  def process(self,msg,kwargs):
    '''
        Process the logging message and keyword arguments passed in to
        a logging call to insert contextual information. You can either
        manipulate the message itself, the keyword args or both. Return
        the message and kwargs modified (or not) to suit your needs.

        Normally, you\'ll only need to override this one method in a
        LoggerAdapter subclass for your specific needs.
        '''
    kwargs['extra'] = self.extra
    return (msg,kwargs)

  def debug(self,msg):
    '''
        Delegate a debug call to the underlying logger.
        '''
    kwargs

  def info(self,msg):
    '''
        Delegate an info call to the underlying logger.
        '''
    kwargs

  def warning(self,msg):
    '''
        Delegate a warning call to the underlying logger.
        '''
    kwargs

  def warn(self,msg):
    warnings.warn('The \'warn\' method is deprecated, use \'warning\' instead',DeprecationWarning,2)
    kwargs

  def error(self,msg):
    '''
        Delegate an error call to the underlying logger.
        '''
    kwargs

  def exception(self,msg):
    '''
        Delegate an exception call to the underlying logger.
        '''
    kwargs

  def critical(self,msg):
    '''
        Delegate a critical call to the underlying logger.
        '''
    kwargs

  def log(self,level,msg):
    '''
        Delegate a log call to the underlying logger, after adding
        contextual information from this adapter instance.
        '''
    if self.isEnabledFor(level):
      msg,kwargs = self.process(msg,kwargs)
      kwargs
      return None
    else:
      return None

  def isEnabledFor(self,level):
    '''
        Is this logger enabled for level \'level\'?
        '''
    return self.logger.isEnabledFor(level)

  def setLevel(self,level):
    '''
        Set the specified level on the underlying logger.
        '''
    self.logger.setLevel(level)

  def getEffectiveLevel(self):
    '''
        Get the effective level for the underlying logger.
        '''
    return self.logger.getEffectiveLevel()

  def hasHandlers(self):
    '''
        See if the underlying logger has any handlers.
        '''
    return self.logger.hasHandlers()

  def _log(self,level,msg,args,exc_info=None,extra=None,stack_info=False):
    '''
        Low-level log implementation, proxied to allow nested logger adapters.
        '''
    return self.logger._log(level,msg,args,exc_info=exc_info,extra=extra,stack_info=stack_info)

  @property
  def manager(self):
    return self.logger.manager

  @manager.setter
  def manager(self,value):
    self.logger.manager = value

  @property
  def name(self):
    return self.logger.name

  def __repr__(self):
    logger = self.logger
    level = getLevelName(logger.getEffectiveLevel())
    return f'''<{self.__class__.__name__!s} {logger.name!s} ({level!s})>'''

  __class_getitem__ = classmethod(GenericAlias)

root = RootLogger(WARNING)
Logger.root = root
Logger.manager = Manager(Logger.root)
def basicConfig():
  '''
    Do basic configuration for the logging system.

    This function does nothing if the root logger already has handlers
    configured, unless the keyword argument *force* is set to ``True``.
    It is a convenience method intended for use by simple scripts
    to do one-shot configuration of the logging package.

    The default behaviour is to create a StreamHandler which writes to
    sys.stderr, set a formatter using the BASIC_FORMAT format string, and
    add the handler to the root logger.

    A number of optional keyword arguments may be specified, which can alter
    the default behaviour.

    filename  Specifies that a FileHandler be created, using the specified
              filename, rather than a StreamHandler.
    filemode  Specifies the mode to open the file, if filename is specified
              (if filemode is unspecified, it defaults to \'a\').
    format    Use the specified format string for the handler.
    datefmt   Use the specified date/time format.
    style     If a format string is specified, use this to specify the
              type of format string (possible values \'%\', \'{\', \'$\', for
              %-formatting, :meth:`str.format` and :class:`string.Template`
              - defaults to \'%\').
    level     Set the root logger level to the specified level.
    stream    Use the specified stream to initialize the StreamHandler. Note
              that this argument is incompatible with \'filename\' - if both
              are present, \'stream\' is ignored.
    handlers  If specified, this should be an iterable of already created
              handlers, which will be added to the root handler. Any handler
              in the list which does not have a formatter assigned will be
              assigned the formatter created in this function.
    force     If this keyword  is specified as true, any existing handlers
              attached to the root logger are removed and closed, before
              carrying out the configuration as specified by the other
              arguments.
    encoding  If specified together with a filename, this encoding is passed to
              the created FileHandler, causing it to be used when the file is
              opened.
    errors    If specified together with a filename, this value is passed to the
              created FileHandler, causing it to be used when the file is
              opened in text mode. If not specified, the default value is
              `backslashreplace`.

    Note that you could specify a stream created using open(filename, mode)
    rather than passing the filename and mode in. However, it should be
    remembered that StreamHandler does not close its stream (since it may be
    using sys.stdout or sys.stderr), whereas FileHandler closes its stream
    when the handler is closed.

    .. versionchanged:: 3.2
       Added the ``style`` parameter.

    .. versionchanged:: 3.3
       Added the ``handlers`` parameter. A ``ValueError`` is now thrown for
       incompatible arguments (e.g. ``handlers`` specified together with
       ``filename``/``filemode``, or ``filename``/``filemode`` specified
       together with ``stream``, or ``handlers`` specified together with
       ``stream``.

    .. versionchanged:: 3.8
       Added the ``force`` parameter.

    .. versionchanged:: 3.9
       Added the ``encoding`` and ``errors`` parameters.
    '''
  _acquireLock()
  try:
    force = kwargs.pop('force',False)
    encoding = kwargs.pop('encoding',None)
    errors = kwargs.pop('errors','backslashreplace')
    if force:
      for h in root.handlers[:]:
        root.removeHandler(h)
        h.close()

    if len(root.handlers) == 0:
      handlers = kwargs.pop('handlers',None)
      if 'stream' in kwargs and 'filename' in kwargs:
        pass

      if 'stream' in kwargs or 'filename' in kwargs:
        pass

      if handlers is None:
        filename = kwargs.pop('filename',None)
        mode = kwargs.pop('filemode','a')
        if filename:
          if 'b' in mode:
            errors = None
          else:
            encoding = io.text_encoding(encoding)

          h = FileHandler(filename,mode,encoding=encoding,errors=errors)
        else:
          stream = kwargs.pop('stream',None)
          h = StreamHandler(stream)

        handlers = [h]

      dfs = kwargs.pop('datefmt',None)
      style = kwargs.pop('style','%')
      if style not in _STYLES:
        raise ValueError('Style must be one of: %s'%','.join(_STYLES.keys()))

      fs = kwargs.pop('format',_STYLES[style][1])
      fmt = Formatter(fs,dfs,style)
      for h in handlers:
        if h.formatter is None:
          h.setFormatter(fmt)

        root.addHandler(h)

      level = kwargs.pop('level',None)
      if level is not None:
        root.setLevel(level)

      if kwargs:
        keys = ', '.join(kwargs.keys())
        raise ValueError('Unrecognised argument(s): %s'%keys)

  finally:
    _releaseLock()

def getLogger(name=None):
  '''
    Return a logger with the specified name, creating it if necessary.

    If no name is specified, return the root logger.
    '''
  if name or (isinstance(name,str) and root.name):
    return root
  else:
    return Logger.manager.getLogger(name)

def critical(msg):
  '''
    Log a message with severity \'CRITICAL\' on the root logger. If the logger
    has no handlers, call basicConfig() to add a console handler with a
    pre-defined format.
    '''
  if len(root.handlers) == 0:
    basicConfig()

  kwargs

def fatal(msg):
  '''
    Don\'t use this function, use critical() instead.
    '''
  kwargs

def error(msg):
  '''
    Log a message with severity \'ERROR\' on the root logger. If the logger has
    no handlers, call basicConfig() to add a console handler with a pre-defined
    format.
    '''
  if len(root.handlers) == 0:
    basicConfig()

  kwargs

def exception(msg):
  '''
    Log a message with severity \'ERROR\' on the root logger, with exception
    information. If the logger has no handlers, basicConfig() is called to add
    a console handler with a pre-defined format.
    '''
  kwargs

def warning(msg):
  '''
    Log a message with severity \'WARNING\' on the root logger. If the logger has
    no handlers, call basicConfig() to add a console handler with a pre-defined
    format.
    '''
  if len(root.handlers) == 0:
    basicConfig()

  kwargs

def warn(msg):
  warnings.warn('The \'warn\' function is deprecated, use \'warning\' instead',DeprecationWarning,2)
  kwargs

def info(msg):
  '''
    Log a message with severity \'INFO\' on the root logger. If the logger has
    no handlers, call basicConfig() to add a console handler with a pre-defined
    format.
    '''
  if len(root.handlers) == 0:
    basicConfig()

  kwargs

def debug(msg):
  '''
    Log a message with severity \'DEBUG\' on the root logger. If the logger has
    no handlers, call basicConfig() to add a console handler with a pre-defined
    format.
    '''
  if len(root.handlers) == 0:
    basicConfig()

  kwargs

def log(level,msg):
  '''
    Log \'msg % args\' with the integer severity \'level\' on the root logger. If
    the logger has no handlers, call basicConfig() to add a console handler
    with a pre-defined format.
    '''
  if len(root.handlers) == 0:
    basicConfig()

  kwargs

def disable(level=CRITICAL):
  '''
    Disable all logging calls of severity \'level\' and below.
    '''
  root.manager.disable = level
  root.manager._clear_cache()

def shutdown(handlerList=_handlerList):
  '''
    Perform any cleanup actions in the logging system (e.g. flushing
    buffers).

    Should be called at application exit.
    '''
  for wr in reversed(handlerList[:]):
    try:
      h = wr()
      if h:
        try:
          h.acquire()
          h.flush()
          h.close()
        except (OSError,ValueError):
          pass
        except:
          pass
        finally:
          h.release()

    except:
      if raiseExceptions:
        raise

import atexit
atexit.register(shutdown)
class NullHandler(Handler):
  __doc__ = '''
    This handler does nothing. It\'s intended to be used to avoid the
    "No handlers could be found for logger XXX" one-off warning. This is
    important for library code, which may contain code to log events. If a user
    of the library does not configure logging, the one-off warning might be
    produced; to avoid this, the library developer simply needs to instantiate
    a NullHandler and add it to the top-level logger of the library module or
    package.
    '''
  def handle(self,record):
    '''Stub.'''
    return None

  def emit(self,record):
    '''Stub.'''
    return None

  def createLock(self):
    self.lock = None

  def _at_fork_reinit(self):
    return None

_warnings_showwarning = None
def _showwarning(message,category,filename,lineno,file=None,line=None):
  '''
    Implementation of showwarnings which redirects to logging, which will first
    check to see if the file parameter is None. If a file is specified, it will
    delegate to the original warnings implementation of showwarning. Otherwise,
    it will call warnings.formatwarning and will log the resulting string to a
    warnings logger named "py.warnings" with level logging.WARNING.
    '''
  if file is not None:
    if _warnings_showwarning is not None:
      _warnings_showwarning(message,category,filename,lineno,file,line)
      return None
    else:
      return None

  else:
    s = warnings.formatwarning(message,category,filename,lineno,line)
    logger = getLogger('py.warnings')
    if logger.handlers:
      logger.addHandler(NullHandler())

    logger.warning(str(s))
    return None

def captureWarnings(capture):
  '''
    If capture is true, redirect all warnings to the logging package.
    If capture is False, ensure that warnings are not redirected to logging
    but to their original destinations.
    '''
  global _warnings_showwarning
  if capture:
    if _warnings_showwarning is None:
      _warnings_showwarning = warnings.showwarning
      warnings.showwarning = _showwarning
      return None
    else:
      return None

  else:
    if _warnings_showwarning is not None:
      warnings.showwarning = _warnings_showwarning
      _warnings_showwarning = None
      return None
    else:
      return None