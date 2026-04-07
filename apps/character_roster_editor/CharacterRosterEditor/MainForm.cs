using System;
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

    private string? _currentPath;
    private PcfileDocument? _document;
    private bool _isUpdatingUi;
    private bool _hasUnsavedChanges;
    private readonly System.Collections.Generic.Dictionary<string, Bitmap[]> _portraitFramesByFile =
        new System.Collections.Generic.Dictionary<string, Bitmap[]>(StringComparer.OrdinalIgnoreCase);

    public MainForm()
    {
        Text = "Wizardry 6 Character Roster Editor";
        Width = 1500;
        Height = 900;
        StartPosition = FormStartPosition.CenterScreen;

        BuildUi();
        ApplyStyle();
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        if (!e.Cancel && !ConfirmCloseWithUnsavedChanges())
        {
            e.Cancel = true;
        }

        base.OnFormClosing(e);
    }

    private void BuildUi()
    {
        var root = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 2,
            RowCount = 2,
            Padding = new Padding(12),
        };
        root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
        root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
        root.RowStyles.Add(new RowStyle(SizeType.Absolute, 46));
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        Controls.Add(root);

        var buttonPanel = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            FlowDirection = FlowDirection.LeftToRight,
            WrapContents = false,
            Padding = new Padding(0, 4, 0, 0),
        };

        buttonPanel.Controls.Add(CreateButton("Open PCFILE.DBS", (_, __) => OpenFile()));
        buttonPanel.Controls.Add(CreateButton("Save", (_, __) => SaveFile(false)));
        buttonPanel.Controls.Add(CreateButton("Save As", (_, __) => SaveFile(true)));
        buttonPanel.Controls.Add(CreateButton("Delete Character", (_, __) => DeleteSelectedCharacter()));

        root.Controls.Add(buttonPanel, 0, 0);
        root.SetColumnSpan(buttonPanel, 2);

        BuildRosterGrid();
        root.Controls.Add(_grid, 0, 1);

        var editorTabs = new TabControl { Dock = DockStyle.Fill };
        editorTabs.TabPages.Add(new TabPage("Core") { Controls = { BuildCoreEditorPanel() } });
        editorTabs.TabPages.Add(new TabPage("Spell Points") { Controls = { BuildSpellPointsPanel() } });
        editorTabs.TabPages.Add(new TabPage("Skills") { Controls = { BuildSkillsPanel() } });
        editorTabs.TabPages.Add(new TabPage("Inventory") { Controls = { BuildInventoryPanel() } });
        editorTabs.TabPages.Add(new TabPage("Known Spells") { Controls = { BuildKnownSpellsPanel() } });

        root.Controls.Add(editorTabs, 1, 1);
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
        _grid.SelectionChanged += (_, __) => LoadSelectionIntoEditor();
        _grid.CellClick += (_, __) => LoadSelectionIntoEditor();

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

    private Control BuildCoreEditorPanel()
    {
        var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(16) };
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, AutoScroll = true };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 140));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));

        ConfigureNumeric(_ageNumeric, 0, uint.MaxValue / 365u);
        ConfigureNumeric(_levelNumeric, 0, ushort.MaxValue);
        ConfigureNumeric(_rankNumeric, 0, ushort.MaxValue);

        BuildStatsEditor();

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
        var section = new TableLayoutPanel
        {
            Dock = DockStyle.Top,
            ColumnCount = 2,
            AutoSize = true,
            Margin = new Padding(0, 0, 0, 8),
        };
        section.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
        section.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
        section.RowStyles.Add(new RowStyle(SizeType.AutoSize));

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
        AddEditorRow(identity, 15, "Portrait", BuildPortraitPreviewPanel());

        _statsPanel.Anchor = AnchorStyles.Top | AnchorStyles.Left;

        section.Controls.Add(identity, 0, 0);
        section.Controls.Add(_statsPanel, 1, 0);
        return section;
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
            selected.Stats[i] = (byte)_statEditors[i].Value;
        }

        MarkDirty();
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
            _statEditors[i].Value = selected.Stats[i];
        }

        RefreshSpellPointsGrid(selected);
        RefreshSkillsGrid(selected);
        RefreshInventoryGrid(selected);
        _knownSpellsHexTextBox.Text = BitConverter.ToString(selected.KnownSpellsBitset).Replace("-", string.Empty);
        RefreshPortraitPreview(selected);

        _isUpdatingUi = false;
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

                _records.Clear();
                foreach (var record in _document.Records)
                {
                    _records.Add(record);
                }

                Text = $"Wizardry 6 Character Roster Editor - {Path.GetFileName(_currentPath)}";
                _hasUnsavedChanges = false;
                if (_records.Count > 0)
                {
                    _grid.Rows[0].Selected = true;
                    _grid.CurrentCell = _grid.Rows[0].Cells[0];
                    LoadSelectionIntoEditor();
                }
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
        foreach (var record in _records)
        {
            _document.Records.Add(record);
        }

        _document.Save(outputPath!);
        _currentPath = outputPath;
        _hasUnsavedChanges = false;

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
