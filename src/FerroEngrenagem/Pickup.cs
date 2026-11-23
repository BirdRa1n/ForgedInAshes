// Pick up the mod's machines and power blocks with crouch + E, like the Crank (user, 2026-11-22: "every time I
// have to hit them to take them away").
//
// Vanilla (IL 3.4.0 b10) only enables "take" on workstations (BlockWorkstation.GetBlockActivationCommands) and on
// power sources (BlockPowerSource) inside the player's OWN land claim (IsMyLandProtectedBlock), for player-placed
// blocks with TakeDelay > 0 (workstations: also with empty input slots). For the mod's blocks ("fe" names) we
// allow it anywhere the player could build instead (CanPlaceBlockAt: not inside someone else's claim), keeping
// the other vanilla conditions. The Crank has the same rule in its own class (Crank.cs).
// Torque network parts (BlockFeKinetic, Torque Crank) use the plain Block "take" (CanPickup + TakeDelay in XML,
// crouch + E); the Electric Motor is a vanilla Powered block, which can already be taken.
//
// C# 5 only.

using HarmonyLib;

namespace FerroEngrenagem
{
    public static class Pickup
    {
        public static bool IsModBlock(Block b)
        {
            return b != null && b.GetBlockName().StartsWith("fe");
        }

        public static bool CanBuildHere(WorldBase world, Vector3i pos)
        {
            return world.CanPlaceBlockAt(pos, world.GetGameManager().GetPersistentLocalPlayer(), false);
        }

        /// <summary>Set enabled on the "take" command, if there is one.</summary>
        public static void EnableTake(BlockActivationCommand[] cmds, bool enabled)
        {
            if (cmds == null) return;
            for (int i = 0; i < cmds.Length; i++)
                if (cmds[i].text == "take") cmds[i].enabled = enabled;
        }
    }

    [HarmonyPatch(typeof(BlockWorkstation), "GetBlockActivationCommands")]
    public static class Patch_BlockWorkstation_Take
    {
        public static void Postfix(BlockWorkstation __instance, WorldBase _world, Vector3i _blockPos,
                                   ref BlockActivationCommand[] __result)
        {
            if (!Pickup.IsModBlock(__instance) || __result == null) return;
            TileEntityWorkstation te = _world.GetTileEntity(_blockPos) as TileEntityWorkstation;
            bool ok = te != null && te.IsPlayerPlaced && __instance.TakeDelay > 0f &&
                      (te.InputSlotCount == 0 || te.InputIsEmpty()) && Pickup.CanBuildHere(_world, _blockPos);
            Pickup.EnableTake(__result, ok);
        }
    }

    [HarmonyPatch(typeof(BlockPowerSource), "GetBlockActivationCommands")]
    public static class Patch_BlockPowerSource_Take
    {
        public static void Postfix(BlockPowerSource __instance, WorldBase _world, Vector3i _blockPos,
                                   ref BlockActivationCommand[] __result)
        {
            if (!Pickup.IsModBlock(__instance) || __instance is BlockFeCrank || __result == null) return;
            TileEntityPowerSource te = _world.GetTileEntity(_blockPos) as TileEntityPowerSource;
            bool ok = te != null && te.IsPlayerPlaced && __instance.TakeDelay > 0f &&
                      Pickup.CanBuildHere(_world, _blockPos);
            Pickup.EnableTake(__result, ok);
        }
    }
}
