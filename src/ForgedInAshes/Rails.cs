// D14 (user 2026-11-27): railways. Track pieces are blocks (BlockFeRail) whose rails are curves in their local space;
// the pieces join where their ends meet, and that makes a graph the trains plan their routes on.
//
//   FeRail="straight"  1x1x1: one cell, south edge to north edge
//   FeRail="curve"     5x1x5: a quarter circle of radius 4.5 from the south edge of the left column to the east edge
//                      of the top row (turned with the block it makes every 90-degree corner)
//   FeRail="ramp"      1x2x3: climbs one block over three cells
//   FeRail="switchR"   5x1x5: the straight of the left column plus the curve (a junction: trains choose by route)
//   FeRail="switchL"   5x1x5: the mirror (straight on the right column, curve to the left)
//
// Local space: x right, z forward (the block's front), y up, origin at the centre of the parent cell at rail height.
// The ends are joined by position (0.1 m grid). A train may only go on from one piece to the next when the rails
// continue (the two directions differ less than 60 degrees): at a junction it can take either branch, never turn
// back along the other one. Trains turn back only at stations (Trains.cs).
//
// The pieces are remembered by position (RailStore, <save>/ForgedInAshes_rails.txt) so routes are planned also
// through unloaded chunks. C# 5 only.

using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

namespace ForgedInAshes
{
    public class RailEdge
    {
        public int Id;
        public Vector3i Piece;              // parent cell of the track block
        public List<Vector3> Pts = new List<Vector3>();
        public List<float> Cum = new List<float>();
        public float Length;
        public Vector3i KeyA, KeyB;         // node keys of the two ends

        public void Finish()
        {
            Cum.Clear();
            float d = 0f;
            Cum.Add(0f);
            for (int i = 1; i < Pts.Count; i++) { d += Vector3.Distance(Pts[i - 1], Pts[i]); Cum.Add(d); }
            Length = d;
            KeyA = Rails.Key(Pts[0]);
            KeyB = Rails.Key(Pts[Pts.Count - 1]);
        }

        public Vector3 At(float s)
        {
            if (s <= 0f) return Pts[0];
            if (s >= Length) return Pts[Pts.Count - 1];
            int i = Cum.BinarySearch(s);
            if (i >= 0) return Pts[i];
            i = ~i;
            float t = (s - Cum[i - 1]) / Mathf.Max(0.0001f, Cum[i] - Cum[i - 1]);
            return Vector3.Lerp(Pts[i - 1], Pts[i], t);
        }

        /// <summary>Direction of the rails at the A end, pointing into the edge.</summary>
        public Vector3 TanA { get { return (Pts[1] - Pts[0]).normalized; } }
        /// <summary>Direction of the rails at the B end, pointing out of the edge (A to B).</summary>
        public Vector3 TanB { get { return (Pts[Pts.Count - 1] - Pts[Pts.Count - 2]).normalized; } }
    }

    public struct RailPos
    {
        public RailEdge Edge;
        public float S;
        public float Dist;
    }

    public static class Rails
    {
        public const float RailY = 0.15f;
        const float MaxTurnDot = 0.5f;   // cos 60

        public static Vector3i Key(Vector3 p)
        {
            return new Vector3i(Mathf.RoundToInt(p.x * 10f), Mathf.RoundToInt(p.y * 10f), Mathf.RoundToInt(p.z * 10f));
        }

        public static string Type(Block b)
        {
            return b != null && b.Properties != null && b.Properties.Contains("FeRail") ? b.Properties.GetString("FeRail").Trim() : "";
        }

        public static bool Is(Block b) { return Type(b).Length > 0; }

        // ------------------------------------------------------------ geometry of one piece
        static List<Vector3> Line(Vector3 a, Vector3 b)
        {
            return new List<Vector3> { a, b };
        }

        static List<Vector3> Arc(Vector3 centre, float r, float fromDeg, float toDeg)
        {
            List<Vector3> l = new List<Vector3>();
            int n = Mathf.Max(4, Mathf.CeilToInt(Mathf.Abs(toDeg - fromDeg) * Mathf.Deg2Rad * r / 0.3f));
            for (int i = 0; i <= n; i++)
            {
                float a = Mathf.Lerp(fromDeg, toDeg, (float)i / n) * Mathf.Deg2Rad;
                l.Add(new Vector3(centre.x + r * Mathf.Cos(a), centre.y, centre.z + r * Mathf.Sin(a)));
            }
            return l;
        }

