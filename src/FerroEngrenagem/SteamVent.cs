// D9: steam puffs over the Steam Engine when it runs and its steam outlet (top centre) has no pipe: the model
// carries objects named FeSteamPuff_<n>; they rise from the outlet, grow and shrink in a loop while it vents,
// and are hidden otherwise. Client-side visual only.
//
// C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace FerroEngrenagem
{
    public class SteamVent : MonoBehaviour
    {
        const float Rise = 1.4f;      // metres a puff climbs
        const float Life = 2.4f;      // seconds per puff

        class Puff
        {
            public Transform T;
            public Vector3 Base;
            public Vector3 Scale;
            public float Offset;
        }

        Vector3i pos;
        readonly List<Puff> puffs = new List<Puff>();
        bool venting;
        float nextCheck;

        public static void Attach(BlockEntityData ebcd, Vector3i pos)
        {
            if (ebcd == null || ebcd.transform == null || GameManager.IsDedicatedServer) return;
            SteamVent v = ebcd.transform.GetComponent<SteamVent>();
            if (v == null) v = ebcd.transform.gameObject.AddComponent<SteamVent>();
            v.Init(pos);
        }

        void Init(Vector3i p)
        {
            pos = p;
            puffs.Clear();
            Collect(transform);
            for (int i = 0; i < puffs.Count; i++) puffs[i].Offset = i * Life / Mathf.Max(1, puffs.Count);
            nextCheck = 0f;
            Show(false);
        }

        void Collect(Transform t)
        {
            for (int i = 0; i < t.childCount; i++)
            {
                Transform c = t.GetChild(i);
                if (c.name.StartsWith("FeSteamPuff", System.StringComparison.Ordinal))
                {
                    Puff p = new Puff();
                    p.T = c;
                    p.Base = c.localPosition;
                    p.Scale = c.localScale;
                    puffs.Add(p);
                }
                Collect(c);
            }
        }

        void Show(bool on)
        {
            foreach (Puff p in puffs) if (p.T != null && p.T.gameObject.activeSelf != on) p.T.gameObject.SetActive(on);
            // HD model (Art/feHD): a particle plume FeFx_SteamVent_* instead of the puff meshes
            foreach (ParticleSystem ps in GetComponentsInChildren<ParticleSystem>(true))
            {
                if (!ps.name.StartsWith("FeFx_SteamVent", System.StringComparison.Ordinal)) continue;
                if (on && !ps.isEmitting) ps.Play(true);
                else if (!on && ps.isEmitting) ps.Stop(true, ParticleSystemStopBehavior.StopEmitting);
            }
        }

        void Update()
        {
            if (Time.time >= nextCheck)
            {
                nextCheck = Time.time + 0.5f;
                World world = GameManager.Instance == null ? null : GameManager.Instance.World;
                bool v = false;
                if (world != null && TorqueEngine.IsRunning(world, pos))
                {
                    v = true;
                    foreach (FluidPort port in Fluids.Ports(world, pos))
                        if (port.Out && port.Fluid == Fluids.Steam && Fluids.PortConnected(world, port)) v = false;
                }
                if (v != venting) { venting = v; Show(v); }
            }
            if (!venting) return;
            float t = Time.time;
            foreach (Puff p in puffs)
            {
                if (p.T == null) continue;
                float k = ((t + p.Offset) % Life) / Life;          // 0..1 along its life
                p.T.localPosition = p.Base + Vector3.up * (k * Rise);
                float g = Mathf.Sin(k * Mathf.PI);                  // grow, then shrink away
                p.T.localScale = p.Scale * (0.4f + 1.4f * g);
            }
        }
    }
}
