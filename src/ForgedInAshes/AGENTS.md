# AGENTS.md — `src/ForgedInAshes` (mod DLL)

Read the [root AGENTS.md](../../AGENTS.md) first.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File tools\build.ps1                       # -> Mods\ForgedInAshes\ForgedInAshes.dll
powershell -ExecutionPolicy Bypass -File tools\build.ps1 -Out $env:TEMP\fia.dll # when the game is running (DLL locked)
```

`build.ps1` compiles every `*.cs` here with the .NET Framework 4 `csc.exe` against the game's managed assemblies
and `Mods/0_TFP_Harmony/0Harmony.dll`. Adding a reference to another game assembly means editing `$refs` in
`build.ps1` (for example `NGUI.dll` for `UILabel`).

## Language level: C# 5

Not allowed: string interpolation `$"..."`, null-conditional `?.` / `??=`, expression-bodied members `=>`,
`nameof`, tuples, `out var`, pattern matching, local functions, auto-property initializers. Write
`string.Format`, explicit null checks and full method bodies.

## Conventions

- Namespace `ForgedInAshes`. Entry point: `ModApi.cs` (`ForgedInAshesMod : IModApi`); Harmony patches are found by
  `PatchAll`, so a new `[HarmonyPatch]` class is picked up automatically.
- Log with `Log.Out(ForgedInAshesMod.LogPrefix + ...)`; put chatty diagnostics behind `ForgedInAshesMod.Verbose`
  and rate-limit anything that can fire every frame.
- XML block classes: `<property name="Class" value="ForgedInAshes.FeName, ForgedInAshes"/>` creates
  `ForgedInAshes.BlockFeName` (the game inserts `Block`). Mark them `[UnityEngine.Scripting.Preserve]`.
- Per-world persistence: `ForgedInAshesMod.SaveFile("name")` → `<save>/ForgedInAshes_name.txt` (migrates the old
  `FerroEngrenagem_name.txt`).
- Block names are compared by prefix `fe` (`GetBlockName().StartsWith("fe", StringComparison.Ordinal)`).
- Every non-obvious workaround cites the game method it relies on, with the build: `IL 3.4.0 b10`.

## Where things live

| Topic | Files |
|---|---|
| Torque networks, look text of torque blocks | `TorqueNetwork.cs`, `TorqueEngine.cs`, `KineticSpinner.cs` |
| Cranks | `Crank.cs`, `CrankNet.cs`, `CrankSlots.cs`, `TorqueCrank.cs` |
| Fluids, valves, steam | `FluidNetwork.cs`, `FluidControl.cs`, `SteamEngine.cs`, `SteamPlant.cs`, `SteamVent.cs` |
| Electricity | `Dynamo.cs`, `PowerPatches.cs`, `PowerGatePatches.cs`, `FuelGenerator.cs`, `WireMultiblock.cs` |
| Belts and items | `Belt.cs`, `Logistics.cs`, `ItemTransport.cs`, `Inline.cs`, `MachineItems.cs`, `ConveyorStand.cs` |
| Processing machines | `Processes.cs` (reads `Data/fe_processes.xml`), `ProcessMachine.cs`, `MetalWorks.cs`, `Industrial.cs` |
| Recipes and crafting | `AutoCraft.cs`, `RecipeBook.cs`, `Pickup.cs`, `Settings.cs` |
| World machines, signals, displays | `WorldMachines.cs`, `Signals.cs`, `Display.cs` |
| UI windows | `FeUi.cs` (XUi controllers declared in `Config/XUi_InGame/windows.xml`) |
| Look-text diagnostics | `UiWatchdog.cs`, `LookTextProbe.cs` |
| Visual effects | `FxVisual.cs`, `MachineVisual.cs`, `CasterVisual.cs`, `CondenserVisual.cs`, `MotorSocketMarker.cs` |

## Testing

Close the game, run `fe.bat mod`, start the game without EAC and read the log (`[ForgedInAshes]` lines). Never
claim a fix works in game without a log or screenshot from a real run.