        /// <summary>The rails of a piece type in local space (one list per rail path).</summary>
        public static List<List<Vector3>> LocalPaths(string type)
        {
            List<List<Vector3>> l = new List<List<Vector3>>();
            switch (type)
            {
                case "straight":
                    l.Add(Line(new Vector3(0f, 0f, -0.5f), new Vector3(0f, 0f, 0.5f)));
                    break;
                case "curve":
                    l.Add(Arc(new Vector3(2.5f, 0f, -2.5f), 4.5f, 180f, 90f));
                    break;
                case "ramp":
                    l.Add(Line(new Vector3(0f, 0f, -1.5f), new Vector3(0f, 1f, 1.5f)));
                    break;
                case "switchR":
                    l.Add(Line(new Vector3(-2f, 0f, -2.5f), new Vector3(-2f, 0f, 2.5f)));
                    l.Add(Arc(new Vector3(2.5f, 0f, -2.5f), 4.5f, 180f, 90f));
                    break;
                case "switchL":
                    l.Add(Line(new Vector3(2f, 0f, -2.5f), new Vector3(2f, 0f, 2.5f)));
                    l.Add(Arc(new Vector3(-2.5f, 0f, -2.5f), 4.5f, 0f, 90f));
                    break;
            }
            return l;
        }

        static BlockValue Bv(string name, int rotation)
        {
            Block b = Block.GetBlockByName(name, false);
            if (b == null) return BlockValue.Air;
            BlockValue v = BlockValue.Air;
            v.type = b.blockID;
            v.rotation = (byte)rotation;
            return v;
        }

        /// <summary>The rails of the piece whose parent cell is p, in world space.</summary>
        public static List<List<Vector3>> WorldPaths(Vector3i p, string name, int rotation)
        {
            List<List<Vector3>> l = new List<List<Vector3>>();
            BlockValue bv = Bv(name, rotation);
            if (bv.isair) return l;
            Quaternion q = bv.Block.shape.GetRotation(bv);
            Vector3 o = new Vector3(p.x + 0.5f, p.y + RailY, p.z + 0.5f);
            foreach (List<Vector3> path in LocalPaths(Type(bv.Block)))
            {
                List<Vector3> w = new List<Vector3>();
                foreach (Vector3 v in path) w.Add(o + q * v);
                l.Add(w);
            }
            return l;
        }

        // ------------------------------------------------------------ graph
        static readonly List<RailEdge> edges = new List<RailEdge>();
        static readonly Dictionary<Vector3i, List<RailEdge>> byNode = new Dictionary<Vector3i, List<RailEdge>>();
        static bool built;
        public static int Version;

        public static List<RailEdge> Edges { get { Build(); return edges; } }

        public static void Dirty() { built = false; Version++; }

        static void Build()
        {
            RailStore.EnsureLoaded();
            if (built) return;
            built = true;
            edges.Clear();
            byNode.Clear();
            foreach (KeyValuePair<Vector3i, string> kv in RailStore.All)
            {
                string name;
                int rot;
                RailStore.Parse(kv.Value, out name, out rot);
                foreach (List<Vector3> path in WorldPaths(kv.Key, name, rot))
                {
                    if (path.Count < 2) continue;
                    RailEdge e = new RailEdge { Id = edges.Count, Piece = kv.Key, Pts = path };
                    e.Finish();
                    edges.Add(e);
                    Link(e.KeyA, e);
                    Link(e.KeyB, e);
                }
            }
        }

        static void Link(Vector3i k, RailEdge e)
        {
            List<RailEdge> l;
            if (!byNode.TryGetValue(k, out l)) { l = new List<RailEdge>(); byNode[k] = l; }
            l.Add(e);
        }

