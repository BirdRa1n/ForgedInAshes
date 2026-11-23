// D9: the Condenser's model comes alive (user, 2026-11-23): a fan that turns while it is powered (faster while it
// condenses), a gas chamber whose fill follows the steam it takes in, and a liquid chamber whose level follows the
// condensed water waiting in its buffer (blue = water).
// Model contract (Art/feKinetic, model_condenser):
//   FeFan        turns around its own local +Z
//   FeLevelGas   pivot at the bottom of the gas chamber; its local Y scale = steam intake (0..1 of FeFluidRate)
//   FeLevelLiquid pivot at the bottom of the liquid chamber; its local Y scale = buffer fill (0..1 of FeFluidBuffer)
// Client-side visual; the fluid state comes from FluidStore (single player / host).
//
// C# 5 only.

using HarmonyLib;
using UnityEngine;

namespace FerroEngrenagem
{
    public class CondenserVisual : MonoBehaviour
    {
        Vector3i pos;
        Transform fan, gas, liquid;
        Vector3 gasScale, liquidScale;
        float fanSpeed, gasNow, liquidNow, gasGoal, liquidGoal, fanGoal, next;

        public static void Attach(BlockEntityData ebcd, Vector3i pos)
        {
            if (ebcd == null || ebcd.transform == null || GameManager.IsDedicatedServer) return;
            CondenserVisual v = ebcd.transform.GetComponent<CondenserVisual>();
            if (v == null) v = ebcd.transform.gameObject.AddComponent<CondenserVisual>();
            v.Init(pos);
        }

        void Init(Vector3i p)
        {
            pos = p;
            fan = Find(transform, "FeFan");
            gas = Find(transform, "FeLevelGas");
            liquid = Find(transform, "FeLevelLiquid");
            if (gas != null) gasScale = gas.localScale;
            if (liquid != null) liquidScale = liquid.localScale;
            gasNow = liquidNow = 0f;
            next = 0f;
            // alignment check: where the model really sits against its cells
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            BlockValue bv = world == null ? BlockValue.Air : world.GetBlock(p);
            Log.Out(FerroEngrenagemMod.LogPrefix + "condenser at " + p + " rot=" + bv.rotation + " model at "
                    + transform.position.ToString("F2") + " liquid at "
                    + (liquid != null ? liquid.position.ToString("F2") : "-") + " fan=" + (fan != null));
            if (world != null)
                foreach (FluidPort port in Fluids.Ports(world, p))
                {
                    Vector3i n = new Vector3i(port.Cell.x + port.Dir.x, port.Cell.y + port.Dir.y, port.Cell.z + port.Dir.z);
                    Log.Out(FerroEngrenagemMod.LogPrefix + "condenser port " + (port.Out ? "out " : "in ") + port.Fluid
                            + " cell " + port.Cell + " dir " + port.Dir + " -> " + n + " = " + world.GetBlock(n).Block.GetBlockName()
                            + " connected=" + Fluids.PortConnected(world, port)
                            + " | cell itself = " + world.GetBlock(port.Cell).Block.GetBlockName()
                            + (world.GetBlock(port.Cell).ischild ? " (child)" : ""));
                }
        }

        static Transform Find(Transform t, string n)
        {
            if (t.name.StartsWith(n, System.StringComparison.Ordinal)) return t;
            for (int i = 0; i < t.childCount; i++)
            {
                Transform r = Find(t.GetChild(i), n);
                if (r != null) return r;
            }
            return null;
        }

        void Update()
        {
            if (Time.time >= next)
            {
                next = Time.time + 0.25f;
                World world = GameManager.Instance == null ? null : GameManager.Instance.World;
                if (world != null)
                {
                    BlockValue bv = world.GetBlock(pos);
                    FluidStore.EnsureLoaded();
                    FluidState s = FluidStore.Get(pos);
                    TileEntityPowered te = world.GetTileEntity(pos) as TileEntityPowered;
                    bool powered = te != null && te.IsPowered;
                    float rate = Fluids.Prop(bv.Block, "FeFluidRate", 120f);
                    float cap = Fluids.Prop(bv.Block, "FeFluidBuffer", 200f);
                    gasGoal = rate > 0f ? Mathf.Clamp01(s.LastFlow / rate) : 0f;
                    liquidGoal = cap > 0f ? Mathf.Clamp01(s.Steam / cap) : 0f;
                    fanGoal = powered ? (s.LastFlow > 0.01f ? 900f : 240f) : 0f;   // degrees per second
                }
            }
            float dt = Time.deltaTime;
            fanSpeed = Mathf.MoveTowards(fanSpeed, fanGoal, 600f * dt);
            if (fan != null && fanSpeed > 0.1f) fan.Rotate(Vector3.forward, fanSpeed * dt, Space.Self);
            gasNow = Mathf.MoveTowards(gasNow, gasGoal, 0.8f * dt);
            liquidNow = Mathf.MoveTowards(liquidNow, liquidGoal, 0.3f * dt);
            if (gas != null) gas.localScale = new Vector3(gasScale.x, gasScale.y * Mathf.Max(0.02f, gasNow), gasScale.z);
            if (liquid != null) liquid.localScale = new Vector3(liquidScale.x, liquidScale.y * Mathf.Max(0.02f, liquidNow), liquidScale.z);
        }
    }

    [HarmonyPatch(typeof(BlockPowered), "OnBlockEntityTransformAfterActivated")]
    public static class Patch_BlockPowered_CondenserVisual
    {
        public static void Postfix(BlockPowered __instance, Vector3i _blockPos, BlockEntityData _ebcd)
        {
            if (Fluids.Kind(__instance) == FluidKind.Condenser) CondenserVisual.Attach(_ebcd, _blockPos);
        }
    }
}
