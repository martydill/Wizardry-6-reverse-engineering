# PIC/WPORT Pixel Editor

Path: `apps/pic_editor/PicEditor.sln`

Standalone WinForms pixel-art editor for Wizardry 6 portrait and monster art files.

## Supported inputs

- `WPORT0.EGA`, `WPORT1.EGA` (portrait sets, 14 frames each)
- Monster `*.PIC` files (animation frame decoding via `bane.data.pic_decoder`)

## Features

- Frame list/navigation
- Monster animation frame editing tools (copy/paste, duplicate, insert blank, delete)
- Pixel painting with palette indices (16-color palette)
- Zoom controls
- Undo / redo
- Keyboard shortcuts:
  - `Ctrl+O` open
  - `Ctrl+S` save
  - `Ctrl+Shift+S` save as
  - `Ctrl+Z` undo
  - `Ctrl+Y` redo
  - Left/Right arrows for frame stepping
  - `Ctrl+C` copy frame
  - `Ctrl+V` paste frame

## Save behavior

- **WPORT**: saves back to binary WPORT format (tile-planar 24×24 frames, padded to 4096 bytes).
- **PIC**: re-encoding to original `.PIC` compression is not implemented yet; save writes a sidecar editable project:
  - `<file>.picedit.json`

This keeps monster-frame edits persistent in an explicit editor format while preserving safe workflow.

## Run

Open in Visual Studio and run:

```powershell
msbuild apps\pic_editor\PicEditor.sln /p:Configuration=Release
```