        /// <summary>The nearest point on any rail to p (within max metres); Edge is null when there is none.</summary>
        public static RailPos Locate(Vector3 p, float max)
        {
            Build();
            RailPos best = new RailPos { Edge = null, S = 0f, Dist = max };
            foreach (RailEdge e in edges)
            {
                for (int i = 1; i < e.Pts.Count; i++)
                {
                    Vector3 a = e.Pts[i - 1], b = e.Pts[i];
                    Vector3 ab = b - a;
                    float t = Mathf.Clamp01(Vector3.Dot(p - a, ab) / Mathf.Max(0.0001f, ab.sqrMagnitude));
                    Vector3 q = a + ab * t;
                    float d = Vector3.Distance(p, q);
                    if (d < best.Dist) best = new RailPos { Edge = e, S = e.Cum[i - 1] + t * (e.Cum[i] - e.Cum[i - 1]), Dist = d };
                }
            }
            return best;
        }

        /// <summary>The direction along e at s when moving with dir (+1 = A to B).</summary>
        public static Vector3 Heading(RailEdge e, float s, int dir)
        {
            Vector3 a = e.At(Mathf.Max(0f, s - 0.2f)), b = e.At(Mathf.Min(e.Length, s + 0.2f));
            Vector3 h = (b - a).normalized;
            return dir > 0 ? h : -h;
        }

        // the edges that go on from the end of e reached with dir, with the direction to take on each
        static List<KeyValuePair<RailEdge, int>> Next(RailEdge e, int dir)
        {
            List<KeyValuePair<RailEdge, int>> l = new List<KeyValuePair<RailEdge, int>>();
            Vector3i key = dir > 0 ? e.KeyB : e.KeyA;
            Vector3 tin = dir > 0 ? e.TanB : -e.TanA;
            List<RailEdge> at;
            if (!byNode.TryGetValue(key, out at)) return l;
            foreach (RailEdge n in at)
            {
                if (n == e) continue;
                if (n.KeyA == key && Vector3.Dot(tin, n.TanA) > MaxTurnDot) l.Add(new KeyValuePair<RailEdge, int>(n, 1));
                if (n.KeyB == key && Vector3.Dot(tin, -n.TanB) > MaxTurnDot) l.Add(new KeyValuePair<RailEdge, int>(n, -1));
            }
            return l;
        }

        /// <summary>Points from (e, s) moving with dir for up to len metres, choosing the straightest way on
        /// (used to lay the track behind a new train).</summary>
        public static List<Vector3> Walk(RailEdge e, float s, int dir, float len)
        {
            return Walk(e, s, dir, len, 0);
        }

        /// <summary>Walk on from the point p (on a rail, within 0.6 m) going along heading, up to len metres; at a
        /// junction prefer = -1 takes the leftmost branch, +1 the rightmost, 0 the straightest (manual driving,
        /// user 2026-11-27). Empty when p is not on a rail.</summary>
        public static List<Vector3> WalkFrom(Vector3 p, Vector3 heading, float len, int prefer)
        {
            RailPos at = Locate(p, 0.6f);
            if (at.Edge == null) return new List<Vector3>();
            int dir = Vector3.Dot(Heading(at.Edge, at.S, 1), heading) >= 0f ? 1 : -1;
            return Walk(at.Edge, at.S, dir, len, prefer);
        }

        public static List<Vector3> Walk(RailEdge e, float s, int dir, float len, int prefer)
        {
            Build();
            List<Vector3> pts = new List<Vector3> { e.At(s) };
            float left = len;
            int guard = 0;
            while (left > 0f && e != null && guard++ < 500)
            {
                float room = dir > 0 ? e.Length - s : s;
                float step = Mathf.Min(room, left);
                Append(pts, e, s, dir > 0 ? s + step : s - step);
                left -= step;
                if (left <= 0f) break;
                List<KeyValuePair<RailEdge, int>> nx = Next(e, dir);
                if (nx.Count == 0) break;
                Vector3 tin = dir > 0 ? e.TanB : -e.TanA;
                KeyValuePair<RailEdge, int> pick = nx[0];
                float bestDot = -2f;
                foreach (KeyValuePair<RailEdge, int> c in nx)
                {
                    // how far the branch bends away (seen a few metres on, where the curve has opened up)
                    Vector3 far = c.Value > 0 ? c.Key.At(Mathf.Min(c.Key.Length, 3f)) : c.Key.At(Mathf.Max(0f, c.Key.Length - 3f));
                    Vector3 from = c.Value > 0 ? c.Key.At(0f) : c.Key.At(c.Key.Length);
                    float side = Vector3.Cross(tin, (far - from).normalized).y;       // > 0: to the right
                    float d = prefer == 0 ? Vector3.Dot(tin, c.Value > 0 ? c.Key.TanA : -c.Key.TanB) : prefer * side;
                    if (d > bestDot) { bestDot = d; pick = c; }
                }
                e = pick.Key;
                dir = pick.Value;
                s = dir > 0 ? 0f : e.Length;
            }
            return pts;
        }

