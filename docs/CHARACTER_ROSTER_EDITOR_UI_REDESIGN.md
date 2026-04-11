# Wizardry 6 Character Roster Editor (WinForms) — UI Redesign Proposal

## Goals

1. **Faster editing** of one character while keeping party context visible.
2. **Safer changes** with clearer dirty state, validation, and save affordances.
3. **Better density + readability** using WinForms-native layouts (`SplitContainer`, `TableLayoutPanel`, `FlowLayoutPanel`, `TabControl`).
4. **Scalable structure** so adding fields/tabs doesn’t cause layout drift.

---

## Information Architecture

### Overall shell

- **Top:** `MenuStrip` + compact `ToolStrip`
- **Center:** 3-pane layout with nested split containers
  - **Left pane (party list):** character roster table + quick filters
  - **Middle pane (detail editor):** tabbed editor for selected character
  - **Right pane (inspector):** derived stats, warnings, portrait preview, and audit log
- **Bottom:** status strip with file path, save state, and validation summary

### Why this is better than the current screen

- The current UI has large unused gray space in the lower-left and places most editing controls in one tall column. A multi-pane structure uses space more effectively and shortens pointer travel.
- Persisting the roster view while editing preserves context (slot order, level spread, HP trends).
- A dedicated inspector pane surfaces “is this valid?” feedback without modal popups.

---

## Proposed layout (WinForms-friendly)

### 1) App chrome

- `MenuStrip`
  - **File:** Open, Save, Save As, Export Character, Exit
  - **Edit:** Undo, Redo, Duplicate Character, Delete Character
  - **View:** Reset Layout, Compact Mode, Show Advanced Fields
  - **Tools:** Recalculate Derived Stats, Validate All Characters
  - **Help:** Field Reference
- `ToolStrip`
  - Open / Save / Save As / Add / Duplicate / Delete / Validate / Search box

### 2) Main body

Use a **vertical `SplitContainer`** (`Panel1` left, `Panel2` right), then split right again:

- `splitMain` (Left 30%, Right 70%)
  - **Panel1: Party panel**
    - Header row: search textbox + race/class filters
    - `DataGridView` roster with fixed key columns:
      - Slot, Name, Race, Class, Level, HP, STAM, Status
    - Footer row:
      - “Add Character”, “Delete”, “Move Up”, “Move Down”
  - **Panel2: `splitEditorInspector` (Editor 75%, Inspector 25%)**
    - **Left (Editor):** `TabControl` for selected character
    - **Right (Inspector):** portrait + derived values + validation

### 3) Character editor tabs

#### Core tab

- 2-column `TableLayoutPanel` with grouped sections (`GroupBox`):
  - Identity: Name, Race, Gender, Class, Portrait
  - Progression: Age, Level, Rank
  - Vitals: HP Cur/Max, STAM Cur/Max, Load Cur/Max
- Numeric fields use `NumericUpDown`; enum fields use `ComboBox` with `DropDownStyle=DropDownList`.

#### Attributes tab

- Grid-like editor for STR/INT/PIE/VIT/DEX/SPD/PER/KAR.
- Each row: label, value control, race/class min-max hint, delta indicator.

#### Skills tab

- `DataGridView` with columns: Skill, Base, Bonus, Effective.
- Right-side mini panel: “Auto-balance” and “Reset to class defaults”.

#### Spells tab

- Split by realm/school using nested tabs.
- Search + known spells grid + spell points summary cards.

#### Inventory tab

- Two-page inventory represented as tabs or subtables.
- Columns: Slot, Item Name, Qty, Charges, Flags.

#### Raw/Advanced tab (optional)

- Hex/offset-oriented controls for power users.
- Hidden behind “Show Advanced Fields”.

---

## Interaction and UX behavior

### Selection and save safety

- Switching selected character with unsaved edits prompts:
  - Save / Discard / Cancel
- Dirty state shown in:
  - Form title (`*`),
  - Status strip,
  - Save button enabled state.

### Validation model

- Inline validation icon next to fields.
- Inspector shows a list of current issues:
  - Error (blocks save), Warning (allowed), Info.
- Example checks:
  - Current ≤ Max fields
  - Attribute range by race/class
  - Slot uniqueness / class-specific constraints

### Keyboard flow

- `Ctrl+S` Save, `Ctrl+Shift+S` Save As
- `Ctrl+F` focus roster search
- `Ctrl+D` duplicate character
- Enter/Tab navigation consistent in all tabs

### Discoverability

- Every field label can expose tooltip with byte mapping/meaning.
- “Field Reference” opens a side sheet or help window tied to selected tab.

---

## Visual style (still WinForms-native)

- Keep default system font + slightly larger row heights for readability.
- Use subtle section backgrounds (`GroupBox` and panel padding) instead of custom skins.
- Reduce bright action buttons: primary only for Save; destructive (Delete) tinted and isolated.
- Use consistent spacing tokens (e.g., 8/12/16 px margins) via shared helper constants.

---

## Suggested implementation approach (incremental)

1. **Refactor layout containers first** without changing data bindings.
2. Move existing controls into **Core tab** and establish reusable field-row helpers.
3. Extract per-tab user controls (`CoreTabControl`, `StatsTabControl`, etc.).
4. Add inspector panel with read-only computed values.
5. Layer validation service and inline indicators.
6. Add toolbar/menu command routing and keyboard shortcuts.
7. Add optional advanced/raw tab.

This sequence keeps risk low and gives a working UI at each step.

---

## WinForms components mapping (concrete)

- `MainForm`
  - `MenuStrip menuMain`
  - `ToolStrip toolMain`
  - `StatusStrip statusMain`
  - `SplitContainer splitMain`
  - `SplitContainer splitEditorInspector`
- `PartyListPanel` (UserControl)
  - search/filter row (`FlowLayoutPanel`)
  - roster `DataGridView`
  - command row
- `CharacterEditorPanel` (UserControl)
  - `TabControl tabsCharacter`
  - tabs: Core, Attributes, Skills, Spells, Inventory, Advanced
- `InspectorPanel` (UserControl)
  - portrait viewer, derived stat cards, validation list (`ListView`)

---

## Example “before/after” outcomes

- **Before:** edit controls are long-form and vertically heavy, difficult to scan quickly.
- **After:** key fields grouped semantically; stats are scannable; validation is always visible.
- **Before:** actions are spread across top buttons and tab content.
- **After:** global actions live in menu/toolbar; contextual actions live in tab-local command strips.

---

## Optional enhancements compatible with WinForms

- Persist layout and column widths in user settings.
- Add command palette (`Ctrl+K`) for power users.
- Compare mode: select two characters and show diff in inspector.
- Batch edits for selected roster subset (e.g., adjust levels).

