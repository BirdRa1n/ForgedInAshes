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

        // Mini conveyors (Ammo Press HD, 2026-11-24): empties FeTrack_<n>_P<i> are the path (in order); the parts
        // FeTrackItem_<n>_<k> ride along it while the machine works, evenly spaced, growing in at the start and
        // shrinking away at the end (cases going in, finished rounds coming out).
        class Track
        {
            public readonly SortedDictionary<int, Vector3> Pts = new SortedDictionary<int, Vector3>();
            public readonly List<Transform> Items = new List<Transform>();
            public readonly List<Vector3> Scales = new List<Vector3>();
            public Vector3[] P;
            public float Length;
        }
        readonly Dictionary<string, Track> tracks = new Dictionary<string, Track>();
        float trackPos;

        Track TrackOf(string id)
        {
            Track t;
            if (!tracks.TryGetValue(id, out t)) { t = new Track(); tracks[id] = t; }
            return t;
        }

        void BuildTracks()
        {
            List<string> bad = new List<string>();
            foreach (KeyValuePair<string, Track> kv in tracks)
            {
                Track t = kv.Value;
                if (t.Pts.Count < 2 || t.Items.Count == 0) { bad.Add(kv.Key); continue; }
                t.P = new Vector3[t.Pts.Count];
                t.Pts.Values.CopyTo(t.P, 0);
                t.Length = 0f;
                for (int i = 1; i < t.P.Length; i++) t.Length += (t.P[i] - t.P[i - 1]).magnitude;
                foreach (Transform it in t.Items) t.Scales.Add(it.localScale);
            }
            foreach (string b in bad) tracks.Remove(b);
        }

        static Vector3 Along(Vector3[] p, float d)
        {
            for (int i = 1; i < p.Length; i++)
            {
                float seg = (p[i] - p[i - 1]).magnitude;
                if (d <= seg || i == p.Length - 1) return Vector3.Lerp(p[i - 1], p[i], seg > 0f ? Mathf.Clamp01(d / seg) : 1f);
                d -= seg;
            }
            return p[p.Length - 1];
        }

        void MoveTracks(float dt)
        {
            trackPos += 0.10f * speed * dt;                                   // 0.10 m/s at full speed
            foreach (Track t in tracks.Values)
            {
                float gap = t.Length / t.Items.Count;
                for (int k = 0; k < t.Items.Count; k++)
                {
                    Transform it = t.Items[k];
                    if (it == null) continue;
                    float d = Mathf.Repeat(trackPos + k * gap, t.Length);
                    it.localPosition = Along(t.P, d);
                    float edge = Mathf.Min(d, t.Length - d) / 0.04f;            // grow in / shrink out over 4 cm
                    it.localScale = t.Scales[k] * Mathf.Clamp01(edge);
                }
            }
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
            v.tracks.Clear();
            v.Collect(ebcd.transform);
            v.BuildTracks();
            v.enabled = v.spins.Count > 0 || v.pistons.Count > 0 || v.tracks.Count > 0;
        }

        void Collect(Transform t)
        {
            for (int i = 0; i < t.childCount; i++)
            {
                Transform c = t.GetChild(i);
                if (c.name.StartsWith("FeTrackItem_", System.StringComparison.Ordinal))
                {
                    string[] tok = c.name.Split('_', '.');
                    if (tok.Length >= 3) TrackOf(tok[1]).Items.Add(c);
                }
                else if (c.name.StartsWith("FeTrack_", System.StringComparison.Ordinal))
                {
                    string[] tok = c.name.Split('_', '.');
                    int pi;
                    if (tok.Length >= 3 && tok[2].Length > 1 && int.TryParse(tok[2].Substring(1), out pi))
                        TrackOf(tok[1]).Pts[pi] = c.localPosition;
                }
                else if (c.name.StartsWith("FeSpin", System.StringComparison.Ordinal))
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
            if (tracks.Count > 0) MoveTracks(dt);
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
