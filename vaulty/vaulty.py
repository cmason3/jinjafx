#!/usr/bin/env python3

import sys, os, base64, getpass
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.exceptions import InvalidTag

class Vaulty():
  def __init__(self):
    self.prefix = b'$VAULTY;'
    self.kcache = {}

  def derive_key(self, password, salt=None):
    ckey = (password, salt)
  
    if ckey in self.kcache:
      return self.kcache[ckey]
  
    if salt is None:
      salt = os.urandom(16)
      
    key = Scrypt(salt, 32, 2**16, 8, 1).derive(password)
    self.kcache[ckey] = [salt, key]
    return salt, key
  
  def encrypt(self, plaintext, password, cols=None):
    salt, key = self.derive_key(password)
    nonce = os.urandom(12)
    ciphertext = ChaCha20Poly1305(key).encrypt(nonce, plaintext, None)
    r = self.prefix + base64.b64encode(b'\x01' + salt + nonce + ciphertext)

    if cols is not None:
      r = b'\n'.join([r[i:i + cols] for i in range(0, len(r), cols)])

    return r + b'\n'
  
  def decrypt(self, ciphertext, password):
    try:
      if ciphertext.startswith(self.prefix):
        ciphertext = base64.b64decode(ciphertext[8:])
        if ciphertext.startswith(b'\x01') and len(ciphertext) > 29:
          key = self.derive_key(password, ciphertext[1:17])[1]
          return ChaCha20Poly1305(key).decrypt(ciphertext[17:29], ciphertext[29:], None)

    except InvalidTag:
      pass

  def encrypt_file(self, filepath, password, cols=None):
    with open(filepath, 'rb') as fh:
      ciphertext = self.encrypt(fh.read(), password, cols)

    if ciphertext is not None:
      os.system('shred -u ' + filepath)
      with open(filepath, 'wb') as fh:
        return fh.write(ciphertext)

  def decrypt_file(self, filepath, password):
    with open(filepath, 'rb') as fh:
      plaintext = self.decrypt(fh.read(), password)

    if plaintext is not None:
      with open(filepath, 'wb') as fh:
        return fh.write(plaintext)


def args():
  if 2 <= len(sys.argv) <= 3:
    m = sys.argv[1].lower()
    if m == 'encrypt' or m == 'decrypt':
      if len(sys.argv) == 2 or os.path.isfile(sys.argv[2]):
        return m

def main(m=args()):
  if m is not None:
    if len(sys.argv) == 2:
      data = sys.stdin.read().encode('utf-8')

    password = getpass.getpass('Enter Password: ').encode('utf-8')

    if m == 'encrypt':
      if password == getpass.getpass('Verify Password: ').encode('utf-8'):
        if len(sys.argv) == 2:
          ciphertext = Vaulty().encrypt(data, password, 80).decode('utf-8')
          print(ciphertext, end='')
    
        else:
          b = Vaulty().encrypt_file(sys.argv[2], password, 80)

      else:
        print('error: password verification failed', file=sys.stderr)

    elif m == 'decrypt':
      if len(sys.argv) == 2:
        plaintext = Vaulty().decrypt(data, password)
        if plaintext is not None:
          print(plaintext.decode('utf-8'), end='')

        else:
          print('error: invalid password or not encrypted', file=sys.stderr)

      else:
        b = Vaulty().decrypt_file(sys.argv[2], password)
        if b is None:
          print('error: invalid password or not encrypted', file=sys.stderr)

  else:
    print('usage: vaulty encrypt|decrypt [filepath]', file=sys.stderr)


if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    pass
