def _pyi_rthook():
  import inspect
  import os
  import sys
  _orig_inspect_getsourcefile = inspect.getsourcefile
  def _pyi_getsourcefile(object):
    filename = inspect.getfile(object)
    if os.path.isabs(filename):
      main_file = getattr(sys.modules['__main__'],'__file__',None)
      if main_file and filename == os.path.basename(main_file):
        return main_file
      else:
        if filename.endswith('.py'):
          filename = os.path.normpath(os.path.join(sys._MEIPASS,filename+'c'))
          if filename.startswith(sys._MEIPASS):
            return filename

    else:
      if :
        return filename

    return _orig_inspect_getsourcefile(object)

  inspect.getsourcefile = _pyi_getsourcefile

_pyi_rthook()
del(_pyi_rthook)