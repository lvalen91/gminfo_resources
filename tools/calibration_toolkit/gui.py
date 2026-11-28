#!/usr/bin/env python3
"""Native macOS desktop UI (AppKit through PyObjC) -- no browser, no server.

    python3.14 run.py gui [file ...]

Layout and behaviour follow Apple's Human Interface Guidelines: standard AppKit
controls, a unified toolbar, a sidebar / content / inspector split view, a full menu
bar, system colours (light and dark come for free), and alerts only for decisions.
This file is only the presentation layer; loading, search, change tracking, the safety
gate and export live in caltool/service.py, which the web UI shares.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import objc
import AppKit as A
from Foundation import NSBundle, NSMakeRect, NSMakeSize, NSObject, NSIndexSet

from caltool import caldef, service, slotinfo

APP_NAME = "Calibration Toolkit"
DOCS_DIR = Path(__file__).resolve().parent / "docs"
SIGNATURE_NOTE = "The digest was recomputed. The signature is the template’s and is stale for any edit."
CUSTOM = "Custom Value…"

SLOTS = {  # slot: (sidebar name, SF Symbol)
    0x02: ("Fuel & Wheel", "fuelpump"), 0x03: ("Empty", "square.dashed"),
    0x04: ("Identity & Apps", "square.grid.2x2"), 0x05: ("Region & Language", "globe"),
    0x06: ("Speech Tuning", "waveform"), 0x07: ("Bluetooth", "phone"),
    0x08: ("Cameras", "camera"), 0x09: ("DTC & GNSS", "location"),
    0x0A: ("Climate", "thermometer.medium"), 0x0B: ("OnStar & Wi-Fi", "wifi"),
    0x0C: ("Radio Tuners", "radio"), 0x0D: ("Trailer & Rear", "car"),
    0x0E: ("Empty", "square.dashed"), 0x0F: ("Speaker EQ", "speaker.wave.2"),
}


# ------------------------------------------------------------------ pure helpers ---

def module_name(m: dict) -> str:
    slot = m["meta"]["slot"]
    return SLOTS[slot][0] if slot in SLOTS else Path(m["filename"]).stem


def module_subtitle(m: dict) -> str:
    meta = m["meta"]
    if meta["slot"] is None:
        return "XML only · no container header"
    return f"Slot {meta['slot']:02X} · {meta['part_number']}"


def position(items: list, item) -> int:
    """Index by identity. list.index() compares dicts by value, so two equal modules (the
    same file opened twice, or a zip holding a copy) or two equal entries resolve to the
    first one: the sidebar then selected, and Remove Entry deleted, the wrong one."""
    return next(i for i, x in enumerate(items) if x is item)


def pretty_value(e: dict) -> str:
    """Table text: enumeration labels rather than bare numbers, summaries for structures."""
    raw = e["value_raw"]
    if e["editable"]:
        for o in e["enum_options"]:
            if o["value"] == raw:
                return f"{o['label']} ({raw})"
        return str(raw)
    if e["type"] == "BinaryFile":
        return f"{raw['filename']}, {raw['length']:,} bytes"
    if e["type"] == "Record":
        return f"{len(raw)} fields"
    if e["type"].endswith("Map"):
        return f"{len(raw)} pairs"
    return ", ".join(raw)


def overview_text() -> str:
    lines = ["This app edits calibration files. It does not sign anything or talk to a radio.",
             SIGNATURE_NOTE,
             "Read CALIBRATION_SLOT_MAP.md and CALIBRATION_CUSTOMIZATION_GUIDE.md (pop-up above) "
             "before writing anything to hardware. A change that hardware accepts is not "
             "necessarily safe or effective.", "", "Calibration slots (A11 LTZ)", ""]
    for s in slotinfo.SLOTS.values():
        lines.append(f"{s.slot:02X}  {s.ltz_part}  {slotinfo.TRIAGE_LABEL[s.triage]}\n      {s.summary}")
    lines += ["", "Elevated-caution CalDef groups", ""]
    lines += sorted(g for g in caldef.groups() if g.upper() in caldef.SAFETY_RESTRICTED_GROUPS)
    return "\n".join(lines)


# ------------------------------------------------------------- AppKit shorthands ---

def symbol(name: str, description: str = ""):
    return A.NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, description or name)


def auto(view):
    view.setTranslatesAutoresizingMaskIntoConstraints_(False)
    return view


def label(text="", style=None, color=None, wrap=False, selectable=False):
    make = A.NSTextField.wrappingLabelWithString_ if wrap else A.NSTextField.labelWithString_
    field = auto(make(text))
    if style is not None:
        field.setFont_(A.NSFont.preferredFontForTextStyle_options_(style, {}))
    if color is not None:
        field.setTextColor_(color)
    field.setSelectable_(selectable)
    if not wrap:
        field.setLineBreakMode_(A.NSLineBreakByTruncatingTail)
    field.setContentCompressionResistancePriority_forOrientation_(250, A.NSLayoutConstraintOrientationHorizontal)
    return field


def secondary(text="", **kw):
    kw.setdefault("style", A.NSFontTextStyleSubheadline)
    return label(text, color=A.NSColor.secondaryLabelColor(), **kw)


def button(title, target, action):
    return auto(A.NSButton.buttonWithTitle_target_action_(title, target, action))


def stack(views, vertical=True, spacing=8.0):
    s = auto(A.NSStackView.stackViewWithViews_(views))
    if vertical:
        s.setOrientation_(A.NSUserInterfaceLayoutOrientationVertical)
        s.setAlignment_(A.NSLayoutAttributeLeading)
    else:
        s.setOrientation_(A.NSUserInterfaceLayoutOrientationHorizontal)
        s.setAlignment_(A.NSLayoutAttributeCenterY)
    s.setSpacing_(spacing)
    return s


def activate(*constraints):
    A.NSLayoutConstraint.activateConstraints_(list(constraints))


def fill(child, parent, top=0.0, left=0.0, bottom=0.0, right=0.0, safe=False):
    parent.addSubview_(child)
    auto(child)
    guide = parent.safeAreaLayoutGuide() if safe else parent
    activate(child.topAnchor().constraintEqualToAnchor_constant_(guide.topAnchor(), top),
             child.leadingAnchor().constraintEqualToAnchor_constant_(parent.leadingAnchor(), left),
             child.bottomAnchor().constraintEqualToAnchor_constant_(parent.bottomAnchor(), -bottom),
             child.trailingAnchor().constraintEqualToAnchor_constant_(parent.trailingAnchor(), -right))


def scroll_view(document):
    s = auto(A.NSScrollView.alloc().initWithFrame_(NSMakeRect(0, 0, 100, 100)))
    s.setDocumentView_(document)
    s.setHasVerticalScroller_(True)
    s.setAutohidesScrollers_(True)
    return s


def text_area(draws_background=False):
    s = auto(A.NSTextView.scrollableTextView())
    view = s.documentView()
    view.setEditable_(False)
    view.setFont_(A.NSFont.preferredFontForTextStyle_options_(A.NSFontTextStyleBody, {}))
    view.setTextColor_(A.NSColor.labelColor())
    view.setDrawsBackground_(draws_background)
    s.setDrawsBackground_(draws_background)
    view.textContainer().setLineFragmentPadding_(0)
    return s, view


def column(table, ident, title, width, minimum):
    c = A.NSTableColumn.alloc().initWithIdentifier_(ident)
    c.setTitle_(title)
    c.setWidth_(width)
    c.setMinWidth_(minimum)
    table.addTableColumn_(c)
    return c


def cell(text, symbol_name=None, color=None, font=None, trailing=None, tooltip=None):
    """A standard table cell: optional leading symbol, text, optional trailing note."""
    view = A.NSTableCellView.alloc().initWithFrame_(NSMakeRect(0, 0, 100, 22))
    parts = []
    if symbol_name:
        image = auto(A.NSImageView.imageViewWithImage_(symbol(symbol_name)))
        image.setContentHuggingPriority_forOrientation_(751, A.NSLayoutConstraintOrientationHorizontal)
        view.setImageView_(image)
        parts.append(image)
    field = label(text)
    if color is not None:
        field.setTextColor_(color)
    if font is not None:
        field.setFont_(font)
    view.setTextField_(field)
    parts.append(field)
    if trailing:
        note = secondary(trailing)
        note.setContentCompressionResistancePriority_forOrientation_(749, A.NSLayoutConstraintOrientationHorizontal)
        note.setContentHuggingPriority_forOrientation_(751, A.NSLayoutConstraintOrientationHorizontal)
        parts.append(note)
    row = stack(parts, vertical=False, spacing=6)
    view.addSubview_(row)
    activate(row.leadingAnchor().constraintEqualToAnchor_constant_(view.leadingAnchor(), 2),
             row.trailingAnchor().constraintEqualToAnchor_constant_(view.trailingAnchor(), -4),
             row.centerYAnchor().constraintEqualToAnchor_(view.centerYAnchor()))
    if tooltip:
        view.setToolTip_(tooltip)
    return view


def sidebar_cell(title, detail, symbol_name, tooltip):
    view = A.NSTableCellView.alloc().initWithFrame_(NSMakeRect(0, 0, 200, 40))
    image = auto(A.NSImageView.imageViewWithImage_(symbol(symbol_name)))
    name, note = label(title), secondary(detail, style=A.NSFontTextStyleFootnote)
    view.setImageView_(image)
    view.setTextField_(name)
    lines = stack([name, note], spacing=1)
    view.addSubview_(image)
    view.addSubview_(lines)
    activate(image.leadingAnchor().constraintEqualToAnchor_constant_(view.leadingAnchor(), 2),
             image.widthAnchor().constraintEqualToConstant_(20),
             image.centerYAnchor().constraintEqualToAnchor_(view.centerYAnchor()),
             lines.leadingAnchor().constraintEqualToAnchor_constant_(image.trailingAnchor(), 7),
             lines.trailingAnchor().constraintEqualToAnchor_constant_(view.trailingAnchor(), -4),
             lines.centerYAnchor().constraintEqualToAnchor_(view.centerYAnchor()))
    view.setToolTip_(tooltip)
    return view


def view_controller(view):
    c = A.NSViewController.alloc().init()
    c.setView_(view)
    return c


def plain_view(width=400, height=500):
    return A.NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))


# ------------------------------------------------------------------ data sources ---

class Node(NSObject):
    """One outline row: a CalDef group, or an entry (index into the module)."""


def make_node(title=None, index=None, children=()):
    n = Node.alloc().init()
    n.title, n.index, n.children = title, index, list(children)
    return n


class SidebarSource(NSObject):
    def initWithController_(self, controller):
        self = objc.super(SidebarSource, self).init()
        self.c = controller
        return self

    def numberOfRowsInTableView_(self, table):
        return len(self.c.modules)

    def tableView_viewForTableColumn_row_(self, table, col, row):
        m = self.c.modules[row]
        changed = sum(service.is_modified(e) for e in m["entries"])
        name = SLOTS.get(m["meta"]["slot"], (None, "doc.text"))[1]
        if m["meta"]["digest_ok"] is False:
            name = "exclamationmark.triangle"
        detail = module_subtitle(m) if m["meta"]["slot"] is not None else "XML"
        if changed:
            detail += f" · {changed} edited"
        return sidebar_cell(module_name(m), detail, name, f"{module_subtitle(m)}\n{m['filename']}")

    def tableViewSelectionDidChange_(self, note):
        row = note.object().selectedRow()
        if row >= 0 and self.c.modules[row] is not self.c.current:
            self.c.select_module(row)


class EntrySource(NSObject):
    def initWithController_(self, controller):
        self = objc.super(EntrySource, self).init()
        self.c = controller
        return self

    def outlineView_numberOfChildrenOfItem_(self, view, item):
        return len(self.c.nodes if item is None else item.children)

    def outlineView_child_ofItem_(self, view, i, item):
        return (self.c.nodes if item is None else item.children)[i]

    def outlineView_isItemExpandable_(self, view, item):
        return item.index is None

    def outlineView_isGroupItem_(self, view, item):
        return False

    def outlineView_shouldSelectItem_(self, view, item):
        return item.index is not None

    def outlineView_viewForTableColumn_item_(self, view, col, item):
        first = col is None or col.identifier() == "name"
        if item.index is None:
            if not first:
                return cell("")
            return cell(item.title, trailing=str(len(item.children)), tooltip=item.title,
                        font=A.NSFont.boldSystemFontOfSize_(A.NSFont.systemFontSize()))
        e = self.c.current["entries"][item.index]
        name = e["name"] or f"Unresolved {e['cal_id']}"
        changed = service.is_modified(e)
        if first:
            mark = "exclamationmark.triangle" if e["safety_restricted"] else None
            view_ = cell(name, symbol_name=mark, tooltip=name)
            if mark:
                view_.imageView().setContentTintColor_(A.NSColor.systemOrangeColor())
                view_.imageView().setAccessibilityLabel_("Elevated caution")
            return view_
        # a symbol as well as colour, so the state does not depend on colour alone
        return cell(pretty_value(e).replace("\n", " "), symbol_name="pencil.circle.fill" if changed else None,
                    color=A.NSColor.controlAccentColor() if changed else A.NSColor.secondaryLabelColor(),
                    tooltip=pretty_value(e))

    def outlineViewSelectionDidChange_(self, note):
        row = self.c.outline.selectedRow()
        item = self.c.outline.itemAtRow_(row) if row >= 0 else None
        if item is not None and item.index is not None:
            self.c.show_entry(self.c.current["entries"][item.index])
        else:
            self.c.show_entry(None)


class CalDefSource(NSObject):
    def initWithSheet_(self, sheet):
        self = objc.super(CalDefSource, self).init()
        self.s = sheet
        return self

    def numberOfRowsInTableView_(self, table):
        return len(self.s.results)

    def tableView_viewForTableColumn_row_(self, table, col, row):
        r = self.s.results[row]
        present = self.s.is_present(r)
        color = A.NSColor.tertiaryLabelColor() if present else None
        key = col.identifier()
        if key == "name":
            mark = "checkmark" if present else "exclamationmark.triangle" if r["safety_restricted"] else None
            return cell(r["name"], symbol_name=mark, color=color, tooltip=r["name"])
        return cell(str(r[key] or ""), color=color or A.NSColor.secondaryLabelColor(),
                    tooltip=str(r[key] or ""))

    def tableViewSelectionDidChange_(self, note):
        self.s.selection_changed()


# ---------------------------------------------------------------- the controller ---

class Controller(NSObject):
    def init(self):
        self = objc.super(Controller, self).init()
        self.modules, self.nodes = [], []
        self.sources = set()          # files loaded this session; never overwritten
        self.current = self.entry = None
        self.dirty = False
        self.query, self.scope, self.type_filter = "", 0, ""
        self.add_sheet = self.help_window = None
        self.pending_paths, self.load_problems = [], []
        self.build_window()
        return self

    # -------------------------------------------------------------- application ---

    def applicationDidFinishLaunching_(self, note):
        self.window.center()
        self.window.makeKeyAndOrderFront_(None)
        A.NSApp.activateIgnoringOtherApps_(True)
        if self.pending_paths:
            self.load_paths(self.pending_paths)

    def applicationShouldTerminateAfterLastWindowClosed_(self, app):
        return True

    def applicationShouldTerminate_(self, app):
        self.window.makeFirstResponder_(None)    # commit a value still being typed first
        ok = not self.dirty or self.ask("Quit without exporting your changes?",
                                        "Changes that you haven’t exported will be lost.", "Quit", True)
        return A.NSTerminateNow if ok else A.NSTerminateCancel

    def windowShouldClose_(self, window):
        if window is not self.window:
            return True
        A.NSApp.terminate_(None)      # asks about unexported changes
        return False

    @objc.python_method
    def ask(self, title, info, confirm, destructive=False) -> bool:
        """A decision alert: verb button plus Cancel, and no default button, so Return
        cannot accept it by reflex."""
        alert = A.NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(info)
        ok = alert.addButtonWithTitle_(confirm)
        alert.addButtonWithTitle_("Cancel").setKeyEquivalent_("\x1b")
        ok.setKeyEquivalent_("")
        ok.setHasDestructiveAction_(destructive)
        return alert.runModal() == A.NSAlertFirstButtonReturn

    # ------------------------------------------------------------------- window ---

    @objc.python_method
    def build_window(self):
        style = (A.NSWindowStyleMaskTitled | A.NSWindowStyleMaskClosable | A.NSWindowStyleMaskResizable
                 | A.NSWindowStyleMaskMiniaturizable | A.NSWindowStyleMaskFullSizeContentView)
        w = A.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 1220, 760), style, A.NSBackingStoreBuffered, False)
        w.setReleasedWhenClosed_(False)
        w.setTitle_("Calibrations")
        w.setDelegate_(self)
        self.window = w

        split = A.NSSplitViewController.alloc().init()
        side = A.NSSplitViewItem.sidebarWithViewController_(view_controller(self.build_sidebar()))
        side.setMinimumThickness_(190)
        side.setMaximumThickness_(300)
        content = A.NSSplitViewItem.splitViewItemWithViewController_(view_controller(self.build_content()))
        content.setMinimumThickness_(430)
        inspector = A.NSSplitViewItem.inspectorWithViewController_(view_controller(self.build_inspector()))
        inspector.setMinimumThickness_(280)
        inspector.setMaximumThickness_(420)
        for item in (side, content, inspector):
            split.addSplitViewItem_(item)
        self.split = split
        w.setContentViewController_(split)
        w.setContentSize_(NSMakeSize(1220, 760))
        w.setContentMinSize_(NSMakeSize(940, 560))

        toolbar = A.NSToolbar.alloc().initWithIdentifier_("caltool.main")
        toolbar.setDelegate_(self)
        toolbar.setDisplayMode_(A.NSToolbarDisplayModeIconOnly)
        w.setToolbar_(toolbar)
        w.setToolbarStyle_(A.NSWindowToolbarStyleUnified)
        self.show_entry(None)
        self.update_state()

    @objc.python_method
    def build_sidebar(self):
        view = plain_view(220)
        table = A.NSTableView.alloc().initWithFrame_(NSMakeRect(0, 0, 220, 500))
        column(table, "module", "Modules", 190, 120)
        table.setHeaderView_(None)
        table.setStyle_(A.NSTableViewStyleSourceList)
        table.setRowHeight_(40)
        table.setAllowsEmptySelection_(False)
        self.sidebar_source = SidebarSource.alloc().initWithController_(self)
        table.setDataSource_(self.sidebar_source)
        table.setDelegate_(self.sidebar_source)
        self.sidebar = table
        scroll = scroll_view(table)
        scroll.setDrawsBackground_(False)
        fill(scroll, view)
        return view

    @objc.python_method
    def build_content(self):
        view = plain_view(640)

        self.workspace = auto(plain_view())
        fill(self.workspace, view)
        self.scope_control = auto(A.NSSegmentedControl.segmentedControlWithLabels_trackingMode_target_action_(
            ["All", "Edited", "Caution"], A.NSSegmentSwitchTrackingSelectOne, self, "changeScope:"))
        self.scope_control.setSelectedSegment_(0)
        self.type_popup = auto(A.NSPopUpButton.alloc().initWithFrame_pullsDown_(NSMakeRect(0, 0, 150, 24), False))
        self.type_popup.setTarget_(self)
        self.type_popup.setAction_("changeType:")
        self.type_popup.setAccessibilityLabel_("Value type")
        self.count = secondary()
        spacer = auto(plain_view(10, 10))
        spacer.setContentHuggingPriority_forOrientation_(1, A.NSLayoutConstraintOrientationHorizontal)
        bar = stack([self.scope_control, self.type_popup, spacer, self.count], vertical=False, spacing=12)

        self.banner = label("", color=A.NSColor.systemOrangeColor(), wrap=True)

        outline = A.NSOutlineView.alloc().initWithFrame_(NSMakeRect(0, 0, 600, 400))
        name = column(outline, "name", "Name", 340, 220)
        column(outline, "value", "Value", 240, 140)
        outline.setOutlineTableColumn_(name)
        outline.setUsesAlternatingRowBackgroundColors_(True)
        outline.setStyle_(A.NSTableViewStyleFullWidth)
        outline.setRowHeight_(24)
        outline.setColumnAutoresizingStyle_(A.NSTableViewUniformColumnAutoresizingStyle)
        outline.setAutoresizesOutlineColumn_(False)
        self.entry_source = EntrySource.alloc().initWithController_(self)
        outline.setDataSource_(self.entry_source)
        outline.setDelegate_(self.entry_source)
        self.outline = outline
        table = scroll_view(outline)

        column_ = stack([bar, self.banner, table], spacing=8)
        fill(column_, self.workspace, top=10, safe=True)
        activate(bar.widthAnchor().constraintEqualToAnchor_constant_(column_.widthAnchor(), -24),
                 bar.leadingAnchor().constraintEqualToAnchor_constant_(column_.leadingAnchor(), 12),
                 self.banner.leadingAnchor().constraintEqualToAnchor_constant_(column_.leadingAnchor(), 12),
                 self.banner.widthAnchor().constraintEqualToAnchor_constant_(column_.widthAnchor(), -24),
                 table.widthAnchor().constraintEqualToAnchor_(column_.widthAnchor()))

        self.empty = auto(plain_view())
        fill(self.empty, view)
        icon = auto(A.NSImageView.imageViewWithImage_(symbol("doc.badge.gearshape")))
        icon.setSymbolConfiguration_(A.NSImageSymbolConfiguration.configurationWithPointSize_weight_(46, A.NSFontWeightLight))
        icon.setContentTintColor_(A.NSColor.tertiaryLabelColor())
        heading = label("No Calibration Files", style=A.NSFontTextStyleTitle2)
        self.empty_note = secondary("Open a container, a .calovride file, or a .zip of them.", wrap=True)
        self.empty_note.setAlignment_(A.NSTextAlignmentCenter)
        open_button = button("Open…", self, "openDocument:")
        open_button.setKeyEquivalent_("\r")
        open_button.setControlSize_(A.NSControlSizeLarge)
        middle = stack([icon, heading, self.empty_note, open_button], spacing=10)
        middle.setAlignment_(A.NSLayoutAttributeCenterX)
        self.empty.addSubview_(middle)
        activate(middle.centerXAnchor().constraintEqualToAnchor_(self.empty.centerXAnchor()),
                 middle.centerYAnchor().constraintEqualToAnchor_(self.empty.centerYAnchor()),
                 self.empty_note.widthAnchor().constraintEqualToConstant_(340))
        return view

    @objc.python_method
    def build_inspector(self):
        view = plain_view(320)
        self.placeholder = secondary("No Selection", style=A.NSFontTextStyleTitle3)
        view.addSubview_(self.placeholder)
        activate(self.placeholder.centerXAnchor().constraintEqualToAnchor_(view.centerXAnchor()),
                 self.placeholder.centerYAnchor().constraintEqualToAnchor_(view.centerYAnchor()))

        self.name_label = label(style=A.NSFontTextStyleHeadline, wrap=True, selectable=True)
        self.name_label.setLineBreakMode_(A.NSLineBreakByCharWrapping)
        self.group_label = secondary(wrap=True)
        self.caution_label = label("⚠︎ Elevated caution: affects chimes, safety volume, or driver workload.",
                                   color=A.NSColor.systemOrangeColor(), wrap=True,
                                   style=A.NSFontTextStyleSubheadline)

        self.switch = auto(A.NSSwitch.alloc().init())
        self.switch.setTarget_(self)
        self.switch.setAction_("toggleValue:")
        self.switch.setAccessibilityLabel_("Value")
        self.switch_label = label()
        self.switch_row = stack([self.switch, self.switch_label], vertical=False)
        self.popup = auto(A.NSPopUpButton.alloc().initWithFrame_pullsDown_(NSMakeRect(0, 0, 200, 24), False))
        self.popup.setTarget_(self)
        self.popup.setAction_("chooseValue:")
        self.popup.setAccessibilityLabel_("Value")
        self.field = auto(A.NSTextField.textFieldWithString_(""))
        self.field.setTarget_(self)
        self.field.setAction_("commitValue:")
        self.field.cell().setSendsActionOnEndEditing_(True)
        self.field.setAccessibilityLabel_("Value")
        self.error_label = label(color=A.NSColor.systemRedColor(), wrap=True, style=A.NSFontTextStyleSubheadline)
        self.was_label = secondary(wrap=True)
        self.revert_button = button("Revert", self, "revertValue:")
        value_title = secondary("Value")
        self.editor = stack([value_title, self.switch_row, self.popup, self.field, self.error_label,
                             self.was_label, self.revert_button], spacing=6)

        about_title = secondary("Description")
        about_scroll, self.about = text_area()
        self.meta_label = secondary(style=A.NSFontTextStyleFootnote, wrap=True, selectable=True)
        separator = auto(A.NSBox.alloc().initWithFrame_(NSMakeRect(0, 0, 100, 1)))
        separator.setBoxType_(A.NSBoxSeparator)

        self.inspector_stack = stack([self.name_label, self.group_label, self.caution_label, separator,
                                      self.editor, about_title, about_scroll, self.meta_label], spacing=10)
        self.inspector_stack.setCustomSpacing_afterView_(3, self.name_label)
        self.inspector_stack.setCustomSpacing_afterView_(18, self.editor)
        self.inspector_stack.setCustomSpacing_afterView_(4, about_title)
        fill(self.inspector_stack, view, top=12, left=16, bottom=14, right=16, safe=True)
        full = [self.name_label, self.group_label, self.caution_label, separator, self.editor,
                about_scroll, self.meta_label]
        activate(*[v.widthAnchor().constraintEqualToAnchor_(self.inspector_stack.widthAnchor()) for v in full])
        activate(*[v.widthAnchor().constraintEqualToAnchor_(self.editor.widthAnchor())
                   for v in (self.popup, self.field, self.error_label, self.was_label)])
        activate(about_scroll.heightAnchor().constraintGreaterThanOrEqualToConstant_(80))
        return view

    # ------------------------------------------------------------------ toolbar ---

    def toolbarDefaultItemIdentifiers_(self, toolbar):
        return [A.NSToolbarToggleSidebarItemIdentifier, A.NSToolbarSidebarTrackingSeparatorItemIdentifier,
                "open", A.NSToolbarFlexibleSpaceItemIdentifier, "add", "export", "search",
                A.NSToolbarInspectorTrackingSeparatorItemIdentifier,
                A.NSToolbarFlexibleSpaceItemIdentifier, A.NSToolbarToggleInspectorItemIdentifier]

    def toolbarAllowedItemIdentifiers_(self, toolbar):
        return self.toolbarDefaultItemIdentifiers_(toolbar)

    def toolbar_itemForItemIdentifier_willBeInsertedIntoToolbar_(self, toolbar, ident, inserted):
        if ident == "search":
            item = A.NSSearchToolbarItem.alloc().initWithItemIdentifier_(ident)
            field = item.searchField()
            field.setPlaceholderString_("Search")
            field.setSendsSearchStringImmediately_(True)
            field.setTarget_(self)
            field.setAction_("search:")
            item.setPreferredWidthForSearchField_(200)
            self.search_item = item
            return item
        if ident == "export":
            item = A.NSMenuToolbarItem.alloc().initWithItemIdentifier_(ident)
            menu = A.NSMenu.alloc().init()
            for title, action in (("Export as Container…", "exportContainer:"),
                                  ("Export as XML…", "exportXML:"), (None, None),
                                  ("Export All as Zip…", "exportAll:")):
                if title is None:
                    menu.addItem_(A.NSMenuItem.separatorItem())
                else:
                    menu.addItemWithTitle_action_keyEquivalent_(title, action, "").setTarget_(self)
            item.setMenu_(menu)
            item.setShowsIndicator_(True)
            item.setImage_(symbol("square.and.arrow.up", "Export"))
            item.setLabel_("Export")
            item.setToolTip_("Export")
            return item
        spec = {"open": ("Open", "folder", "openDocument:", "Open files"),
                "add": ("Add Entry", "plus", "addEntry:", "Add an entry to this module")}.get(ident)
        if spec is None:
            return None
        title, image, action, tip = spec
        item = A.NSToolbarItem.alloc().initWithItemIdentifier_(ident)
        item.setLabel_(title)
        item.setImage_(symbol(image, title))
        item.setTarget_(self)
        item.setAction_(action)
        item.setBordered_(True)
        item.setToolTip_(tip)
        return item

    # --------------------------------------------------------------- validation ---

    @objc.python_method
    def allowed(self, action: str) -> bool:
        # While the Add sheet is up its module is fixed; Open (Cmd-O) or another Add would
        # replace or re-target self.current underneath it, and the sheet's next Add would
        # then write into a module that is no longer shown.
        if (action in ("openDocument:", "addEntry:", "exportXML:", "exportContainer:", "exportAll:", "find:")
                and self.window.attachedSheet() is not None):
            return False
        if action in ("addEntry:", "exportXML:", "find:"):
            return self.current is not None
        if action == "exportContainer:":
            return self.current is not None and self.current["template"] is not None
        if action == "exportAll:":
            return bool(self.modules)
        return True

    def validateMenuItem_(self, item):
        return self.allowed(item.action())

    def validateToolbarItem_(self, item):
        return self.allowed(item.action()) if item.action() else True

    @objc.python_method
    def update_state(self):
        has = bool(self.modules)
        self.empty.setHidden_(has)
        self.workspace.setHidden_(not has)
        self.window.setDocumentEdited_(self.dirty)

    # ------------------------------------------------------------------ loading ---

    def openDocument_(self, sender):
        panel = A.NSOpenPanel.openPanel()
        panel.setAllowsMultipleSelection_(True)
        panel.setCanChooseDirectories_(False)
        if panel.runModal() == A.NSModalResponseOK:
            self.load_paths([url.path() for url in panel.URLs()])

    def application_openFiles_(self, app, names):
        self.load_paths(list(names))

    @objc.python_method
    def load_paths(self, paths):
        if self.window.attachedSheet() is not None:   # Finder "Open With" while adding
            A.NSBeep()
            return
        self.window.makeFirstResponder_(None)    # so a value still being typed counts as dirty
        if self.dirty and not self.ask("Replace the open modules?",
                                       "Changes that you haven’t exported will be lost.", "Replace", True):
            return
        modules, problems = [], []
        for p in map(Path, paths):
            try:
                data = p.read_bytes()
                if p.suffix.lower() == ".zip":
                    found, skipped = service.load_zip(data)
                    modules += found
                    problems += [f"{s['filename']}: {s['reason']}" for s in skipped]
                else:
                    modules.append(service.load_module(p.name, data))
                self.sources.add(p.resolve())
            except Exception as e:   # as the web UI: any unparseable file is a skipped file,
                problems.append(f"{p.name}: {e}")   # never an exception lost in the run loop
        self.load_problems = problems
        if not modules:
            if problems:    # shown in place rather than as an alert: nothing to decide
                text = "Nothing could be opened. " + problems[0]
                if self.modules:
                    self.window.setSubtitle_(text)
                else:
                    self.empty_note.setStringValue_(text)
            return
        self.set_modules(modules)

    @objc.python_method
    def set_modules(self, modules):
        modules = sorted(modules, key=lambda m: (m["meta"]["slot"] is None, m["meta"]["slot"] or 0,
                                                 m["filename"]))
        self.modules = [service.start_tracking(m) for m in modules]
        self.current, self.dirty = None, False
        self.sidebar.reloadData()
        self.update_state()
        # open on something with content rather than an empty slot
        self.select_module(next((i for i, m in enumerate(self.modules) if m["entries"]), 0))

    @objc.python_method
    def select_module(self, index: int):
        self.current = m = self.modules[index]
        self.sidebar.selectRowIndexes_byExtendingSelection_(NSIndexSet.indexSetWithIndex_(index), False)
        self.window.setTitle_(module_name(m))
        self.window.setSubtitle_(module_subtitle(m))
        notes = []
        if m["meta"]["digest_ok"] is False:
            notes.append("⚠︎ Digest mismatch: this file was changed or damaged after it was sealed.")
        if self.load_problems:
            notes.append(f"{len(self.load_problems)} file(s) were not calibration modules and were skipped.")
        bad = m["meta"]["digest_ok"] is False
        self.banner.setTextColor_(A.NSColor.systemOrangeColor() if bad else A.NSColor.secondaryLabelColor())
        self.banner.setStringValue_("  ".join(notes))
        self.banner.setHidden_(not notes)
        self.refresh_types()
        self.reset_filters()
        if self.window.toolbar():
            self.window.toolbar().validateVisibleItems()

    @objc.python_method
    def refresh_types(self):
        self.type_popup.removeAllItems()
        self.type_popup.addItemWithTitle_("All Types")
        types = sorted({e["type"] for e in self.current["entries"]})
        for t in types:
            self.type_popup.addItemWithTitle_(t)
        # keep the popup and the filter it drives in step: rebuilding the menu selects
        # "All Types", which must not leave a stale type_filter still applied
        if self.type_filter in types:
            self.type_popup.selectItemWithTitle_(self.type_filter)
        else:
            self.type_filter = ""
            self.type_popup.selectItemAtIndex_(0)

    @objc.python_method
    def reset_filters(self):
        self.query, self.scope, self.type_filter = "", 0, ""
        if getattr(self, "search_item", None) is not None:
            self.search_item.searchField().setStringValue_("")
        self.scope_control.setSelectedSegment_(0)
        self.type_popup.selectItemAtIndex_(0)
        self.reload_entries()

    # ------------------------------------------------------------------ entries ---

    def search_(self, sender):
        self.query = sender.stringValue().strip()
        self.reload_entries()

    def changeScope_(self, sender):
        self.scope = sender.selectedSegment()
        self.reload_entries()

    def changeType_(self, sender):
        self.type_filter = "" if sender.indexOfSelectedItem() == 0 else sender.titleOfSelectedItem()
        self.reload_entries()

    def find_(self, sender):
        self.search_item.beginSearchInteraction()

    @objc.python_method
    def reload_entries(self, select: int | None = None):
        grouped = {}
        for i, e in enumerate(self.current["entries"] if self.current else []):
            if not service.matches(e, self.query, self.type_filter, self.scope == 1):
                continue
            if self.scope == 2 and not e["safety_restricted"]:
                continue
            grouped.setdefault(e["group"] or "Unresolved CalID", []).append(make_node(index=i))
        self.nodes = [make_node(title=g, children=kids) for g, kids in grouped.items()]
        self.outline.reloadData()
        self.outline.expandItem_expandChildren_(None, True)
        shown = sum(len(n.children) for n in self.nodes)
        total = len(self.current["entries"]) if self.current else 0
        self.count.setStringValue_(f"{total} entries" if shown == total else f"{shown} of {total}")
        self.show_entry(None)
        if select is not None:
            self.select_entry(select)

    @objc.python_method
    def visible_indexes(self) -> list[int]:
        return [c.index for n in self.nodes for c in n.children]

    @objc.python_method
    def select_entry(self, index: int):
        for group in self.nodes:
            for node in group.children:
                if node.index == index:
                    row = self.outline.rowForItem_(node)
                    self.outline.selectRowIndexes_byExtendingSelection_(NSIndexSet.indexSetWithIndex_(row), False)
                    self.outline.scrollRowToVisible_(row)
                    self.show_entry(self.current["entries"][index])
                    return

    @objc.python_method
    def show_entry(self, e: dict | None):
        self.entry = e
        self.placeholder.setHidden_(e is not None)
        self.inspector_stack.setHidden_(e is None)
        if e is None:
            return
        self.name_label.setStringValue_(e["name"] or "Unresolved CalID")
        self.group_label.setStringValue_(f"{e['group'] or 'Not in the CalDef database'} · {e['type']}")
        self.caution_label.setHidden_(not e["safety_restricted"])
        self.error_label.setHidden_(True)
        raw = e["value_raw"]
        labels = {o["value"]: o["label"] for o in e["enum_options"]}
        is_bool = e["editable"] and e["type"] == "Boolean" and raw in ("true", "false")
        is_enum = e["editable"] and bool(labels)
        self.editor.setHidden_(not e["editable"])
        self.switch_row.setHidden_(not is_bool)
        self.popup.setHidden_(not is_enum)
        self.field.setHidden_(is_bool or (is_enum and raw in labels))
        if e["editable"]:
            if is_bool:
                self.switch.setState_(1 if raw == "true" else 0)
                self.switch_label.setStringValue_(raw)
            if is_enum:
                self.popup.removeAllItems()
                for o in e["enum_options"]:
                    self.popup.addItemWithTitle_(f"{o['label']} ({o['value']})")
                    self.popup.lastItem().setRepresentedObject_(o["value"])
                self.popup.menu().addItem_(A.NSMenuItem.separatorItem())
                self.popup.addItemWithTitle_(CUSTOM)
                if raw in labels:
                    self.popup.selectItemAtIndex_(list(labels).index(raw))
                else:
                    self.popup.selectItemWithTitle_(CUSTOM)
            self.field.setStringValue_(raw)
        changed = e["editable"] and service.is_modified(e)
        self.was_label.setHidden_(not changed)
        self.revert_button.setHidden_(not changed)
        if changed:
            old = e["original_value_raw"]
            self.was_label.setStringValue_(
                "Added since you opened this file." if e["is_new"] else
                f"Originally {labels[old]} ({old})" if old in labels else f"Originally {old}")
            self.revert_button.setTitle_("Remove Entry" if e["is_new"] else "Revert")
        text = e["description"] or "The CalDef database has no description for this entry."
        known = e.get("known_effect")
        if known:
            text += "\n\n" + known["text"]
        if not e["editable"]:
            shown = raw
            if e["type"] == "BinaryFile":
                shown = {k: v for k, v in raw.items() if k != "data_b64"}
            text += ("\n\nThis type is read-only here. To change it, edit the ingested JSON and use the "
                     "command line.\n\n" + json.dumps(shown, indent=2))
        self.about.setString_(text)
        self.meta_label.setStringValue_(f"CalID {e['cal_id']}\nVersion {e['version']}")

    # ------------------------------------------------------------------ editing ---

    def toggleValue_(self, sender):
        self.set_current_value("true" if sender.state() else "false")

    def chooseValue_(self, sender):
        value = sender.selectedItem().representedObject()
        if value is None:     # "Custom Value…"
            self.field.setHidden_(False)
            self.window.makeFirstResponder_(self.field)
        else:
            self.set_current_value(str(value))

    def commitValue_(self, sender):
        if not sender.isHidden():
            self.set_current_value(str(sender.stringValue()))

    @objc.python_method
    def set_current_value(self, text: str):
        e = self.entry
        if e is None or not e["editable"]:
            return
        self.error_label.setHidden_(True)    # a previous refusal no longer applies
        if text == e["value_raw"]:
            return
        try:
            service.set_value(e, text)
        except service.USER_ERRORS as exc:   # inline, next to the control
            self.error_label.setStringValue_(str(exc))
            self.error_label.setHidden_(False)
            return
        self.changed(position(self.current["entries"], e))

    def revertValue_(self, sender):
        e = self.entry
        if e is None:
            return
        index = position(self.current["entries"], e)
        if e["is_new"]:
            del self.current["entries"][index]
            self.refresh_types()
            self.changed(None)
            return
        e["value_raw"] = e["original_value_raw"]
        e["value"] = service.display_value(e["type"], e["value_raw"])
        self.changed(index)

    @objc.python_method
    def changed(self, select: int | None):
        self.dirty = True
        self.window.setDocumentEdited_(True)
        row = position(self.modules, self.current)
        self.sidebar.reloadData()
        self.sidebar.selectRowIndexes_byExtendingSelection_(NSIndexSet.indexSetWithIndex_(row), False)
        origin = self.outline.enclosingScrollView().contentView().bounds().origin
        self.reload_entries(select)
        self.outline.scrollPoint_(origin)
        if self.outline.selectedRow() >= 0:
            self.outline.scrollRowToVisible_(self.outline.selectedRow())

    # ------------------------------------------------------------------- adding ---

    def addEntry_(self, sender):
        if self.current is None:
            return
        self.add_sheet = AddSheet(self, self.current)
        self.window.beginSheet_completionHandler_(self.add_sheet.window, None)

    def addSearch_(self, sender):
        self.add_sheet.search(str(sender.stringValue()))

    def addConfirm_(self, sender):
        self.add_sheet.add()

    def addDone_(self, sender):
        self.window.endSheet_(self.add_sheet.window)
        self.add_sheet.window.orderOut_(None)

    @objc.python_method
    def added(self, module: dict, entry: dict):
        self.refresh_types()
        self.reset_filters()
        if module is not self.current:     # cannot happen while allowed() guards the sheet
            return
        self.changed(position(module["entries"], entry))

    # ------------------------------------------------------------------- export ---

    @objc.python_method
    def confirm_caution(self, entries) -> bool:
        changed = service.changed_restricted(entries)
        if not changed:
            return True
        lines = [f"{e['name']}: " + ("added" if e["is_new"] else
                 f"{e['original_value_raw']} → {e['value_raw']}") for e in changed[:8]]
        if len(changed) > 8:
            lines.append(f"…and {len(changed) - 8} more")
        n = len(changed)
        return self.ask(f"Export {n} safety-related {'change' if n == 1 else 'changes'}?",
                        "These calibrations affect chimes, safety volume, driver workload, or security "
                        "logging. See section 3 of the customization guide.\n\n" + "\n".join(lines),
                        "Export", True)

    @objc.python_method
    def save(self, data: bytes, default_name: str, done: str) -> bool:
        panel = A.NSSavePanel.savePanel()
        panel.setNameFieldStringValue_(default_name)
        if panel.runModal() != A.NSModalResponseOK:
            return False
        path = Path(panel.URL().path())
        if path.resolve() in self.sources:
            self.report("The original file wasn’t replaced.",
                        "Choose a different name. Files you open are never overwritten.")
            return False
        try:
            path.write_bytes(data)
        except OSError as e:
            self.report("The file couldn’t be saved.", str(e))
            return False
        self.window.setSubtitle_(f"Exported {path.name}")
        if done:
            self.banner.setTextColor_(A.NSColor.secondaryLabelColor())
            self.banner.setStringValue_(done)
            self.banner.setHidden_(False)
        return True

    @objc.python_method
    def report(self, title, info):
        alert = A.NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(info)
        alert.runModal()

    @objc.python_method
    def export(self, fmt: str):
        m = self.current
        self.window.makeFirstResponder_(None)     # commit a value still being typed
        if m is None or not self.confirm_caution(m["entries"]):
            return
        try:
            # every changed restricted entry was confirmed above
            data = service.export_module(m["entries"], fmt, m["template"], safety_ack=True)
        except service.USER_ERRORS as e:
            self.report("The module couldn’t be exported.", str(e))
            return
        name = Path(m["filename"]).name
        if fmt == "xml":
            name = Path(name).stem + ".calovride"
        if self.save(data, name, SIGNATURE_NOTE if fmt == "container" else "") and len(self.modules) == 1:
            self.dirty = False
            self.window.setDocumentEdited_(False)

    def exportContainer_(self, sender):
        self.export("container")

    def exportXML_(self, sender):
        self.export("xml")

    def exportAll_(self, sender):
        self.window.makeFirstResponder_(None)
        if not self.modules or not self.confirm_caution([e for m in self.modules for e in m["entries"]]):
            return
        try:
            data = service.export_zip(self.modules, safety_ack=True)
        except service.USER_ERRORS as e:
            self.report("The modules couldn’t be exported.", str(e))
            return
        if self.save(data, "custom_calibration_set.zip", SIGNATURE_NOTE):
            self.dirty = False
            self.window.setDocumentEdited_(False)

    # --------------------------------------------------------------------- help ---

    def showHelp_(self, sender):
        if self.help_window is None:
            self.help_window = self.build_help()
        self.help_window.makeKeyAndOrderFront_(None)

    @objc.python_method
    def build_help(self):
        style = A.NSWindowStyleMaskTitled | A.NSWindowStyleMaskClosable | A.NSWindowStyleMaskResizable
        w = A.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 820, 620), style, A.NSBackingStoreBuffered, False)
        w.setReleasedWhenClosed_(False)
        w.setTitle_("Help")
        popup = auto(A.NSPopUpButton.alloc().initWithFrame_pullsDown_(NSMakeRect(0, 0, 300, 24), False))
        popup.addItemWithTitle_("Overview")
        for doc in sorted(DOCS_DIR.glob("*.md")):
            popup.addItemWithTitle_(doc.name)
        popup.setTarget_(self)
        popup.setAction_("chooseDocument:")
        scroll, self.help_text = text_area(True)
        self.help_text.setTextContainerInset_(NSMakeSize(16, 12))
        self.help_text.setString_(overview_text())
        content = stack([popup, scroll], spacing=10)
        fill(content, w.contentView(), top=12)
        activate(popup.leadingAnchor().constraintEqualToAnchor_constant_(content.leadingAnchor(), 16),
                 scroll.widthAnchor().constraintEqualToAnchor_(content.widthAnchor()))
        w.setContentSize_(NSMakeSize(820, 620))
        w.center()
        return w

    def chooseDocument_(self, sender):
        name = sender.titleOfSelectedItem()
        mono = name != "Overview"
        self.help_text.setString_((DOCS_DIR / name).read_text(encoding="utf-8") if mono else overview_text())
        self.help_text.setFont_(
            A.NSFont.monospacedSystemFontOfSize_weight_(12, A.NSFontWeightRegular) if mono else
            A.NSFont.preferredFontForTextStyle_options_(A.NSFontTextStyleBody, {}))


class AddSheet:
    """A sheet that searches the whole CalDef reference and adds to one module."""

    def __init__(self, controller, module):
        self.c, self.module, self.results = controller, module, []
        w = A.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 760, 520), A.NSWindowStyleMaskTitled, A.NSBackingStoreBuffered, False)
        w.setReleasedWhenClosed_(False)
        self.window = w

        title = label(f"Add an Entry to {module_name(module)}", style=A.NSFontTextStyleHeadline)
        self.field = auto(A.NSSearchField.alloc().initWithFrame_(NSMakeRect(0, 0, 400, 24)))
        self.field.setPlaceholderString_("Search calibration names")
        self.field.setSendsSearchStringImmediately_(True)
        self.field.setTarget_(controller)
        self.field.setAction_("addSearch:")

        table = A.NSTableView.alloc().initWithFrame_(NSMakeRect(0, 0, 700, 280))
        for ident, name, width in (("name", "Name", 300), ("group", "Group", 220),
                                   ("type", "Type", 90), ("default", "Default", 60)):
            column(table, ident, name, width, 60)
        table.setUsesAlternatingRowBackgroundColors_(True)
        table.setStyle_(A.NSTableViewStyleFullWidth)
        table.setRowHeight_(24)
        self.source = CalDefSource.alloc().initWithSheet_(self)
        table.setDataSource_(self.source)
        table.setDelegate_(self.source)
        self.table = table
        scroll = scroll_view(table)
        scroll.setBorderType_(A.NSBezelBorder)

        self.note = secondary("Type at least 2 characters.", wrap=True)
        self.note.setMaximumNumberOfLines_(4)
        done = button("Done", controller, "addDone:")
        done.setKeyEquivalent_("\x1b")
        self.add_button = button("Add", controller, "addConfirm:")
        self.add_button.setKeyEquivalent_("\r")
        self.add_button.setEnabled_(False)
        spacer = auto(plain_view(10, 10))
        spacer.setContentHuggingPriority_forOrientation_(1, A.NSLayoutConstraintOrientationHorizontal)
        buttons = stack([spacer, done, self.add_button], vertical=False)

        body = stack([title, self.field, scroll, self.note, buttons], spacing=12)
        fill(body, w.contentView(), top=20, left=20, bottom=20, right=20)
        activate(*[v.widthAnchor().constraintEqualToAnchor_(body.widthAnchor())
                   for v in (self.field, scroll, self.note, buttons)])
        activate(self.note.heightAnchor().constraintEqualToConstant_(68))
        w.setContentSize_(NSMakeSize(760, 520))
        w.setInitialFirstResponder_(self.field)

    def is_present(self, r):
        return any((e["name"], e["group"]) == (r["name"], r["group"]) for e in self.module["entries"])

    def search(self, query):
        query = query.strip()
        self.results = service.search_caldefs(query)
        self.table.deselectAll_(None)
        self.table.reloadData()
        self.add_button.setEnabled_(False)
        if len(query) < 2:
            self.note.setStringValue_("Type at least 2 characters.")
        elif len(self.results) == 50:
            self.note.setStringValue_("Showing the first 50 results. Type more to narrow them.")
        else:
            self.note.setStringValue_(f"{len(self.results)} results")

    def selected(self):
        row = self.table.selectedRow()
        return self.results[row] if 0 <= row < len(self.results) else None

    def selection_changed(self):
        r = self.selected()
        if r is None:
            self.add_button.setEnabled_(False)
            return
        present, supported = self.is_present(r), service.is_editable(r["type"])
        why = ("Already in this module. " if present else
               "" if supported else f"{r['type']} entries can’t be added here. ")
        self.note.setStringValue_(why + (r["description"] or "No description."))
        self.add_button.setEnabled_(supported and not present)

    def add(self):
        r = self.selected()
        if r is None or self.is_present(r) or not service.is_editable(r["type"]):
            return
        try:
            detail = service.caldef_detail(r["name"], r["group"])
            if detail["safety_restricted"] and not self.c.ask(
                    f"Add the safety-related calibration {r['name']}?",
                    f"It belongs to {r['group']}, which affects chimes, safety volume, driver workload, "
                    "or security logging. Read section 3 of the customization guide first.", "Add", True):
                return
            entry = service.add_entry(self.module, detail)
        except service.USER_ERRORS as e:
            self.note.setStringValue_(str(e))
            return
        self.c.added(self.module, entry)
        self.table.reloadData()
        self.add_button.setEnabled_(False)
        self.note.setStringValue_(f"Added {r['name']} with its default value.")


# --------------------------------------------------------------------- menu bar ---

def build_menu_bar(controller):
    bar = A.NSMenu.alloc().init()
    command, option, control, shift = (A.NSEventModifierFlagCommand, A.NSEventModifierFlagOption,
                                       A.NSEventModifierFlagControl, A.NSEventModifierFlagShift)

    def menu(title):
        holder = A.NSMenuItem.alloc().init()
        bar.addItem_(holder)
        m = A.NSMenu.alloc().initWithTitle_(title)
        holder.setSubmenu_(m)
        return m

    def item(m, title, action, key="", mods=command, target=None):
        if title is None:
            m.addItem_(A.NSMenuItem.separatorItem())
            return
        i = m.addItemWithTitle_action_keyEquivalent_(title, action, key)
        i.setKeyEquivalentModifierMask_(mods)
        if target is not None:
            i.setTarget_(target)

    app = menu(APP_NAME)
    item(app, f"About {APP_NAME}", "orderFrontStandardAboutPanel:")
    item(app, None, None)
    item(app, f"Hide {APP_NAME}", "hide:", "h")
    item(app, "Hide Others", "hideOtherApplications:", "h", command | option)
    item(app, "Show All", "unhideAllApplications:")
    item(app, None, None)
    item(app, f"Quit {APP_NAME}", "terminate:", "q")

    file = menu("File")
    item(file, "Open…", "openDocument:", "o", target=controller)
    item(file, None, None)
    item(file, "Add Entry…", "addEntry:", "n", command | shift, controller)
    item(file, None, None)
    item(file, "Export as Container…", "exportContainer:", "e", target=controller)
    item(file, "Export as XML…", "exportXML:", "e", command | shift, controller)
    item(file, "Export All as Zip…", "exportAll:", "e", command | option, controller)
    item(file, None, None)
    item(file, "Close", "performClose:", "w")

    edit = menu("Edit")
    for title, action, key in (("Undo", "undo:", "z"), ("Redo", "redo:", "Z"), (None, None, ""),
                               ("Cut", "cut:", "x"), ("Copy", "copy:", "c"), ("Paste", "paste:", "v"),
                               ("Select All", "selectAll:", "a"), (None, None, "")):
        item(edit, title, action, key)
    item(edit, "Find", "find:", "f", target=controller)

    view = menu("View")
    item(view, "Show Sidebar", "toggleSidebar:", "s", command | control)
    item(view, "Show Inspector", "toggleInspector:", "i", command | option)
    item(view, None, None)
    item(view, "Enter Full Screen", "toggleFullScreen:", "f", command | control)

    window = menu("Window")
    item(window, "Minimize", "performMiniaturize:", "m")
    item(window, "Zoom", "performZoom:")
    A.NSApp.setWindowsMenu_(window)

    help_ = menu("Help")
    item(help_, f"{APP_NAME} Help", "showHelp:", "?", target=controller)
    A.NSApp.setHelpMenu_(help_)
    A.NSApp.setMainMenu_(bar)


def main(paths=()):
    info = NSBundle.mainBundle().infoDictionary()
    info["CFBundleName"] = APP_NAME          # menu-bar title when run from a script
    app = A.NSApplication.sharedApplication()
    app.setActivationPolicy_(A.NSApplicationActivationPolicyRegular)
    controller = Controller.alloc().init()
    controller.pending_paths = [str(Path(p).resolve()) for p in paths]
    app.setDelegate_(controller)
    build_menu_bar(controller)
    app.run()


if __name__ == "__main__":
    main(sys.argv[1:])
