// D7: while the local player holds an Electric Motor or a Torque Crank, outline the motor socket of every power-gated machine
// nearby (PowerGate.SocketPos), so it is clear where the motor has to go to "plug into" the machine.
//   green  = free, place the motor here
//   cyan   = a motor / torque crank is already plugged in
//   red    = something else is in the way
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
        readonly List<Vector3i> sockets = new List<Vector3i>();
        readonly List<Color> colors = new List<Color>();
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
                sockets.Clear();
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

        void Scan(World world, EntityPlayerLocal player)
        {
            sockets.Clear();
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
                        if (PowerGate.IsDriver(there.Block)) col = new Color(0.2f, 0.85f, 1f, 1f);
                        else if (there.isair) col = new Color(0.3f, 1f, 0.3f, 1f);
                        else col = new Color(1f, 0.25f, 0.2f, 1f);
                        sockets.Add(s);
                        colors.Add(col);
                    }
        }

        void Draw()
        {
            while (pool.Count < sockets.Count) pool.Add(NewLine());
            float pulse = 0.55f + 0.45f * Mathf.Abs(Mathf.Sin(Time.time * 3f));
            for (int i = 0; i < pool.Count; i++)
            {
                LineRenderer lr = pool[i];
                bool on = i < sockets.Count;
                if (lr.gameObject.activeSelf != on) lr.gameObject.SetActive(on);
                if (!on) continue;
                // world (block) space -> Unity space (the game shifts its floating origin)
                Vector3 a = sockets[i].ToVector3() - Origin.position;
                const float e = 0.02f;
                Vector3 lo = a + new Vector3(-e, -e, -e), hi = a + new Vector3(1 + e, 1 + e, 1 + e);
                lr.SetPositions(CubePath(lo, hi));
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
