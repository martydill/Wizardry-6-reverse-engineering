# Repository Guidelines

## App Overview
This app is a Windows Forms pixel editor for `Wizardry 6` image assets. It opens `WPORT*.EGA` portrait sheets and `.PIC` sprite/scene files, lets you edit indexed-color frames with the built-in EGA palette, and supports frame-level operations such as copy, paste, duplicate, insert, delete, and save back to the game formats.

## Project Structure & Module Organization
`PicEditor.sln` contains two projects. `PicEditor/` is the Windows Forms application targeting `.NET Framework 4.8`; key files include `Program.cs`, `MainForm.cs`, `ImageFormats.cs`, and `FrameEditingService.cs`. `PicEditor.Tests/` contains NUnit coverage for format handling and frame-editing behavior. Ignore `bin/` and `obj/` outputs. Place new documentation in `docs/` and any ad hoc test scripts or one-off helpers in `scratch/`.

## Build, Test, and Development Commands
Run `dotnet build PicEditor.sln` to compile the app and tests. Run `dotnet test PicEditor.sln` to execute the NUnit suite. For a faster verification pass when packages are already restored, use `dotnet test PicEditor.sln --no-restore`. Open the solution in Visual Studio for interactive WinForms work and debugger-driven UI checks.

## Coding Style & Naming Conventions
Use 4-space indentation and standard C# brace style. Nullable reference types are enabled, so prefer explicit null handling over suppression. Keep type and member names in `PascalCase`, locals and parameters in `camelCase`, and test methods in descriptive `Behavior_Result` style such as `Paste_ReturnsFalse_WhenDimensionsDiffer`. Favor small, focused methods in services and keep UI event logic in `MainForm.cs`.

## Testing Guidelines
Tests use NUnit with `[TestFixture]` and `[Test]`. Add coverage in `PicEditor.Tests/` next to the closest existing test file, or create a new `*Tests.cs` file when introducing a new area. Cover both success paths and invalid file or dimension cases, especially around image parsing and save/load round trips. Run `dotnet test PicEditor.sln` before opening a PR.

## Commit & Pull Request Guidelines
Recent commits use short, imperative subjects with leading capitals, for example `Improve drawing performance` and `Fix typo in path`. Keep commit messages concise and scoped to one change. Pull requests should include a brief summary, note any affected file formats or editor behaviors, link the related issue when applicable, and attach screenshots for UI-visible changes.

## Configuration Notes
This project targets `net48` and `UseWindowsForms=true`; keep new dependencies compatible with that runtime. Avoid committing temporary assets, generated binaries, or local experiment files outside `scratch/`.
