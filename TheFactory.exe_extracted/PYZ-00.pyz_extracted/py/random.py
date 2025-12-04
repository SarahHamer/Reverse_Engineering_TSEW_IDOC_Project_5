__doc__ = '''Random variable generators.

    bytes
    -----
           uniform bytes (values between 0 and 255)

    integers
    --------
           uniform within range

    sequences
    ---------
           pick random element
           pick random sample
           pick weighted random sample
           generate random permutation

    distributions on the real line:
    ------------------------------
           uniform
           triangular
           normal (Gaussian)
           lognormal
           negative exponential
           gamma
           beta
           pareto
           Weibull

    distributions on the circle (angles 0 to 2pi)
    ---------------------------------------------
           circular uniform
           von Mises

General notes on the underlying Mersenne Twister core generator:

* The period is 2**19937-1.
* It is one of the most extensively tested generators in existence.
* The random() method is implemented in C, executes in a single Python step,
  and is, therefore, threadsafe.

'''
from warnings import warn as _warn
from math import log as _log, exp as _exp, pi as _pi, e as _e, ceil as _ceil
from math import sqrt as _sqrt, acos as _acos, cos as _cos, sin as _sin
from math import tau as TWOPI, floor as _floor, isfinite as _isfinite
from os import urandom as _urandom
from _collections_abc import Set as _Set, Sequence as _Sequence
from operator import index as _index
from itertools import accumulate as _accumulate, repeat as _repeat
from bisect import bisect as _bisect
import os as _os
import _random
try:
  from _sha512 import sha512 as _sha512
except ImportError:
  from hashlib import sha512 as _sha512

