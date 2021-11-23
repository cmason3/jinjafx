#!/usr/bin/env python3

# Vaulty - Encrypt/Decrypt with ChaCha20-Poly1305
# Copyright (c) 2021 Chris Mason <chris@netnix.org>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import sys, os, base64, getpass
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag

class Vaulty():
  def __init__(self):
    self.__version__ = '1.0.0'
    self.__prefix = '$VAULTY;'
    self.__extension = '.vy'
    self.__kcache = {}

  def __derive_key(self, password, salt=None):
    if salt is None:
      salt = os.urandom(16)
      
    ckey = (password, salt)
  
    if ckey in self.__kcache:
      return self.__kcache[ckey]
  
    key = Scrypt(salt, 32, 2**16, 8, 1, default_backend()).derive(password)
    self.__kcache[ckey] = [salt, key]
    return salt, key
  
  def encrypt(self, plaintext, password, cols=None):
    salt, key = self.__derive_key(password)
    nonce = os.urandom(12)
    ciphertext = ChaCha20Poly1305(key).encrypt(nonce, plaintext, None)
    r = self.__prefix.encode('utf-8') + base64.b64encode(b'\x01' + salt + nonce + ciphertext)

    if cols is not None:
      r = b'\n'.join([r[i:i + cols] for i in range(0, len(r), cols)])

    return r + b'\n'
  
  def decrypt(self, ciphertext, password):
    try:
      ciphertext = ciphertext.strip()
      if ciphertext.startswith(self.__prefix.encode('utf-8')):
        ciphertext = base64.b64decode(ciphertext[8:])
        if ciphertext.startswith(b'\x01') and len(ciphertext) > 29:
          key = self.__derive_key(password, ciphertext[1:17])[1]
          return ChaCha20Poly1305(key).decrypt(ciphertext[17:29], ciphertext[29:], None)

    except InvalidTag:
      pass

  def encrypt_file(self, filepath, password, cols=None):
    with open(filepath, 'rb') as fh:
      ciphertext = self.encrypt(fh.read(), password, cols)

    if ciphertext is not None:
      with open(filepath, 'wb') as fh:
        fh.write(ciphertext)

      os.rename(filepath, filepath + self.__extension)
      return True

  def decrypt_file(self, filepath, password):
    with open(filepath, 'rb') as fh:
      plaintext = self.decrypt(fh.read(), password)

    if plaintext is not None:
      with open(filepath, 'wb') as fh:
        fh.write(plaintext)

      if filepath.endswith(self.__extension):
        os.rename(filepath, filepath[:-len(self.__extension)])

      return True


def args():
  if len(sys.argv) >= 2:
    m = sys.argv[1].lower()
    if len(sys.argv) == 2 or all([os.path.isfile(f) for f in sys.argv[2:]]):
      if m.lower() == 'encrypt'[0:len(m)]:
        return 'encrypt'
      elif m.lower() == 'decrypt'[0:len(m)]:
        return 'decrypt'

def main(m=args(), cols=80):
  if m is not None:
    if len(sys.argv) == 2:
      data = sys.stdin.read().encode('utf-8')

    password = getpass.getpass('Vaulty Password: ').encode('utf-8')
    if len(password) > 0:
      v = Vaulty()

      if m == 'encrypt':
        if password == getpass.getpass('Verify Password: ').encode('utf-8'):
          if len(sys.argv) == 2:
            print(v.encrypt(data, password, cols).decode('utf-8'), flush=True, end='')
      
          else:
            print()
            for f in sys.argv[2:]:
              print('encrypting ' + f + '... ', flush=True, end='')
              v.encrypt_file(f, password, cols)
              print('\x1b[1;32mok\x1b[0m')
  
        else:
          print('\x1b[1;31merror: password verification failed\x1b[0m', file=sys.stderr)
  
      elif m == 'decrypt':
        if len(sys.argv) == 2:
          plaintext = v.decrypt(data, password)
          if plaintext is not None:
            print(plaintext.decode('utf-8'), flush=True, end='')
  
          else:
            print('\x1b[1;31merror: invalid password or data not encrypted\x1b[0m', file=sys.stderr)
  
        else:
          print()
          for f in sys.argv[2:]:
            print('decrypting ' + f + '... ', flush=True, end='')
            if v.decrypt_file(f, password) is None:
              print('\x1b[1;31mfailed\nerror: invalid password or file not encrypted\x1b[0m', file=sys.stderr)

            else:
              print('\x1b[1;32mok\x1b[0m')

    else:
      print('\x1b[1;31merror: password is mandatory\x1b[0m', file=sys.stderr)

  else:
    print('usage: ' + os.path.basename(sys.argv[0]) + ' encrypt|decrypt [file1[ file2[ ...]]]', file=sys.stderr)


if __name__ == '__main__':
  try:
    main()

  except KeyboardInterrupt:
    pass
