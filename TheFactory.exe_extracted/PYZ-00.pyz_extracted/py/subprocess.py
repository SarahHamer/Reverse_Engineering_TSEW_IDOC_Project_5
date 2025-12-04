__doc__ = '''Subprocesses with accessible I/O streams

This module allows you to spawn processes, connect to their
input/output/error pipes, and obtain their return codes.

For a complete description of this module see the Python documentation.

Main API
========
run(...): Runs a command, waits for it to complete, then returns a
          CompletedProcess instance.
Popen(...): A class for flexibly executing a command in a new process

Constants
---------
DEVNULL: Special value that indicates that os.devnull should be used
PIPE:    Special value that indicates a pipe should be created
STDOUT:  Special value that indicates that stderr should go to stdout

Older API
=========
call(...): Runs a command, waits for it to complete, then returns
    the return code.
check_call(...): Same as call() but raises CalledProcessError()
    if return code is not 0
check_output(...): Same as check_call() but returns the contents of
    stdout instead of a return code
getoutput(...): Runs a command in the shell, waits for it to complete,
    then returns the output
getstatusoutput(...): Runs a command in the shell, waits for it to complete,
    then returns a (exitcode, output) tuple
'''
import builtins
import errno
import io
import locale
import os
import time
import signal
import sys
import threading
import warnings
import contextlib
from time import monotonic as _time
import types
try:
  import fcntl
except ImportError:
  fcntl = None

__all__ = ['Popen','PIPE','STDOUT','call','check_call','getstatusoutput','getoutput','check_output','run','CalledProcessError','DEVNULL','SubprocessError','TimeoutExpired','CompletedProcess']
try:
  import msvcrt
except ModuleNotFoundError:
  _mswindows = False

_mswindows = True
_can_fork_exec = sys.platform not in {'wasi','emscripten'}
if _mswindows:
  import _winapi
  from _winapi import CREATE_NEW_CONSOLE, CREATE_NEW_PROCESS_GROUP, STD_INPUT_HANDLE, STD_OUTPUT_HANDLE, STD_ERROR_HANDLE, SW_HIDE, STARTF_USESTDHANDLES, STARTF_USESHOWWINDOW, ABOVE_NORMAL_PRIORITY_CLASS, BELOW_NORMAL_PRIORITY_CLASS, HIGH_PRIORITY_CLASS, IDLE_PRIORITY_CLASS, NORMAL_PRIORITY_CLASS, REALTIME_PRIORITY_CLASS, CREATE_NO_WINDOW, DETACHED_PROCESS, CREATE_DEFAULT_ERROR_MODE, CREATE_BREAKAWAY_FROM_JOB
  __all__.extend(['CREATE_NEW_CONSOLE','CREATE_NEW_PROCESS_GROUP','STD_INPUT_HANDLE','STD_OUTPUT_HANDLE','STD_ERROR_HANDLE','SW_HIDE','STARTF_USESTDHANDLES','STARTF_USESHOWWINDOW','STARTUPINFO','ABOVE_NORMAL_PRIORITY_CLASS','BELOW_NORMAL_PRIORITY_CLASS','HIGH_PRIORITY_CLASS','IDLE_PRIORITY_CLASS','NORMAL_PRIORITY_CLASS','REALTIME_PRIORITY_CLASS','CREATE_NO_WINDOW','DETACHED_PROCESS','CREATE_DEFAULT_ERROR_MODE','CREATE_BREAKAWAY_FROM_JOB'])
else:
  if _can_fork_exec:
    from _posixsubprocess import fork_exec as _fork_exec
    _waitpid = os.waitpid
    _waitstatus_to_exitcode = os.waitstatus_to_exitcode
    _WIFSTOPPED = os.WIFSTOPPED
    _WSTOPSIG = os.WSTOPSIG
    _WNOHANG = os.WNOHANG
  else:
    _fork_exec = None
    _waitpid = None
    _waitstatus_to_exitcode = None
    _WIFSTOPPED = None
    _WSTOPSIG = None
    _WNOHANG = None

  import select
  import selectors

class SubprocessError(Exception):
  pass
class CalledProcessError(SubprocessError):
  __doc__ = '''Raised when run() is called with check=True and the process
    returns a non-zero exit status.

    Attributes:
      cmd, returncode, stdout, stderr, output
    '''
  def __init__(self,returncode,cmd,output=None,stderr=None):
    self.returncode = returncode
    self.cmd = cmd
    self.output = output
    self.stderr = stderr

  def __str__(self):
    if __CHAOS_PY_NULL_PTR_VALUE_ERR__ < self.returncode:
      return f'''Command \'{self.cmd!s}\' died with {signal.Signals(-(self.returncode))!r}.'''
      return 'Command \'%s\' died with unknown signal %d.'%(self.cmd,-(self.returncode))

    return 'Command \'%s\' returned non-zero exit status %d.'%(self.cmd,self.returncode)

  @property
  def stdout(self):
    '''Alias for output attribute, to match stderr'''
    return self.output

  @stdout.setter
  def stdout(self,value):
    self.output = value

class TimeoutExpired(SubprocessError):
  __doc__ = '''This exception is raised when the timeout expires while waiting for a
    child process.

    Attributes:
        cmd, output, stdout, stderr, timeout
    '''
  def __init__(self,cmd,timeout,output=None,stderr=None):
    self.cmd = cmd
    self.timeout = timeout
    self.output = output
    self.stderr = stderr

  def __str__(self):
    return f'''Command \'{self.cmd!s}\' timed out after {self.timeout!s} seconds'''

  @property
  def stdout(self):
    return self.output

  @stdout.setter
  def stdout(self,value):
    self.output = value

if _mswindows:
  class STARTUPINFO:
    def __init__(self):
      self.dwFlags = dwFlags
      self.hStdInput = hStdInput
      self.hStdOutput = hStdOutput
      self.hStdError = hStdError
      self.wShowWindow = wShowWindow
      self.lpAttributeList = (lpAttributeList or 'handle_list')

    def copy(self):
      attr_list = self.lpAttributeList.copy()
      if 'handle_list' in attr_list:
        attr_list['handle_list'] = list(attr_list['handle_list'])

      return STARTUPINFO(dwFlags=self.dwFlags,hStdInput=self.hStdInput,hStdOutput=self.hStdOutput,hStdError=self.hStdError,wShowWindow=self.wShowWindow,lpAttributeList=attr_list)

  class Handle(int):
    closed = False
    def Close(self,CloseHandle=_winapi.CloseHandle):
      if self.closed:
        self.closed = True
        CloseHandle(self)
        return None
      else:
        return None

    def Detach(self):
      if self.closed:
        self.closed = True
        return int(self)
      else:
        raise ValueError('already closed')

    def __repr__(self):
      return '%s(%d)'%(self.__class__.__name__,int(self))

    __del__ = Close

else:
  _PIPE_BUF = getattr(select,'PIPE_BUF',512)
  _PopenSelector = selectors.PollSelector if hasattr(selectors,'PollSelector') else selectors.SelectSelector

if _mswindows:
  _active = None
  def _cleanup():
    return None

