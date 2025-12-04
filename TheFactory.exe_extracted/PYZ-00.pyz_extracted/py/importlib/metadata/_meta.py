from typing import Any, Dict, Iterator, List, Protocol, TypeVar, Union
_T = TypeVar('_T')
class PackageMetadata(Protocol):
  def __len__(self) -> int:
    return None

  def __contains__(self,item: str) -> bool:
    return None

  def __getitem__(self,key: str) -> str:
    return None

  def __iter__(self) -> Iterator[str]:
    return None

  def get_all(self,name: str,failobj: _T = [PYERR>] PycObject type: TYPE_ELLIPSIS [<PYERR]) -> Union[(List[Any],_T)]:
    '''
        Return all values associated with a possibly multi-valued key.
        '''
    return None

  @property
  def json(self) -> Dict[(str,Union[(str,List[str])])]:
    '''
        A JSON-compatible form of the metadata.
        '''
    return None

class SimplePath(Protocol):
  __doc__ = '''
    A minimal subset of pathlib.Path required by PathDistribution.
    '''
  def joinpath(self) -> SimplePath:
    return None

  def __truediv__(self) -> SimplePath:
    return None

  def parent(self) -> SimplePath:
    return None

  def read_text(self) -> str:
    return None