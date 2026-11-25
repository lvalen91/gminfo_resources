"""Parse and serialize GM "CalOvride" calibration XML (the A11/gminfo37 CSM platform format).

Format facts this module encodes (verified byte-for-byte against all 28 genuine LTZ+HC
containers for this platform, independently re-verified by a second from-scratch
implementation — see docs/CALIBRATION_CUSTOMIZATION_GUIDE.md §5):

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
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Union

NS = "http://caltools.gm.com/calovride"
ET.register_namespace("calovride", NS)

SCALAR_TYPES = {"Boolean", "Integer", "Float", "Enumeration"}
# StringArray (seen on Android_Auto_VEC_Whitelist) behaves identically to Integer/FloatArray
# at this layer -- always a list of <ArrayValue> text, with no type-specific parsing here.
ARRAY_TYPES = {"IntegerArray", "FloatArray", "StringArray"}
MAP_TYPES = {"EnumIntegerMap", "EnumFloatMap"}
ALL_VALUE_TYPES = SCALAR_TYPES | ARRAY_TYPES | MAP_TYPES | {"String", "Record", "BinaryFile"}


def _escape(text) -> str:
    """Escape &, < and > in element text. GM's format never puts our interpolated values
    in an attribute, only in element text, so this is the only escaping ever needed. Order
    matters: & must be escaped first or the escapes themselves get re-escaped."""
    s = str(text)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def validate_value(type_: str, value) -> None:
    """Raise CalOvrideError if `value` is not a sane assignment for `type_`. Intended for
    callers (the CLI, the web API) accepting a user-supplied scalar edit -- catches the
    "set a Boolean to 'maybe'" class of mistake before it reaches serialize(). Does not
    (and cannot, without the CalDef's declared Min/Max/ArrayLen) catch every bad value --
    this is a sanity check, not full schema validation."""
    if type_ == "Boolean":
        if value not in ("true", "false"):
            raise CalOvrideError(f"Boolean value must be exactly 'true' or 'false', got {value!r}")
    elif type_ == "Integer":
        try:
            int(str(value))
        except ValueError:
            raise CalOvrideError(f"Integer value must parse as an integer, got {value!r}") from None
    elif type_ == "Float":
        try:
            f = float(str(value))
        except ValueError:
            raise CalOvrideError(f"Float value must parse as a number, got {value!r}") from None
        if not math.isfinite(f):
            raise CalOvrideError(f"Float value must be a finite number, got {value!r}")
    elif type_ == "Enumeration":
        # Enumeration values are always integers in this format (the enum label is a
        # display name keyed by the integer); a non-integer would serialize to a value
        # the module can't interpret. int(str(...)) also rejects embedded newlines.
        try:
            int(str(value))
        except ValueError:
            raise CalOvrideError(f"Enumeration value must be an integer, got {value!r}") from None
    elif type_ in SCALAR_TYPES or type_ == "String":
        if not isinstance(value, str):
            raise CalOvrideError(f"{type_} value must be a string, got {type(value).__name__}")
        if "\n" in value or "\r" in value:
            raise CalOvrideError(f"{type_} value may not contain embedded newlines (would corrupt CRLF framing)")
    else:
        raise CalOvrideError(
            f"{type_} is a structured type (array/map/record/binary) -- it cannot be set from a "
            f"single scalar value; edit its structured JSON representation directly"
        )


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
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise CalOvrideError(f"not well-formed XML: {e}") from e
    if _local(root.tag) != "CalOvrideFile":
        raise CalOvrideError(f"unexpected root element {root.tag!r}")
    overrides = []
    for ov in root:
        if _local(ov.tag) != "OverrideValue":
            raise CalOvrideError(f"unexpected child of root: {ov.tag!r}")
        cal_id = _require(ov.findtext("CalID"), "<OverrideValue><CalID>")
        version = _require(ov.findtext("Version"), "<OverrideValue><Version>")
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


def _require(value, what: str):
    if value is None:
        raise CalOvrideError(f"missing/empty required element: {what}")
    return value


def _parse_value(type_: str, elem: ET.Element):
    if type_ in SCALAR_TYPES:
        return _require(elem.findtext("Value"), f"<{type_}><Value>")
    if type_ == "String":
        return _require(elem.findtext("StringValue"), "<String><StringValue>")
    if type_ in ARRAY_TYPES:
        out = []
        for c in elem:
            if _local(c.tag) != "ArrayValue":
                continue
            # An empty <ArrayValue/> is a legitimate empty-string element, not a missing
            # one: ElementTree gives .text == None for it. serialize() round-trips an
            # empty-string element, so parse() must accept it too, or the tool cannot
            # re-ingest its own output (and would reject a genuine empty array element).
            out.append(c.text if c.text is not None else "")
        return out
    if type_ in MAP_TYPES:
        pairs = []
        for entry in elem:
            if _local(entry.tag) != "Entry":
                continue
            k = _require(entry.findtext("Key"), f"<{type_}><Entry><Key>")
            v = _require(entry.findtext("Value"), f"<{type_}><Entry><Value>")
            pairs.append((k, v))
        return pairs
    if type_ == "Record":
        fields = []
        for f in elem:
            if _local(f.tag) != "Field":
                continue
            name = _require(f.findtext("FieldName"), "<Record><Field><FieldName>")
            nested = None
            for c in f:
                if _local(c.tag) != "FieldName":
                    nested = c
                    break
            if nested is None:
                raise CalOvrideError(f"Record Field {name!r} has no typed value")
            ntype = _local(nested.tag)
            nval = nested.findtext("StringValue") if ntype == "String" else nested.findtext("Value")
            nval = _require(nval, f"<Record><Field {name!r}> nested <{ntype}> value")
            fields.append(Field(name, ntype, nval))
        return fields
    if type_ == "BinaryFile":
        filename = _require(elem.findtext("Filename"), "<BinaryFile><Filename>")
        data_b64 = _require(elem.findtext("Data"), "<BinaryFile><Data>")
        length_s = _require(elem.findtext("Length"), "<BinaryFile><Length>")
        checksum_s = _require(elem.findtext("Checksum"), "<BinaryFile><Checksum>")
        try:
            length, checksum = int(length_s), int(checksum_s)
        except ValueError as e:
            raise CalOvrideError(f"<BinaryFile> Length/Checksum not integers: {e}") from e
        return BinaryFileValue(filename=filename, data_b64=data_b64, length=length, checksum=checksum)
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
        lines.append(f"    <CalID>{_escape(_require(ov.cal_id, 'CalID'))}</CalID>")
        lines.append(f"    <Version>{_escape(_require(ov.version, 'Version'))}</Version>")
        lines.extend(_serialize_value(ov.type_, ov.value, depth=2))
        lines.append("  </OverrideValue>")
    lines.append("</calovride:CalOvrideFile>")
    doc = CR.join(lines)
    try:
        return doc.encode("ascii")
    except UnicodeEncodeError as e:
        raise CalOvrideError(
            f"this CalOvride document is ASCII-only -- a value contains a non-ASCII character "
            f"({e.reason} at document offset {e.start}); GM's own writer would need a numeric "
            f"character reference for this, which this module does not attempt to produce "
            f"automatically since the exact form GM uses for that is unverified"
        ) from e


def _pad(depth: int) -> str:
    return "  " * depth


def _serialize_value(type_: str, value, depth: int) -> list[str]:
    p = _pad(depth)
    p1 = _pad(depth + 1)
    if type_ in SCALAR_TYPES:
        v = _escape(_require(value, f"<{type_}><Value>"))
        return [f"{p}<{type_}>", f"{p1}<Value>{v}</Value>", f"{p}</{type_}>"]
    if type_ == "String":
        v = _escape(_require(value, "<String><StringValue>"))
        return [f"{p}<String>", f"{p1}<StringValue>{v}</StringValue>", f"{p}</String>"]
    if type_ in ARRAY_TYPES:
        out = [f"{p}<{type_}>"]
        out += [f"{p1}<ArrayValue>{_escape(_require(v, f'<{type_}><ArrayValue>'))}</ArrayValue>" for v in value]
        out.append(f"{p}</{type_}>")
        return out
    if type_ in MAP_TYPES:
        out = [f"{p}<{type_}>"]
        p2 = _pad(depth + 2)
        for k, v in value:
            out.append(f"{p1}<Entry>")
            out.append(f"{p2}<Key>{_escape(_require(k, f'<{type_}><Entry><Key>'))}</Key>")
            out.append(f"{p2}<Value>{_escape(_require(v, f'<{type_}><Entry><Value>'))}</Value>")
            out.append(f"{p1}</Entry>")
        out.append(f"{p}</{type_}>")
        return out
    if type_ == "Record":
        out = [f"{p}<Record>"]
        p2 = _pad(depth + 2)
        for f in value:
            out.append(f"{p1}<Field>")
            out.append(f"{p2}<FieldName>{_escape(_require(f.name, '<Record><Field><FieldName>'))}</FieldName>")
            out.extend(_serialize_value(f.type_, f.value, depth + 2))
            out.append(f"{p1}</Field>")
        out.append(f"{p}</Record>")
        return out
    if type_ == "BinaryFile":
        bf: BinaryFileValue = value
        if not isinstance(bf, BinaryFileValue):
            raise CalOvrideError(
                f"BinaryFile value must be a BinaryFileValue instance, got {type(bf).__name__} "
                f"-- this type cannot be assigned from a plain string/scalar"
            )
        return [
            f"{p}<BinaryFile>",
            f"{p1}<Filename>{_escape(_require(bf.filename, '<BinaryFile><Filename>'))}</Filename>",
            f"{p1}<Data>{_escape(_require(bf.data_b64, '<BinaryFile><Data>'))}</Data>",
            f"{p1}<Length>{_escape(_require(bf.length, '<BinaryFile><Length>'))}</Length>",
            f"{p1}<Checksum>{_escape(_require(bf.checksum, '<BinaryFile><Checksum>'))}</Checksum>",
            f"{p}</BinaryFile>",
        ]
    raise CalOvrideError(f"unknown override type {type_!r}")


def roundtrip_ok(xml_bytes: bytes) -> bool:
    """True if parse(xml_bytes) -> serialize(...) reproduces xml_bytes exactly."""
    return serialize(parse(xml_bytes)) == xml_bytes


# --------------------------------------------------------- JSON interchange shape ---
#
# One canonical full-fidelity JSON representation of an Override, shared by the CLI and
# the web API so there's a single place that knows how to round-trip every type --
# including the structured ones (array/map/record/binary). Anything that flattens a
# structured value to a display string (e.g. for showing in a table) must keep that
# string separate from what actually gets sent to to_jsonable/from_jsonable, or editing
# unrelated entries and re-exporting will silently corrupt or crash on them -- this was
# a real, confirmed bug (both the CLI and the web UI independently corrupted
# IntegerArray/FloatArray values and crashed on Map/Record/BinaryFile on export, because
# the display string was what got sent back instead of this shape).

def to_jsonable(ov: Override) -> dict:
    value = ov.value
    if isinstance(value, BinaryFileValue):
        value = {"filename": value.filename, "length": value.length,
                 "checksum": value.checksum, "data_b64": value.data_b64}
    elif ov.type_ in MAP_TYPES:
        value = [{"key": k, "value": v} for k, v in value]
    elif ov.type_ == "Record":
        value = [{"name": f.name, "type": f.type_, "value": f.value} for f in value]
    return {"cal_id": ov.cal_id, "version": ov.version, "type": ov.type_, "value": value}


def from_jsonable(d: dict) -> Override:
    value = d["value"]
    type_ = d["type"]
    if type_ == "BinaryFile":
        value = BinaryFileValue(value["filename"], value["data_b64"], value["length"], value["checksum"])
    elif type_ in MAP_TYPES:
        value = [(e["key"], e["value"]) for e in value]
    elif type_ == "Record":
        value = [Field(e["name"], e["type"], e["value"]) for e in value]
    return Override(d["cal_id"], str(d["version"]), type_, value)