        /// <summary>Append the points of e from s0 to s1 (either way), without repeating the first.</summary>
        static void Append(List<Vector3> pts, RailEdge e, float s0, float s1)
        {
            if (s1 >= s0)
            {
                for (int i = 0; i < e.Pts.Count; i++)
                    if (e.Cum[i] > s0 + 0.01f && e.Cum[i] < s1 - 0.01f) pts.Add(e.Pts[i]);
            }
            else
            {
                for (int i = e.Pts.Count - 1; i >= 0; i--)
                    if (e.Cum[i] < s0 - 0.01f && e.Cum[i] > s1 + 0.01f) pts.Add(e.Pts[i]);
            }
            Vector3 end = e.At(s1);
            if (pts.Count == 0 || Vector3.Distance(pts[pts.Count - 1], end) > 0.01f) pts.Add(end);
        }

        struct State
        {
            public RailEdge E;
            public int Dir;
        }

        /// <summary>Shortest way along the rails from (from, dir) to the point to (either direction of arrival).
        /// Null when there is none. The result starts at from and ends at to.</summary>
        public static List<Vector3> Path(RailPos from, int dir, RailPos to)
        {
            Build();
            if (from.Edge == null || to.Edge == null) return null;
            // same edge, ahead
            if (from.Edge == to.Edge && ((dir > 0 && to.S >= from.S) || (dir < 0 && to.S <= from.S)))
            {
                List<Vector3> direct = new List<Vector3> { from.Edge.At(from.S) };
                Append(direct, from.Edge, from.S, to.S);
                return direct;
            }
            Dictionary<long, float> cost = new Dictionary<long, float>();
            Dictionary<long, long> prev = new Dictionary<long, long>();
            Dictionary<long, State> states = new Dictionary<long, State>();
            List<long> open = new List<long>();
            System.Func<RailEdge, int, long> id = delegate (RailEdge e, int d) { return (long)e.Id * 2 + (d > 0 ? 1 : 0); };
            long start = -1;
            float bestTotal = float.MaxValue;
            long bestState = long.MinValue;
            // leave the start edge
            float first = dir > 0 ? from.Edge.Length - from.S : from.S;
            foreach (KeyValuePair<RailEdge, int> nx in Next(from.Edge, dir))
            {
                long k = id(nx.Key, nx.Value);
                if (!cost.ContainsKey(k) || cost[k] > first)
                {
                    cost[k] = first;
                    prev[k] = start;
                    states[k] = new State { E = nx.Key, Dir = nx.Value };
                    if (!open.Contains(k)) open.Add(k);
                }
            }
            int guard = 0;
            while (open.Count > 0 && guard++ < 20000)
            {
                long cur = open[0];
                foreach (long o in open) if (cost[o] < cost[cur]) cur = o;
                open.Remove(cur);
                float c = cost[cur];
                if (c >= bestTotal) break;
                State st = states[cur];
                if (st.E == to.Edge)
                {
                    float tail = st.Dir > 0 ? to.S : st.E.Length - to.S;
                    if (c + tail < bestTotal) { bestTotal = c + tail; bestState = cur; }
                }
                float through = c + st.E.Length;
                foreach (KeyValuePair<RailEdge, int> nx in Next(st.E, st.Dir))
                {
                    long k = id(nx.Key, nx.Value);
                    float old;
                    if (cost.TryGetValue(k, out old) && old <= through) continue;
                    cost[k] = through;
                    prev[k] = cur;
                    states[k] = new State { E = nx.Key, Dir = nx.Value };
                    if (!open.Contains(k)) open.Add(k);
                }
            }
            if (bestState == long.MinValue) return null;
            // rebuild the chain of edges
            List<State> chain = new List<State>();
            long s = bestState;
            while (s != start) { chain.Add(states[s]); s = prev[s]; }
            chain.Reverse();
            List<Vector3> pts = new List<Vector3> { from.Edge.At(from.S) };
            Append(pts, from.Edge, from.S, dir > 0 ? from.Edge.Length : 0f);
            for (int i = 0; i < chain.Count; i++)
            {
                State x = chain[i];
                float s0 = x.Dir > 0 ? 0f : x.E.Length;
                float s1 = i == chain.Count - 1 ? to.S : (x.Dir > 0 ? x.E.Length : 0f);
                Append(pts, x.E, s0, s1);
            }
            return pts;
        }
    }

