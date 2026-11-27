[← Documentation home](README.md) · **English** · [Português (Brasil)](../pt-BR/installation.md) · [Español](../es/installation.md)

# 📥 Installation

## Requirements

| Requirement | Details |
|---|---|
| Game | **7 Days to Die V3.4** (developed and tested on build **b10**) |
| Anti-cheat | **EasyAntiCheat must be off.** The mod includes a DLL, which EAC blocks. Use *Play without EAC* in the launcher, or start `7DaysToDie.exe` directly. |
| Harmony | Nothing to install: the game already ships it as `Mods/0_TFP_Harmony`. Keep that folder. |
| Mode | **Single player.** Multiplayer has not been tested yet. |

> [!WARNING]
> Never use mods with a DLL on official or EAC-protected servers. ForgedInAshes is meant for your own worlds.

## Install

1. Download the latest release (or the repository as a ZIP) from
   **[github.com/BirdRa1n/ForgedInAshes](https://github.com/BirdRa1n/ForgedInAshes)**.
2. Open your game folder. On Steam: *Library → 7 Days to Die → right click → Manage → Browse local files*.
3. Copy the folder **`Mods/ForgedInAshes`** from the download into the game's **`Mods`** folder. The result must be:

   ```text
   7 Days To Die/
   └─ Mods/
      ├─ 0_TFP_Harmony/        (comes with the game)
      └─ ForgedInAshes/
         ├─ ModInfo.xml
         ├─ ForgedInAshes.dll
         ├─ Config/
         ├─ Data/
         ├─ Resources/
         └─ UIAtlases/
   ```

   **The 3D models and textures come in a separate download:** in the same release, under *Assets*, download
   **`forgedinashes.unity3d`** and put it in `Mods/ForgedInAshes/Resources/` (the repository does not carry it).
   Without it the mod loads, but the machines have no models.

4. Start the game **without EAC**. On the main menu, open *Mods*: **ForgedInAshes** must be listed.

> [!TIP]
> Building from source? `fe.bat mod` validates, compiles and links the repository straight into the game folder.
> See [Development](development.md).

## Starting a world

- **New worlds** are recommended: the mod changes how most items are crafted, and the progression is designed
  around it.
- **Existing worlds** load fine — the new blocks and items simply become available.
- The mod keeps per-world state (belt contents, fluids, signals, fixed recipes) in small files inside the save
  folder: `ForgedInAshes_belts.txt`, `ForgedInAshes_fluids.txt`, `ForgedInAshes_logic.txt` and
  `ForgedInAshes_autocraft.txt`.

## Settings

`Mods/ForgedInAshes/Data/fe_settings.xml` holds the options. The main one:

| Setting | Values | Effect |
|---|---|---|
| `VanillaShortcuts` | `remove` (default) / `expensive` | `remove` takes away the one-click vanilla recipes that the production chains replace. `expensive` brings them back at **3×** their cost, as an emergency option. |

## Updating

1. Close the game.
2. Replace the `Mods/ForgedInAshes` folder with the new one (delete the old folder first, do not merge).
3. Start the game. Your worlds keep working.

### Coming from *Ferro & Engrenagem*

ForgedInAshes was previously called **Ferro & Engrenagem**. Block and item IDs did not change, so your worlds are
compatible:

1. Delete the old `Mods/FerroEngrenagem` folder — **keeping both would load the mod twice**.
2. Install `Mods/ForgedInAshes` as above.
3. On the first load, the mod renames the old state files of each world (`FerroEngrenagem_*.txt` →
   `ForgedInAshes_*.txt`) automatically. Belts, fluids and signals keep their contents.

## Uninstalling

> [!CAUTION]
> Removing the mod from a world that contains its blocks breaks those blocks and can corrupt the save. Only
> uninstall for worlds where you never placed a ForgedInAshes block, or start a new world.

1. Close the game.
2. Delete `Mods/ForgedInAshes`.

## Multiplayer status

| Scenario | Status |
|---|---|
| Single player | ✅ Supported |
| Peer-to-peer (host + friends) | ⚠️ Untested — every player needs the same mod version |
| Dedicated server | 🚧 Not supported yet — planned for a later stage |

---

Next: **[Gameplay guide →](gameplay.md)**