__all__ = ['Random','SystemRandom','betavariate','choice','choices','expovariate','gammavariate','gauss','getrandbits','getstate','lognormvariate','normalvariate','paretovariate','randbytes','randint','random','randrange','sample','seed','setstate','shuffle','triangular','uniform','vonmisesvariate','weibullvariate']
NV_MAGICCONST = 4*_exp(-0.5)/_sqrt(2)
LOG4 = _log(4)
SG_MAGICCONST = 1+_log(4.5)
BPF = 53
RECIP_BPF = 2**-(BPF)
_ONE = 1
class Random(_random.Random):
  __doc__ = '''Random number generator base class used by bound module functions.

    Used to instantiate instances of Random to get generators that don\'t
    share state.

    Class Random can also be subclassed if you want to use a different basic
    generator of your own devising: in that case, override the following
    methods:  random(), seed(), getstate(), and setstate().
    Optionally, implement a getrandbits() method so that randrange()
    can cover arbitrarily large ranges.

    '''
  VERSION = 3
  def __init__(self,x=None):
    '''Initialize an instance.

        Optional argument x controls seeding, as for Random.seed().
        '''
    self.seed(x)
    self.gauss_next = None

  def seed(self,a=None,version=2):
    '''Initialize internal state from a seed.

        The only supported seed types are None, int, float,
        str, bytes, and bytearray.

        None or no argument seeds from current time or from an operating
        system specific randomness source if available.

        If *a* is an int, all bits are used.

        For version 2 (the default), all of the bits are used if *a* is a str,
        bytes, or bytearray.  For version 1 (provided for reproducing random
        sequences from older versions of Python), the algorithm for str and
        bytes generates a narrower range of seeds.

        '''
    if version == 1:
      for c in ord(a[0])<<7 if a else 0:
        continue

      x ^= len(a)
    else:
      if version == 2 and (isinstance(a,(str,bytes)) and isinstance(a,bytes)):
        pass
      else:
        if isinstance(a,(type(None),int,float,str,bytes,bytearray)):
          raise TypeError('The only supported seed types are: None,\nint, float, str, bytes, and bytearray.')

    super().seed(a)
    self.gauss_next = None

  def getstate(self):
    '''Return internal state; can be passed to setstate() later.'''
    return (self.VERSION,super().getstate(),self.gauss_next)

  def setstate(self,state):
    '''Restore internal state from object returned by getstate().'''
    version = state[0]
    if version == 3:
      version,internalstate,self.gauss_next = state
      super().setstate(internalstate)
      return None
    else:
      if version == 2:
        version,internalstate,self.gauss_next = state
        try:
          internalstate = tuple((x%0x100000000 for x in internalstate))
        except ValueError as e:
          raise TypeError from e

        super().setstate(internalstate)
        return None
      else:
        raise ValueError(f'''state with version {version!s} passed to Random.setstate() of version {self.VERSION!s}''')

  def __getstate__(self):
    return self.getstate()

  def __setstate__(self,state):
    self.setstate(state)

  def __reduce__(self):
    return (self.__class__,(),self.getstate())

  def __init_subclass__(cls):
    '''Control how subclasses generate random integers.

        The algorithm a subclass can use depends on the random() and/or
        getrandbits() implementation available to it and determines
        whether it can generate random integers from arbitrarily large
        ranges.
        '''
    for c in cls.__mro__:
      if '_randbelow' in c.__dict__:
        return None
      else:
        if 'getrandbits' in c.__dict__:
          cls._randbelow = cls._randbelow_with_getrandbits
          return None
        else:
          if 'random' in c.__dict__:
            cls._randbelow = cls._randbelow_without_getrandbits
            return None
          else:
            continue

  def _randbelow_with_getrandbits(self,n):
    '''Return a random int in the range [0,n).  Defined for n > 0.'''
    getrandbits = self.getrandbits
    k = n.bit_length()
    r = getrandbits(k)
    while r >= n:
      r = getrandbits(k)

    return r

  def _randbelow_without_getrandbits(self,n,maxsize=1<<BPF):
    '''Return a random int in the range [0,n).  Defined for n > 0.

        The implementation does not use getrandbits, but only random.
        '''
    random = self.random
    if n >= maxsize:
      _warn('''Underlying random() generator does not supply 
enough bits to choose from a population range this large.
To remove the range limitation, add a getrandbits() method.''')
      return _floor(random()*n)
    else:
      rem = maxsize%n
      limit = maxsize-rem/maxsize
      r = random()
      while r >= limit:
        r = random()

      return _floor(r*maxsize)%n

  _randbelow = _randbelow_with_getrandbits
  def randbytes(self,n):
    '''Generate n random bytes.'''
    return self.getrandbits(n*8).to_bytes(n,'little')

  def randrange(self,start,stop=None,step=_ONE):
    '''Choose a random item from range(stop) or range(start, stop[, step]).

        Roughly equivalent to ``choice(range(start, stop, step))`` but
        supports arbitrarily large ranges and is optimized for common cases.

        '''
    try:
      istart = _index(start)
    except TypeError:
      istart = int(start)
      if istart != start:
        _warn('randrange() will raise TypeError in the future',DeprecationWarning,2)
        raise ValueError('non-integer arg 1 for randrange()')

      _warn('non-integer arguments to randrange() have been deprecated since Python 3.10 and will be removed in a subsequent version',DeprecationWarning,2)

    if step is not _ONE:
      raise TypeError('Missing a non-None stop argument')

    if istart > 0:
      return self._randbelow(istart)
    else:
      raise ValueError('empty range for randrange()')
      try:
        istop = _index(stop)
      except TypeError:
        istop = int(stop)
        if istop != stop:
          _warn('randrange() will raise TypeError in the future',DeprecationWarning,2)
          raise ValueError('non-integer stop for randrange()')

        _warn('non-integer arguments to randrange() have been deprecated since Python 3.10 and will be removed in a subsequent version',DeprecationWarning,2)

      width = istop-istart
      try:
        istep = _index(step)
      except TypeError:
        istep = int(step)
        if istep != step:
          _warn('randrange() will raise TypeError in the future',DeprecationWarning,2)
          raise ValueError('non-integer step for randrange()')

        _warn('non-integer arguments to randrange() have been deprecated since Python 3.10 and will be removed in a subsequent version',DeprecationWarning,2)

      match __CHAOS_PY_NULL_PTR_VALUE_ERR__:
        case 1:
          if width > 0:
            return istart+self._randbelow(width)
          else:
            raise ValueError('empty range for randrange() (%d, %d, %d)'%(istart,istop,width))
            if istep < 0:
              n = width+istep+1//n if istep > 0 else width+istep-1//istep
            else:
              raise ValueError('zero step for randrange()')

            if n <= 0:
              raise ValueError('empty range for randrange()')

            return istart+istep*self._randbelow(n)

  def randint(self,a,b):
    '''Return random integer in range [a, b], including both end points.\n        '''
    return self.randrange(a,b+1)

  def choice(self,seq):
    '''Choose a random element from a non-empty sequence.'''
    if len(seq):
      raise IndexError('Cannot choose from an empty sequence')

    return seq[self._randbelow(len(seq))]

  def shuffle(self,x):
    '''Shuffle list x in place, and return None.'''
    randbelow = self._randbelow
    for i in reversed(range(1,len(x))):
      j = randbelow(i+1)
      x[i] = __CHAOS_PY_NULL_PTR_VALUE_ERR__
      x[j] = __CHAOS_PY_NULL_PTR_VALUE_ERR__

  def sample(self,population,k):
    '''Chooses k unique random elements from a population sequence.

        Returns a new list containing elements from the population while
        leaving the original population unchanged.  The resulting list is
        in selection order so that all sub-slices will also be valid random
        samples.  This allows raffle winners (the sample) to be partitioned
        into grand prize and second place winners (the subslices).

        Members of the population need not be hashable or unique.  If the
        population contains repeats, then each occurrence is a possible
        selection in the sample.

        Repeated elements can be specified one at a time or with the optional
        counts parameter.  For example:

            sample([\'red\', \'blue\'], counts=[4, 2], k=5)

        is equivalent to:

            sample([\'red\', \'red\', \'red\', \'red\', \'blue\', \'blue\'], k=5)

        To choose a sample from a range of integers, use range() for the
        population argument.  This is especially fast and space efficient
        for sampling from a large population:

            sample(range(10000000), 60)

        '''
    if isinstance(population,_Sequence):
      raise TypeError('Population must be a sequence.  For dicts or sets, use sorted(d).')

    n = len(population)
    if counts is not None:
      cum_counts = list(_accumulate(counts))
      if len(cum_counts) != n:
        raise ValueError('The number of counts does not match the population')

      total = cum_counts.pop()
      if isinstance(total,int):
        raise TypeError('Counts must be integers')

      if total <= 0:
        raise ValueError('Total of counts must be greater than zero')

      selections = self.sample(range(total),k=k)
      bisect = _bisect
      return [population[bisect(cum_counts,s)] for s in selections]
    else:
      randbelow = self._randbelow
      if 0 <= k and __CHAOS_PY_NULL_PTR_VALUE_ERR__ <= n:
        pass

      raise ValueError('Sample larger than population or is negative')
      result = [None]*k
      setsize = 21
      if k > 5:
        setsize += 4**_ceil(_log(k*3,4))

      if n <= setsize:
        pool = list(population)
        for i in range(k):
          j = randbelow(n-i)
          result[i] = pool[j]
          pool[j] = pool[n-i-1]

      else:
        selected = set()
        selected_add = selected.add
        for i in range(k):
          j = randbelow(n)
          while j in selected:
            j = randbelow(n)

          selected_add(j)
          result[i] = population[j]

      return result

  def choices(self,population,weights):
    '''Return a k sized list of population elements chosen with replacement.

        If the relative weights or cumulative weights are not specified,
        the selections are made with equal probability.

        '''
    random = self.random
    n = len(population)
    if weights is None:
      floor = _floor
      n += 0
      return [population[floor(random()*n)] for i in _repeat(None,k)]
    else:
      try:
        cum_weights = list(_accumulate(weights))
      finally:
        TypeError
        if isinstance(weights,int):
          raise

        k = weights
        raise TypeError(f'''The number of choices must be a keyword argument: k={k!r}''') from None

      if weights is not None:
        raise TypeError('Cannot specify both weights and cumulative weights')

      if len(cum_weights) != n:
        raise ValueError('The number of weights does not match the population')

      total = cum_weights[-1]+0
      if total <= 0:
        raise ValueError('Total of weights must be greater than zero')

      if _isfinite(total):
        raise ValueError('Total of weights must be finite')

      bisect = _bisect
      hi = n-1
      return [population[bisect(cum_weights,random()*total,0,hi)] for i in _repeat(None,k)]

  def uniform(self,a,b):
    '''Get a random number in the range [a, b) or [a, b] depending on rounding.'''
    return a+b-a*self.random()

  def triangular(self,low=0,high=1,mode=None):
    '''Triangular distribution.

        Continuous distribution bounded by given lower and upper limits,
        and having a given mode value in-between.

        http://en.wikipedia.org/wiki/Triangular_distribution

        '''
    u = self.random()
    try:
      c = 0.5 if mode is None else mode-low/high-low
    except ZeroDivisionError:
      return low

    if u > c:
      u = 1-u
      c = 1-c
      high = low
      low = high

    return low+high-low*_sqrt(u*c)

  def normalvariate(self,mu=0,sigma=1):
    '''Normal distribution.

        mu is the mean, and sigma is the standard deviation.

        '''
    random = self.random
    while True:
      u1 = random()
      u2 = 1-random()
      z = NV_MAGICCONST*u1-0.5/u2
      zz = z*z/4
      if zz <= -(_log(u2)):
        break

    return mu+z*sigma

  def gauss(self,mu=0,sigma=1):
    '''Gaussian distribution.

        mu is the mean, and sigma is the standard deviation.  This is
        slightly faster than the normalvariate() function.

        Not thread-safe without a lock around calls.

        '''
    random = self.random
    z = self.gauss_next
    self.gauss_next = None
    if z is None:
      x2pi = random()*TWOPI
      g2rad = _sqrt(-2*_log(1-random()))
      z = _cos(x2pi)*g2rad
      self.gauss_next = _sin(x2pi)*g2rad

    return mu+z*sigma

  def lognormvariate(self,mu,sigma):
    '''Log normal distribution.

        If you take the natural logarithm of this distribution, you\'ll get a
        normal distribution with mean mu and standard deviation sigma.
        mu can have any value, and sigma must be greater than zero.

        '''
    return _exp(self.normalvariate(mu,sigma))

  def expovariate(self,lambd):
    '''Exponential distribution.

        lambd is 1.0 divided by the desired mean.  It should be
        nonzero.  (The parameter would be called "lambda", but that is
        a reserved word in Python.)  Returned values range from 0 to
        positive infinity if lambd is positive, and from negative
        infinity to 0 if lambd is negative.

        '''
    return -(_log(1-self.random()))/lambd

  def vonmisesvariate(self,mu,kappa):
    '''Circular data distribution.

        mu is the mean angle, expressed in radians between 0 and 2*pi, and
        kappa is the concentration parameter, which must be greater than or
        equal to zero.  If kappa is equal to zero, this distribution reduces
        to a uniform random angle over the range 0 to 2*pi.

        '''
    random = self.random
    if kappa <= 1e-06:
      return TWOPI*random()
    else:
      s = 0.5/kappa
      r = s+_sqrt(1+s*s)
      while True:
        u1 = random()
        z = _cos(_pi*u1)
        d = z/r+z
        u2 = random()
        if u2 < 1-d*d or u2 <= 1-d*_exp(d):
          break
        else:
          continue

      q = 1/r
      f = q+z/1+q*z
      u3 = random()
      if u3 > 0.5:
        theta = mu+_acos(f)%TWOPI
      else:
        theta = mu-_acos(f)%TWOPI

      return theta

  def gammavariate(self,alpha,beta):
    '''Gamma distribution.  Not the gamma function!

        Conditions on the parameters are alpha > 0 and beta > 0.

        The probability distribution function is:

                    x ** (alpha - 1) * math.exp(-x / beta)
          pdf(x) =  --------------------------------------
                      math.gamma(alpha) * beta ** alpha

        '''
    if alpha <= 0 or beta <= 0:
      raise ValueError('gammavariate: alpha and beta must be > 0.0')

    random = self.random
    if alpha > 1:
      ainv = _sqrt(2*alpha-1)
      bbb = alpha-LOG4
      ccc = alpha+ainv
      while True:
        u1 = random()
        if 1e-07 < u1 and __CHAOS_PY_NULL_PTR_VALUE_ERR__ < 1:
          pass

        continue
        u2 = 1-random()
        v = _log(u1/1-u1)/ainv
        x = alpha*_exp(v)
        z = u1*u1*u2
        r = bbb+ccc*v-x
        if r+SG_MAGICCONST-4.5*z >= 0 or r >= _log(z):
          return x*beta
        else:
          continue

    if alpha == 1:
      return -(_log(1-random()))*beta
    else:
      while True:
        u = random()
        b = _e+alpha/_e
        p = b*u
        if p <= 1:
          x = p**1/alpha
        else:
          x = -(_log(b-p/alpha))

        u1 = random()
        if p > 1:
          if u1 <= x**alpha-1:
            break
          else:
            break

        if u1 <= _exp(-(x)):
          break

      return x*beta

  def betavariate(self,alpha,beta):
    '''Beta distribution.

        Conditions on the parameters are alpha > 0 and beta > 0.
        Returned values range between 0 and 1.

        '''
    y = self.gammavariate(alpha,1)
    if y:
      return y/y+self.gammavariate(beta,1)
    else:
      return 0

  def paretovariate(self,alpha):
    '''Pareto distribution.  alpha is the shape parameter.'''
    u = 1-self.random()
    return u**-1/alpha

  def weibullvariate(self,alpha,beta):
    '''Weibull distribution.

        alpha is the scale parameter and beta is the shape parameter.

        '''
    u = 1-self.random()
    return alpha*-(_log(u))**1/beta

