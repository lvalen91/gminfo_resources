"""Offline checks: bundled data, shared backend, web routes and (where Tk works) the
desktop UI. Uses only files inside the toolkit."""
from __future__ import annotations

import base64
import io
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from caltool import caldef, calovride, container, service  # noqa: E402

SAMPLE = (ROOT / "tests/fixtures/ltz_trim_sample.calovride").read_bytes()


def template() -> bytes:
    """A synthetic, unsigned container: enough structure to exercise resealing."""
    header = bytearray(container.HEADER_LEN)
    header[3] = 0x0C
    header[6:10] = b"CSM\x00"
    return container.pack_outer(container.reseal(bytes(header), SAMPLE))


def module():
    return service.start_tracking(service.load_module("sample", template()))


def by_name(m, name):
    return next(e for e in m["entries"] if e["name"] == name)


class Bundle(unittest.TestCase):
    def test_database_is_bundled(self):
        self.assertEqual(len(caldef.groups()), 146)
        self.assertGreater(len(caldef.search("carplay")), 0)
        self.assertTrue((ROOT / "docs/CALIBRATION_CUSTOMIZATION_GUIDE.md").is_file())

    def test_sample_roundtrips_byte_exact(self):
        self.assertTrue(calovride.roundtrip_ok(SAMPLE))

    def test_empty_array_element_roundtrips(self):
        # serialize() emits an empty <ArrayValue/> for an empty-string element; parse()
        # must read it back as "" rather than rejecting it, or the tool cannot re-ingest
        # its own output (previously raised "missing/empty required element").
        ov = calovride.Override("X", "1", "IntegerArray", ["1", "", "3"])
        self.assertEqual(calovride.parse(calovride.serialize([ov]))[0].value, ["1", "", "3"])

    def test_validate_value_type_gaps(self):
        for t, v in [("Float", "inf"), ("Float", "nan"), ("Float", "-inf"),
                     ("Enumeration", "banana"), ("Enumeration", "1.5"), ("Integer", "3.5")]:
            with self.assertRaises(calovride.CalOvrideError, msg=f"{t}={v!r}"):
                calovride.validate_value(t, v)
        for t, v in [("Float", "1.5"), ("Enumeration", "3"), ("Integer", "-7")]:
            calovride.validate_value(t, v)  # must not raise


class Backend(unittest.TestCase):
    def test_load_and_unchanged_export(self):
        m = module()
        self.assertEqual((len(m["entries"]), m["meta"]["slot"], m["meta"]["digest_ok"]), (404, 12, True))
        self.assertEqual(service.export_module(m["entries"], safety_ack=True), SAMPLE)

    def test_edit_track_and_reseal(self):
        m = module()
        e = by_name(m, "GMBrand")
        service.set_value(e, "4" if e["value_raw"] != "4" else "3")
        self.assertTrue(service.is_modified(e))
        out = service.export_module(m["entries"], "container", m["template"], safety_ack=True)
        c = container.parse(out)
        self.assertTrue(c.digest_ok)
        self.assertEqual(sum(a != b for a, b in zip(c.inner_xml.split(b"\r\n"), SAMPLE.split(b"\r\n"))), 1)

    def test_invalid_values_refused(self):
        m = module()
        e = next(e for e in m["entries"] if e["type"] == "Boolean")
        with self.assertRaises(calovride.CalOvrideError):
            service.set_value(e, "maybe")
        with self.assertRaises(service.InputError):
            service.export_module([{**e, "value_raw": "maybe"}], safety_ack=True)

    def test_safety_gate(self):
        m = module()
        with self.assertRaises(service.SafetyAckRequired):
            service.export_module(m["entries"])
        self.assertEqual(service.changed_restricted(m["entries"]), [])
        e = next(e for e in m["entries"] if e["safety_restricted"])
        e["value_raw"] = "changed"
        self.assertEqual(service.changed_restricted(m["entries"]), [e])

    def test_add_entry(self):
        m = module()
        present = {e["cal_id"] for e in m["entries"]}
        for r in service.search_caldefs("carplay"):
            d = service.caldef_detail(r["name"], r["group"])
            if d["cal_id"] not in present and service.is_editable(d["type"]):
                break
        entry = service.add_entry(m, d)
        self.assertTrue(entry["is_new"] and service.is_modified(entry))
        with self.assertRaises(service.InputError):
            service.add_entry(m, d)

    def test_zip_roundtrip_keeps_duplicates(self):
        m = module()
        data = service.export_zip([m, m], safety_ack=True)
        self.assertEqual(len(zipfile.ZipFile(io.BytesIO(data)).namelist()), 2)
        modules, skipped = service.load_zip(data)
        self.assertEqual((len(modules), skipped), (2, []))