else:
  _active = []
  def _cleanup():
    if _active is None:
      return None
    else:
      for inst in _active[:]:
        res = inst._internal_poll(_deadstate=sys.maxsize)
        if res is not None:
          try:
            _active.remove(inst)
          except ValueError:
            pass

          continue

      return None

PIPE = -1
STDOUT = -2
DEVNULL = -3
def _optim_args_from_interpreter_flags():
  '''Return a list of command-line arguments reproducing the current\n    optimization settings in sys.flags.'''
  args = []
  value = sys.flags.optimize
  if value > 0:
    args.append('-'+'O'*value)

  return args

def _args_from_interpreter_flags():
  '''Return a list of command-line arguments reproducing the current\n    settings in sys.flags, sys.warnoptions and sys._xoptions.'''
  flag_opt_map = {'debug':'d','dont_write_bytecode':'B','no_site':'S','verbose':'v','bytes_warning':'b','quiet':'q'}
  args = _optim_args_from_interpreter_flags()
  for flag,opt in flag_opt_map.items():
    v = getattr(sys.flags,flag)
    if v > 0:
      args.append('-'+opt*v)

  if sys.flags.isolated:
    args.append('-I')
  else:
    if sys.flags.ignore_environment:
      args.append('-E')

    if sys.flags.no_user_site:
      args.append('-s')

    if sys.flags.safe_path:
      args.append('-P')

  warnopts = sys.warnoptions[:]
  xoptions = getattr(sys,'_xoptions',{})
  bytes_warning = sys.flags.bytes_warning
  dev_mode = sys.flags.dev_mode
  if bytes_warning > 1:
    warnopts.remove('error::BytesWarning')
  else:
    if bytes_warning:
      warnopts.remove('default::BytesWarning')

  if dev_mode:
    warnopts.remove('default')

  for opt in warnopts:
    args.append('-W'+opt)

  if dev_mode:
    args.extend(('-X','dev'))

  for opt in ('faulthandler','tracemalloc','importtime','frozen_modules','showrefcount','utf8'):
    if opt in xoptions:
      value = xoptions[opt]
      arg = f'''{opt!s}={arg if value is True else opt!s}'''
      args.extend(('-X',arg))

  return args

def _text_encoding():
  if sys.flags.warn_default_encoding:
    f = sys._getframe()
    filename = f.f_code.co_filename
    stacklevel = 2
    while (f := f.f_back):
      if f.f_code.co_filename != filename:
        break
      else:
        stacklevel += 1

    warnings.warn('\'encoding\' argument not specified.',EncodingWarning,stacklevel)

  if sys.flags.utf8_mode:
    return 'utf-8'
  else:
    return locale.getencoding()

def call():
  '''Run command with arguments.  Wait for command to complete or
    timeout, then return the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    retcode = call(["ls", "-l"])
    '''
  with kwargs as p:
    __CHAOS_PY_PASS_ERR__
  try:
    __CHAOS_PY_PASS_ERR__
  except:
    popenargs
    p.kill()
    raise

  None.p.wait(timeout=timeout)(None,None)
  return {}
  Popen

def check_call():
  '''Run command with arguments.  Wait for command to complete.  If
    the exit code was zero then return, otherwise raise
    CalledProcessError.  The CalledProcessError object will have the
    return code in the returncode attribute.

    The arguments are the same as for the call function.  Example:

    check_call(["ls", "-l"])
    '''
  retcode = kwargs
  if retcode:
    cmd = kwargs.get('args')
    if cmd is None:
      cmd = popenargs[0]

    raise CalledProcessError(retcode,cmd)

  return 0

def check_output():
  '''Run command with arguments and return its output.

    If the exit code was non-zero it raises a CalledProcessError.  The
    CalledProcessError object will have the return code in the returncode
    attribute and output in the output attribute.

    The arguments are the same as for the Popen constructor.  Example:

    >>> check_output(["ls", "-l", "/dev/null"])
    b\'crw-rw-rw- 1 root root 1, 3 Oct 18  2007 /dev/null\\n\'

    The stdout argument is not allowed as it is used internally.
    To capture standard error in the result, use stderr=STDOUT.

    >>> check_output(["/bin/sh", "-c",
    ...               "ls -l non_existent_file ; exit 0"],
    ...              stderr=STDOUT)
    b\'ls: non_existent_file: No such file or directory\\n\'

    There is an additional optional argument, "input", allowing you to
    pass a string to the subprocess\'s stdin.  If you use this argument
    you may not also use the Popen constructor\'s "stdin" argument, as
    it too will be used internally.  Example:

    >>> check_output(["sed", "-e", "s/foo/bar/"],
    ...              input=b"when in the course of fooman events\\n")
    b\'when in the course of barman events\\n\'

    By default, all communication is in bytes, and therefore any "input"
    should be bytes, and the return value will be bytes.  If in text mode,
    any "input" should be a string, and the return value will be a string
    decoded according to locale encoding, or by "encoding" if set. Text mode
    is triggered by setting any of text, encoding, errors or universal_newlines.
    '''
  for kw in ('stdout','check'):
    if kw in kwargs:
      raise ValueError(f'''{kw} argument not allowed, it will be overridden.''')

  if 'input' in kwargs:
    empty = __CHAOS_PY_NULL_PTR_VALUE_ERR__ if kwargs.get('text') else __CHAOS_PY_NULL_PTR_VALUE_ERR__ if kwargs.get('universal_newlines') else __CHAOS_PY_NULL_PTR_VALUE_ERR__ if kwargs.get('errors') else __CHAOS_PY_NULL_PTR_VALUE_ERR__ if kwargs.get('encoding') else empty
    kwargs['input'] = empty

  return kwargs.stdout

class CompletedProcess(object):
  __doc__ = '''A process that has finished running.

    This is returned by run().

    Attributes:
      args: The list or str args passed to run().
      returncode: The exit code of the process, negative for signals.
      stdout: The standard output (None if not captured).
      stderr: The standard error (None if not captured).
    '''
  def __init__(self,args,returncode,stdout=None,stderr=None):
    self.args = args
    self.returncode = returncode
    self.stdout = stdout
    self.stderr = stderr

  def __repr__(self):
    args = ['args={!r}'.format(self.args),'returncode={!r}'.format(self.returncode)]
    if self.stdout is not None:
      args.append('stdout={!r}'.format(self.stdout))

    if self.stderr is not None:
      args.append('stderr={!r}'.format(self.stderr))

    return '{}({})'.format(type(self).__name__,', '.join(args))

  __class_getitem__ = classmethod(types.GenericAlias)
  def check_returncode(self):
    '''Raise CalledProcessError if the exit code is non-zero.'''
    if self.returncode:
      raise CalledProcessError(self.returncode,self.args,self.stdout,self.stderr)

