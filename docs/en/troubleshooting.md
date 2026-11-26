[← Documentation home](README.md) · **English** · [Português (Brasil)](../pt-BR/troubleshooting.md) · [Español](../es/troubleshooting.md)

# 🩺 Troubleshooting

## The mod does not load

| Symptom | Cause and fix |
|---|---|
| ForgedInAshes is missing from the *Mods* list | The folder is in the wrong place. It must be `<game>/Mods/ForgedInAshes/ModInfo.xml` (not nested twice). |
| The game says the mod's DLL was blocked | EasyAntiCheat is on. Start the game **without EAC**. |
| Everything is duplicated, errors about patches already applied | An old copy is still installed. Keep only `Mods/ForgedInAshes`; delete `Mods/FerroEngrenagem` if present. |
| Red errors about `0Harmony` | `Mods/0_TFP_Harmony` was deleted. Verify the game files in Steam to restore it. |

## Machines

| Symptom | Cause and fix |
|---|---|
| Machine says it needs torque | Its **motor socket** is empty. Put an Electric Motor against it, or bring a shaft from a torque network. |
| Network shows **OVERLOADED** and stops after 20 s | The machines cost more UT than the sources offer. Add sources, lower the RPM, or split the network with a **Clutch** or **Torque Regulator**. |
| Network shows **LOCKED** | Sources turn against each other, or at different speeds. Turn one around, add a **Spin Inverter**, or match speeds with a **Speed Box**. |
| Wrong spin on a machine | Turn the motor around or add a **Spin Inverter**. |
| Engine says *No water* / *No Lubricant* | Pipe water into the engine and put Lubricant in its slots. |

## Fluids

| Symptom | Cause and fix |
|---|---|
| Pipe shows **BLOCKED** | Two different fluids met in one network. Separate them, or use a **Fluid Separator**. |
| Pipe **leaks** | Pressure above its limit: 4 bar for **Pipe**, 12 bar for **High Pressure Pipe**. Use HP pipes or a **Relief Valve**. |
| Boiler drum says *No lit Boiler Firebox touching this drum* | Put a lit firebox against the drum, ideally **under** it. The firebox only burns while a drum asks for heat, so it needs fuel. |
| Sap Tapper says its back must touch a trunk | Rotate it so its **back** faces the trunk; latex comes out of the front. |

## Belts

| Symptom | Cause and fix |
|---|---|
| Items stop at a machine (*not taken, it waits*) | The machine's input is full, or it does not use that item in the current recipe. |
| Belt does not move | No torque: put a shaft beside any belt of the line (8 UT per belt). |
| Funnel does nothing | It waits while the crate is open or the belt in front is full. |

## The look text disappears

The readout shown when you look at a block appears only within **4 m** (**5 m** for big machines). Step closer.
If it is gone even right next to a machine, please [report it](#reporting-a-bug) with your log: the mod writes
detailed diagnostics about this case (lines starting with `ui watchdog` and `look probe`).

## Logs

| File | Where |
|---|---|
| Game log (Windows) | `%APPDATA%\7DaysToDie\logs\output_log_client__<date>.txt` |
| Mod lines | Every line written by the mod starts with **`[ForgedInAshes]`** |

For a much more detailed log, create an empty file named **`debug.txt`** inside `Mods/ForgedInAshes/` and restart
the game. Delete it afterwards: verbose logging is large.

## Reporting a bug

Open an issue at **[github.com/BirdRa1n/ForgedInAshes/issues](https://github.com/BirdRa1n/ForgedInAshes/issues)**
with:

1. What you did, what you expected and what happened.
2. Game version and mod version (see `Mods/ForgedInAshes/ModInfo.xml`).
3. The **full** `output_log_client__*.txt` of the session where it happened.
4. A screenshot, if it is visual.

---

[← Gameplay guide](gameplay.md) · Next: **[Development →](development.md)**