    /// <summary>The track pieces of the world by parent cell: "name:rotation".</summary>
    public static class RailStore
    {
        public static readonly Dictionary<Vector3i, string> All = new Dictionary<Vector3i, string>();
        static string loadedFor;
        static bool dirty;

        static string FilePath() { return ForgedInAshesMod.SaveFile("rails"); }

        public static void EnsureLoaded()
        {
            string f = FilePath();
            if (f == null || f == loadedFor) return;
            loadedFor = f;
            All.Clear();
            Rails.Dirty();
            if (!File.Exists(f)) return;
            foreach (string line in File.ReadAllLines(f))
            {
                string[] a = line.Split(';');
                if (a.Length < 2) continue;
                string[] c = a[0].Split(',');
                int x, y, z;
                if (c.Length < 3 || !int.TryParse(c[0], out x) || !int.TryParse(c[1], out y) || !int.TryParse(c[2], out z)) continue;
                All[new Vector3i(x, y, z)] = a[1];
            }
        }

        public static void Parse(string v, out string name, out int rot)
        {
            int c = v.LastIndexOf(':');
            name = c > 0 ? v.Substring(0, c) : v;
            if (c <= 0 || !int.TryParse(v.Substring(c + 1), out rot)) rot = 0;
        }

        public static void Add(Vector3i p, BlockValue bv)
        {
            EnsureLoaded();
            string v = bv.Block.GetBlockName() + ":" + bv.rotation;
            string old;
            if (All.TryGetValue(p, out old) && old == v) return;
            All[p] = v;
            dirty = true;
            Rails.Dirty();
            Save();
        }

        public static void Remove(Vector3i p)
        {
            EnsureLoaded();
            if (!All.Remove(p)) return;
            dirty = true;
            Rails.Dirty();
            Save();
        }

        public static void Save()
        {
            string f = FilePath();
            if (f == null || !dirty) return;
            StringBuilder sb = new StringBuilder();
            foreach (KeyValuePair<Vector3i, string> kv in All)
                sb.Append(kv.Key.x).Append(',').Append(kv.Key.y).Append(',').Append(kv.Key.z).Append(';').Append(kv.Value).Append('\n');
            try { File.WriteAllText(f, sb.ToString()); dirty = false; }
            catch (System.Exception e) { Log.Warning(ForgedInAshesMod.LogPrefix + "rails: " + e.Message); }
        }
    }

    /// <summary>Track blocks: remember the piece by position.</summary>
    [UnityEngine.Scripting.Preserve]
    public class BlockFeRail : Block
    {
        public override void Init()
        {
            base.Init();
            TrainSim.Ensure();
        }

        public override void OnBlockAdded(WorldBase _world, Chunk _chunk, Vector3i _blockPos, BlockValue _blockValue, PlatformUserIdentifierAbs _addedByPlayer)
        {
            base.OnBlockAdded(_world, _chunk, _blockPos, _blockValue, _addedByPlayer);
            if (!_blockValue.ischild) RailStore.Add(_blockPos, _blockValue);
        }

        public override void OnBlockLoaded(WorldBase _world, Vector3i _blockPos, BlockValue _blockValue)
        {
            base.OnBlockLoaded(_world, _blockPos, _blockValue);
            if (!_blockValue.ischild) RailStore.Add(_blockPos, _blockValue);
        }

        public override void OnBlockRemoved(WorldBase _world, Chunk _chunk, Vector3i _blockPos, BlockValue _blockValue)
        {
            base.OnBlockRemoved(_world, _chunk, _blockPos, _blockValue);
            if (!_blockValue.ischild) RailStore.Remove(_blockPos);
        }
    }
}
