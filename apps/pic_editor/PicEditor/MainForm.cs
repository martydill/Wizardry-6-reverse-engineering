using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Windows.Forms;

namespace PicEditor;

internal sealed class MainForm : Form
{
    private readonly ListBox _frameList = new ListBox();
    private readonly PictureBox _canvas = new PictureBox();
    private readonly FlowLayoutPanel _palettePanel = new FlowLayoutPanel();
    private readonly NumericUpDown _zoomNumeric = new NumericUpDown();
    private readonly Label _statusLabel = new Label();

    private readonly List<Stack<byte[]>> _undoStacks = new List<Stack<byte[]>>();
    private readonly List<Stack<byte[]>> _redoStacks = new List<Stack<byte[]>>();

    private SpriteDocument? _document;
    private int _currentFrameIndex;
    private int _zoom = 16;
    private int _selectedColorIndex = 1;
    private bool _dragging;
    private IndexedFrame? _copiedFrame;

    public MainForm()
    {
        Text = "Wizardry 6 PIC/WPORT Pixel Editor";
        Width = 1400;
        Height = 900;
        StartPosition = FormStartPosition.CenterScreen;
        BuildUi();
        ApplyStyle();
    }

    private void BuildUi()
    {
        var root = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2 };
        root.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 280));
        root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        Controls.Add(root);

        var left = new TableLayoutPanel { Dock = DockStyle.Fill, RowCount = 10, Padding = new Padding(8) };
        left.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        left.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        left.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        left.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        left.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        left.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        left.RowStyles.Add(new RowStyle(SizeType.Absolute, 24));
        left.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        left.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        left.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.Controls.Add(left, 0, 0);

        left.Controls.Add(CreateButton("Open", (_, __) => OpenFile()), 0, 0);
        left.Controls.Add(CreateButton("Save", (_, __) => SaveFile(false)), 0, 1);
        left.Controls.Add(CreateButton("Save As", (_, __) => SaveFile(true)), 0, 2);

        var zoomPanel = new FlowLayoutPanel { Dock = DockStyle.Fill, Height = 36 };
        zoomPanel.Controls.Add(new Label { Text = "Zoom", Width = 60, TextAlign = ContentAlignment.MiddleLeft });
        _zoomNumeric.Minimum = 4;
        _zoomNumeric.Maximum = 32;
        _zoomNumeric.Value = 16;
        _zoomNumeric.ValueChanged += (_, __) =>
        {
            _zoom = (int)_zoomNumeric.Value;
            Redraw();
        };
        zoomPanel.Controls.Add(_zoomNumeric);
        left.Controls.Add(zoomPanel, 0, 3);

        left.Controls.Add(new Label { Text = "Frames", Dock = DockStyle.Fill, TextAlign = ContentAlignment.BottomLeft }, 0, 5);
        _frameList.Dock = DockStyle.Fill;
        _frameList.SelectedIndexChanged += (_, __) =>
        {
            if (_frameList.SelectedIndex >= 0)
            {
                _currentFrameIndex = _frameList.SelectedIndex;
                Redraw();
            }
        };
        left.Controls.Add(_frameList, 0, 6);

        var frameEditPanel = new FlowLayoutPanel { Dock = DockStyle.Fill, Height = 72, WrapContents = true };
        frameEditPanel.Controls.Add(CreateButton("Copy Frame", (_, __) => CopyFrame()));
        frameEditPanel.Controls.Add(CreateButton("Paste Frame", (_, __) => PasteFrame()));
        frameEditPanel.Controls.Add(CreateButton("Duplicate", (_, __) => DuplicateFrame()));
        frameEditPanel.Controls.Add(CreateButton("Insert Blank", (_, __) => InsertBlankFrameAfter()));
        frameEditPanel.Controls.Add(CreateButton("Delete Frame", (_, __) => DeleteFrame()));
        left.Controls.Add(frameEditPanel, 0, 7);

        var undoPanel = new FlowLayoutPanel { Dock = DockStyle.Fill, Height = 36 };
        undoPanel.Controls.Add(CreateButton("Undo", (_, __) => Undo()));
        undoPanel.Controls.Add(CreateButton("Redo", (_, __) => Redo()));
        left.Controls.Add(undoPanel, 0, 8);

        var right = new TableLayoutPanel { Dock = DockStyle.Fill, RowCount = 3, Padding = new Padding(8) };
        right.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        right.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        right.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.Controls.Add(right, 1, 0);

        _statusLabel.Text = "Open WPORT*.EGA or *.PIC to begin.";
        _statusLabel.Dock = DockStyle.Fill;
        _statusLabel.Height = 24;
        right.Controls.Add(_statusLabel, 0, 0);

        _canvas.Dock = DockStyle.Fill;
        _canvas.SizeMode = PictureBoxSizeMode.Normal;
        _canvas.MouseDown += CanvasOnMouseDown;
        _canvas.MouseMove += CanvasOnMouseMove;
        _canvas.MouseUp += (_, __) => _dragging = false;
        right.Controls.Add(_canvas, 0, 1);

        _palettePanel.Dock = DockStyle.Fill;
        _palettePanel.WrapContents = true;
        _palettePanel.Height = 80;
        right.Controls.Add(_palettePanel, 0, 2);

        KeyPreview = true;
        KeyDown += MainFormOnKeyDown;
    }

    private Button CreateButton(string text, EventHandler onClick)
    {
        var b = new Button
        {
            Text = text,
            Width = 120,
            Height = 30,
            Margin = new Padding(0, 0, 8, 8),
        };
        b.Click += onClick;
        return b;
    }

    private void MainFormOnKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Control && e.KeyCode == Keys.O)
        {
            OpenFile();
            e.SuppressKeyPress = true;
        }
        else if (e.Control && e.KeyCode == Keys.S && !e.Shift)
        {
            SaveFile(false);
            e.SuppressKeyPress = true;
        }
        else if (e.Control && e.Shift && e.KeyCode == Keys.S)
        {
            SaveFile(true);
            e.SuppressKeyPress = true;
        }
        else if (e.Control && e.KeyCode == Keys.Z)
        {
            Undo();
            e.SuppressKeyPress = true;
        }
        else if (e.Control && e.KeyCode == Keys.Y)
        {
            Redo();
            e.SuppressKeyPress = true;
        }
        else if (e.KeyCode == Keys.Left)
        {
            StepFrame(-1);
        }
        else if (e.KeyCode == Keys.Right)
        {
            StepFrame(1);
        }
        else if (e.Control && e.KeyCode == Keys.C)
        {
            CopyFrame();
            e.SuppressKeyPress = true;
        }
        else if (e.Control && e.KeyCode == Keys.V)
        {
            PasteFrame();
            e.SuppressKeyPress = true;
        }
    }

    private void OpenFile()
    {
        using var dialog = new OpenFileDialog
        {
            Filter = "Wizardry art (*.ega;*.pic)|*.ega;*.pic|All files (*.*)|*.*",
            Title = "Open WPORT or PIC",
        };
        if (dialog.ShowDialog(this) != DialogResult.OK)
        {
            return;
        }

        try
        {
            _document = ImageFormats.Load(dialog.FileName);
            _currentFrameIndex = 0;
            _undoStacks.Clear();
            _redoStacks.Clear();
            foreach (var _ in _document.Frames)
            {
                _undoStacks.Add(new Stack<byte[]>());
                _redoStacks.Add(new Stack<byte[]>());
            }

            ReloadFrameList();
            BuildPalette();
            Redraw();
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "Open failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void SaveFile(bool saveAs)
    {
        if (_document == null)
        {
            return;
        }

        var targetPath = _document.SourcePath ?? string.Empty;
        if (saveAs || string.IsNullOrWhiteSpace(targetPath))
        {
            using var dialog = new SaveFileDialog
            {
                Filter = "Wizardry art (*.ega;*.pic)|*.ega;*.pic|All files (*.*)|*.*",
                FileName = Path.GetFileName(targetPath),
            };
            if (dialog.ShowDialog(this) != DialogResult.OK)
            {
                return;
            }

            targetPath = dialog.FileName;
        }

        try
        {
            if (_document.Kind == "wport")
            {
                ImageFormats.SaveWport(targetPath, _document);
                _statusLabel.Text = $"Saved WPORT: {targetPath}";
            }
            else
            {
                ImageFormats.SavePicEditProject(targetPath, _document);
                _statusLabel.Text = $"Saved PIC edit sidecar: {targetPath}.picedit.json";
                MessageBox.Show(
                    this,
                    "PIC binary re-encoding is not implemented yet.\nSaved editable frame data to .picedit.json.",
                    "PIC save",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information);
            }

            _document.SourcePath = targetPath;
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "Save failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void ReloadFrameList()
    {
        _frameList.Items.Clear();
        if (_document == null)
        {
            return;
        }

        for (var i = 0; i < _document.Frames.Count; i++)
        {
            var frame = _document.Frames[i];
            _frameList.Items.Add($"Frame {i} ({frame.Width}x{frame.Height})");
        }

        if (_frameList.Items.Count > 0)
        {
            _frameList.SelectedIndex = _currentFrameIndex;
        }
    }

    private void BuildPalette()
    {
        _palettePanel.Controls.Clear();
        if (_document == null)
        {
            return;
        }

        for (var i = 0; i < 16; i++)
        {
            var index = i;
            var button = new Button
            {
                Width = 36,
                Height = 36,
                BackColor = _document.Palette[i],
                Margin = new Padding(2),
                FlatStyle = FlatStyle.Flat,
            };
            button.FlatAppearance.BorderColor = i == _selectedColorIndex ? Color.White : Color.Black;
            button.FlatAppearance.BorderSize = i == _selectedColorIndex ? 3 : 1;
            button.Click += (_, __) =>
            {
                _selectedColorIndex = index;
                BuildPalette();
            };
            _palettePanel.Controls.Add(button);
        }
    }

    private bool CanModifyFrameCount() => _document != null && _document.Kind == "pic";

    private void CopyFrame()
    {
        var frame = CurrentFrame();
        if (frame == null)
        {
            return;
        }

        _copiedFrame = FrameEditingService.Copy(frame);
        _statusLabel.Text = $"Copied frame {_currentFrameIndex}.";
    }

    private void PasteFrame()
    {
        var frame = CurrentFrame();
        if (frame == null || _copiedFrame == null)
        {
            return;
        }

        if (!FrameEditingService.Paste(frame, _copiedFrame))
        {
            MessageBox.Show(this, "Copied frame dimensions do not match current frame.", "Paste failed", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        PushUndo();
        Redraw();
    }

    private void DuplicateFrame()
    {
        var frame = CurrentFrame();
        if (frame == null || _document == null || !CanModifyFrameCount())
        {
            return;
        }

        var insertIndex = FrameEditingService.Duplicate(_document.Frames, _currentFrameIndex);
        _undoStacks.Insert(insertIndex, new Stack<byte[]>());
        _redoStacks.Insert(insertIndex, new Stack<byte[]>());
        _currentFrameIndex = insertIndex;
        ReloadFrameList();
        Redraw();
    }

    private void InsertBlankFrameAfter()
    {
        var frame = CurrentFrame();
        if (frame == null || _document == null || !CanModifyFrameCount())
        {
            return;
        }

        var insertIndex = FrameEditingService.InsertBlankAfter(_document.Frames, _currentFrameIndex);
        _undoStacks.Insert(insertIndex, new Stack<byte[]>());
        _redoStacks.Insert(insertIndex, new Stack<byte[]>());
        _currentFrameIndex = insertIndex;
        ReloadFrameList();
        Redraw();
    }

    private void DeleteFrame()
    {
        if (_document == null || !CanModifyFrameCount())
        {
            return;
        }

        if (_document.Frames.Count <= 1)
        {
            MessageBox.Show(this, "PIC document must contain at least one frame.", "Delete blocked", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }

        var removedIndex = _currentFrameIndex;
        _currentFrameIndex = FrameEditingService.DeleteAt(_document.Frames, removedIndex);
        _undoStacks.RemoveAt(removedIndex);
        _redoStacks.RemoveAt(removedIndex);
        ReloadFrameList();
        Redraw();
    }

    private void CanvasOnMouseDown(object? sender, MouseEventArgs e)
    {
        if (_document == null)
        {
            return;
        }

        _dragging = true;
        PushUndo();
        PaintAt(e.X, e.Y);
    }

    private void CanvasOnMouseMove(object? sender, MouseEventArgs e)
    {
        if (_dragging)
        {
            PaintAt(e.X, e.Y);
        }
    }

    private void PaintAt(int x, int y)
    {
        var frame = CurrentFrame();
        if (frame == null)
        {
            return;
        }

        var px = x / _zoom;
        var py = y / _zoom;
        if (px < 0 || py < 0 || px >= frame.Width || py >= frame.Height)
        {
            return;
        }

        frame.Pixels[(py * frame.Width) + px] = (byte)_selectedColorIndex;
        Redraw();
    }

    private void PushUndo()
    {
        var frame = CurrentFrame();
        if (frame == null)
        {
            return;
        }

        _undoStacks[_currentFrameIndex].Push(ClonePixels(frame.Pixels));
        _redoStacks[_currentFrameIndex].Clear();
    }

    private void Undo()
    {
        var frame = CurrentFrame();
        if (frame == null || _undoStacks[_currentFrameIndex].Count == 0)
        {
            return;
        }

        _redoStacks[_currentFrameIndex].Push(ClonePixels(frame.Pixels));
        frame.Pixels = _undoStacks[_currentFrameIndex].Pop();
        Redraw();
    }

    private void Redo()
    {
        var frame = CurrentFrame();
        if (frame == null || _redoStacks[_currentFrameIndex].Count == 0)
        {
            return;
        }

        _undoStacks[_currentFrameIndex].Push(ClonePixels(frame.Pixels));
        frame.Pixels = _redoStacks[_currentFrameIndex].Pop();
        Redraw();
    }

    private static byte[] ClonePixels(byte[] pixels)
    {
        var copy = new byte[pixels.Length];
        Buffer.BlockCopy(pixels, 0, copy, 0, pixels.Length);
        return copy;
    }

    private void StepFrame(int delta)
    {
        if (_document == null)
        {
            return;
        }

        var next = _currentFrameIndex + delta;
        if (next < 0 || next >= _document.Frames.Count)
        {
            return;
        }

        _currentFrameIndex = next;
        _frameList.SelectedIndex = next;
        Redraw();
    }

    private IndexedFrame? CurrentFrame()
    {
        if (_document == null || _currentFrameIndex < 0 || _currentFrameIndex >= _document.Frames.Count)
        {
            return null;
        }

        return _document.Frames[_currentFrameIndex];
    }

    private void Redraw()
    {
        var frame = CurrentFrame();
        if (_document == null || frame == null)
        {
            return;
        }

        var bmp = new Bitmap(frame.Width * _zoom, frame.Height * _zoom);
        using (var g = Graphics.FromImage(bmp))
        {
            g.InterpolationMode = InterpolationMode.NearestNeighbor;
            g.PixelOffsetMode = PixelOffsetMode.Half;
            g.Clear(Color.Black);
            for (var y = 0; y < frame.Height; y++)
            {
                for (var x = 0; x < frame.Width; x++)
                {
                    var colorIndex = frame.Pixels[(y * frame.Width) + x] & 0x0F;
                    using var brush = new SolidBrush(_document.Palette[colorIndex]);
                    g.FillRectangle(brush, x * _zoom, y * _zoom, _zoom, _zoom);
                }
            }

            if (_zoom >= 8)
            {
                using var pen = new Pen(Color.FromArgb(50, 50, 50));
                for (var x = 0; x <= frame.Width; x++)
                {
                    g.DrawLine(pen, x * _zoom, 0, x * _zoom, frame.Height * _zoom);
                }

                for (var y = 0; y <= frame.Height; y++)
                {
                    g.DrawLine(pen, 0, y * _zoom, frame.Width * _zoom, y * _zoom);
                }
            }
        }

        _canvas.Image?.Dispose();
        _canvas.Image = bmp;
        _canvas.Width = bmp.Width;
        _canvas.Height = bmp.Height;
        _statusLabel.Text = $"{Path.GetFileName(_document.SourcePath)} | {_document.Kind.ToUpperInvariant()} | Frame {_currentFrameIndex + 1}/{_document.Frames.Count} | Zoom {_zoom}x";
    }

    private void ApplyStyle()
    {
        BackColor = Color.FromArgb(245, 247, 250);
        ForeColor = Color.FromArgb(33, 37, 41);
    }
}