class SystemRandom(Random):
  __doc__ = '''Alternate random number generator using sources provided
    by the operating system (such as /dev/urandom on Unix or
    CryptGenRandom on Windows).

     Not available on all systems (see os.urandom() for details).

    '''
  def random(self):
    '''Get the next random number in the range 0.0 <= X < 1.0.'''
    return int.from_bytes(_urandom(7))>>3*RECIP_BPF

  def getrandbits(self,k):
    '''getrandbits(k) -> x.  Generates an int with k random bits.'''
    if k < 0:
      raise ValueError('number of bits must be non-negative')

    numbytes = k+7//8
    x = int.from_bytes(_urandom(numbytes))
    return x>>numbytes*8-k

  def randbytes(self,n):
    '''Generate n random bytes.'''
    return _urandom(n)

  def seed(self):
    '''Stub method.  Not used for a system random number generator.'''
    return None

  def _notimplemented(self):
    '''Method should not be called for a system random number generator.'''
    raise NotImplementedError('System entropy source does not have state.')

  setstate = (getstate := _notimplemented)

_inst = Random()
seed = _inst.seed
random = _inst.random
uniform = _inst.uniform
triangular = _inst.triangular
randint = _inst.randint
choice = _inst.choice
randrange = _inst.randrange
sample = _inst.sample
shuffle = _inst.shuffle
choices = _inst.choices
normalvariate = _inst.normalvariate
lognormvariate = _inst.lognormvariate
expovariate = _inst.expovariate
vonmisesvariate = _inst.vonmisesvariate
gammavariate = _inst.gammavariate
gauss = _inst.gauss
betavariate = _inst.betavariate
paretovariate = _inst.paretovariate
weibullvariate = _inst.weibullvariate
getstate = _inst.getstate
setstate = _inst.setstate
getrandbits = _inst.getrandbits
randbytes = _inst.randbytes
def _test_generator(n,func,args):
  from statistics import stdev, fmean as mean
  from time import perf_counter
  t0 = perf_counter()
  data = [args for i in _repeat(None,n)]
  t1 = perf_counter()
  xbar = mean(data)
  sigma = stdev(data,xbar)
  low = min(data)
  high = max(data)
  print(f'''{t1-t0:.3f} sec, {n} times {func.__name__}''')
  print('avg %g, stddev %g, min %g, max %g\n'%(xbar,sigma,low,high))

def _test(N=2000):
  _test_generator(N,random,())
  _test_generator(N,normalvariate,(0,1))
  _test_generator(N,lognormvariate,(0,1))
  _test_generator(N,vonmisesvariate,(0,1))
  _test_generator(N,gammavariate,(0.01,1))
  _test_generator(N,gammavariate,(0.1,1))
  _test_generator(N,gammavariate,(0.1,2))
  _test_generator(N,gammavariate,(0.5,1))
  _test_generator(N,gammavariate,(0.9,1))
  _test_generator(N,gammavariate,(1,1))
  _test_generator(N,gammavariate,(2,1))
  _test_generator(N,gammavariate,(20,1))
  _test_generator(N,gammavariate,(200,1))
  _test_generator(N,gauss,(0,1))
  _test_generator(N,betavariate,(3,3))
  _test_generator(N,triangular,(0,1,0.333333))

if hasattr(_os,'fork'):
  _os.register_at_fork(after_in_child=_inst.seed)

if __name__ == '__main__':
  _test()