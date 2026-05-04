# Repository Guidelines

## App Overview
This app is a Windows Forms editor for `Wizardry 6` party roster data. It opens `PCFILE.DBS` character roster files, lets you inspect and edit per-character stats and metadata, and can optionally load `SCENARIO.DBS` so the UI can resolve scenario-specific names and portrait information instead of showing only raw values.

## Project Structure & Module Organization
`CharacterRosterEditor/` contains the WinForms application code targeting `.NET Framework 4.8`. Core domain and file-format logic lives beside the UI in files such as `CharacterRecord.cs`, `PcfileDocument.cs`, and `ScenarioDatabase.cs`. `CharacterRosterEditor.Tests/` contains NUnit coverage for parsing, persistence, and record behavior. Keep new documentation in `docs/` and any temporary or ad hoc test scripts in `scratch/`.

## Build, Test, and Development Commands
Use these commands from the repository root:

- `dotnet build CharacterRosterEditor.sln` builds the app and test project.
- `dotnet test CharacterRosterEditor.sln --no-restore` runs the NUnit suite.
- `dotnet run --project CharacterRosterEditor\CharacterRosterEditor.csproj` launches the editor locally.

Prefer solution-level commands unless you are isolating work in a single project.

## Coding Style & Naming Conventions
Follow the existing C# style in this repo: 4-space indentation, file-scoped namespaces, nullable reference types enabled, and PascalCase for types, methods, and public members. Use `_camelCase` for private readonly fields, especially WinForms controls. Keep methods focused and place UI wiring in clearly named helpers such as `BuildUi()` or `ApplyStyle()`.

## Testing Guidelines
Tests use NUnit with `Microsoft.NET.Test.Sdk`. Add new tests to `CharacterRosterEditor.Tests/` and name files after the class or feature under test, for example `ScenarioDatabaseTests.cs`. Prefer descriptive test names in the `Method_ExpectedBehavior_WhenCondition` style already used here, such as `FromBytes_Throws_WhenRecordIsTooSmall`. Run the full suite before submitting changes.

## Commit & Pull Request Guidelines
Recent history favors short, imperative commit subjects such as `Fix incorrect race names` or `Improve drawing performance`. Keep commits narrowly scoped and explain behavior changes, not implementation trivia. Pull requests should include a concise summary, note any file-format or UI impact, link related issues, and attach screenshots when the WinForms interface changes.

## Configuration & Safety Notes
This editor works with game data files such as `PCFILE.DBS` and `SCENARIO.DBS`. Avoid checking proprietary sample data into the repo. When reproducing bugs, describe the file source and scenario in the PR instead of committing user data.
