import base64

enc_password = "0Nv32PTwgYjzg9/8j5TbmvPd3e7WhtWWyuPsyO76/Y+U193E"
key = b"armando"

array = base64.b64decode(enc_password)
result = bytearray(array)

for i in range(len(array)):
    result[i] = (array[i] ^ key[i % len(key)]) ^ 0xDF

print(result.decode())