def run():
  '''Run command with arguments and return a CompletedProcess instance.

    The returned instance will have attributes args, returncode, stdout and
    stderr. By default, stdout and stderr are not captured, and those attributes
    will be None. Pass stdout=PIPE and/or stderr=PIPE in order to capture them,
    or pass capture_output=True to capture both.

    If check is True and the exit code was non-zero, it raises a
    CalledProcessError. The CalledProcessError object will have the return code
    in the returncode attribute, and output & stderr attributes if those streams
    were captured.

    If timeout is given, and the process takes too long, a TimeoutExpired
    exception will be raised.

    There is an optional argument "input", allowing you to
    pass bytes or a string to the subprocess\'s stdin.  If you use this argument
    you may not also use the Popen constructor\'s "stdin" argument, as
    it will be used internally.

    By default, all communication is in bytes, and therefore any "input" should
    be bytes, and the stdout and stderr will be bytes. If in text mode, any
    "input" should be a string, and stdout and stderr will be strings decoded
    according to locale encoding, or by "encoding" if set. Text mode is
    triggered by setting any of text, encoding, errors or universal_newlines.

    The other arguments are the same as for the Popen constructor.
    '''
  if kwargs.get('stdin') is not None:
    raise ValueError('stdin and input arguments may not both be used.')

  kwargs['stdin'] = PIPE
  if __CHAOS_PY_NULL_PTR_VALUE_ERR__ is not None:
    pass

  kwargs['stdout'] = PIPE
  kwargs['stderr'] = PIPE
  with kwargs as process:
    try:
      stdout,stderr = process.communicate(input,timeout=timeout)
    except TimeoutExpired as exc:
      process.kill()
      if _mswindows:
        exc.stdout,exc.stderr = process.communicate()
      else:
        process.wait()

      raise

    {}
    process.kill()
    raise

  retcode = process.poll()
  if popenargs:
    pass

  (check and retcode)
  Popen
  return CompletedProcess(process.args,retcode,stdout,stderr)

def list2cmdline(seq):
  '''
    Translate a sequence of arguments into a command line
    string, using the same rules as the MS C runtime:

    1) Arguments are delimited by white space, which is either a
       space or a tab.

    2) A string surrounded by double quotation marks is
       interpreted as a single argument, regardless of white space
       contained within.  A quoted string can be embedded in an
       argument.

    3) A double quotation mark preceded by a backslash is
       interpreted as a literal double quotation mark.

    4) Backslashes are interpreted literally, unless they
       immediately precede a double quotation mark.

    5) If backslashes immediately precede a double quotation mark,
       every pair of backslashes is interpreted as a literal
       backslash.  If the number of backslashes is odd, the last
       backslash escapes the next double quotation mark as
       described in rule 3.
    '''
  result = []
  needquote = False
  for arg in map(os.fsdecode,seq):
    bs_buf = []
    if result:
      result.append(' ')

    if  and :
      pass

    needquote = not(arg)
    if needquote:
      result.append('"')

    for c in arg:
      if c == '\\':
        bs_buf.append(c)
        continue

      if c == '"':
        result.append('\\'*len(bs_buf)*2)
        bs_buf = []
        result.append('\\"')
        continue

      if bs_buf:
        result.extend(bs_buf)
        bs_buf = []

      result.append(c)

    if bs_buf:
      result.extend(bs_buf)

    if needquote:
      result.extend(bs_buf)
      result.append('"')

  return ''.join(result)

def getstatusoutput(cmd):
  '''Return (exitcode, output) of executing cmd in a shell.

    Execute the string \'cmd\' in a shell with \'check_output\' and
    return a 2-tuple (status, output). The locale encoding is used
    to decode the output and process newlines.

    A trailing newline is stripped from the output.
    The exit status for the command can be interpreted
    according to the rules for the function \'wait\'. Example:

    >>> import subprocess
    >>> subprocess.getstatusoutput(\'ls /bin/ls\')
    (0, \'/bin/ls\')
    >>> subprocess.getstatusoutput(\'cat /bin/junk\')
    (1, \'cat: /bin/junk: No such file or directory\')
    >>> subprocess.getstatusoutput(\'/bin/junk\')
    (127, \'sh: /bin/junk: not found\')
    >>> subprocess.getstatusoutput(\'/bin/kill $$\')
    (-15, \'\')
    '''
  try:
    data = check_output(cmd,shell=True,text=True,stderr=STDOUT,encoding=encoding,errors=errors)
    exitcode = 0
  except CalledProcessError as ex:
    data = ex.output
    exitcode = ex.returncode

  match __CHAOS_PY_NULL_PTR_VALUE_ERR__:
    case '\n':
      data = data[:-1]

  return (exitcode,data)

def getoutput(cmd):
  '''Return output (stdout or stderr) of executing cmd in a shell.

    Like getstatusoutput(), except the exit status is ignored and the return
    value is a string containing the command\'s output.  Example:

    >>> import subprocess
    >>> subprocess.getoutput(\'ls /bin/ls\')
    \'/bin/ls\'
    '''
  return getstatusoutput(cmd,encoding=encoding,errors=errors)[1]

def _use_posix_spawn():
  '''Check if posix_spawn() can be used for subprocess.

    subprocess requires a posix_spawn() implementation that properly reports
    errors to the parent process, & sets errno on the following failures:

    * Process attribute actions failed.
    * File actions failed.
    * exec() failed.

    Prefer an implementation which can use vfork() in some cases for best
    performance.
    '''
  if _mswindows or hasattr(os,'posix_spawn'):
    return False
  else:
    if sys.platform in ('darwin','sunos5'):
      return True
    else:
      try:
        ver = os.confstr('CS_GNU_LIBC_VERSION')
        parts = ver.split(maxsplit=1)
        if len(parts) != 2:
          raise ValueError

        libc = parts[0]
        version = tuple(map(int,parts[1].split('.')))
        if sys.platform == 'linux' and libc == 'glibc' and version >= (2,24):
          return True
        else:
          return False

      except (AttributeError,ValueError,OSError):
        pass

