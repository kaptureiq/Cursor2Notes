"""Leitor mínimo do formato de serialização de valores do V8.

O IndexedDB do Chromium guarda objetos JavaScript nesse formato.
Cobre os tipos usados nas conversas do aplicativo Claude: objetos,
listas, mapas, textos, números e referências.
"""
from __future__ import annotations

import struct
from typing import Any


class V8Error(ValueError):
    pass


_PAD = 0x00
_VERSION = 0xFF
_INT32 = ord("I")
_UINT32 = ord("U")
_DOUBLE = ord("N")
_UTF8 = ord("S")
_ONEBYTE = ord('"')
_TWOBYTE = ord("c")
_REF = ord("^")
_BEGIN_OBJECT = ord("o")
_END_OBJECT = ord("{")
_BEGIN_SPARSE = ord("a")
_END_SPARSE = ord("@")
_BEGIN_DENSE = ord("A")
_END_DENSE = ord("$")
_DATE = ord("D")
_TRUE = ord("T")
_FALSE = ord("F")
_NULL = ord("0")
_UNDEFINED = ord("_")
_HOLE = ord("-")
_BEGIN_MAP = ord(";")
_END_MAP = ord(":")
_BEGIN_SET = ord("'")
_END_SET = ord(",")
_ARRAY_BUFFER = ord("B")
_ARRAY_BUFFER_VIEW = ord("V")
_REGEXP = ord("R")
_VERIFY = ord("?")


