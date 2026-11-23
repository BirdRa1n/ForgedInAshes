// D7: while the local player holds an Electric Motor or a Torque Crank, outline the motor socket of every power-gated machine
// nearby (PowerGate.SocketPos), so it is clear where the motor has to go to "plug into" the machine.
//   green  = free, place the motor here
//   cyan   = a motor / torque crank / shaft is plugged in and drives the machine
//   orange = something is plugged in but faces or turns the wrong way
//   red    = something else is in the way
// D8: it also marks the CONNECTION POINTS of every torque block nearby (small plates on the faces that carry
// torque: the two ends of shafts / motors / engines, the six sides of gearboxes), so it is clear where the next
// piece has to go and whether it lines up (user, 2026-11-22: an indicator like the machines' socket):
//   green plate  = open end, attach the next piece here
//   cyan plate   = joined to the next piece (or driving the machine whose socket it is)
//   orange plate = the next piece is there but does not line up (or turns the machine the wrong way round)
// Shown while holding any torque block (motor, crank, engine, shaft, boxes...).
// Client-only visual (one GameObject, LineRenderers; nothing is saved or sent over the network).
//
// C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace FerroEngrenagem
{
    public class MotorSocketMarker : MonoBehaviour
    {
        const int RadiusXZ = 7;
        const int RadiusY = 3;
        const float ScanSeconds = 0.3f;
        const float Width = 0.035f;

        static GameObject host;
        static Material material;

        readonly List<LineRenderer> pool = new List<LineRenderer>();
        // boxes in world block space (lo / hi corners) and their colours
        readonly List<Vector3> boxLo = new List<Vector3>();
        readonly List<Vector3> boxHi = new List<Vector3>();
        readonly List<Color> colors = new List<Color>();

        static readonly Color Green = new Color(0.3f, 1f, 0.3f, 1f);
        static readonly Color Cyan = new Color(0.2f, 0.85f, 1f, 1f);
        static readonly Color Orange = new Color(1f, 0.6f, 0.1f, 1f);
        static readonly Color Red = new Color(1f, 0.25f, 0.2f, 1f);
        static readonly Vector3i[] Dirs =
        {
            new Vector3i(1, 0, 0), new Vector3i(-1, 0, 0), new Vector3i(0, 1, 0),
            new Vector3i(0, -1, 0), new Vector3i(0, 0, 1), new Vector3i(0, 0, -1)
        };
        float nextScan;

        public static void Ensure()
        {
            if (host != null || GameManager.IsDedicatedServer) return;
            host = new GameObject("FerroEngrenagem.MotorSocketMarker");
            Object.DontDestroyOnLoad(host);
            host.AddComponent<MotorSocketMarker>();
        }

        static bool HoldingMotor(EntityPlayerLocal player)
        {
            if (player.inventory == null) return false;
            ItemClassBlock icb = player.inventory.holdingItem as ItemClassBlock;
            return icb != null && PowerGate.IsDriver(icb.GetBlock());
        }

        void Update()
        {
            GameManager gm = GameManager.Instance;
            World world = gm == null ? null : gm.World;
            EntityPlayerLocal player = world == null ? null : world.GetPrimaryPlayer();
            if (player == null || player.IsDead() || !HoldingMotor(player))
            {
                boxLo.Clear();
                boxHi.Clear();
                colors.Clear();
                Draw();
                return;
            }
            if (Time.time >= nextScan)
            {
                nextScan = Time.time + ScanSeconds;
                Scan(world, player);
            }
            Draw();
        }

        void AddBox(Vector3 lo, Vector3 hi, Color col)
        {
            boxLo.Add(lo);
            boxHi.Add(hi);
            colors.Add(col);
        }

        void AddSocket(Vector3i s, Color col)
        {
            const float e = 0.02f;
            Vector3 a = s.ToVector3();
            AddBox(a + new Vector3(-e, -e, -e), a + new Vector3(1 + e, 1 + e, 1 + e), col);
        }

        // a thin plate on face d of the block at pos
        void AddFace(Vector3i pos, Vector3i d, Color col)
        {
            Vector3 c = pos.ToVector3() + new Vector3(0.5f, 0.5f, 0.5f) + d.ToVector3() * 0.52f;
            Vector3 half = new Vector3(d.x != 0 ? 0.03f : 0.22f, d.y != 0 ? 0.03f : 0.22f, d.z != 0 ? 0.03f : 0.22f);
            AddBox(c - half, c + half, col);
        }

        void Scan(World world, EntityPlayerLocal player)
        {
            boxLo.Clear();
            boxHi.Clear();
            colors.Clear();
            Vector3i c = World.worldToBlockPos(player.position);
            HashSet<Vector3i> seen = new HashSet<Vector3i>();
            for (int dx = -RadiusXZ; dx <= RadiusXZ; dx++)
                for (int dy = -RadiusY; dy <= RadiusY; dy++)
                    for (int dz = -RadiusXZ; dz <= RadiusXZ; dz++)
                    {
                        TileEntityWorkstation w =
                            world.GetTileEntity(new Vector3i(c.x + dx, c.y + dy, c.z + dz)) as TileEntityWorkstation;
                        if (w == null || !PowerGate.IsGated(w)) continue;
                        Vector3i parent = w.ToWorldPos();
                        if (!seen.Add(parent)) continue;
                        Vector3i s = PowerGate.SocketPos(world.GetBlock(parent), parent);
                        BlockValue there = world.GetBlock(s);
                        Color col;
                        if (PowerGate.IsDriver(there.Block))
                        {
                            // plugged: cyan when it really drives the machine, orange when it faces the wrong
                            // way or turns the wrong way round
                            TorqueNet net = Kinetic.Get(world, s);
                            bool ok = net != null && net.Machines.ContainsKey(parent);
                            col = ok ? new Color(0.2f, 0.85f, 1f, 1f) : new Color(1f, 0.6f, 0.1f, 1f);
                        }
                        else if (there.isair) col = Green;
                        else col = Red;
                        AddSocket(s, col);
                    }

            // connection points of the torque blocks nearby
            for (int dx = -RadiusXZ; dx <= RadiusXZ; dx++)
                for (int dy = -RadiusY; dy <= RadiusY; dy++)
                    for (int dz = -RadiusXZ; dz <= RadiusXZ; dz++)
                    {
                        Vector3i p = new Vector3i(c.x + dx, c.y + dy, c.z + dz);
                        BlockValue bv = world.GetBlock(p);
                        if (Kinetic.Kind(bv.Block) == KineticKind.None) continue;
                        TorqueNet net = null;
                        foreach (Vector3i d in Dirs)
                        {
                            if (!Kinetic.NodeHasFace(world, p, bv, d)) continue;
                            Vector3i n = new Vector3i(p.x + d.x, p.y + d.y, p.z + d.z);
                            BlockValue nb = world.GetBlock(n);
                            if (Kinetic.Kind(nb.Block) != KineticKind.None)
                            {
                                bool joined = Kinetic.NodeHasFace(world, n, nb, new Vector3i(-d.x, -d.y, -d.z));
                                AddFace(p, d, joined ? Cyan : Orange);
                                continue;
                            }
                            if (nb.isair) { AddFace(p, d, Green); continue; }
                            // a machine: only its socket counts
                            if (PowerGate.MinPower(nb.Block) <= 0) continue;
                            Vector3i parent = n;
                            if (nb.ischild && nb.Block.multiBlockPos != null)
                                parent = nb.Block.multiBlockPos.GetParentPos(n, nb);
                            if (PowerGate.SocketPos(world.GetBlock(parent), parent) != p) continue;
                            if (net == null) net = Kinetic.Get(world, p);
                            bool drives = net != null && net.Machines.ContainsKey(parent);
                            AddFace(p, d, drives ? Cyan : Orange);
                        }
                    }
        }

        void Draw()
        {
            while (pool.Count < boxLo.Count) pool.Add(NewLine());
            float pulse = 0.55f + 0.45f * Mathf.Abs(Mathf.Sin(Time.time * 3f));
            for (int i = 0; i < pool.Count; i++)
            {
                LineRenderer lr = pool[i];
                bool on = i < boxLo.Count;
                if (lr.gameObject.activeSelf != on) lr.gameObject.SetActive(on);
                if (!on) continue;
                // world (block) space -> Unity space (the game shifts its floating origin)
                lr.SetPositions(CubePath(boxLo[i] - Origin.position, boxHi[i] - Origin.position));
                Color col = colors[i];
                col.a = pulse;
                lr.startColor = col;
                lr.endColor = col;
            }
        }

        LineRenderer NewLine()
        {
            GameObject go = new GameObject("socket");
            go.transform.SetParent(transform, false);
            LineRenderer lr = go.AddComponent<LineRenderer>();
            lr.useWorldSpace = true;
            lr.positionCount = 16;
            lr.startWidth = Width;
            lr.endWidth = Width;
            lr.numCornerVertices = 2;
            lr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            lr.receiveShadows = false;
            if (material == null)
            {
                Shader sh = Shader.Find("Sprites/Default");
                if (sh == null) sh = Shader.Find("Unlit/Color");
                if (sh == null) sh = Shader.Find("Hidden/Internal-Colored");
                material = new Material(sh);
                Log.Out(FerroEngrenagemMod.LogPrefix + "socket marker shader: " + (sh == null ? "none" : sh.name));
            }
            lr.sharedMaterial = material;
            return lr;
        }

        // one continuous path over all 12 edges of the box
        static Vector3[] CubePath(Vector3 lo, Vector3 hi)
        {
            Vector3 p000 = lo, p100 = new Vector3(hi.x, lo.y, lo.z), p110 = new Vector3(hi.x, hi.y, lo.z),
                    p010 = new Vector3(lo.x, hi.y, lo.z), p001 = new Vector3(lo.x, lo.y, hi.z),
                    p101 = new Vector3(hi.x, lo.y, hi.z), p111 = hi, p011 = new Vector3(lo.x, hi.y, hi.z);
            return new Vector3[]
            {
                p000, p100, p110, p010, p000, p001, p101, p111, p011, p001,
                p011, p010, p110, p111, p101, p100
            };
        }
    }
}
