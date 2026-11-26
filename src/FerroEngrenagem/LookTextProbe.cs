// Diagnostic for "the look text disappears" (user, 2026-11-26: "I think the mod's items themselves cause it").
// PlayerMoveController.HandleInteraction (IL 3.4.0 b10) builds the look text each frame. Before the block, it lets an
// "Item"-tagged collider (items raycast, mask 73728 = layers 13 + 16) win when it is less than 1.2 m behind the
// block point; it skips blocks when TPCameraCheckResult == 2; and it keeps strTextLabelPointingTo as a cache.
// This postfix logs every time the text goes from shown to empty while the voxel ray still hits an "fe" block, with
// everything HandleInteraction was given. Rate limited (10 s). Client side only. C# 5 only.

using HarmonyLib;
using UnityEngine;

namespace FerroEngrenagem
{
    [HarmonyPatch(typeof(PlayerMoveController), "HandleInteraction")]
    public static class Patch_PlayerMoveController_HandleInteraction_Probe
    {
        static float lastLog = -100f;

        public static void Prefix(PlayerMoveController __instance, out string __state)
        {
            __state = __instance.strTextLabelPointingTo;
        }

        public static void Postfix(PlayerMoveController __instance, string __state, WorldRayHitInfo _hitInfo,
                                   Vector3i _blockPosInside, bool _bHitWorldAndEntities, bool _bItemHit,
                                   bool _bBackpackHit, RaycastHit _raycastHitItems)
        {
            try
            {
                if (string.IsNullOrEmpty(__state) || !string.IsNullOrEmpty(__instance.strTextLabelPointingTo)) return;
                if (Time.time - lastLog < 10f) return;
                World world = GameManager.Instance == null ? null : GameManager.Instance.World;
                if (world == null) return;
                // what block is really in front of the player (the voxel hit, before any item override)?
                BlockValue inside = world.GetBlock(_blockPosInside);
                string insideName = inside.isair ? "air" : inside.Block.GetBlockName();
                bool feInside = insideName.StartsWith("fe", System.StringComparison.Ordinal);
                bool feHit = _hitInfo != null && _hitInfo.bHitValid && !_hitInfo.hit.blockValue.isair
                             && _hitInfo.hit.blockValue.Block.GetBlockName().StartsWith("fe", System.StringComparison.Ordinal);
                if (!feInside && !feHit && !_bItemHit) return;
                lastLog = Time.time;
                EntityPlayerLocal pl = GameManager.Instance.World.GetPrimaryPlayer();
                string item = "no";
                if (_bItemHit && _raycastHitItems.collider != null)
                {
                    Transform t = _raycastHitItems.collider.transform;
                    item = "'" + t.name + "' (root '" + t.root.name + "') tag " + t.tag + " layer " + t.gameObject.layer
                           + " dist " + _raycastHitItems.distance.ToString("0.00");
                }
                Log.Out(FerroEngrenagemMod.LogPrefix + "look probe: text gone. hit valid " + (_hitInfo != null && _hitInfo.bHitValid)
                        + ", tag '" + (_hitInfo == null ? "-" : _hitInfo.tag) + "', block "
                        + (_hitInfo == null || _hitInfo.hit.blockValue.isair ? "air" : _hitInfo.hit.blockValue.Block.GetBlockName())
                        + " at " + (_hitInfo == null ? "-" : _hitInfo.hit.blockPos.ToString())
                        + " dist " + (_hitInfo == null ? "-" : Mathf.Sqrt(_hitInfo.hit.distanceSq).ToString("0.00"))
                        + " | inside " + insideName + " at " + _blockPosInside
                        + " | world+entities " + _bHitWorldAndEntities + ", item hit " + item + ", backpack " + _bBackpackHit
                        + " | camera check " + (pl == null ? "-" : pl.TPCameraCheckResult.ToString())
                        + ", attached " + (pl != null && pl.AttachedToEntity != null)
                        + ", held " + (pl == null || pl.inventory == null || pl.inventory.holdingItem == null ? "-" : pl.inventory.holdingItem.GetItemName())
                        + " | was: " + Short(__state));
            }
            catch (System.Exception e)
            {
                if (Time.time - lastLog > 10f) { lastLog = Time.time; Log.Warning(FerroEngrenagemMod.LogPrefix + "look probe: " + e.Message); }
            }
        }

        static string Short(string s)
        {
            s = s.Replace("\n", " / ");
            return s.Length > 120 ? s.Substring(0, 120) + "..." : s;
        }
    }
}
