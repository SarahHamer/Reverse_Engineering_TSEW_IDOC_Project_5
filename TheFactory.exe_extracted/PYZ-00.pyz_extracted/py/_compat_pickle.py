IMPORT_MAPPING = {'Tix':'tkinter.tix','Tkconstants':'tkinter.constants','ScrolledText':'tkinter.scrolledtext','tkMessageBox':'tkinter.messagebox','tkFont':'tkinter.font','Tkdnd':'tkinter.dnd','Dialog':'tkinter.dialog','tkCommonDialog':'tkinter.commondialog','tkColorChooser':'tkinter.colorchooser','tkSimpleDialog':'tkinter.simpledialog','tkFileDialog':'tkinter.filedialog','repr':'reprlib','ConfigParser':'configparser','SocketServer':'socketserver','Queue':'queue','copy_reg':'copyreg','__builtin__':'builtins'}
NAME_MAPPING = {('_multiprocessing','Connection'):('multiprocessing.connection','Connection'),('_socket','fromfd'):('socket','fromfd'),('whichdb','whichdb'):('dbm','whichdb'),('UserString','UserString'):('collections','UserString'),('UserList','UserList'):('collections','UserList'),('UserDict','IterableUserDict'):('collections','UserDict'),('itertools','izip_longest'):('itertools','zip_longest'),('itertools','ifilterfalse'):('itertools','filterfalse'),('itertools','ifilter'):('builtins','filter'),('itertools','imap'):('builtins','map'),('itertools','izip'):('builtins','zip'),('__builtin__','long'):('builtins','int'),('__builtin__','unicode'):('builtins','str'),('__builtin__','unichr'):('builtins','chr'),('__builtin__','intern'):('sys','intern'),('__builtin__','reduce'):('functools','reduce'),('__builtin__','xrange'):('builtins','range')}
PYTHON2_EXCEPTIONS = ('ArithmeticError','AssertionError','AttributeError','BaseException','BufferError','BytesWarning','DeprecationWarning','EOFError','EnvironmentError','Exception','FloatingPointError','FutureWarning','GeneratorExit','IOError','ImportError','ImportWarning','IndentationError','IndexError','KeyError','KeyboardInterrupt','LookupError','MemoryError','NameError','NotImplementedError','OSError','OverflowError','PendingDeprecationWarning','ReferenceError','RuntimeError','RuntimeWarning','StopIteration','SyntaxError','SyntaxWarning','SystemError','SystemExit','TabError','TypeError','UnboundLocalError','UnicodeDecodeError','UnicodeEncodeError','UnicodeError','UnicodeTranslateError','UnicodeWarning','UserWarning','ValueError','Warning','ZeroDivisionError')
try:
  WindowsError
except NameError:
  pass

PYTHON2_EXCEPTIONS += ('WindowsError',)
for excname in PYTHON2_EXCEPTIONS:
  NAME_MAPPING[('exceptions',excname)] = ('builtins',excname)

MULTIPROCESSING_EXCEPTIONS = ('AuthenticationError','BufferTooShort','ProcessError','TimeoutError')
for excname in MULTIPROCESSING_EXCEPTIONS:
  NAME_MAPPING[('multiprocessing',excname)] = ('multiprocessing.context',excname)

REVERSE_IMPORT_MAPPING = dict(((v,k) for k,v in IMPORT_MAPPING.items()))
assert len(REVERSE_IMPORT_MAPPING) == len(IMPORT_MAPPING)
REVERSE_NAME_MAPPING = dict(((v,k) for k,v in NAME_MAPPING.items()))
assert len(REVERSE_NAME_MAPPING) == len(NAME_MAPPING)
IMPORT_MAPPING.update({'cPickle':'pickle','_elementtree':'xml.etree.ElementTree','FileDialog':'tkinter.filedialog','SimpleDialog':'tkinter.simpledialog','DocXMLRPCServer':'xmlrpc.server','SimpleHTTPServer':'http.server','CGIHTTPServer':'http.server','UserDict':'collections','UserList':'collections','UserString':'collections','whichdb':'dbm','StringIO':'io','cStringIO':'io'})
REVERSE_IMPORT_MAPPING.update({'_bz2':'bz2','_dbm':'dbm','_functools':'functools','_gdbm':'gdbm','_pickle':'pickle'})
NAME_MAPPING.update({('__builtin__','basestring'):('builtins','str'),('exceptions','StandardError'):('builtins','Exception'),('UserDict','UserDict'):('collections','UserDict'),('socket','_socketobject'):('socket','SocketType')})
REVERSE_NAME_MAPPING.update({('_functools','reduce'):('__builtin__','reduce'),('tkinter.filedialog','FileDialog'):('FileDialog','FileDialog'),('tkinter.filedialog','LoadFileDialog'):('FileDialog','LoadFileDialog'),('tkinter.filedialog','SaveFileDialog'):('FileDialog','SaveFileDialog'),('tkinter.simpledialog','SimpleDialog'):('SimpleDialog','SimpleDialog'),('xmlrpc.server','ServerHTMLDoc'):('DocXMLRPCServer','ServerHTMLDoc'),('xmlrpc.server','XMLRPCDocGenerator'):('DocXMLRPCServer','XMLRPCDocGenerator'),('xmlrpc.server','DocXMLRPCRequestHandler'):('DocXMLRPCServer','DocXMLRPCRequestHandler'),('xmlrpc.server','DocXMLRPCServer'):('DocXMLRPCServer','DocXMLRPCServer'),('xmlrpc.server','DocCGIXMLRPCRequestHandler'):('DocXMLRPCServer','DocCGIXMLRPCRequestHandler'),('http.server','SimpleHTTPRequestHandler'):('SimpleHTTPServer','SimpleHTTPRequestHandler'),('http.server','CGIHTTPRequestHandler'):('CGIHTTPServer','CGIHTTPRequestHandler'),('_socket','socket'):('socket','_socketobject')})
PYTHON3_OSERROR_EXCEPTIONS = ('BrokenPipeError','ChildProcessError','ConnectionAbortedError','ConnectionError','ConnectionRefusedError','ConnectionResetError','FileExistsError','FileNotFoundError','InterruptedError','IsADirectoryError','NotADirectoryError','PermissionError','ProcessLookupError','TimeoutError')
for excname in PYTHON3_OSERROR_EXCEPTIONS:
  REVERSE_NAME_MAPPING[('builtins',excname)] = ('exceptions','OSError')

PYTHON3_IMPORTERROR_EXCEPTIONS = ('ModuleNotFoundError',)
for excname in PYTHON3_IMPORTERROR_EXCEPTIONS:
  REVERSE_NAME_MAPPING[('builtins',excname)] = ('exceptions','ImportError')

del(excname)