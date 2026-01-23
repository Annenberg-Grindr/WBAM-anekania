# CLAUDE.md - AI Assistant Guide for The Millionaire Game

This document provides essential information for AI assistants working with this codebase.

## Project Overview

**The Millionaire Game** is a Windows desktop application based on the TV show "Who Wants to Be a Millionaire". It simulates and controls quiz games with features for hosting, contestant gameplay, TV/audience displays, and Fastest Finger First (FFF) challenges.

- **Version:** 1.2.0 (Build 976)
- **Primary Language:** VB.NET
- **Secondary Language:** C# (Question Editor)
- **Framework:** .NET Framework 4.8 (main), 4.7.2 (utilities)
- **GUI Framework:** Windows Forms (WinForms)
- **Database:** Microsoft SQL Server (LocalDB or Remote)

## Quick Commands

```bash
# Build the solution (requires Visual Studio or MSBuild)
msbuild "Het DJG Toernooi.sln" /p:Configuration=Release

# Build debug configuration
msbuild "Het DJG Toernooi.sln" /p:Configuration=Debug
```

## Project Structure

```
WBAM-anekania/
├── Het DJG Toernooi.sln          # Visual Studio solution file
├── Het DJG Toernooi/             # Main application (VB.NET)
│   ├── Source_Scripts/           # Core game logic
│   │   ├── Classes/
│   │   │   ├── Game/             # Game state and modes
│   │   │   │   ├── GameModes/    # modeNormal, modeRisk, modeFree
│   │   │   │   └── FastestFinger/# FFF server/client classes
│   │   │   ├── Question.vb       # Question handling
│   │   │   ├── User.vb           # User state management
│   │   │   ├── Sounds.vb         # Sound management
│   │   │   └── Hotkey.vb         # Hotkey definitions
│   │   ├── DatabaseAndSettings/  # Configuration and database
│   │   │   ├── QDatabase.vb      # SQL queries for questions
│   │   │   ├── Data.vb           # Database connections
│   │   │   ├── SQLInfo.vb        # SQL connection settings
│   │   │   └── ApplicationSettings.vb # Game settings
│   │   ├── Lifelines/            # Lifeline implementations
│   │   │   ├── LifelineManager.vb
│   │   │   ├── Lifeline5050.vb   # 50:50 lifeline
│   │   │   ├── LifelinePO.vb     # Plus One/Phone-A-Friend
│   │   │   ├── LifelineATA.vb    # Ask the Audience
│   │   │   ├── LifelineSwitch.vb # Switch the Question
│   │   │   ├── LifeLineDouble.vb # Double Dip
│   │   │   └── LifelineHost.vb   # Ask the Host
│   │   └── Sound Engine/
│   │       └── SOUND.vb          # WinMM.dll audio wrapper
│   ├── Windows/                  # Windows Forms UI
│   │   ├── ControlPanel.vb       # Main operator interface
│   │   ├── General/
│   │   │   ├── HostScreen.vb     # Host display
│   │   │   ├── GuestScreen.vb    # Contestant display
│   │   │   └── TVControlPnl*.vb  # TV displays (720p, 1080p)
│   │   ├── Options/              # Settings dialogs
│   │   └── Fastest Finger First/ # FFF server UI
│   ├── Resources/                # Images, sounds, icons
│   └── App.config
├── FFF_Guest/                    # FFF Client application (VB.NET)
│   ├── frmMain.vb                # Main contestant interface
│   └── App.config
├── MillionaireGameQEditor/       # Question Editor (C#)
│   ├── QuestionManager.cs        # Main editor form
│   ├── Windows/
│   │   ├── AddQuestion.cs
│   │   ├── EditQuestion.cs
│   │   ├── ImportQuestion.cs     # CSV import
│   │   └── ExportQuestionsCSV.cs # CSV export
│   └── SQLInfo.cs
└── Guides/                       # User documentation
    └── Exporting and Importing CSV Files.md
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `Het DJG Toernooi/Windows/ControlPanel.vb` | Main operator control interface |
| `Het DJG Toernooi/Source_Scripts/DatabaseAndSettings/QDatabase.vb` | Database queries for questions |
| `Het DJG Toernooi/Source_Scripts/Classes/Game/Game.vb` | Game state and level management |
| `Het DJG Toernooi/Source_Scripts/Lifelines/LifelineManager.vb` | Manages all lifeline types |
| `Het DJG Toernooi/Source_Scripts/Sound Engine/SOUND.vb` | Audio playback system |
| `MillionaireGameQEditor/QuestionManager.cs` | Question editor main form |

## Architecture

### Game Modes
- **Normal Mode** (`modeNormal.vb`) - Traditional Millionaire rules
- **Risk Mode** (`modeRisk.vb`) - 2nd safety net disabled, extra lifelines
- **Free Safety Net Mode** (`modeFree.vb`) - 2nd safety net placeable after Q5

### Lifelines (0-4 configurable)
- 50:50, Plus One, Ask the Audience, Switch Question, Double Dip, Ask the Host

### Display Components
- **Control Panel** - Operator interface
- **Host Screen** - Display for quizmaster
- **Contestant Screen** - Display for player
- **TV Screen** - Broadcast display (720p/1080p variants)

### Fastest Finger First (FFF)
- Server/client architecture over TCP (default port 3818)
- Supports 2-8 networked players
- Requires Windows Firewall configuration

## Database Schema

**Question Table:**
- ID, Question, Answer A/B/C/D, Correct Answer (A-D)
- Difficulty (1=Specific level, 2=Range)
- Level (1-15), Level Range (1-4)
- Notes (optional), Used flag

**FFF Questions:** Separate table `fff_questions` with same structure

## Technology Stack

- **VB.NET** - Main application and FFF_Guest
- **C#** - Question Editor (QEDIT.exe)
- **Windows Forms** - All UI components
- **SQL Server** - LocalDB or remote SQL Server 2019+
- **WinMM.dll** - Audio playback via MCI commands
- **XML Serialization** - Configuration persistence

**No external NuGet packages** - uses only .NET Framework built-in libraries.

## Code Conventions

### VB.NET Settings
- `OptionStrict: Off` (type flexibility allowed)
- `OptionExplicit: On`
- `OptionInfer: On`

### Naming Patterns
- Forms: `frmXxx` or `XxxScreen`
- Manager classes: `XxxManager`
- Configuration: `AppSettings`, `SQLInfo`

### File Organization
- Windows Forms: `Form.vb` + `Form.Designer.vb` (designer-generated)
- Resources embedded via `Resources.Designer.vb`

### Global State
Uses `Shared` classes for global state:
- `Game` - Current game state
- `LifelineManager` - Active lifelines
- `Sounds` - Sound cue system

## Common Tasks

### Adding a New Lifeline
1. Create new class in `Source_Scripts/Lifelines/`
2. Inherit from base lifeline pattern
3. Register in `LifelineManager.vb`
4. Add UI elements to `ControlPanel.vb`

### Adding a New Question
Use the Question Editor (`QEDIT.exe`) or:
1. Import via CSV (see `Guides/Exporting and Importing CSV Files.md`)
2. Format: `Question,A,B,C,D,CorrectLetter,Level,LevelRange,Notes`

### Modifying Game Logic
- Game state: `Source_Scripts/Classes/Game/Game.vb`
- Question handling: `Source_Scripts/Classes/Question.vb`
- Database queries: `Source_Scripts/DatabaseAndSettings/QDatabase.vb`

### Adding New Sounds
1. Add sound file to Resources
2. Register in `SOUND.vb`
3. Add trigger in appropriate game logic

## Build Configuration

### Debug
- Full debug symbols enabled
- Output: `bin\Debug\`
- Documentation: `MillionaireGame.xml`

### Release
- PDB-only debug info
- Optimization enabled
- Output: `bin\Release\`

## Output Executables

- `MillionaireGame.exe` - Main application
- `FFF_Guest.exe` - Fastest Finger First client
- `QEDIT.exe` - Question Editor tool

## Requirements

### Runtime
- Windows 7 or later
- .NET Framework 4.8
- SQL Server Express LocalDB or SQL Server 2019+
- Visual C++ Redistributable (for LocalDB)

### Development
- Visual Studio 2015+ (VS2019 recommended)
- .NET Framework 4.8 SDK

## Important Notes for AI Assistants

1. **Read before modifying** - Always read existing code before suggesting changes
2. **Windows Forms Designer** - Do not manually edit `*.Designer.vb` files; use the designer pattern
3. **SQL Queries** - Current implementation uses direct SQL; be aware of SQL injection risks when adding new queries
4. **Threading** - Audio and network operations use threading; consider thread safety
5. **Resource files** - `Resources.Designer.vb` is auto-generated; add resources through the Resources editor
6. **Configuration** - Settings stored via XML serialization in `sql.xml` at runtime
7. **Sound system** - Uses WinMM.dll P/Invoke; check `SOUND.vb` for audio patterns
8. **Multiple projects** - Solution contains 4 projects; ensure changes are made in the correct project

## Git Workflow

- **Main branch:** `master` (stable releases)
- **Development:** Feature branches merged via PRs
- Commit messages should describe the change clearly
- Test changes before creating PRs

## Troubleshooting

See `Troubleshooting.md` for common issues:
- SQL connection errors
- Visual C++ redistributable requirements
- Server VSS service errors

## Additional Documentation

- `README.md` - Project introduction and setup
- `Troubleshooting.md` - Common issues and solutions
- `Guides/Exporting and Importing CSV Files.md` - CSV format guide