@unittest.skipIf(sys.version_info < (3, 10), "web UI needs Python 3.10+")
class Web(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from web.app import app
        cls.client = app.test_client()

    def test_pages_and_lookups(self):
        for url in ("/", "/help", "/static/editor.js", "/static/style.css",
                    "/api/caldef/groups", "/api/caldef/search?q=carplay",
                    "/api/caldef/entry?name=SXM_Enabled"):
            with self.client.get(url) as r:
                self.assertEqual(r.status_code, 200, url)

    def test_flask_comes_from_the_bundle(self):
        import flask
        self.assertTrue(Path(flask.__file__).is_relative_to(ROOT / "vendor"), flask.__file__)

    def test_ingest_then_export(self):
        r = self.client.post("/api/ingest", data={"file": (io.BytesIO(template()), "sample")})
        body = r.get_json()
        self.assertEqual((r.status_code, len(body["entries"])), (200, 404))
        req = {"entries": body["entries"], "format": "container", "template_b64": body["template_b64"]}
        refused = self.client.post("/api/export", json=req)
        self.assertEqual(refused.status_code, 400)
        self.assertIn("safety_ack", refused.get_json()["error"])
        ok = self.client.post("/api/export", json={**req, "safety_ack": True})
        self.assertEqual(container.parse(ok.data).inner_xml, SAMPLE)
        z = self.client.post("/api/export_zip", json={"safety_ack": True, "modules": [
            {"filename": "sample", "entries": body["entries"], "template_b64": body["template_b64"]}]})
        self.assertEqual(z.status_code, 200)

    def test_bad_requests_are_400(self):
        for payload in ([], {"entries": 3}, {"entries": [{}]},
                        {"entries": [], "format": "container", "template_b64": "!!"}):
            self.assertEqual(self.client.post("/api/export", json=payload).status_code, 400, payload)


def _appkit_problem():
    if sys.platform != "darwin":
        return "the desktop UI is macOS only"
    sys.path.append(str(ROOT / "vendor_mac"))
    try:
        import AppKit  # noqa: F401
        import objc    # noqa: F401
    except ImportError as e:
        return f"no usable PyObjC for this Python (needs 3.14): {e}"
    return None


class Desktop(unittest.TestCase):
    """Drives the real AppKit controller and controls without showing a window."""

    @classmethod
    def setUpClass(cls):
        problem = _appkit_problem()
        if problem:
            raise unittest.SkipTest(problem)
        import AppKit
        import gui
        cls.gui = gui
        AppKit.NSApplication.sharedApplication()

    def setUp(self):
        self.c = self.gui.Controller.alloc().init()

    def load(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sample"
            path.write_bytes(template())
            self.c.load_paths([str(path)])
        return self.c

    def pick(self, predicate):
        c = self.c
        index = next(i for i, e in enumerate(c.current["entries"]) if predicate(e))
        c.select_entry(index)
        return index, c.current["entries"][index]

    def test_empty_state_disables_actions(self):
        self.assertFalse(self.c.empty.isHidden())
        for action in ("addEntry:", "exportXML:", "exportContainer:", "exportAll:"):
            self.assertFalse(self.c.allowed(action), action)

    def test_load_filter_and_switch(self):
        c = self.load()
        self.assertEqual(len(c.visible_indexes()), 404)
        self.assertTrue(c.allowed("exportContainer:"))
        index, e = self.pick(lambda e: e["type"] == "Boolean")
        old = e["value_raw"]
        c.switch.setState_(0 if old == "true" else 1)
        c.toggleValue_(c.switch)
        self.assertTrue(c.dirty and service.is_modified(e))
        c.scope = 1
        c.reload_entries()
        self.assertEqual(c.visible_indexes(), [index])
        c.select_entry(index)
        c.revertValue_(None)
        self.assertEqual(e["value_raw"], old)

    def test_enumeration_popup_and_inline_error(self):
        c = self.load()
        _, e = self.pick(lambda e: e["name"] == "GMBrand")
        self.assertFalse(c.popup.isHidden())
        target = next(o["value"] for o in e["enum_options"] if o["value"] != e["value_raw"])
        c.popup.selectItemAtIndex_([o["value"] for o in e["enum_options"]].index(target))
        c.chooseValue_(c.popup)
        self.assertEqual(e["value_raw"], target)
        _, number = self.pick(lambda e: e["type"] == "Integer")
        before = number["value_raw"]
        c.set_current_value("not a number")
        self.assertFalse(c.error_label.isHidden())
        self.assertEqual(number["value_raw"], before)

    def test_add_sheet_and_help(self):
        c = self.load()
        sheet = self.gui.AddSheet(c, c.current)
        sheet.search("carplay")
        self.assertGreater(len(sheet.results), 0)
        c.showHelp_  # selector exists
        self.assertIsNotNone(c.build_help())
        self.assertIn("Calibration slots", self.gui.overview_text())


if __name__ == "__main__":
    unittest.main()
