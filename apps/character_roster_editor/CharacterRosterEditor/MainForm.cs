using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows.Forms;

namespace CharacterRosterEditor;

internal sealed class MainForm : Form
{
    private static readonly string[] SpellSchoolNames = { "Fire", "Water", "Air", "Earth", "Mental", "Magic" };
    private static readonly int[] VisibleSkillIndices = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 22, 23, 24, 25, 26, 27, 28, 29 };

    private readonly BindingList<CharacterRecord> _records = new BindingList<CharacterRecord>();
    private readonly List<CharacterRecord> _allRecords = new List<CharacterRecord>();

    private readonly DataGridView _grid = new DataGridView();
    private readonly TextBox _nameTextBox = new TextBox();
    private readonly NumericUpDown _levelNumeric = new NumericUpDown();
    private readonly NumericUpDown _rankNumeric = new NumericUpDown();
    private readonly NumericUpDown _ageNumeric = new NumericUpDown();
    private readonly NumericUpDown _hpCurNumeric = new NumericUpDown();
    private readonly NumericUpDown _hpMaxNumeric = new NumericUpDown();
    private readonly NumericUpDown _staminaCurNumeric = new NumericUpDown();
    private readonly NumericUpDown _staminaMaxNumeric = new NumericUpDown();
    private readonly NumericUpDown _loadCurNumeric = new NumericUpDown();
    private readonly NumericUpDown _loadMaxNumeric = new NumericUpDown();
    private readonly NumericUpDown _inventoryPage1Numeric = new NumericUpDown();
    private readonly NumericUpDown _inventoryPage2Numeric = new NumericUpDown();
    private readonly ComboBox _raceCombo = new ComboBox();
    private readonly ComboBox _genderCombo = new ComboBox();
    private readonly ComboBox _classCombo = new ComboBox();
    private readonly TableLayoutPanel _statsPanel = new TableLayoutPanel();
    private readonly NumericUpDown[] _statEditors = new NumericUpDown[8];
    private readonly PictureBox _portraitPictureBox = new PictureBox();
    private readonly Label _portraitInfoLabel = new Label();
    private readonly Button _portraitPrevButton = new Button();
    private readonly Button _portraitNextButton = new Button();
    private readonly DataGridView _spellPointsGrid = new DataGridView();
    private readonly DataGridView _skillsGrid = new DataGridView();
    private readonly DataGridView _inventoryGrid = new DataGridView();
    private readonly TextBox _knownSpellsHexTextBox = new TextBox();
    private readonly TextBox _searchTextBox = new TextBox();
    private readonly ComboBox _raceFilterCombo = new ComboBox();
    private readonly ComboBox _classFilterCombo = new ComboBox();
    private readonly Label _derivedStatsLabel = new Label();
    private readonly ListView _validationList = new ListView();
    private readonly StatusStrip _statusStrip = new StatusStrip();
    private readonly ToolStripStatusLabel _statusLabel = new ToolStripStatusLabel();
    private readonly TabControl _editorTabs = new TabControl();
    private readonly ToolStrip _toolStrip = new ToolStrip();
    private readonly SplitContainer _splitMain = new SplitContainer();
    private readonly SplitContainer _splitEditorInspector = new SplitContainer();

    private string? _currentPath;
    private PcfileDocument? _document;
    private bool _isUpdatingUi;
    private bool _hasUnsavedChanges;
    private int _selectedSlotIndex = -1;
    private bool _suppressSelectionPrompt;
    private readonly Dictionary<string, Bitmap[]> _portraitFramesByFile =
        new Dictionary<string, Bitmap[]>(StringComparer.OrdinalIgnoreCase);

    public MainForm()
    {
        Text = "Wizardry 6 Character Roster Editor";
        Width = 1500;
        Height = 900;
        StartPosition = FormStartPosition.CenterScreen;
        KeyPreview = true;

        BuildUi();
        ApplyStyle();
        UpdateWindowTitle();
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        if (!e.Cancel && !ConfirmCloseWithUnsavedChanges())
        {
            e.Cancel = true;
        }

        base.OnFormClosing(e);
    }


    protected override void OnShown(EventArgs e)
    {
        base.OnShown(e);
        ConfigureInitialSplitters();
    }

    private void ConfigureInitialSplitters()
    {
        ConfigureSplitterDistance(_splitMain, (int)(_splitMain.ClientSize.Width * 0.30));
        ConfigureSplitterDistance(_splitEditorInspector, (int)(_splitEditorInspector.ClientSize.Width * 0.75));
    }

    private static void ConfigureSplitterDistance(SplitContainer split, int target)
    {
        var max = split.ClientSize.Width - split.Panel2MinSize;
        var min = split.Panel1MinSize;
        if (max <= min)
        {
            split.SplitterDistance = Math.Max(1, Math.Min(min, split.ClientSize.Width - 1));
            return;
        }

        split.SplitterDistance = Math.Max(min, Math.Min(target, max));
    }


    protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
    {
        if (keyData == (Keys.Control | Keys.S))
        {
            SaveFile(false);
            return true;
        }

        if (keyData == (Keys.Control | Keys.Shift | Keys.S))
        {
            SaveFile(true);
            return true;
        }

        if (keyData == (Keys.Control | Keys.F))
        {
            _searchTextBox.Focus();
            _searchTextBox.SelectAll();
            return true;
        }

        return base.ProcessCmdKey(ref msg, keyData);
    }
    private void BuildUi()
    {
        BuildMenu();
        BuildToolStrip();
        BuildStatusStrip();

        _splitMain.Dock = DockStyle.Fill;
        _splitMain.Orientation = Orientation.Vertical;
        _splitMain.Panel1MinSize = 220;
        _splitMain.Panel2MinSize = 320;
        _splitMain.Padding = new Padding(8);

        _splitMain.Panel1.Controls.Add(BuildPartyPanel());

        _splitEditorInspector.Dock = DockStyle.Fill;
        _splitEditorInspector.Orientation = Orientation.Vertical;
        _splitEditorInspector.Panel1MinSize = 360;
        _splitEditorInspector.Panel2MinSize = 200;

        _editorTabs.Dock = DockStyle.Fill;
        _editorTabs.TabPages.Add(new TabPage("Core") { Controls = { BuildCoreEditorPanel() } });
        _editorTabs.TabPages.Add(new TabPage("Attributes") { Controls = { BuildAttributesPanel() } });
        _editorTabs.TabPages.Add(new TabPage("Spell Points") { Controls = { BuildSpellPointsPanel() } });
        _editorTabs.TabPages.Add(new TabPage("Skills") { Controls = { BuildSkillsPanel() } });
        _editorTabs.TabPages.Add(new TabPage("Inventory") { Controls = { BuildInventoryPanel() } });
        _editorTabs.TabPages.Add(new TabPage("Known Spells") { Controls = { BuildKnownSpellsPanel() } });

        _splitEditorInspector.Panel1.Controls.Add(_editorTabs);
        _splitEditorInspector.Panel2.Controls.Add(BuildInspectorPanel());

        _splitMain.Panel2.Controls.Add(_splitEditorInspector);

        Controls.Add(_splitMain);
    }

    private void BuildMenu()
    {
        var menu = new MenuStrip { Dock = DockStyle.Top };

        var fileMenu = new ToolStripMenuItem("&File");
        var openItem = new ToolStripMenuItem("Open...", null, (_, __) => OpenFile()) { ShortcutKeys = Keys.Control | Keys.O };
        var saveItem = new ToolStripMenuItem("Save", null, (_, __) => SaveFile(false)) { ShortcutKeys = Keys.Control | Keys.S };
        var saveAsItem = new ToolStripMenuItem("Save As...", null, (_, __) => SaveFile(true)) { ShortcutKeys = Keys.Control | Keys.Shift | Keys.S };
        fileMenu.DropDownItems.Add(openItem);
        fileMenu.DropDownItems.Add(saveItem);
        fileMenu.DropDownItems.Add(saveAsItem);
        fileMenu.DropDownItems.Add(new ToolStripSeparator());
        fileMenu.DropDownItems.Add("Exit", null, (_, __) => Close());

        var editMenu = new ToolStripMenuItem("&Edit");
        editMenu.DropDownItems.Add("Delete Character", null, (_, __) => DeleteSelectedCharacter());

        var toolsMenu = new ToolStripMenuItem("&Tools");
        toolsMenu.DropDownItems.Add("Validate Selected", null, (_, __) => RefreshInspector(GetSelectedRecord()));

        menu.Items.Add(fileMenu);
        menu.Items.Add(editMenu);
        menu.Items.Add(toolsMenu);

        MainMenuStrip = menu;
        Controls.Add(menu);
    }

    private void BuildToolStrip()
    {
        _toolStrip.Dock = DockStyle.Top;
        _toolStrip.GripStyle = ToolStripGripStyle.Hidden;

        _toolStrip.Items.Add(CreateToolButton("Open", (_, __) => OpenFile()));
        _toolStrip.Items.Add(CreateToolButton("Save", (_, __) => SaveFile(false)));
        _toolStrip.Items.Add(CreateToolButton("Save As", (_, __) => SaveFile(true)));
        _toolStrip.Items.Add(new ToolStripSeparator());
        _toolStrip.Items.Add(CreateToolButton("Delete", (_, __) => DeleteSelectedCharacter()));
        _toolStrip.Items.Add(new ToolStripSeparator());
        _toolStrip.Items.Add(new ToolStripLabel("Search"));

        var searchHost = new ToolStripControlHost(new TextBox { Width = 180 });
        if (searchHost.Control is TextBox textBox)
        {
            textBox.TextChanged += (_, __) =>
            {
                _searchTextBox.Text = textBox.Text;
                ApplyRosterFilter();
            };
        }

        _toolStrip.Items.Add(searchHost);
        Controls.Add(_toolStrip);
    }

    private void BuildStatusStrip()
    {
        _statusStrip.Dock = DockStyle.Bottom;
        _statusLabel.Text = "Ready";
        _statusStrip.Items.Add(_statusLabel);
        Controls.Add(_statusStrip);
    }

    private Control BuildPartyPanel()
    {
        var panel = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 1,
            RowCount = 3,
            Padding = new Padding(4),
        };
        panel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        panel.RowStyles.Add(new RowStyle(SizeType.AutoSize));

        panel.Controls.Add(BuildRosterFilterPanel(), 0, 0);

        BuildRosterGrid();
        panel.Controls.Add(_grid, 0, 1);

        var commandRow = new FlowLayoutPanel { Dock = DockStyle.Fill, AutoSize = true };
        commandRow.Controls.Add(CreateButton("Delete", (_, __) => DeleteSelectedCharacter()));
        panel.Controls.Add(commandRow, 0, 2);

        return panel;
    }

    private Control BuildRosterFilterPanel()
    {
        var panel = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            AutoSize = true,
            WrapContents = false,
            Padding = new Padding(0, 0, 0, 8),
        };

        _searchTextBox.Width = 180;
        _searchTextBox.TextChanged += (_, __) => ApplyRosterFilter();

        PopulateFilterCombo(_raceFilterCombo, "All Races", LookupTables.Races);
        PopulateFilterCombo(_classFilterCombo, "All Classes", LookupTables.Classes);
        _raceFilterCombo.SelectedIndexChanged += (_, __) => ApplyRosterFilter();
        _classFilterCombo.SelectedIndexChanged += (_, __) => ApplyRosterFilter();

        panel.Controls.Add(new Label { Text = "Find", AutoSize = true, Margin = new Padding(0, 7, 4, 0) });
        panel.Controls.Add(_searchTextBox);
        panel.Controls.Add(new Label { Text = "Race", AutoSize = true, Margin = new Padding(12, 7, 4, 0) });
        panel.Controls.Add(_raceFilterCombo);
        panel.Controls.Add(new Label { Text = "Class", AutoSize = true, Margin = new Padding(12, 7, 4, 0) });
        panel.Controls.Add(_classFilterCombo);

        return panel;
    }

    private Control BuildInspectorPanel()
    {
        var panel = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 1,
            RowCount = 3,
            Padding = new Padding(8),
        };
        panel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        panel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        var portrait = BuildPortraitPreviewPanel();
        portrait.Dock = DockStyle.Top;

        _derivedStatsLabel.Dock = DockStyle.Top;
        _derivedStatsLabel.AutoSize = true;
        _derivedStatsLabel.Text = "Derived stats will appear here.";

        _validationList.Dock = DockStyle.Fill;
        _validationList.View = View.Details;
        _validationList.Columns.Add("Severity", 70);
        _validationList.Columns.Add("Issue", 280);
        _validationList.FullRowSelect = true;

        panel.Controls.Add(portrait, 0, 0);
        panel.Controls.Add(_derivedStatsLabel, 0, 1);
        panel.Controls.Add(_validationList, 0, 2);

        return panel;
    }

    private void BuildRosterGrid()
    {
        _grid.Dock = DockStyle.Fill;
        _grid.AutoGenerateColumns = false;
        _grid.MultiSelect = false;
        _grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
        _grid.AllowUserToAddRows = false;
        _grid.AllowUserToDeleteRows = false;
        _grid.DataSource = _records;
        _grid.RowHeadersVisible = false;
        _grid.SelectionChanged += GridOnSelectionChanged;
        _grid.CellClick += (_, __) => LoadSelectionIntoEditor();

        _grid.Columns.Clear();
        _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CharacterRecord.SlotIndex), HeaderText = "Slot", Width = 50 });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CharacterRecord.Name), HeaderText = "Name", Width = 140 });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CharacterRecord.Level), HeaderText = "Level", Width = 60 });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CharacterRecord.Rank), HeaderText = "Rank", Width = 60 });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Race", Width = 110, Name = "RaceDisplay" });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Class", Width = 110, Name = "ClassDisplay" });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CharacterRecord.HitPointsCurrent), HeaderText = "HP", Width = 60 });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CharacterRecord.StaminaCurrent), HeaderText = "STM", Width = 60 });
        _grid.CellFormatting += GridOnCellFormatting;
    }

    private Control BuildAttributesPanel()
    {
        var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(16) };
        BuildStatsEditor();
        panel.Controls.Add(_statsPanel);
        return panel;
    }

    private ToolStripButton CreateToolButton(string text, EventHandler onClick)
    {
        var button = new ToolStripButton(text)
        {
            DisplayStyle = ToolStripItemDisplayStyle.Text,
        };
        button.Click += onClick;
        return button;
    }

    private void PopulateFilterCombo(ComboBox combo, string allLabel, IReadOnlyDictionary<byte, string> values)
    {
        combo.DropDownStyle = ComboBoxStyle.DropDownList;
        combo.Width = 150;
        combo.Items.Clear();
        combo.Items.Add(allLabel);
        foreach (var value in values.OrderBy(k => k.Key))
        {
            combo.Items.Add(new ComboItem(value.Key, value.Value));
        }

        combo.SelectedIndex = 0;
    }

    private void ApplyRosterFilter()
    {
        if (_document == null)
        {
            return;
        }

        var search = _searchTextBox.Text.Trim();
        byte? raceFilter = _raceFilterCombo.SelectedItem is ComboItem race ? race.Key : null;
        byte? classFilter = _classFilterCombo.SelectedItem is ComboItem klass ? klass.Key : null;

        var currentSlot = GetSelectedRecord()?.SlotIndex;

        _records.RaiseListChangedEvents = false;
        _records.Clear();
        foreach (var record in _allRecords)
        {
            if (!string.IsNullOrWhiteSpace(search) && record.Name.IndexOf(search, StringComparison.OrdinalIgnoreCase) < 0)
            {
                continue;
            }

            if (raceFilter.HasValue && record.RaceId != raceFilter.Value)
            {
                continue;
            }

            if (classFilter.HasValue && record.ClassId != classFilter.Value)
            {
                continue;
            }

            _records.Add(record);
        }

        _records.RaiseListChangedEvents = true;
        _records.ResetBindings();

        if (_records.Count == 0)
        {
            _selectedSlotIndex = -1;
            LoadSelectionIntoEditor();
            return;
        }

        var rowToSelect = 0;
        if (currentSlot.HasValue)
        {
            for (var i = 0; i < _records.Count; i++)
            {
                if (_records[i].SlotIndex == currentSlot.Value)
                {
                    rowToSelect = i;
                    break;
                }
            }
        }

        _grid.ClearSelection();
        _grid.Rows[rowToSelect].Selected = true;
        _grid.CurrentCell = _grid.Rows[rowToSelect].Cells[0];
        LoadSelectionIntoEditor();
        UpdateStatus($"Showing {_records.Count} characters");
    }

    private bool ConfirmSelectionChange(int newSlotIndex)
    {
        if (_suppressSelectionPrompt || !_hasUnsavedChanges || _selectedSlotIndex < 0 || _selectedSlotIndex == newSlotIndex)
        {
            return true;
        }

        var result = MessageBox.Show(
            this,
            "You have unsaved edits. Save before switching characters?",
            "Unsaved changes",
            MessageBoxButtons.YesNoCancel,
            MessageBoxIcon.Warning);

        if (result == DialogResult.Cancel)
        {
            return false;
        }

        if (result == DialogResult.Yes)
        {
            return SaveFile(false);
        }

        return true;
    }

    private void SelectSlot(int slotIndex)
    {
        for (var i = 0; i < _records.Count; i++)
        {
            if (_records[i].SlotIndex != slotIndex)
            {
                continue;
            }

            _suppressSelectionPrompt = true;
            _grid.ClearSelection();
            _grid.Rows[i].Selected = true;
            _grid.CurrentCell = _grid.Rows[i].Cells[0];
            _suppressSelectionPrompt = false;
            return;
        }
    }

    private void GridOnSelectionChanged(object? sender, EventArgs e)
    {
        if (_document == null)
        {
            return;
        }

        var selected = GetSelectedRecord();
        if (selected == null)
        {
            LoadSelectionIntoEditor();
            return;
        }

        if (!ConfirmSelectionChange(selected.SlotIndex))
        {
            SelectSlot(_selectedSlotIndex);
            return;
        }

        _selectedSlotIndex = selected.SlotIndex;
        LoadSelectionIntoEditor();
    }

    private void RefreshInspector(CharacterRecord? selected)
    {
        _validationList.Items.Clear();
        if (selected == null)
        {
            _derivedStatsLabel.Text = "No character selected.";
            return;
        }

        _derivedStatsLabel.Text =
            $"HP {selected.HitPointsCurrent}/{selected.HitPointsMax}\n" +
            $"Stamina {selected.StaminaCurrent}/{selected.StaminaMax}\n" +
            $"Load {selected.LoadCurrentTenths / 10.0:F1}/{selected.LoadMaxTenths / 10.0:F1}";

        if (selected.HitPointsCurrent > selected.HitPointsMax)
        {
            _validationList.Items.Add(new ListViewItem(new[] { "Error", "HP Current exceeds HP Max" }));
        }

        if (selected.StaminaCurrent > selected.StaminaMax)
        {
            _validationList.Items.Add(new ListViewItem(new[] { "Error", "Stamina Current exceeds Stamina Max" }));
        }

        if (selected.LoadCurrentTenths > selected.LoadMaxTenths)
        {
            _validationList.Items.Add(new ListViewItem(new[] { "Warning", "Current load exceeds max load" }));
        }

        if (_validationList.Items.Count == 0)
        {
            _validationList.Items.Add(new ListViewItem(new[] { "Info", "No validation issues." }));
        }
    }

    private void UpdateWindowTitle()
    {
        var fileName = string.IsNullOrWhiteSpace(_currentPath) ? "(no file)" : Path.GetFileName(_currentPath);
        var dirtyMarker = _hasUnsavedChanges ? "*" : string.Empty;
        Text = $"Wizardry 6 Character Roster Editor{dirtyMarker} - {fileName}";
    }

    private void UpdateStatus(string message)
    {
        _statusLabel.Text = message;
    }

    private Control BuildCoreEditorPanel()
    {
        var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(16) };
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, AutoScroll = true };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 140));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));

        ConfigureNumeric(_ageNumeric, 0, uint.MaxValue / 365u);
        ConfigureNumeric(_levelNumeric, 0, ushort.MaxValue);
        ConfigureNumeric(_rankNumeric, 0, ushort.MaxValue);

        var identityAndStats = BuildIdentityAndStatsSection();
        layout.Controls.Add(identityAndStats, 0, 0);
        layout.SetColumnSpan(identityAndStats, 2);

        PopulateCombo(_raceCombo, LookupTables.Races);
        PopulateCombo(_genderCombo, LookupTables.Genders);
        PopulateCombo(_classCombo, LookupTables.Classes);

        WireEditorEvents();
        panel.Controls.Add(layout);
        return panel;
    }

    private Control BuildIdentityAndStatsSection()
    {
        var identity = new TableLayoutPanel { AutoSize = true, ColumnCount = 2, Anchor = AnchorStyles.Top | AnchorStyles.Left };
        identity.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 140));
        identity.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        AddEditorRow(identity, 0, "Name", _nameTextBox);
        AddEditorRow(identity, 1, "Age (Years)", _ageNumeric);
        AddEditorRow(identity, 2, "Level", _levelNumeric);
        AddEditorRow(identity, 3, "Rank", _rankNumeric);
        AddEditorRow(identity, 4, "HP Current", ConfigureNumeric(_hpCurNumeric, 0, ushort.MaxValue));
        AddEditorRow(identity, 5, "HP Max", ConfigureNumeric(_hpMaxNumeric, 0, ushort.MaxValue));
        AddEditorRow(identity, 6, "Stamina Cur", ConfigureNumeric(_staminaCurNumeric, 0, ushort.MaxValue));
        AddEditorRow(identity, 7, "Stamina Max", ConfigureNumeric(_staminaMaxNumeric, 0, ushort.MaxValue));
        AddEditorRow(identity, 8, "Load Cur (x10)", ConfigureNumeric(_loadCurNumeric, 0, 65535));
        AddEditorRow(identity, 9, "Load Max (x10)", ConfigureNumeric(_loadMaxNumeric, 0, 65535));
        AddEditorRow(identity, 10, "Race", _raceCombo);
        AddEditorRow(identity, 11, "Gender", _genderCombo);
        AddEditorRow(identity, 12, "Class", _classCombo);
        AddEditorRow(identity, 13, "Inv Page1 Cnt", ConfigureNumeric(_inventoryPage1Numeric, 0, 255));
        AddEditorRow(identity, 14, "Inv Page2 Cnt", ConfigureNumeric(_inventoryPage2Numeric, 0, 255));
        return identity;
    }

    private void BuildStatsEditor()
    {
        _statsPanel.Controls.Clear();
        _statsPanel.Dock = DockStyle.Top;
        _statsPanel.AutoSize = true;
        _statsPanel.ColumnCount = 2;
        _statsPanel.RowCount = 8;
        _statsPanel.GrowStyle = TableLayoutPanelGrowStyle.FixedSize;
        _statsPanel.AutoScroll = false;
        _statsPanel.ColumnStyles.Clear();
        _statsPanel.RowStyles.Clear();
        _statsPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 80));
        _statsPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 180));

        var statNames = new[] { "STR", "INT", "PIE", "VIT", "DEX", "SPD", "PER", "KAR" };
        for (var i = 0; i < statNames.Length; i++)
        {
            _statsPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 36));
            var numeric = new NumericUpDown { Name = $"Stat{i}", Minimum = 0, Maximum = 255 };
            ConfigureNumeric(numeric, 0, 255);
            numeric.Anchor = AnchorStyles.Left;
            numeric.Margin = new Padding(0, 4, 0, 4);
            numeric.ValueChanged += (_, __) => ApplyEditorValues();
            _statEditors[i] = numeric;

            var label = new Label
            {
                Text = statNames[i],
                AutoSize = true,
                Anchor = AnchorStyles.Left,
                TextAlign = ContentAlignment.MiddleLeft,
                Margin = new Padding(0, 0, 8, 0),
            };

            _statsPanel.Controls.Add(label, 0, i);
            _statsPanel.Controls.Add(numeric, 1, i);
        }
    }

    private Control BuildSpellPointsPanel()
    {
        ConfigureTableGrid(_spellPointsGrid);
        _spellPointsGrid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "School", ReadOnly = true, Width = 120 });
        _spellPointsGrid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Current", Width = 90 });
        _spellPointsGrid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Max", Width = 90 });
        _spellPointsGrid.CellEndEdit += (_, __) => ApplySpellPointGrid();

        var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(12) };
        panel.Controls.Add(_spellPointsGrid);
        return panel;
    }

    private Control BuildSkillsPanel()
    {
        ConfigureTableGrid(_skillsGrid);
        _skillsGrid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Index", ReadOnly = true, Width = 60 });
        _skillsGrid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Label", ReadOnly = true, Width = 180 });
        _skillsGrid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Value", Width = 80 });
        _skillsGrid.CellEndEdit += (_, __) => ApplySkillsGrid();

        var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(12) };
        panel.Controls.Add(_skillsGrid);
        return panel;
    }

    private Control BuildInventoryPanel()
    {
        ConfigureTableGrid(_inventoryGrid);
        _inventoryGrid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Slot", ReadOnly = true, Width = 50 });
        _inventoryGrid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "ItemId", Width = 80 });
        _inventoryGrid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Load(x10)", Width = 80 });
        _inventoryGrid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "B4", Width = 60 });
        _inventoryGrid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "B5", Width = 60 });
        _inventoryGrid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "B6", Width = 60 });
        _inventoryGrid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "B7", Width = 60 });
        _inventoryGrid.CellEndEdit += (_, __) => ApplyInventoryGrid();

        var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(12) };
        panel.Controls.Add(_inventoryGrid);
        return panel;
    }

    private Control BuildKnownSpellsPanel()
    {
        var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(16) };
        var label = new Label
        {
            Dock = DockStyle.Top,
            Height = 48,
            Text = "Known spells bitset hex (12 bytes / 24 hex chars, spell id = bit index).",
        };

        _knownSpellsHexTextBox.Dock = DockStyle.Top;
        _knownSpellsHexTextBox.Height = 28;
        _knownSpellsHexTextBox.TextChanged += (_, __) => ApplyKnownSpellsHex();

        panel.Controls.Add(_knownSpellsHexTextBox);
        panel.Controls.Add(label);
        return panel;
    }

    private void WireEditorEvents()
    {
        _nameTextBox.TextChanged += (_, __) => ApplyEditorValues();
        _levelNumeric.ValueChanged += (_, __) => ApplyEditorValues();
        _rankNumeric.ValueChanged += (_, __) => ApplyEditorValues();
        _ageNumeric.ValueChanged += (_, __) => ApplyEditorValues();
        _hpCurNumeric.ValueChanged += (_, __) => ApplyEditorValues();
        _hpMaxNumeric.ValueChanged += (_, __) => ApplyEditorValues();
        _staminaCurNumeric.ValueChanged += (_, __) => ApplyEditorValues();
        _staminaMaxNumeric.ValueChanged += (_, __) => ApplyEditorValues();
        _loadCurNumeric.ValueChanged += (_, __) => ApplyEditorValues();
        _loadMaxNumeric.ValueChanged += (_, __) => ApplyEditorValues();
        _raceCombo.SelectedIndexChanged += (_, __) => ApplyEditorValues();
        _genderCombo.SelectedIndexChanged += (_, __) => ApplyEditorValues();
        _classCombo.SelectedIndexChanged += (_, __) => ApplyEditorValues();
        _inventoryPage1Numeric.ValueChanged += (_, __) => ApplyEditorValues();
        _inventoryPage2Numeric.ValueChanged += (_, __) => ApplyEditorValues();
    }

    private Control BuildPortraitPreviewPanel()
    {
        var panel = new FlowLayoutPanel
        {
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
            AutoSize = true,
            Width = 220,
        };

        _portraitPictureBox.Width = 96;
        _portraitPictureBox.Height = 96;
        _portraitPictureBox.SizeMode = PictureBoxSizeMode.Zoom;
        _portraitPictureBox.BorderStyle = BorderStyle.FixedSingle;

        _portraitInfoLabel.AutoSize = true;
        _portraitInfoLabel.Text = "No portrait loaded.";

        _portraitPrevButton.Text = "<";
        _portraitPrevButton.AutoSize = true;
        _portraitPrevButton.Click += (_, __) => CyclePortraitIndex(-1);

        _portraitNextButton.Text = ">";
        _portraitNextButton.AutoSize = true;
        _portraitNextButton.Click += (_, __) => CyclePortraitIndex(1);

        var navPanel = new FlowLayoutPanel
        {
            FlowDirection = FlowDirection.LeftToRight,
            WrapContents = false,
            AutoSize = true,
        };
        navPanel.Controls.Add(_portraitPrevButton);
        navPanel.Controls.Add(_portraitNextButton);

        panel.Controls.Add(_portraitPictureBox);
        panel.Controls.Add(navPanel);
        panel.Controls.Add(_portraitInfoLabel);
        return panel;
    }

    private void ApplyEditorValues()
    {
        if (_isUpdatingUi)
        {
            return;
        }

        if (_document == null)
        {
            return;
        }

        var selected = GetSelectedRecord();
        if (selected == null)
        {
            return;
        }

        selected.Name = _nameTextBox.Text;
        selected.Level = (ushort)_levelNumeric.Value;
        selected.Rank = (ushort)_rankNumeric.Value;
        var targetAgeYears = (uint)_ageNumeric.Value;
        if ((selected.AgeDays / 365u) != targetAgeYears)
        {
            selected.AgeDays = targetAgeYears * 365u;
        }
        selected.HitPointsCurrent = (ushort)_hpCurNumeric.Value;
        selected.HitPointsMax = (ushort)_hpMaxNumeric.Value;
        selected.StaminaCurrent = (ushort)_staminaCurNumeric.Value;
        selected.StaminaMax = (ushort)_staminaMaxNumeric.Value;
        selected.LoadCurrentTenths = (ushort)_loadCurNumeric.Value;
        selected.LoadMaxTenths = (ushort)_loadMaxNumeric.Value;
        selected.InventoryPage1Count = (byte)_inventoryPage1Numeric.Value;
        selected.InventoryPage2Count = (byte)_inventoryPage2Numeric.Value;

        if (_raceCombo.SelectedItem is ComboItem raceItem)
        {
            selected.RaceId = raceItem.Key;
        }

        if (_genderCombo.SelectedItem is ComboItem genderItem)
        {
            selected.GenderId = genderItem.Key;
        }

        if (_classCombo.SelectedItem is ComboItem classItem)
        {
            selected.ClassId = classItem.Key;
        }

        for (var i = 0; i < 8; i++)
        {
            if (_statEditors[i] == null)
            {
                continue;
            }

            selected.Stats[i] = (byte)_statEditors[i].Value;
        }

        MarkDirty();
        RefreshInspector(selected);
        _grid.Refresh();
    }

    private void LoadSelectionIntoEditor()
    {
        var selected = GetSelectedRecord();
        if (selected == null)
        {
            _portraitPictureBox.Image = null;
            _portraitInfoLabel.Text = "No portrait loaded.";
            _portraitPrevButton.Enabled = false;
            _portraitNextButton.Enabled = false;
            RefreshInspector(null);
            return;
        }

        _isUpdatingUi = true;
        _nameTextBox.Text = selected.Name;
        SetNumericValue(_levelNumeric, selected.Level);
        SetNumericValue(_rankNumeric, selected.Rank);
        SetNumericValue(_ageNumeric, selected.AgeYears);
        SetNumericValue(_hpCurNumeric, selected.HitPointsCurrent);
        SetNumericValue(_hpMaxNumeric, selected.HitPointsMax);
        SetNumericValue(_staminaCurNumeric, selected.StaminaCurrent);
        SetNumericValue(_staminaMaxNumeric, selected.StaminaMax);
        SetNumericValue(_loadCurNumeric, selected.LoadCurrentTenths);
        SetNumericValue(_loadMaxNumeric, selected.LoadMaxTenths);
        SetNumericValue(_inventoryPage1Numeric, selected.InventoryPage1Count);
        SetNumericValue(_inventoryPage2Numeric, selected.InventoryPage2Count);

        SelectComboByKey(_raceCombo, selected.RaceId);
        SelectComboByKey(_genderCombo, selected.GenderId);
        SelectComboByKey(_classCombo, selected.ClassId);

        for (var i = 0; i < 8; i++)
        {
            if (_statEditors[i] == null)
            {
                continue;
            }

            _statEditors[i].Value = selected.Stats[i];
        }

        RefreshSpellPointsGrid(selected);
        RefreshSkillsGrid(selected);
        RefreshInventoryGrid(selected);
        _knownSpellsHexTextBox.Text = BitConverter.ToString(selected.KnownSpellsBitset).Replace("-", string.Empty);
        RefreshPortraitPreview(selected);
        RefreshInspector(selected);

        _isUpdatingUi = false;
        UpdateStatus($"Editing slot {selected.SlotIndex}: {selected.Name}");
    }

    private void RefreshPortraitPreview(CharacterRecord selected)
    {
        var portraitIndexRaw = selected.PortraitIndex;
        var portraitFileRaw = selected.PortraitFileSelector;
        var portraitFrameRaw = selected.PortraitFrameSelector;
        _portraitPrevButton.Enabled = true;
        _portraitNextButton.Enabled = true;
        var portrait = ResolvePortraitReference(portraitIndexRaw, portraitFileRaw, portraitFrameRaw);
        if (portrait == null)
        {
            _portraitPictureBox.Image = null;
            _portraitInfoLabel.Text = $"Portrait not available (raw 0x19C={portraitIndexRaw}, 0x1A9={portraitFileRaw}, 0x1AA={portraitFrameRaw}).";
            return;
        }

        if (!_portraitFramesByFile.TryGetValue(portrait.Value.FileName, out var frames)
            || portrait.Value.FrameIndex < 0
            || portrait.Value.FrameIndex >= frames.Length)
        {
            _portraitPictureBox.Image = null;
            _portraitInfoLabel.Text = $"Missing {portrait.Value.FileName} frame {portrait.Value.FrameIndex}.";
            return;
        }

        _portraitPictureBox.Image = ScaleNearest(frames[portrait.Value.FrameIndex], 4);
        _portraitInfoLabel.Text = $"{portrait.Value.FileName} frame {portrait.Value.FrameIndex} via {portrait.Value.Source} (raw: 0x19C={portraitIndexRaw}, 0x1A9={portraitFileRaw}, 0x1AA={portraitFrameRaw})";
    }

    private void CyclePortraitIndex(int delta)
    {
        var selected = GetSelectedRecord();
        if (selected == null)
        {
            return;
        }

        const int portraitCount = 28;
        var nextIndex = (selected.PortraitIndex + delta + portraitCount) % portraitCount;
        selected.PortraitIndex = (byte)nextIndex;
        MarkDirty();
        RefreshPortraitPreview(selected);
        _grid.Refresh();
    }

    private void RefreshSpellPointsGrid(CharacterRecord selected)
    {
        _spellPointsGrid.Rows.Clear();
        for (var i = 0; i < 6; i++)
        {
            _spellPointsGrid.Rows.Add(SpellSchoolNames[i], selected.SpellPointsCurrent[i], selected.SpellPointsMax[i]);
        }
    }

    private void RefreshSkillsGrid(CharacterRecord selected)
    {
        _skillsGrid.Rows.Clear();
        foreach (var skillIndex in VisibleSkillIndices)
        {
            _skillsGrid.Rows.Add(skillIndex, GetSkillLabel(skillIndex), selected.Skills[skillIndex]);
        }
    }

    private void RefreshInventoryGrid(CharacterRecord selected)
    {
        _inventoryGrid.Rows.Clear();
        for (var i = 0; i < selected.Inventory.Length; i++)
        {
            var entry = selected.Inventory[i];
            _inventoryGrid.Rows.Add(i, entry.ItemId, entry.LoadTenths, entry.Byte4, entry.Byte5, entry.Byte6, entry.Byte7);
        }
    }

    private void ApplySpellPointGrid()
    {
        if (_isUpdatingUi)
        {
            return;
        }

        var selected = GetSelectedRecord();
        if (selected == null)
        {
            return;
        }

        for (var i = 0; i < 6 && i < _spellPointsGrid.Rows.Count; i++)
        {
            var row = _spellPointsGrid.Rows[i];
            selected.SpellPointsCurrent[i] = ParseUShortCell(row.Cells[1].Value);
            selected.SpellPointsMax[i] = ParseUShortCell(row.Cells[2].Value);
        }

        MarkDirty();
    }

    private void ApplySkillsGrid()
    {
        if (_isUpdatingUi)
        {
            return;
        }

        var selected = GetSelectedRecord();
        if (selected == null)
        {
            return;
        }

        for (var rowIndex = 0; rowIndex < _skillsGrid.Rows.Count; rowIndex++)
        {
            if (_skillsGrid.Rows[rowIndex].Cells[0].Value is null)
            {
                continue;
            }

            if (!int.TryParse(_skillsGrid.Rows[rowIndex].Cells[0].Value.ToString(), out var skillIndex))
            {
                continue;
            }

            if (skillIndex < 0 || skillIndex >= selected.Skills.Length)
            {
                continue;
            }

            selected.Skills[skillIndex] = ParseByteCell(_skillsGrid.Rows[rowIndex].Cells[2].Value);
        }

        MarkDirty();
    }

    private void ApplyInventoryGrid()
    {
        if (_isUpdatingUi)
        {
            return;
        }

        var selected = GetSelectedRecord();
        if (selected == null)
        {
            return;
        }

        for (var i = 0; i < selected.Inventory.Length && i < _inventoryGrid.Rows.Count; i++)
        {
            var row = _inventoryGrid.Rows[i];
            var entry = selected.Inventory[i];
            entry.ItemId = ParseUShortCell(row.Cells[1].Value);
            entry.LoadTenths = ParseUShortCell(row.Cells[2].Value);
            entry.Byte4 = ParseByteCell(row.Cells[3].Value);
            entry.Byte5 = ParseByteCell(row.Cells[4].Value);
            entry.Byte6 = ParseByteCell(row.Cells[5].Value);
            entry.Byte7 = ParseByteCell(row.Cells[6].Value);
        }

        MarkDirty();
    }

    private void ApplyKnownSpellsHex()
    {
        if (_isUpdatingUi)
        {
            return;
        }

        var selected = GetSelectedRecord();
        if (selected == null)
        {
            return;
        }

        var text = _knownSpellsHexTextBox.Text.Trim().Replace(" ", string.Empty);
        if (text.Length != 24)
        {
            return;
        }

        try
        {
            for (var i = 0; i < 12; i++)
            {
                selected.KnownSpellsBitset[i] = byte.Parse(text.Substring(i * 2, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture);
            }

            MarkDirty();
        }
        catch (FormatException)
        {
        }
    }

    private CharacterRecord? GetSelectedRecord()
    {
        if (_grid.CurrentRow?.DataBoundItem is CharacterRecord record)
        {
            return record;
        }

        return null;
    }

    private void OpenFile()
    {
        if (!ConfirmCloseWithUnsavedChanges())
        {
            return;
        }

        using (var dialog = new OpenFileDialog())
        {
            dialog.Filter = "Wizardry PCFILE (*.dbs)|*.dbs|All files (*.*)|*.*";
            dialog.Title = "Open PCFILE.DBS";

            if (dialog.ShowDialog(this) == DialogResult.OK)
            {
                _document = PcfileDocument.Load(dialog.FileName);
                _currentPath = dialog.FileName;
                LoadPortraitFiles(Path.GetDirectoryName(dialog.FileName));

                _allRecords.Clear();
                foreach (var record in _document.Records)
                {
                    _allRecords.Add(record);
                }

                _hasUnsavedChanges = false;
                _selectedSlotIndex = -1;
                UpdateWindowTitle();
                ApplyRosterFilter();
                UpdateStatus($"Loaded {_allRecords.Count} roster slots from {Path.GetFileName(_currentPath)}");
            }
        }
    }

    private void LoadPortraitFiles(string? directory)
    {
        _portraitFramesByFile.Clear();
        if (string.IsNullOrWhiteSpace(directory))
        {
            return;
        }

        var resolvedDirectory = directory!;
        LoadPortraitFile(resolvedDirectory, "WPORT1.EGA");
        LoadPortraitFile(resolvedDirectory, "WPORT2.EGA");
    }

    private void LoadPortraitFile(string directory, string fileName)
    {
        var path = FindPortraitFile(directory, fileName);
        if (path == null)
        {
            return;
        }

        var bytes = File.ReadAllBytes(path);
        if (bytes.Length < 14 * 288)
        {
            return;
        }

        var frames = new Bitmap[14];
        for (var i = 0; i < 14; i++)
        {
            frames[i] = DecodePortraitFrame(bytes, i * 288);
        }

        _portraitFramesByFile[fileName] = frames;
    }

    private static string? FindPortraitFile(string baseDirectory, string fileName)
    {
        foreach (var candidateDir in CandidatePortraitDirectories(baseDirectory))
        {
            if (!Directory.Exists(candidateDir))
            {
                continue;
            }

            var exactPath = Path.Combine(candidateDir, fileName);
            if (File.Exists(exactPath))
            {
                return exactPath;
            }

            var match = Directory
                .EnumerateFiles(candidateDir, "*", SearchOption.TopDirectoryOnly)
                .FirstOrDefault(path => string.Equals(Path.GetFileName(path), fileName, StringComparison.OrdinalIgnoreCase));
            if (match != null)
            {
                return match;
            }
        }

        return null;
    }

    private static System.Collections.Generic.IEnumerable<string> CandidatePortraitDirectories(string baseDirectory)
    {
        yield return baseDirectory;
        yield return Path.Combine(baseDirectory, "gamedata");

        if (Directory.GetParent(baseDirectory)?.FullName is string parent && !string.IsNullOrWhiteSpace(parent))
        {
            yield return parent;
            yield return Path.Combine(parent, "gamedata");
        }
    }

    private static Bitmap DecodePortraitFrame(byte[] bytes, int offset)
    {
        var bitmap = new Bitmap(24, 24, PixelFormat.Format24bppRgb);

        for (var tileY = 0; tileY < 3; tileY++)
        {
            for (var tileX = 0; tileX < 3; tileX++)
            {
                var tileIndex = tileY * 3 + tileX;
                var tileOffset = offset + tileIndex * 32;

                for (var row = 0; row < 8; row++)
                {
                    for (var col = 0; col < 8; col++)
                    {
                        var mask = 0x80 >> col;
                        var colorIndex = 0;
                        for (var plane = 0; plane < 4; plane++)
                        {
                            if ((bytes[tileOffset + row + (plane * 8)] & mask) != 0)
                            {
                                colorIndex |= (1 << plane);
                            }
                        }

                        var x = tileX * 8 + col;
                        var y = tileY * 8 + row;
                        bitmap.SetPixel(x, y, PortraitPalette[colorIndex]);
                    }
                }
            }
        }

        return bitmap;
    }

    private static Bitmap ScaleNearest(Bitmap source, int factor)
    {
        var output = new Bitmap(source.Width * factor, source.Height * factor, PixelFormat.Format24bppRgb);
        using (var graphics = Graphics.FromImage(output))
        {
            graphics.InterpolationMode = InterpolationMode.NearestNeighbor;
            graphics.PixelOffsetMode = PixelOffsetMode.Half;
            graphics.DrawImage(source, new Rectangle(0, 0, output.Width, output.Height));
        }

        return output;
    }

    private static (string FileName, int FrameIndex, string Source)? ResolvePortraitReference(byte portraitIndex, byte raw1A9, byte raw1AA)
    {
        if (portraitIndex < 28)
        {
            return (portraitIndex < 14 ? "WPORT1.EGA" : "WPORT2.EGA", portraitIndex % 14, "0x19C portrait index");
        }

        if (raw1A9 <= 1)
        {
            if (raw1AA < 14)
            {
                return (raw1A9 == 0 ? "WPORT1.EGA" : "WPORT2.EGA", raw1AA, "0x1A9+0x1AA (0-based)");
            }

            if (raw1AA is >= 1 and <= 14)
            {
                return (raw1A9 == 0 ? "WPORT1.EGA" : "WPORT2.EGA", raw1AA - 1, "0x1A9+0x1AA (1-based)");
            }
        }

        if (raw1A9 < 28)
        {
            return (raw1A9 < 14 ? "WPORT1.EGA" : "WPORT2.EGA", raw1A9 % 14, "0x1A9 absolute");
        }

        return null;
    }

    private bool SaveFile(bool forceChoosePath)
    {
        if (_document == null)
        {
            MessageBox.Show(this, "Load a file first.", "No document", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return false;
        }

        var outputPath = _currentPath;
        if (forceChoosePath || string.IsNullOrWhiteSpace(outputPath))
        {
            using (var dialog = new SaveFileDialog())
            {
                dialog.Filter = "Wizardry PCFILE (*.dbs)|*.dbs|All files (*.*)|*.*";
                dialog.Title = "Save PCFILE.DBS";
                dialog.FileName = Path.GetFileName(outputPath) ?? "PCFILE.DBS";

                if (dialog.ShowDialog(this) != DialogResult.OK)
                {
                    return false;
                }

                outputPath = dialog.FileName;
            }
        }

        _document.Records.Clear();
        foreach (var record in _allRecords)
        {
            _document.Records.Add(record);
        }

        _document.Save(outputPath!);
        _currentPath = outputPath;
        _hasUnsavedChanges = false;
        UpdateWindowTitle();
        UpdateStatus($"Saved to {Path.GetFileName(_currentPath)}");

        MessageBox.Show(this, "Roster saved successfully.", "Saved", MessageBoxButtons.OK, MessageBoxIcon.Information);
        return true;
    }

    private void DeleteSelectedCharacter()
    {
        var selected = GetSelectedRecord();
        if (selected == null)
        {
            MessageBox.Show(this, "Select a character slot first.", "No selection", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }

        if (!selected.IsActive)
        {
            MessageBox.Show(this, "This slot is already empty.", "Nothing to delete", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }

        var confirmation = MessageBox.Show(
            this,
            $"Delete character in slot {selected.SlotIndex} ({selected.Name})?",
            "Confirm deletion",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Warning);

        if (confirmation != DialogResult.Yes)
        {
            return;
        }

        selected.Clear();
        MarkDirty();
        LoadSelectionIntoEditor();
        _grid.Refresh();
    }

    private void MarkDirty()
    {
        _hasUnsavedChanges = true;
        UpdateWindowTitle();
        UpdateStatus("Unsaved changes");
    }

    private bool ConfirmCloseWithUnsavedChanges()
    {
        if (!_hasUnsavedChanges)
        {
            return true;
        }

        var result = MessageBox.Show(
            this,
            "You have unsaved changes. Save before closing?",
            "Unsaved changes",
            MessageBoxButtons.YesNoCancel,
            MessageBoxIcon.Warning);

        if (result == DialogResult.Cancel)
        {
            return false;
        }

        if (result == DialogResult.Yes)
        {
            return SaveFile(false);
        }

        return true;
    }

    private Button CreateButton(string text, EventHandler onClick)
    {
        var button = new Button
        {
            Text = text,
            Height = 34,
            Width = 150,
            FlatStyle = FlatStyle.Flat,
            Margin = new Padding(0, 0, 12, 0),
        };
        button.FlatAppearance.BorderSize = 1;
        button.Click += onClick;
        return button;
    }

    private NumericUpDown ConfigureNumeric(NumericUpDown control, decimal min, decimal max)
    {
        control.Minimum = min;
        control.Maximum = max;
        control.Width = 180;
        return control;
    }

    private void AddEditorRow(TableLayoutPanel layout, int row, string labelText, Control control)
    {
        if (layout.RowStyles.Count <= row)
        {
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        }

        var label = new Label { Text = labelText, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft, Margin = new Padding(0, 6, 8, 6) };

        control.Dock = DockStyle.Left;
        control.Margin = new Padding(0, 4, 0, 4);

        layout.Controls.Add(label, 0, row);
        layout.Controls.Add(control, 1, row);
    }

    private void PopulateCombo(ComboBox combo, System.Collections.Generic.IReadOnlyDictionary<byte, string> values)
    {
        combo.DropDownStyle = ComboBoxStyle.DropDownList;
        combo.Width = 220;
        combo.Items.Clear();

        foreach (var kvp in values.OrderBy(k => k.Key))
        {
            combo.Items.Add(new ComboItem(kvp.Key, kvp.Value));
        }

        if (combo.Items.Count > 0)
        {
            combo.SelectedIndex = 0;
        }
    }

    private static void SelectComboByKey(ComboBox combo, byte key)
    {
        for (var i = 0; i < combo.Items.Count; i++)
        {
            if (combo.Items[i] is ComboItem item && item.Key == key)
            {
                combo.SelectedIndex = i;
                return;
            }
        }

        combo.Items.Add(new ComboItem(key, $"Unknown ({key})"));
        combo.SelectedIndex = combo.Items.Count - 1;
    }

    private static void SetNumericValue(NumericUpDown numeric, decimal value)
    {
        if (value < numeric.Minimum)
        {
            numeric.Value = numeric.Minimum;
            return;
        }

        if (value > numeric.Maximum)
        {
            numeric.Value = numeric.Maximum;
            return;
        }

        numeric.Value = value;
    }

    private static ushort ParseUShortCell(object? value)
    {
        return ushort.TryParse(value?.ToString(), out var parsed) ? parsed : (ushort)0;
    }

    private static byte ParseByteCell(object? value)
    {
        return byte.TryParse(value?.ToString(), out var parsed) ? parsed : (byte)0;
    }

    private static string GetSkillLabel(int index)
    {
        switch (index)
        {
            case 0: return "wand_and_dagger";
            case 1: return "sword";
            case 2: return "axe";
            case 3: return "mace_and_flail";
            case 4: return "pole_and_staff";
            case 5: return "throwing";
            case 6: return "sling";
            case 7: return "bow";
            case 8: return "shield";
            case 9: return "hands_and_feet";
            case 11: return "artifacts";
            case 12: return "music";
            case 13: return "oratory";
            case 14: return "legerdemain";
            case 15: return "skulduggery";
            case 16: return "ninjutsu";
            case 22: return "scouting";
            case 23: return "mythology";
            case 24: return "scribe";
            case 25: return "alchemy";
            case 26: return "theology";
            case 27: return "theosophy";
            case 28: return "thaumaturgy";
            case 29: return "kirijutsu";
            default: return "unknown";
        }
    }

    private void GridOnCellFormatting(object? sender, DataGridViewCellFormattingEventArgs e)
    {
        if (_grid.Rows[e.RowIndex].DataBoundItem is not CharacterRecord record)
        {
            return;
        }

        if (_grid.Columns[e.ColumnIndex].Name == "RaceDisplay")
        {
            e.Value = record.GetRaceDisplayName();
            e.FormattingApplied = true;
        }
        else if (_grid.Columns[e.ColumnIndex].Name == "ClassDisplay")
        {
            e.Value = record.GetClassDisplayName();
            e.FormattingApplied = true;
        }
    }

    private static void ConfigureTableGrid(DataGridView grid)
    {
        grid.Dock = DockStyle.Fill;
        grid.AllowUserToAddRows = false;
        grid.AllowUserToDeleteRows = false;
        grid.RowHeadersVisible = false;
        grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.None;
    }

    private void ApplyStyle()
    {
        Font = new Font("Segoe UI", 9F, FontStyle.Regular, GraphicsUnit.Point);
        BackColor = Color.FromArgb(245, 247, 250);
        ForeColor = Color.FromArgb(33, 37, 41);
        ApplyControlStyle(Controls);

        StyleGrid(_grid);
        StyleGrid(_spellPointsGrid);
        StyleGrid(_skillsGrid);
        StyleGrid(_inventoryGrid);
    }

    private void StyleGrid(DataGridView grid)
    {
        grid.BackgroundColor = Color.White;
        grid.BorderStyle = BorderStyle.None;
        grid.DefaultCellStyle.BackColor = Color.White;
        grid.DefaultCellStyle.ForeColor = ForeColor;
        grid.DefaultCellStyle.SelectionBackColor = Color.FromArgb(220, 236, 255);
        grid.DefaultCellStyle.SelectionForeColor = Color.FromArgb(20, 52, 100);
        grid.AlternatingRowsDefaultCellStyle.BackColor = Color.FromArgb(248, 250, 252);
        grid.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(235, 240, 246);
        grid.ColumnHeadersDefaultCellStyle.ForeColor = Color.FromArgb(47, 62, 79);
        grid.ColumnHeadersDefaultCellStyle.Font = new Font(Font, FontStyle.Bold);
        grid.ColumnHeadersHeight = 34;
        grid.EnableHeadersVisualStyles = false;
        grid.GridColor = Color.FromArgb(220, 227, 234);
    }

    private void ApplyControlStyle(Control.ControlCollection controls)
    {
        foreach (Control control in controls)
        {
            switch (control)
            {
                case Button button:
                    button.BackColor = Color.FromArgb(42, 120, 228);
                    button.ForeColor = Color.White;
                    button.FlatAppearance.BorderColor = Color.FromArgb(29, 95, 184);
                    break;
                case TextBox textBox:
                    textBox.BackColor = Color.White;
                    textBox.ForeColor = Color.FromArgb(33, 37, 41);
                    textBox.BorderStyle = BorderStyle.FixedSingle;
                    break;
                case NumericUpDown numeric:
                    numeric.BackColor = Color.White;
                    numeric.ForeColor = Color.FromArgb(33, 37, 41);
                    break;
                case ComboBox combo:
                    combo.BackColor = Color.White;
                    combo.ForeColor = Color.FromArgb(33, 37, 41);
                    break;
                case TabControl tabs:
                    tabs.BackColor = Color.FromArgb(245, 247, 250);
                    tabs.ForeColor = Color.FromArgb(33, 37, 41);
                    break;
                case TabPage page:
                    page.BackColor = Color.FromArgb(245, 247, 250);
                    page.ForeColor = Color.FromArgb(33, 37, 41);
                    break;
                case FlowLayoutPanel flowPanel:
                    flowPanel.BackColor = Color.FromArgb(245, 247, 250);
                    flowPanel.ForeColor = Color.FromArgb(33, 37, 41);
                    break;
                case Panel panel:
                    panel.BackColor = Color.FromArgb(245, 247, 250);
                    break;
                case Label label:
                    label.ForeColor = Color.FromArgb(52, 58, 64);
                    break;
            }

            ApplyControlStyle(control.Controls);
        }
    }

    private sealed class ComboItem
    {
        public ComboItem(byte key, string value)
        {
            Key = key;
            Value = value;
        }

        public byte Key { get; }

        public string Value { get; }

        public override string ToString() => Value;
    }

    private static readonly Color[] PortraitPalette =
    {
        Color.FromArgb(0, 0, 0),
        Color.FromArgb(255, 255, 255),
        Color.FromArgb(85, 85, 255),
        Color.FromArgb(255, 85, 255),
        Color.FromArgb(255, 85, 85),
        Color.FromArgb(255, 255, 85),
        Color.FromArgb(85, 255, 85),
        Color.FromArgb(85, 255, 255),
        Color.FromArgb(85, 85, 85),
        Color.FromArgb(170, 170, 170),
        Color.FromArgb(0, 0, 170),
        Color.FromArgb(170, 0, 170),
        Color.FromArgb(170, 0, 0),
        Color.FromArgb(170, 85, 0),
        Color.FromArgb(0, 170, 0),
        Color.FromArgb(0, 170, 170),
    };
}
