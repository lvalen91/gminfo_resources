"""Parse and serialize GM "CalOvride" calibration XML (the A11/gminfo37 CSM platform format).

Format facts this module encodes (verified byte-for-byte against all 28 genuine LTZ+HC
containers for this platform, independently re-verified by a second from-scratch
implementation — see research/eeprom-calibration/CALIBRATION_CUSTOMIZATION_GUIDE.md §5):

- CRLF line endings throughout, no bare LF/CR anywhere in the document.
- Uniform indent of 2 spaces per nesting depth (root=0, OverrideValue=2, CalID/Version/
  type-tag=4, the type's own scalar/array children=6, Entry/Field children one level
  deeper again=8, and the typed value nested inside a Record Field=10).
- No trailing newline after the final closing tag.
- An override set with zero entries serializes the root as self-closing
  (<calovride:CalOvrideFile .../>), not as an open/close pair with no content.
- Ten override types exist: Boolean, Integer, Float, Enumeration, String, IntegerArray,
  FloatArray, EnumIntegerMap, EnumFloatMap, Record. BinaryFile is an eleventh, used for
  embedded binary blobs (base64 Data + Length + CRC-32 Checksum).

This module is schema-TYPED (not a generic tree re-indenter): it parses into plain
dataclasses per type and re-emits the exact same bytes GM's own compiler produces, which
is also how the three easy-to-miss array/map/record types were caught in the first place
— a generic tree re-indenter happens to reproduce them by accident without anyone
noticing they exist.

Deliberately out of scope here: the signed-container header, the RSA signature, and the
CAN613/614 VIP-RAM bypass needed to get an edited payload accepted on real hardware. See
GM_SEED_KEY_AND_CALIBRATION_SIGNATURES.md and DPS_TYPE4_CUSTOM_CALIBRATION_WORKFLOW.md for
those — this module only produces a correctly-formatted payload, nothing more.
"""
from __future__ import annotations

import base64
import binascii
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Union

NS = "http://caltools.gm.com/calovride"
ET.register_namespace("calovride", NS)

SCALAR_TYPES = {"Boolean", "Integer", "Float", "Enumeration"}
ARRAY_TYPES = {"IntegerArray", "FloatArray"}
MAP_TYPES = {"EnumIntegerMap", "EnumFloatMap"}
ALL_VALUE_TYPES = SCALAR_TYPES | ARRAY_TYPES | MAP_TYPES | {"String", "Record", "BinaryFile"}


class CalOvrideError(ValueError):
    pass


@dataclass
class Override:
    """One <OverrideValue> entry. `type_` is one of ALL_VALUE_TYPES. `value` depends on
    type_:
      scalar types   -> str (the literal text of <Value>, e.g. "true"/"3"/"-6.0")
      String         -> str (the literal text of <StringValue>)
      *Array types   -> list[str] (each <ArrayValue> text, in order)
      *Map types     -> list[tuple[str, str]] (each (Key, Value) text pair, in order)
      Record         -> list[Field] (see below)
      BinaryFile     -> BinaryFileValue
    """
    cal_id: str
    version: str
    type_: str
    value: Union[str, list, "BinaryFileValue"]


@dataclass
class Field:
    """One <Field> inside a <Record>: a name plus a nested typed value (String/Integer/
    Float/Enumeration have been observed; the format allows any scalar or String type)."""
    name: str
    type_: str
    value: str


@dataclass
class BinaryFileValue:
    filename: str
    data_b64: str
    length: int
    checksum: int

    def decoded(self) -> bytes:
        return base64.b64decode(self.data_b64)

    def verify_checksum(self) -> bool:
        return binascii.crc32(self.decoded()) == self.checksum and len(self.decoded()) == self.length

    @classmethod
    def from_bytes(cls, filename: str, raw: bytes) -> "BinaryFileValue":
        return cls(
            filename=filename,
            data_b64=base64.b64encode(raw).decode("ascii"),
            length=len(raw),
            checksum=binascii.crc32(raw),
        )


# --------------------------------------------------------------------------- parsing ---

def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def parse(xml_bytes: bytes) -> list[Override]:
    """Parse a CalOvride document (bytes, as extracted from a container's inner gzip, or
    a standalone .calovride file) into a list of Override records."""
    root = ET.fromstring(xml_bytes)
    if _local(root.tag) != "CalOvrideFile":
        raise CalOvrideError(f"unexpected root element {root.tag!r}")
    overrides = []
    for ov in root:
        if _local(ov.tag) != "OverrideValue":
            raise CalOvrideError(f"unexpected child of root: {ov.tag!r}")
        cal_id = ov.findtext("CalID")
        version = ov.findtext("Version")
        type_elem = None
        for c in ov:
            if _local(c.tag) not in ("CalID", "Version"):
                type_elem = c
                break
        if type_elem is None:
            raise CalOvrideError(f"OverrideValue for {cal_id} has no typed value")
        type_ = _local(type_elem.tag)
        overrides.append(Override(cal_id, version, type_, _parse_value(type_, type_elem)))
    return overrides


