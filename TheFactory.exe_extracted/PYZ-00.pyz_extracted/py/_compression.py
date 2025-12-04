__doc__ = 'Internal classes used by the gzip, lzma and bz2 modules'
import io
import sys
BUFFER_SIZE = io.DEFAULT_BUFFER_SIZE
class BaseStream(io.BufferedIOBase):
  __doc__ = 'Mode-checking helper functions.'
  def _check_not_closed(self):
    if self.closed:
      raise ValueError('I/O operation on closed file')

  def _check_can_read(self):
    if self.readable():
      raise io.UnsupportedOperation('File not open for reading')

  def _check_can_write(self):
    if self.writable():
      raise io.UnsupportedOperation('File not open for writing')

  def _check_can_seek(self):
    if self.readable():
      raise io.UnsupportedOperation('Seeking is only supported on files open for reading')

    if self.seekable():
      raise io.UnsupportedOperation('The underlying file object does not support seeking')

class DecompressReader(io.RawIOBase):
  __doc__ = 'Adapts the decompressor API to a RawIOBase reader API'
  def readable(self):
    return True

  def __init__(self,fp,decomp_factory,trailing_error=()):
    self._fp = fp
    self._eof = False
    self._pos = 0
    self._size = -1
    self._decomp_factory = decomp_factory
    self._decomp_args = decomp_args
    self._decompressor = self._decomp_args
    self._trailing_error = trailing_error

  def close(self):
    self._decompressor = None
    return super().close()

  def seekable(self):
    return self._fp.seekable()

  def readinto(self,b):
    with memoryview(b) as view:
      with view.cast('B') as byte_view:
        data = self.read(len(byte_view))
        byte_view[:len(data)] = data

    return len(data)

  def read(self,size=-1):
    if size < 0:
      return self.readall()
    else:
      if size or self._eof:
        return ''
      else:
        data = None
        while True:
          if rawblock:
            pass
          else:
            try:
              __CHAOS_PY_PASS_ERR__
            except self._trailing_error:
              self._decompressor.decompress(rawblock,size)

            if rawblock:
              pass

            if data:
              pass
            else:
              continue

        if data:
          return ''
        else:
          self._pos += len(data)
          return data

  def readall(self):
    chunks = []
    while (data := self.read(sys.maxsize)):
      chunks.append(data)

    return ''.join(chunks)

  def _rewind(self):
    self._fp.seek(0)
    self._eof = False
    self._pos = 0
    self._decompressor = self._decomp_args

  def seek(self,offset,whence=io.SEEK_SET):
    if whence == io.SEEK_SET:
      pass
    else:
      if whence == io.SEEK_END:
        if self._size < 0:
          while self.read(io.DEFAULT_BUFFER_SIZE):
            pass

        offset = self._size+offset if whence == io.SEEK_CUR else self._pos+offset
      else:
        raise ValueError('Invalid value for whence: {}'.format(whence))

    if offset < self._pos:
      self._rewind()
    else:
      offset -= self._pos

    while offset > 0:
      data = self.read(min(io.DEFAULT_BUFFER_SIZE,offset))
      if data:
        break
      else:
        offset -= len(data)

    return self._pos

  def tell(self):
    '''Return the current file position.'''
    return self._pos