class _Reader:
    def __init__(self, data: bytes, pos: int, version: int) -> None:
        self.data = data
        self.pos = pos
        self.version = version
        self.objects: list[Any] = []

    def read_byte(self) -> int:
        if self.pos >= len(self.data):
            raise V8Error("fim inesperado dos dados")
        value = self.data[self.pos]
        self.pos += 1
        return value

    def read_varint(self) -> int:
        result = 0
        shift = 0
        for _ in range(5):
            byte = self.read_byte()
            result |= (byte & 0x7F) << shift
            if byte < 0x80:
                return result
            shift += 7
        raise V8Error("varint longo demais")

    def read_zigzag(self) -> int:
        number = self.read_varint()
        return (number >> 1) ^ -(number & 1)

    def read_bytes(self, size: int) -> bytes:
        if size < 0 or self.pos + size > len(self.data):
            raise V8Error("bloco maior que o restante do valor")
        chunk = self.data[self.pos : self.pos + size]
        self.pos += size
        return chunk

    def peek_tag(self) -> int:
        while self.pos < len(self.data) and self.data[self.pos] == _PAD:
            self.pos += 1
        if self.pos >= len(self.data):
            raise V8Error("tag ausente")
        return self.data[self.pos]

    def read_tag(self) -> int:
        tag = self.peek_tag()
        self.pos += 1
        return tag

    def read_string(self, kind: int) -> str:
        length = self.read_varint()
        if kind == _ONEBYTE:
            return self.read_bytes(length).decode("latin-1")
        if kind == _UTF8:
            return self.read_bytes(length).decode("utf-8", "replace")
        raw = self.read_bytes(length)
        return raw.decode("utf-16-le", "replace")

    def read_value(self) -> Any:
        tag = self.read_tag()
        if tag == _VERIFY:
            self.read_varint()
            return self.read_value()
        if tag == _NULL:
            return None
        if tag == _UNDEFINED or tag == _HOLE:
            return None
        if tag == _TRUE:
            return True
        if tag == _FALSE:
            return False
        if tag == _INT32:
            return self.read_zigzag()
        if tag == _UINT32:
            return self.read_varint()
        if tag == _DOUBLE:
            return struct.unpack("<d", self.read_bytes(8))[0]
        if tag in {_ONEBYTE, _UTF8, _TWOBYTE}:
            return self.read_string(tag)
        if tag == _REF:
            index = self.read_varint()
            if index >= len(self.objects):
                raise V8Error("referência para objeto ainda não lido")
            return self.objects[index]
        if tag == _BEGIN_OBJECT:
            return self.read_object()
        if tag == _BEGIN_DENSE:
            return self.read_dense_array()
        if tag == _BEGIN_SPARSE:
            return self.read_sparse_array()
        if tag == _BEGIN_MAP:
            return self.read_map()
        if tag == _BEGIN_SET:
            return self.read_set()
        if tag == _DATE:
            return struct.unpack("<d", self.read_bytes(8))[0]
        if tag == _ARRAY_BUFFER:
            return self.read_buffer()
        if tag == _REGEXP:
            pattern = self.read_string(_UTF8)
            self.read_varint()
            self.objects.append(pattern)
            return pattern
        if tag == ord("s"):
            self.objects.append("")
            index = len(self.objects) - 1
            text = self.read_value()
            if not isinstance(text, str):
                raise V8Error("objeto string sem texto")
            self.objects[index] = text
            return text
        raise V8Error(f"tag não suportada: {tag:#x} na posição {self.pos - 1}")

    def finish_buffer_view(self, payload: bytes) -> bytes:
        if self.pos < len(self.data) and self.peek_tag() == _ARRAY_BUFFER_VIEW:
            self.read_tag()
            self.read_varint()
            self.read_varint()
            self.read_varint()
            if self.version >= 14:
                self.read_varint()
            self.objects.append(payload)
        return payload

    def read_buffer(self) -> bytes:
        self.objects.append(b"")
        index = len(self.objects) - 1
        size = self.read_varint()
        payload = self.read_bytes(size)
        self.objects[index] = payload
        return self.finish_buffer_view(payload)

    def read_object(self) -> dict:
        result: dict[Any, Any] = {}
        self.objects.append(result)
        while self.peek_tag() != _END_OBJECT:
            key = self.read_value()
            result[key] = self.read_value()
        self.read_tag()
        count = self.read_varint()
        if count != len(result):
            raise V8Error("objeto com quantidade de campos diferente da anunciada")
        return result

    def read_dense_array(self) -> list:
        length = self.read_varint()
        result: list[Any] = [None] * length
        self.objects.append(result)
        for index in range(length):
            if self.peek_tag() == _HOLE:
                self.read_tag()
                continue
            result[index] = self.read_value()
        extra: dict[Any, Any] = {}
        while self.peek_tag() != _END_DENSE:
            key = self.read_value()
            extra[key] = self.read_value()
        self.read_tag()
        count = self.read_varint()
        declared = self.read_varint()
        if count != len(extra) or declared != length:
            raise V8Error("lista densa inconsistente")
        if extra:
            result.append(extra)
        return result

    def read_sparse_array(self) -> dict:
        length = self.read_varint()
        result: dict[Any, Any] = {"length": length}
        self.objects.append(result)
        while self.peek_tag() != _END_SPARSE:
            key = self.read_value()
            result[key] = self.read_value()
        self.read_tag()
        count = self.read_varint()
        declared = self.read_varint()
        stored = len(result) - 1
        if count != stored or declared != length:
            raise V8Error("lista esparsa inconsistente")
        return result

    def read_map(self) -> dict:
        result: dict[Any, Any] = {}
        self.objects.append(result)
        pairs = 0
        while self.peek_tag() != _END_MAP:
            key = self.read_value()
            result[key] = self.read_value()
            pairs += 2
        self.read_tag()
        if self.read_varint() != pairs:
            raise V8Error("mapa inconsistente")
        return result

    def read_set(self) -> list:
        result: list[Any] = []
        self.objects.append(result)
        while self.peek_tag() != _END_SET:
            result.append(self.read_value())
        self.read_tag()
        if self.read_varint() != len(result):
            raise V8Error("conjunto inconsistente")
        return result


def decode(data: bytes, start: int = 0) -> tuple[Any, int]:
    """Decodifica um valor. Se houver cabeçalho de versão, ele é consumido."""
    pos = start
    version = 13
    if pos < len(data) and data[pos] == _VERSION:
        pos += 1
        result = 0
        shift = 0
        while pos < len(data):
            byte = data[pos]
            pos += 1
            result |= (byte & 0x7F) << shift
            if byte < 0x80:
                break
            shift += 7
        version = result
    reader = _Reader(data, pos, version)
    value = reader.read_value()
    return value, reader.pos
