from jinja2.ext import Extension

import hashlib, re, random

class jinjafx(Extension):
  def __init__(self, environment):
    Extension.__init__(self, environment)
    environment.filters['cisco_snmpv3_key'] = self.__cisco_snmpv3_key
    environment.filters['junos_snmpv3_key'] = self.__junos_snmpv3_key
    environment.filters['cisco7encode'] = self.__cisco7encode
    environment.filters['junos9encode'] = self.__junos9encode

  def __expand_snmpv3_key(self, password, algorithm):
    h = hashlib.new(algorithm)
    h.update(((password * (1048576 // len(password))) + password[:1048576 % len(password)]).encode('utf-8'))
    return h.digest()

  def __cisco_snmpv3_key(self, password, engineid, algorithm='sha1'):
    ekey = self.__expand_snmpv3_key(password, algorithm)

    h = hashlib.new(algorithm)
    h.update(ekey + bytearray.fromhex(engineid) + ekey)
    return ':'.join([h.hexdigest()[i:i + 2] for i in range(0, len(h.hexdigest()), 2)])

  def __junos_snmpv3_key(self, password, engineid, algorithm='sha1', prefix='80000a4c'):
    ekey = self.__expand_snmpv3_key(password, algorithm)

    if re.match(r'^(?:[a-f0-9]{2}:){5}[a-f0-9]{2}$', engineid):
      engineid = prefix + '03' + ''.join(engineid.split(':'))

    elif re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', engineid):
      engineid = prefix + '01' + ''.join("{:02x}".format(int(o), 2) for o in engineid.split('.'))

    else:
      engineid = prefix + '04' + ''.join("{:02x}".format(ord(c)) for c in engineid)

    h = hashlib.new(algorithm)
    h.update(ekey + bytearray.fromhex(engineid) + ekey)
    return h.hexdigest()

  def __cisco7encode(self, string, seed=False):
    KEY = 'dsfd;kfoA,.iyewrkldJKDHSUBsgvca69834ncxv9873254k;fg87'

    if seed:
      random.seed(seed)

    result = format(random.randint(0, 15), '02d')
    
    for i in range(0, len(string)):
      result += format(ord(string[i]) ^ ord(KEY[(i + int(result[:2])) % len(KEY)]), '02X')

    return result

  def __junos9encode(self, string, seed=False):
    ENCODING = [[1, 4, 32], [1, 16, 32], [1, 8, 32], [1, 64], [1, 32], [1, 4, 16, 128], [1, 32, 64]]
    FAMILY = ['QzF3n6/9CAtpu0O', 'B1IREhcSyrleKvMW8LXx', '7N-dVbwsY2g4oaJZGUDj', 'iHkq.mPf5T']
    EXTRA = { char: 3-i for i, f in enumerate(FAMILY) for char in f }
    NUM_ALPHA = [char for char in ''.join(FAMILY)]
    ALPHA_NUM = { NUM_ALPHA[i]: i for i, c in enumerate(NUM_ALPHA) }
  
    def random_salt(length):
      salt = ''

      for i in range(length):
        salt += NUM_ALPHA[random.randrange(len(NUM_ALPHA))]

      return salt
  
    def gap_encode(char, prev, encode):
      gaps = []
      val = ord(char)
      for e in encode[::-1]:
        gaps.insert(0, val // e)
        val %= e
  
      result = ''
      for g in gaps:
        g += ALPHA_NUM[prev] + 1
        c = prev = NUM_ALPHA[g % len(NUM_ALPHA)]
        result += c
  
      return result
  
    if seed:
      random.seed(seed)
  
    salt = random_salt(1)
    rand = random_salt(EXTRA[salt])
  
    pos = 0
    prev = salt
    result = '$9$' + salt + rand
  
    for char in string:
      result += gap_encode(char, prev, ENCODING[pos % len(ENCODING)])
      prev = result[-1]
      pos += 1
  
    return result
