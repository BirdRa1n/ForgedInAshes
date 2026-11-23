// Phase 6: the production machines' own models (Art/feKinetic, model_m_*) come alive while they work: FeSpin_* parts
// turn about their local +Z (an "x<mult>" token in the name scales the speed: FeSpin_x8_Blade), FePiston_* parts slide
// back and forth along their local +Z (the Press ram, the brake blade, the lift arms). "Working" = a recipe in the
// queue (or a Foundry that is burning). Client-side, from the tile entity the host has.
//
// C# 5 only.

using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace FerroEngrenagem
{
    public class MachineVisual : MonoBehaviour
    {
        class Spin
        {
            public Transform T;
            public float Mult = 1f;
        }

        class Piston
        {
            public Transform T;
            public Vector3 Base;
            public float Phase;
        }

        readonly List<Spin> spins = new List<Spin>();
        readonly List<Piston> pistons = new List<Piston>();
        Vector3i pos;
        bool working;
        float speed, angle, next;

        public static void Attach(BlockEntityData ebcd, Vector3i pos)
        {
            if (ebcd == null || ebcd.transform == null || GameManager.IsDedicatedServer) return;
            MachineVisual v = ebcd.transform.GetComponent<MachineVisual>();
            if (v == null) v = ebcd.transform.gameObject.AddComponent<MachineVisual>();
            v.pos = pos;
            v.spins.Clear();
            v.pistons.Clear();
            v.Collect(ebcd.transform);
            if (v.spins.Count == 0 && v.pistons.Count == 0) v.enabled = false;
        }

        void Collect(Transform t)
        {
            for (int i = 0; i < t.childCount; i++)
            {
                Transform c = t.GetChild(i);
                if (c.name.StartsWith("FeSpin", System.StringComparison.Ordinal))
                {
                    Spin s = new Spin();
                    s.T = c;
                    foreach (string tok in c.name.Split('_'))
                    {
                        float m;
                        if (tok.Length > 1 && tok[0] == 'x' &&
                            float.TryParse(tok.Substring(1), System.Globalization.NumberStyles.Float,
                                           System.Globalization.CultureInfo.InvariantCulture, out m)) s.Mult = m;
                    }
                    spins.Add(s);
                }
                else if (c.name.StartsWith("FePiston", System.StringComparison.Ordinal))
                {
                    Piston p = new Piston();
                    p.T = c;
                    p.Base = c.localPosition;
                    p.Phase = pistons.Count * Mathf.PI / 2f;
                    pistons.Add(p);
                }
                Collect(c);
            }
        }

        bool Working(World world)
        {
            TileEntityWorkstation ws = world.GetTileEntity(Fluids.ParentOf(world, pos, world.GetBlock(pos))) as TileEntityWorkstation;
            if (ws == null) return false;
            if (ws.IsBurning) return true;
            RecipeQueueItem[] q = ws.Queue;
            if (q == null) return false;
            foreach (RecipeQueueItem it in q)
                if (it != null && it.Recipe != null && it.Multiplier > 0) return true;
            return false;
        }

        void Update()
        {
            if (Time.time >= next)
            {
                next = Time.time + 0.5f;
                World world = GameManager.Instance == null ? null : GameManager.Instance.World;
                working = world != null && Working(world);
            }
            speed = Mathf.MoveTowards(speed, working ? 1f : 0f, Time.deltaTime);
            if (speed <= 0.001f) return;
            float dt = Time.deltaTime;
            foreach (Spin s in spins)
                if (s.T != null) s.T.Rotate(Vector3.forward, 360f * s.Mult * speed * dt, Space.Self);
            angle += 4f * speed * dt;
            foreach (Piston p in pistons)
                if (p.T != null)
                    p.T.localPosition = p.Base + p.T.localRotation * Vector3.forward * (0.15f * (Mathf.Sin(angle + p.Phase) - 1f) * speed);
        }
    }

    // declared on Block only (BlockWorkstation / BlockParticle do not override it, IL 3.4.0 b10)
    [HarmonyPatch(typeof(Block), "OnBlockEntityTransformAfterActivated")]
    public static class Patch_Workstation_MachineVisual
    {
        public static void Postfix(Block __instance, Vector3i _blockPos, BlockEntityData _ebcd)
        {
            if (__instance is BlockWorkstation && __instance.GetBlockName().StartsWith("fe", System.StringComparison.Ordinal))
                MachineVisual.Attach(_ebcd, _blockPos);
        }
    }
}