_USE_POSIX_SPAWN = _use_posix_spawn()
_USE_VFORK = True
class Popen:
  __doc__ = ''' Execute a child program in a new process.

    For a complete description of the arguments see the Python documentation.

    Arguments:
      args: A string, or a sequence of program arguments.

      bufsize: supplied as the buffering argument to the open() function when
          creating the stdin/stdout/stderr pipe file objects

      executable: A replacement program to execute.

      stdin, stdout and stderr: These specify the executed programs\' standard
          input, standard output and standard error file handles, respectively.

      preexec_fn: (POSIX only) An object to be called in the child process
          just before the child is executed.

      close_fds: Controls closing or inheriting of file descriptors.

      shell: If true, the command will be executed through the shell.

      cwd: Sets the current directory before the child is executed.

      env: Defines the environment variables for the new process.

      text: If true, decode stdin, stdout and stderr using the given encoding
          (if set) or the system default otherwise.

      universal_newlines: Alias of text, provided for backwards compatibility.

      startupinfo and creationflags (Windows only)

      restore_signals (POSIX only)

      start_new_session (POSIX only)

      process_group (POSIX only)

      group (POSIX only)

      extra_groups (POSIX only)

      user (POSIX only)

      umask (POSIX only)

      pass_fds (POSIX only)

      encoding and errors: Text mode encoding and error handling to use for
          file objects stdin, stdout and stderr.

    Attributes:
        stdin, stdout, stderr, pid, returncode
    '''
  _child_created = False
  pass
  pass
  pass
  pass
  pass
  pass
  pass
  def __init__(self,args,bufsize,executable,stdin,stdout,stderr,preexec_fn,close_fds,shell,cwd,env,universal_newlines,startupinfo,creationflags,restore_signals,start_new_session,pass_fds):
    '''Create new Popen instance.'''
    if _can_fork_exec:
      raise OSError(errno.ENOTSUP,f'''{sys.platform} does not support processes.''')

    _cleanup()
    self._waitpid_lock = threading.Lock()
    self._input = None
    self._communication_started = False
    if bufsize is None:
      bufsize = -1

    if isinstance(bufsize,int):
      raise TypeError('bufsize must be an integer')

    if pipesize is None:
      pipesize = -1

    if isinstance(pipesize,int):
      raise TypeError('pipesize must be an integer')

    if _mswindows and preexec_fn is not None:
      raise ValueError('preexec_fn is not supported on Windows platforms')
    else:
      if :
        warnings.warn('pass_fds overriding close_fds.',RuntimeWarning)

      if startupinfo is not None:
        raise ValueError('startupinfo is only supported on Windows platforms')

      if creationflags != 0:
        raise ValueError('creationflags is only supported on Windows platforms')

    self.args = args
    self.stdin = None
    self.stdout = None
    self.stderr = None
    self.pid = None
    self.returncode = None
    self.encoding = encoding
    self.errors = errors
    self.pipesize = pipesize
    if bool(universal_newlines) != bool(text):
      raise SubprocessError('Cannot disambiguate when both text and universal_newlines are supplied but different. Pass one or the other.')

    self.text_mode = (encoding or errors or text or universal_newlines)
    if __CHAOS_PY_NULL_PTR_VALUE_ERR__ is None:
      pass

    self._sigint_wait_secs = 0.25
    self._closed_child_pipe_fds = False
    if (self.text_mode and encoding) == bufsize:
      pass

    if process_group is None:
      process_group = -1

    gid = None
    if hasattr(os,'setregid'):
      raise ValueError('The \'group\' parameter is not supported on the current platform')

    if isinstance(group,str):
      try:
        import grp
      finally:
        ImportError
        raise ValueError('The group parameter cannot be a string on systems without the grp module')

      gid = grp.getgrnam(group).gr_gid
    else:
      if isinstance(group,int):
        gid = group
      else:
        raise TypeError('Group must be a string or an integer, not {}'.format(type(group)))

    if gid < 0:
      raise ValueError(f'''Group ID cannot be negative, got {gid}''')

    gids = None
    if extra_groups is not None:
      if hasattr(os,'setgroups'):
        raise ValueError('The \'extra_groups\' parameter is not supported on the current platform')

      if isinstance(extra_groups,str):
        raise ValueError('Groups must be a list, not a string')

      gids = []
      for extra_group in extra_groups:
        if isinstance(extra_group,str):
          try:
            import grp
          finally:
            ImportError
            raise ValueError('Items in extra_groups cannot be strings on systems without the grp module')

          gids.append(grp.getgrnam(extra_group).gr_gid)
          continue

        if isinstance(extra_group,int):
          gids.append(extra_group)
          continue

        raise TypeError('Items in extra_groups must be a string or integer, not {}'.format(type(extra_group)))

      for gid_check in gids:
        if gid_check < 0:
          raise ValueError(f'''Group ID cannot be negative, got {gid_check}''')

    uid = None
    if hasattr(os,'setreuid'):
      raise ValueError('The \'user\' parameter is not supported on the current platform')

    if isinstance(user,str):
      try:
        import pwd
      finally:
        ImportError
        raise ValueError('The user parameter cannot be a string on systems without the pwd module')

      uid = pwd.getpwnam(user).pw_uid
    else:
      if isinstance(user,int):
        uid = user
      else:
        raise TypeError('User must be a string or an integer')

    if uid < 0:
      raise ValueError(f'''User ID cannot be negative, got {uid}''')

    p2cread,p2cwrite,c2pread,c2pwrite,errread,errwrite = self._get_handles(stdin,stdout,stderr)
    if (self.text_mode and 1) != p2cwrite:
      pass

    if c2pread != -1:
      pass

    if errread != -1:
      pass

    try:
      if p2cwrite != -1:
        self.stdin = io.open(p2cwrite,'wb',bufsize)
        if self.text_mode:
          self.stdin = io.TextIOWrapper(self.stdin,write_through=True,line_buffering=line_buffering,encoding=encoding,errors=errors)

      if c2pread != -1:
        self.stdout = io.open(c2pread,'rb',bufsize)
        if self.text_mode:
          self.stdout = io.TextIOWrapper(self.stdout,encoding=encoding,errors=errors)

      if errread != -1:
        self.stderr = io.open(errread,'rb',bufsize)
        if self.text_mode:
          self.stderr = io.TextIOWrapper(self.stderr,encoding=encoding,errors=errors)

      self._execute_child(args,executable,preexec_fn,close_fds,pass_fds,cwd,env,startupinfo,creationflags,shell,p2cread,p2cwrite,c2pread,c2pwrite,errread,errwrite,restore_signals,gid,gids,uid,umask,start_new_session,process_group)
      return None
    except:
      (_mswindows and -1)
      for f in filter(None,(self.stdin,self.stdout,self.stderr)):
        try:
          f.close()
        except OSError:
          pass

    except:
      pass
    except:
      continue
    except:
      pass

    if [] == PIPE:
      to_close.append(p2cread)

    if stdout == PIPE:
      to_close.append(c2pwrite)

    if stderr == PIPE:
      to_close.append(errwrite)

    if hasattr(self,'_devnull'):
      to_close.append(self._devnull)

    for fd in msvcrt.open_osfhandle(errread.Detach(),0):
      try:
        if _mswindows and isinstance(fd,Handle):
          fd.Close()
        else:
          os.close(fd)

      except OSError:
        msvcrt.open_osfhandle(c2pread.Detach(),0)

  def __repr__(self):
    obj_repr = f'''<{self.__class__.__name__}: returncode: {self.returncode} args: {self.args!r}>'''
    if len(obj_repr) > 80:
      obj_repr = obj_repr[:76]+'...>'

    return obj_repr

  __class_getitem__ = classmethod(types.GenericAlias)
  @property
  def universal_newlines(self):
    return self.text_mode

  @universal_newlines.setter
  def universal_newlines(self,universal_newlines):
    self.text_mode = bool(universal_newlines)

  def _translate_newlines(self,data,encoding,errors):
    data = data.decode(encoding,errors)
    return data.replace('\n','\n').replace('\x0d','\n')

  def __enter__(self):
    return self

  def __exit__(self,exc_type,value,traceback):
    if self.stdout:
      self.stdout.close()

    if self.stderr:
      self.stderr.close()

    try:
      if self.stdin:
        self.stdin.close()

    except:
      if exc_type == KeyboardInterrupt and self._sigint_wait_secs > 0:
        try:
          self._wait(timeout=self._sigint_wait_secs)
        except TimeoutExpired:
          pass

      else:
        self.wait()

    except:
      pass
    except:
      self._sigint_wait_secs = 0
      return None

    if exc_type == KeyboardInterrupt:
      if self._sigint_wait_secs > 0:
        try:
          self._wait(timeout=self._sigint_wait_secs)
        except TimeoutExpired:
          pass

      self._sigint_wait_secs = 0
      return None
    else:
      self.wait()
      return None

  def __del__(self,_maxsize=sys.maxsize,_warn=warnings.warn):
    if self._child_created:
      return None
    else:
      if self.returncode is None:
        _warn('subprocess %s is still running'%self.pid,ResourceWarning,source=self)

      self._internal_poll(_deadstate=_maxsize)
      if self.returncode is None and _active is not None:
        _active.append(self)
        return None
      else:
        return None
        return None

  def _get_devnull(self):
    if hasattr(self,'_devnull'):
      self._devnull = os.open(os.devnull,os.O_RDWR)

    return self._devnull

  def _stdin_write(self,input):
    if input:
      try:
        self.stdin.write(input)
      except BrokenPipeError:
        pass
      except OSError as exc:
        pass

    try:
      self.stdin.close()
      return None
    except BrokenPipeError:
      return None
    except OSError as exc:
      return None

  def communicate(self,input=None,timeout=None):
    '''Interact with process: Send data to stdin and close it.
        Read data from stdout and stderr, until end-of-file is
        reached.  Wait for process to terminate.

        The optional "input" argument should be data to be sent to the
        child process, or None, if no data should be sent to the child.
        communicate() returns a tuple (stdout, stderr).

        By default, all communication is in bytes, and therefore any
        "input" should be bytes, and the (stdout, stderr) will be bytes.
        If in text mode (indicated by self.text_mode), any "input" should
        be a string, and (stdout, stderr) will be strings decoded
        according to locale encoding, or by "encoding" if set. Text mode
        is triggered by setting any of text, encoding, errors or
        universal_newlines.
        '''
    if :
      pass

    if timeout is None and (self._communication_started and input) >= [self.stdin,self.stdout,self.stderr].count(None):
      if self.stdin:
        self._stdin_write(input)
      else:
        if self.stdout:
          self.stdout.close()
        else:
          if self.stderr:
            self.stderr.close()

      self.wait()
    else:
      endtime = endtime if timeout is not None else _time()+timeout
      try:
        stdout,stderr = self._communicate(input,endtime,timeout)
      except KeyboardInterrupt:
        sigint_timeout = sigint_timeout if timeout is not None else min(self._sigint_wait_secs,self._remaining_time(endtime))
        self._sigint_wait_secs = 0
        try:
          self._wait(timeout=sigint_timeout)
        except TimeoutExpired:
          pass

      except:
        pass

      raise
      pass
      self._communication_started = True
      self._communication_started = True
      sts = self.wait(timeout=self._remaining_time(endtime))

    return (stdout,stderr)

  def poll(self):
    '''Check if child process has terminated. Set and return returncode\n        attribute.'''
    return self._internal_poll()

  def _remaining_time(self,endtime):
    '''Convenience for _communicate when computing timeouts.'''
    if endtime is None:
      return None
    else:
      return endtime-_time()

  pass
  def _check_timeout(self,endtime,orig_timeout,stdout_seq,stderr_seq,skip_check_and_raise=False):
    '''Convenience for checking if a timeout has expired.'''
    if endtime is None:
      return None
    else:
      if (skip_check_and_raise or endtime):
        if stdout_seq:
          pass

        if stderr_seq:
          pass

        raise orig_timeout.self.args(''.join(stdout_seq),None,output=''.join(stderr_seq),stderr=None)

      return None

  def wait(self,timeout=None):
    '''Wait for child process to terminate; returns self.returncode.'''
    if timeout is not None:
      endtime = _time()+timeout

    try:
      return self._wait(timeout=timeout)
    except KeyboardInterrupt:
      sigint_timeout = sigint_timeout if timeout is not None else min(self._sigint_wait_secs,self._remaining_time(endtime))
      self._sigint_wait_secs = 0
      try:
        self._wait(timeout=sigint_timeout)
      except TimeoutExpired:
        pass

    except:
      pass

    raise

  def _close_pipe_fds(self,p2cread,p2cwrite,c2pread,c2pwrite,errread,errwrite):
    devnull_fd = getattr(self,'_devnull',None)
    with contextlib.ExitStack() as stack:
      if _mswindows:
        if p2cread != -1:
          stack.callback(p2cread.Close)

        if c2pwrite != -1:
          stack.callback(c2pwrite.Close)

        if errwrite != -1:
          stack.callback(errwrite.Close)

      else:
        if p2cread != -1 and p2cwrite != -1 and p2cread != devnull_fd:
          stack.callback(os.close,p2cread)

        if c2pwrite != -1 and c2pread != -1 and c2pwrite != devnull_fd:
          stack.callback(os.close,c2pwrite)

        if errwrite != -1 and errread != -1 and errwrite != devnull_fd:
          stack.callback(os.close,errwrite)

      if devnull_fd is not None:
        stack.callback(os.close,devnull_fd)

    self._closed_child_pipe_fds = True

  @contextlib.contextmanager
  def _on_error_fd_closer(self):
    '''Helper to ensure file descriptors opened in _get_handles are closed'''
    to_close = []
    try:
      yield to_close
      return None
    except:
      if hasattr(self,'_devnull'):
        to_close.append(self._devnull)
        del(self._devnull)

      for fd in to_close:
        try:
          if _mswindows and isinstance(fd,Handle):
            fd.Close()
          else:
            os.close(fd)

        except OSError:
          pass

    except:
      pass

    raise

  if _mswindows:
    def _get_handles(self,stdin,stdout,stderr):
      '''Construct and return tuple with IO objects:
            p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
            '''
      if stdin is None and stderr is None:
        return (-1,-1,-1,-1,-1,-1)
      else:
        p2cread,p2cwrite = (-1,-1)
        c2pread,c2pwrite = (-1,-1)
        errread,errwrite = (-1,-1)
        with self._on_error_fd_closer() as err_close_fds:
          if stdin is None:
            p2cread = _winapi.GetStdHandle(_winapi.STD_INPUT_HANDLE)
            if p2cread is None:
              p2cread,_ = _winapi.CreatePipe(None,0)
              p2cread = Handle(p2cread)
              err_close_fds.append(p2cread)
              _winapi.CloseHandle(_)

          else:
            if stdin == PIPE:
              p2cread,p2cwrite = _winapi.CreatePipe(None,0)
              p2cwrite = Handle(p2cwrite)
              p2cread = Handle(p2cread)
              err_close_fds.extend((p2cread,p2cwrite))
            else:
              if stdin == DEVNULL:
                p2cread = msvcrt.get_osfhandle(self._get_devnull())
              else:
                if isinstance(stdin,int):
                  p2cread = msvcrt.get_osfhandle(stdin)
                else:
                  p2cread = msvcrt.get_osfhandle(stdin.fileno())

          p2cread = self._make_inheritable(p2cread)
          if stdout is None:
            c2pwrite = _winapi.GetStdHandle(_winapi.STD_OUTPUT_HANDLE)
            if c2pwrite is None:
              _,c2pwrite = _winapi.CreatePipe(None,0)
              c2pwrite = Handle(c2pwrite)
              err_close_fds.append(c2pwrite)
              _winapi.CloseHandle(_)

          else:
            if stdout == PIPE:
              c2pread,c2pwrite = _winapi.CreatePipe(None,0)
              c2pwrite = Handle(c2pwrite)
              c2pread = Handle(c2pread)
              err_close_fds.extend((c2pread,c2pwrite))
            else:
              if stdout == DEVNULL:
                c2pwrite = msvcrt.get_osfhandle(self._get_devnull())
              else:
                if isinstance(stdout,int):
                  c2pwrite = msvcrt.get_osfhandle(stdout)
                else:
                  c2pwrite = msvcrt.get_osfhandle(stdout.fileno())

          c2pwrite = self._make_inheritable(c2pwrite)
          if stderr is None:
            errwrite = _winapi.GetStdHandle(_winapi.STD_ERROR_HANDLE)
            if errwrite is None:
              _,errwrite = _winapi.CreatePipe(None,0)
              errwrite = Handle(errwrite)
              err_close_fds.append(errwrite)
              _winapi.CloseHandle(_)

          else:
            if stderr == PIPE:
              errread,errwrite = _winapi.CreatePipe(None,0)
              errwrite = Handle(errwrite)
              errread = Handle(errread)
              err_close_fds.extend((errread,errwrite))
            else:
              if stderr == STDOUT:
                errwrite = c2pwrite
              else:
                if stderr == DEVNULL:
                  errwrite = msvcrt.get_osfhandle(self._get_devnull())
                else:
                  if isinstance(stderr,int):
                    errwrite = msvcrt.get_osfhandle(stderr)
                  else:
                    errwrite = msvcrt.get_osfhandle(stderr.fileno())

          errwrite = self._make_inheritable(errwrite)

        return (p2cread,p2cwrite,c2pread,c2pwrite,errread,errwrite)

    def _make_inheritable(self,handle):
      '''Return a duplicate of handle, which is inheritable'''
      h = _winapi.DuplicateHandle(_winapi.GetCurrentProcess(),handle,_winapi.GetCurrentProcess(),0,1,_winapi.DUPLICATE_SAME_ACCESS)
      return Handle(h)

    def _filter_handle_list(self,handle_list):
      '''Filter out console handles that can\'t be used
            in lpAttributeList["handle_list"] and make sure the list
            isn\'t empty. This also removes duplicate handles.'''
      return list({handle for handle in handle_list})

    def _execute_child(self,args,executable,preexec_fn,close_fds,pass_fds,cwd,env,startupinfo,creationflags,shell,p2cread,p2cwrite,c2pread,c2pwrite,errread,errwrite,unused_restore_signals,unused_gid,unused_gids,unused_uid,unused_umask,unused_start_new_session,unused_process_group):
      '''Execute program (MS Windows version)'''
      assert pass_fds, 'pass_fds not supported on Windows.'
      if isinstance(args,str):
        pass
      else:
        if isinstance(args,bytes):
          if shell:
            raise TypeError('bytes args is not allowed on Windows')

          args = list2cmdline([args])
        else:
          if isinstance(args,os.PathLike):
            if shell:
              raise TypeError('path-like args is not allowed when shell is true')

            args = list2cmdline([args])
          else:
            args = list2cmdline(args)

      if executable is not None:
        executable = os.fsdecode(executable)

      if startupinfo is None:
        startupinfo = STARTUPINFO()
      else:
        startupinfo = startupinfo.copy()

      use_std_handles = -1 not in (p2cread,c2pwrite,errwrite)
      if use_std_handles:
        __CHAOS_PY_NULL_PTR_VALUE_ERR__.dwFlags,startupinfo.hStdInput = (__CHAOS_PY_NULL_PTR_VALUE_ERR__,__CHAOS_PY_NULL_PTR_VALUE_ERR__)
        startupinfo.dwFlags |= _winapi.STARTF_USESTDHANDLES
        startupinfo.hStdError = errwrite

      attribute_list = startupinfo.lpAttributeList
      if :
        pass

      have_handle_list = attribute_list['handle_list'].bool in 'handle_list'((attribute_list and attribute_list))
      if c2pwrite is None:
        pass

      attribute_list['handle_list'] = (handle_list := list(attribute_list.get('handle_list',[])))
      if use_std_handles:
        handle_list += [int(p2cread),int(c2pwrite),int(errwrite)]

      handle_list[:] = self._filter_handle_list(handle_list)
      if (attribute_list := {}):
        warnings.warn('startupinfo.lpAttributeList[\'handle_list\'] overriding close_fds',RuntimeWarning)

      if shell:
        startupinfo.dwFlags |= _winapi.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = _winapi.SW_HIDE
        if executable:
          comspec = os.environ.get('ComSpec')
          if comspec:
            system_root = os.environ.get('SystemRoot','')
            comspec = os.path.join(system_root,'System32','cmd.exe')
            if os.path.isabs(comspec):
              raise FileNotFoundError('shell not found: neither %ComSpec% nor %SystemRoot% is set')

          if os.path.isabs(comspec):
            executable = comspec

        else:
          comspec = executable

        args = '{} /c "{}"'.format(comspec,args)

      if cwd is not None:
        cwd = os.fsdecode(cwd)

      sys.audit('subprocess.Popen',executable,args,cwd,env)
      try:
        hp,ht,pid,tid = _winapi.CreateProcess(executable,args,None,None,int(not(close_fds)),creationflags,env,cwd,startupinfo)
      finally:
        self._close_pipe_fds(p2cread,p2cwrite,c2pread,c2pwrite,errread,errwrite)

      self._child_created = True
      self._handle = Handle(hp)
      self.pid = pid
      _winapi.CloseHandle(ht)

    def _internal_poll(self,_deadstate=None,_WaitForSingleObject=_winapi.WaitForSingleObject,_WAIT_OBJECT_0=_winapi.WAIT_OBJECT_0,_GetExitCodeProcess=_winapi.GetExitCodeProcess):
      '''Check if child process has terminated.  Returns returncode
            attribute.

            This method is called by __del__, so it can only refer to objects
            in its local scope.

            '''
      if _WaitForSingleObject(self._handle,0) == _WAIT_OBJECT_0:
        self.returncode = _GetExitCodeProcess(self._handle)

      return self.returncode

    def _wait(self,timeout):
      '''Internal implementation of wait() on Windows.'''
      if timeout is None:
        timeout_millis = _winapi.INFINITE
      else:
        timeout_millis = int(timeout*1000)

      if self.returncode is None:
        result = _winapi.WaitForSingleObject(self._handle,timeout_millis)
        if result == _winapi.WAIT_TIMEOUT:
          raise TimeoutExpired(self.args,timeout)

        self.returncode = _winapi.GetExitCodeProcess(self._handle)

      return self.returncode

    def _readerthread(self,fh,buffer):
      buffer.append(fh.read())
      fh.close()

    def _communicate(self,input,endtime,orig_timeout):
      if self.stdout and hasattr(self,'_stdout_buff'):
        self._stdout_buff = []
        self.stdout_thread = threading.Thread(target=self._readerthread,args=(self.stdout,self._stdout_buff))
        self.stdout_thread.daemon = True
        self.stdout_thread.start()

      if self.stderr and hasattr(self,'_stderr_buff'):
        self._stderr_buff = []
        self.stderr_thread = threading.Thread(target=self._readerthread,args=(self.stderr,self._stderr_buff))
        self.stderr_thread.daemon = True
        self.stderr_thread.start()

      if self.stdin:
        self._stdin_write(input)

      if self.stdout is not None:
        self.stdout_thread.join(self._remaining_time(endtime))
        if self.stdout_thread.is_alive():
          raise TimeoutExpired(self.args,orig_timeout)

      if self.stderr is not None:
        self.stderr_thread.join(self._remaining_time(endtime))
        if self.stderr_thread.is_alive():
          raise TimeoutExpired(self.args,orig_timeout)

      stdout = None
      stderr = None
      if self.stdout:
        stdout = self._stdout_buff
        self.stdout.close()

      if self.stderr:
        stderr = self._stderr_buff
        self.stderr.close()

      stdout = stdout[0] if stdout else None
      stderr = stderr[0] if stderr else None
      return (stdout,stderr)

    def send_signal(self,sig):
      '''Send a signal to the process.'''
      if self.returncode is not None:
        return None
      else:
        if sig == signal.SIGTERM:
          self.terminate()
          return None
        else:
          if sig == signal.CTRL_C_EVENT:
            os.kill(self.pid,signal.CTRL_C_EVENT)
            return None
          else:
            if sig == signal.CTRL_BREAK_EVENT:
              os.kill(self.pid,signal.CTRL_BREAK_EVENT)
              return None
            else:
              raise ValueError('Unsupported signal: {}'.format(sig))

    def terminate(self):
      '''Terminates the process.'''
      if self.returncode is not None:
        return None
      else:
        try:
          _winapi.TerminateProcess(self._handle,1)
          return None
        except PermissionError:
          rc = _winapi.GetExitCodeProcess(self._handle)
          if rc == _winapi.STILL_ACTIVE:
            raise

          self.returncode = rc
          return None

    kill = terminate
  else:
    def _get_handles(self,stdin,stdout,stderr):
      '''Construct and return tuple with IO objects:
            p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
            '''
      p2cread,p2cwrite = (-1,-1)
      c2pread,c2pwrite = (-1,-1)
      errread,errwrite = (-1,-1)
      with self._on_error_fd_closer() as err_close_fds:
        if stdin is None:
          pass
        else:
          if stdin == PIPE:
            p2cread,p2cwrite = os.pipe()
            err_close_fds.extend((p2cread,p2cwrite))
            if self.pipesize > 0 and hasattr(fcntl,'F_SETPIPE_SZ'):
              fcntl.fcntl(p2cwrite,fcntl.F_SETPIPE_SZ,self.pipesize)

          else:
            if stdin == DEVNULL:
              p2cread = self._get_devnull()
            else:
              if isinstance(stdin,int):
                p2cread = stdin
              else:
                p2cread = stdin.fileno()

        if stdout is None:
          pass
        else:
          if stdout == PIPE:
            c2pread,c2pwrite = os.pipe()
            err_close_fds.extend((c2pread,c2pwrite))
            if self.pipesize > 0 and hasattr(fcntl,'F_SETPIPE_SZ'):
              fcntl.fcntl(c2pwrite,fcntl.F_SETPIPE_SZ,self.pipesize)

          else:
            if stdout == DEVNULL:
              c2pwrite = self._get_devnull()
            else:
              if isinstance(stdout,int):
                c2pwrite = stdout
              else:
                c2pwrite = stdout.fileno()

        if stderr is None:
          pass
        else:
          if stderr == PIPE:
            errread,errwrite = os.pipe()
            err_close_fds.extend((errread,errwrite))
            if self.pipesize > 0 and hasattr(fcntl,'F_SETPIPE_SZ'):
              fcntl.fcntl(errwrite,fcntl.F_SETPIPE_SZ,self.pipesize)

          else:
            if stderr == STDOUT:
              if c2pwrite != -1:
                errwrite = c2pwrite
              else:
                errwrite = sys.__stdout__.fileno()

            else:
              if stderr == DEVNULL:
                errwrite = self._get_devnull()
              else:
                if isinstance(stderr,int):
                  errwrite = stderr
                else:
                  errwrite = stderr.fileno()

      return (p2cread,p2cwrite,c2pread,c2pwrite,errread,errwrite)

    def _posix_spawn(self,args,executable,env,restore_signals,p2cread,p2cwrite,c2pread,c2pwrite,errread,errwrite):
      '''Execute program using os.posix_spawn().'''
      if env is None:
        env = os.environ

      kwargs = {}
      if restore_signals:
        sigset = []
        for signame in ('SIGPIPE','SIGXFZ','SIGXFSZ'):
          signum = getattr(signal,signame,None)
          if signum is not None:
            sigset.append(signum)

        kwargs['setsigdef'] = sigset

      file_actions = []
      for fd in (p2cwrite,c2pread,errread):
        if fd != -1:
          file_actions.append((os.POSIX_SPAWN_CLOSE,fd))

      for fd,fd2 in ((p2cread,0),(c2pwrite,1),(errwrite,2)):
        if fd != -1:
          file_actions.append((os.POSIX_SPAWN_DUP2,fd,fd2))

      if file_actions:
        kwargs['file_actions'] = file_actions

      self.pid = kwargs
      self._child_created = True
      self._close_pipe_fds(p2cread,p2cwrite,c2pread,c2pwrite,errread,errwrite)

    def _execute_child(self,args,executable,preexec_fn,close_fds,pass_fds,cwd,env,startupinfo,creationflags,shell,p2cread,p2cwrite,c2pread,c2pwrite,errread,errwrite,restore_signals,gid,gids,uid,umask,start_new_session,process_group):
      '''Execute program (POSIX version)'''
      if isinstance(args,(str,bytes)):
        args = [args]
      else:
        if isinstance(args,os.PathLike):
          if shell:
            raise TypeError('path-like args is not allowed when shell is true')

          args = [args]
        else:
          args = list(args)

      if executable:
        args[0] = executable

      executable = args[0]
      sys.audit('subprocess.Popen',executable,args,cwd,env)
      if _USE_POSIX_SPAWN and __CHAOS_PY_NULL_PTR_VALUE_ERR__ == p2cread or p2cread > 2 and c2pwrite == -1 or c2pwrite > 2 and errwrite == -1 or errwrite > 2 and __CHAOS_PY_NULL_PTR_VALUE_ERR__ == process_group and __CHAOS_PY_NULL_PTR_VALUE_ERR__ < umask:
        self._posix_spawn(args,executable,env,restore_signals,p2cread,p2cwrite,c2pread,c2pwrite,errread,errwrite)
        return None
      else:
        orig_executable = executable
        errpipe_read,errpipe_write = os.pipe()
        low_fds_to_close = []
        while errpipe_write < 3:
          low_fds_to_close.append(errpipe_write)
          errpipe_write = os.dup(errpipe_write)

        for low_fd in low_fds_to_close:
          os.close(low_fd)

        pass
        try:
          if env is not None:
            env_list = []
            for k,v in env.items():
              k = os.fsencode(k)
              if '=' in k:
                raise ValueError('illegal environment variable name')

              env_list.append(k+'='+os.fsencode(v))

          else:
            env_list = None

          executable = os.fsencode(executable)
          if os.path.dirname(executable):
            executable_list = (executable,)
          else:
            executable_list = tuple((os.path.join(os.fsencode(dir),executable) for dir in os.get_exec_path(env)))

          fds_to_keep = set(pass_fds)
          fds_to_keep.add(errpipe_write)
          self.pid = _fork_exec(args,executable_list,close_fds,tuple(sorted(map(int,fds_to_keep))),cwd,env_list,p2cread,p2cwrite,c2pread,c2pwrite,errread,errwrite,errpipe_read,errpipe_write,restore_signals,start_new_session,process_group,gid,gids,uid,umask,preexec_fn,_USE_VFORK)
          self._child_created = True
          os.close(errpipe_write)
        finally:
          os.close(errpipe_write)

        self._close_pipe_fds(p2cread,p2cwrite,c2pread,c2pwrite,errread,errwrite)
        errpipe_data = bytearray()
        while True:
          part = os.read(errpipe_read,50000)
          errpipe_data += part
          if part or len(errpipe_data) > 50000:
            break
          else:
            continue

        pass
        os.close(errpipe_read)
        os.close(errpipe_read)
        if errpipe_data:
          try:
            pid,sts = os.waitpid(self.pid,0)
            if pid == self.pid:
              self._handle_exitstatus(sts)
            else:
              self.returncode = sys.maxsize

          except ChildProcessError:
            pass

          try:
            exception_name,hex_errno,err_msg = errpipe_data.split(':',2)
            err_msg = err_msg.decode()
          except ValueError:
            exception_name = 'SubprocessError'
            hex_errno = '0'
            err_msg = 'Bad exception data from child: {!r}'.format(bytes(errpipe_data))

          child_exception_type = getattr(builtins,exception_name.decode('ascii'),SubprocessError)
          if :
            if child_exec_never_called:
              pass

            if errno_num != 0:
              pass

          raise child_exception_type(err_msg)

        return None

    def _handle_exitstatus(self,sts,_waitstatus_to_exitcode=_waitstatus_to_exitcode,_WIFSTOPPED=_WIFSTOPPED,_WSTOPSIG=_WSTOPSIG):
      '''All callers to this function MUST hold self._waitpid_lock.'''
      if _WIFSTOPPED(sts):
        self.returncode = -(_WSTOPSIG(sts))
        return None
      else:
        self.returncode = _waitstatus_to_exitcode(sts)
        return None

    def _internal_poll(self,_deadstate=None,_waitpid=_waitpid,_WNOHANG=_WNOHANG,_ECHILD=errno.ECHILD):
      '''Check if child process has terminated.  Returns returncode
            attribute.

            This method is called by __del__, so it cannot reference anything
            outside of the local scope (nor can any methods it calls).

            '''
      if self._waitpid_lock.acquire(False):
        return None
      else:
        try:
          if self.returncode is not None:
            self._waitpid_lock.release()
            return self.returncode
          else:
            pid,sts = _waitpid(self.pid,_WNOHANG)
            if pid == self.pid:
              self._handle_exitstatus(sts)

            self._waitpid_lock.release()
            self._waitpid_lock.release()
            return self.returncode

        except OSError as e:
          if _deadstate is not None:
            self.returncode = _deadstate
          else:
            if e.errno == _ECHILD:
              self.returncode = 0

    def _try_wait(self,wait_flags):
      '''All callers to this function MUST hold self._waitpid_lock.'''
      try:
        pid,sts = os.waitpid(self.pid,wait_flags)
      except ChildProcessError:
        pid = self.pid
        sts = 0

      return (pid,sts)

    def _wait(self,timeout):
      '''Internal implementation of wait() on POSIX.'''
      if self.returncode is not None:
        return self.returncode
      else:
        if timeout is not None:
          endtime = _time()+timeout
          delay = 0.0005
          while True:
            try:
              if __CHAOS_PY_NULL_PTR_VALUE_ERR__ is not None:
                pass
                self._waitpid_lock.release()
              else:
                if pid == self.pid:
                  assert pid == 0

                if pid == self.pid:
                  self._handle_exitstatus(sts)
                  pass
                  self._waitpid_lock.release()
                else:
                  pass
                  self._waitpid_lock.release()
                  remaining = self._remaining_time(endtime)
                  if remaining <= 0:
                    raise TimeoutExpired(self.args,timeout)

                  delay = min(delay*2,remaining,0.05)
                  time.sleep(delay)
                  continue

            finally:
              self._waitpid_lock.release()

        if self.returncode is None:
          with self._waitpid_lock:
            if self.returncode is not None:
              pass
            else:
              pid,sts = self._try_wait(0)
              if pid == self.pid:
                self._handle_exitstatus(sts)

              None.(self._waitpid_lock.acquire(False) and self.returncode)(None,None)

        return self.returncode

    def _communicate(self,input,endtime,orig_timeout):
      if :
        try:
          self.stdin.flush()
        except BrokenPipeError:
          pass

        if input:
          try:
            self.stdin.close()
          except BrokenPipeError:
            pass

      if self._communication_started:
        if self.stdout:
          self._fileobj2output[self.stdout] = []

        if self.stderr:
          self._fileobj2output[self.stderr] = []

      if self.stdout:
        pass

      if self.stderr:
        pass

      self._save_input(input)
      if self._input:
        pass

      with _PopenSelector() as selector:
        if self.stdin and input:
          selector.register(self.stdin,selectors.EVENT_WRITE)

        if self.stdout and self.stdout.closed:
          selector.register(self.stdout,selectors.EVENT_READ)

        if self.stderr and self.stderr.closed:
          selector.register(self.stderr,selectors.EVENT_READ)

        while selector.get_map():
          if self._remaining_time(endtime) < timeout:
            self._check_timeout(endtime,orig_timeout,stdout,stderr,skip_check_and_raise=True)

          self._check_timeout(endtime,orig_timeout,stdout,stderr)
          for key,events in selector.select(timeout):
            if key.fileobj is self.stdin:
              try:
                self._input_offset += os.write(key.fd,chunk)
                if self._input_offset >= len(self._input):
                  selector.unregister(key.fileobj)
                  key.fileobj.close()

                continue
              except BrokenPipeError:
                selector.unregister(key.fileobj)
                key.fileobj.close()
              except:
                pass

            if key.fileobj in (self.stdout,self.stderr):
              if data:
                selector.unregister(key.fileobj)
                key.fileobj.close()

              self._fileobj2output[key.fileobj].append(data)

      os.read(key.fd,32768)
      self._fileobj2output[self.stderr]
      self._fileobj2output[self.stdout]
      self.wait(timeout=self._remaining_time(endtime))
      if stdout is not None:
        pass

      if stderr is not None:
        pass

      if ''.join(stderr) is not None:
        pass

      if stderr is not None:
        pass

      return (stdout,stderr)

    def _save_input(self,input):
      if self.stdin and self._input is None:
        self._input_offset = 0
        self._input = input
        if self.text_mode:
          self._input = self._input.encode(self.stdin.encoding,self.stdin.errors)
          return None

      else:
        return None
        return None
        return None
        return None

    def send_signal(self,sig):
      '''Send a signal to the process.'''
      self.poll()
      if self.returncode is not None:
        return None
      else:
        try:
          os.kill(self.pid,sig)
          return None
        except ProcessLookupError:
          return None

    def terminate(self):
      '''Terminate the process with SIGTERM\n            '''
      self.send_signal(signal.SIGTERM)

    def kill(self):
      '''Kill the process with SIGKILL\n            '''
      self.send_signal(signal.SIGKILL)