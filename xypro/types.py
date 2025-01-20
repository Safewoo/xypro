"types defined"

import typing as t

NetAddress = t.Tuple[bytes, int]  # (addr, port)
AtypAddress = t.Tuple[int, bytes, int]  # (atyp, addr, port)