def _parse_value(type_: str, elem: ET.Element):
    if type_ in SCALAR_TYPES:
        return elem.findtext("Value")
    if type_ == "String":
        return elem.findtext("StringValue")
    if type_ in ARRAY_TYPES:
        return [c.text for c in elem if _local(c.tag) == "ArrayValue"]
    if type_ in MAP_TYPES:
        pairs = []
        for entry in elem:
            if _local(entry.tag) != "Entry":
                continue
            pairs.append((entry.findtext("Key"), entry.findtext("Value")))
        return pairs
    if type_ == "Record":
        fields = []
        for f in elem:
            if _local(f.tag) != "Field":
                continue
            name = f.findtext("FieldName")
            nested = None
            for c in f:
                if _local(c.tag) != "FieldName":
                    nested = c
                    break
            if nested is None:
                raise CalOvrideError(f"Record Field {name!r} has no typed value")
            ntype = _local(nested.tag)
            nval = nested.findtext("StringValue") if ntype == "String" else nested.findtext("Value")
            fields.append(Field(name, ntype, nval))
        return fields
    if type_ == "BinaryFile":
        return BinaryFileValue(
            filename=elem.findtext("Filename"),
            data_b64=elem.findtext("Data"),
            length=int(elem.findtext("Length")),
            checksum=int(elem.findtext("Checksum")),
        )
    raise CalOvrideError(f"unknown override type {type_!r}")


# ------------------------------------------------------------------------ serializing ---

def serialize(overrides: list[Override]) -> bytes:
    """Produce the exact bytes GM's own compiler would produce for this entry list."""
    CR = "\r\n"
    lines = ['<?xml version="1.0" encoding="ASCII"?>']
    if not overrides:
        lines.append(f'<calovride:CalOvrideFile xmlns:calovride="{NS}"/>')
        return CR.join(lines).encode("ascii")

    lines.append(f'<calovride:CalOvrideFile xmlns:calovride="{NS}">')
    for ov in overrides:
        lines.append("  <OverrideValue>")
        lines.append(f"    <CalID>{ov.cal_id}</CalID>")
        lines.append(f"    <Version>{ov.version}</Version>")
        lines.extend(_serialize_value(ov.type_, ov.value, depth=2))
        lines.append("  </OverrideValue>")
    lines.append("</calovride:CalOvrideFile>")
    doc = CR.join(lines)
    return doc.encode("ascii")


def _pad(depth: int) -> str:
    return "  " * depth


def _serialize_value(type_: str, value, depth: int) -> list[str]:
    p = _pad(depth)
    p1 = _pad(depth + 1)
    if type_ in SCALAR_TYPES:
        return [f"{p}<{type_}>", f"{p1}<Value>{value}</Value>", f"{p}</{type_}>"]
    if type_ == "String":
        return [f"{p}<String>", f"{p1}<StringValue>{value}</StringValue>", f"{p}</String>"]
    if type_ in ARRAY_TYPES:
        out = [f"{p}<{type_}>"]
        out += [f"{p1}<ArrayValue>{v}</ArrayValue>" for v in value]
        out.append(f"{p}</{type_}>")
        return out
    if type_ in MAP_TYPES:
        out = [f"{p}<{type_}>"]
        p2 = _pad(depth + 2)
        for k, v in value:
            out.append(f"{p1}<Entry>")
            out.append(f"{p2}<Key>{k}</Key>")
            out.append(f"{p2}<Value>{v}</Value>")
            out.append(f"{p1}</Entry>")
        out.append(f"{p}</{type_}>")
        return out
    if type_ == "Record":
        out = [f"{p}<Record>"]
        p2 = _pad(depth + 2)
        for f in value:
            out.append(f"{p1}<Field>")
            out.append(f"{p2}<FieldName>{f.name}</FieldName>")
            out.extend(_serialize_value(f.type_, f.value, depth + 2))
            out.append(f"{p1}</Field>")
        out.append(f"{p}</Record>")
        return out
    if type_ == "BinaryFile":
        bf: BinaryFileValue = value
        return [
            f"{p}<BinaryFile>",
            f"{p1}<Filename>{bf.filename}</Filename>",
            f"{p1}<Data>{bf.data_b64}</Data>",
            f"{p1}<Length>{bf.length}</Length>",
            f"{p1}<Checksum>{bf.checksum}</Checksum>",
            f"{p}</BinaryFile>",
        ]
    raise CalOvrideError(f"unknown override type {type_!r}")


def roundtrip_ok(xml_bytes: bytes) -> bool:
    """True if parse(xml_bytes) -> serialize(...) reproduces xml_bytes exactly."""
    return serialize(parse(xml_bytes)) == xml_bytes
