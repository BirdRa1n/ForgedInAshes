// Wire tool on big powered blocks (user 2026-11-24: "the Industrial Dynamo does not connect to the Bus").
//
// IL 3.4.0 b10: ItemActionConnectPower.OnHoldingUpdate takes the aimed cell as it is (HitInfo.hit.blockPos) for the
// wire's start point and for GetPoweredBlock(ItemInventoryData), which, when that cell has no tile entity, CREATES a
// new powered tile entity there. On a multi-block power source (Industrial Dynamo 3x2x3, Coal Generator 2x2x1) most
// of the model is child cells: the wire went to a ghost power source in the child cell instead of the block's own
// (only the parent cell holds it), so the Bus never saw the dynamo. Fix: while the wire tool is held, a hit on a child
// cell of one of our powered blocks is moved to its parent cell (BlockValue.parent is the offset to it), before the
// tool reads it. Ghost tile entities left in a child cell by earlier attempts are removed when the tool aims there.
//
// C# 5 only.

using HarmonyLib;
using UnityEngine;

namespace ForgedInAshes
{
    public static class WireMultiblock
    {
        /// <summary>Moves the player's hit from a child cell of a multi-block fe* powered block to its parent.</summary>
        public static void ToParent(ItemActionData data)
        {
            if (data == null || data.invData == null) return;
            EntityPlayerLocal pl = data.invData.holdingEntity as EntityPlayerLocal;
            World world = data.invData.world as World;
            if (pl == null || world == null || pl.HitInfo == null || !pl.HitInfo.bHitValid) return;
            Vector3i pos = pl.HitInfo.hit.blockPos;
            BlockValue bv = world.GetBlock(pos);
            if (!bv.ischild) return;
            Block b = bv.Block;
            if (b == null || !(b is BlockPowered || b is BlockPowerSource)) return;
            if (!b.GetBlockName().StartsWith("fe", System.StringComparison.Ordinal)) return;
            Vector3i parent = pos + bv.parent;
            RemoveGhost(world, pos);
            pl.HitInfo.hit.blockPos = parent;
        }

        static void RemoveGhost(World world, Vector3i pos)
        {
            TileEntityPowered ghost = world.GetTileEntity(pos) as TileEntityPowered;
            if (ghost == null) return;
            if (!SingletonMonoBehaviour<ConnectionManager>.Instance.IsServer) return;
            PowerItem pi = ghost.GetPowerItem();
            if (pi != null && PowerManager.HasInstance) PowerManager.Instance.RemovePowerNode(pi);
            Chunk c = world.GetChunkFromWorldPos(pos) as Chunk;
            if (c != null) c.RemoveTileEntity(world, ghost);
            Log.Out("[ForgedInAshes] wire tool: removed a stray power tile entity from the child cell " + pos);
        }
    }

    [HarmonyPatch(typeof(ItemActionConnectPower), "OnHoldingUpdate")]
    public static class Patch_ConnectPower_Hold_Multiblock
    {
        public static void Prefix(ItemActionData _actionData)
        {
            WireMultiblock.ToParent(_actionData);
        }
    }

    [HarmonyPatch(typeof(ItemActionConnectPower), "ExecuteAction")]
    public static class Patch_ConnectPower_Execute_Multiblock
    {
        public static void Prefix(ItemActionData _actionData)
        {
            WireMultiblock.ToParent(_actionData);
        }
    }
}
