// D13 Display Panel: a sign that shows, in big digits on its front, what the block BEHIND it reads:
//   gauge -> bar or tank %;  tank -> litres;  counter belt -> count;  crate / vault -> items inside (only the item
//   chosen in its settings, or all);  process machine -> progress %;  torque block -> RPM and UT used / capacity.
// The text is a TextMesh made on the client (no model needed: it floats on the front face); the look text shows it
// too. C# 5 only.

using System.Globalization;
using UnityEngine;

namespace ForgedInAshes
{
    public static class Display
    {
        static string F1(float v) { return v.ToString("0.0", CultureInfo.InvariantCulture); }

        public static string Text(World world, Vector3i p, BlockValue bv)
        {
            Vector3i f = Fluids.Rot(bv, Vector3.forward);
            Vector3i c = new Vector3i(p.x - f.x, p.y - f.y, p.z - f.z);
            BlockValue cb = world.GetBlock(c);
            if (cb.isair) return "--";
            Vector3i par = Fluids.ParentOf(world, c, cb);
            FluidKind k = Fluids.Kind(cb.Block);
            if (k == FluidKind.Gauge)
            {
                FluidState s = FluidStore.Get(par);
                return Fluids.IsGas(s.Fluid) ? F1(s.Bar) + " bar" : (s.Steam > 0f ? Mathf.RoundToInt(100f * s.Amount / s.Steam) + " %" : "0 %");
            }
            if (k == FluidKind.Tank || k == FluidKind.GasTank)
            {
                float a, cap;
                int n;
                FluidControl.TankTotal(world, par, out a, out cap, out n);
                return Mathf.RoundToInt(a) + " L";
            }
            if (k == FluidKind.Processor)
            {
                FluidState s = FluidStore.Get(par);
                foreach (Process pr in ProcessMachine.Of(cb.Block))
                    if (pr.Id == s.Mold) return Mathf.RoundToInt(100f * Mathf.Clamp01(s.Steam / Mathf.Max(0.1f, pr.Time))) + " %";
                return "0 %";
            }
            if (Belt.Is(cb.Block) && Logistics.IsCounter(cb.Block)) return Logistics.CounterCount(c) + " / " + Logistics.CounterN(c);
            TileEntityComposite tc = world.GetTileEntity(par) as TileEntityComposite;
            TEFeatureStorage st = tc == null ? null : tc.GetFeature<TEFeatureStorage>();
            if (st != null)
            {
                string only = LogicStore.Field(p, "f");
                int total = 0;
                foreach (Vector3i v in ItemTransport.IsVault(cb.Block) ? ItemTransport.Cluster(world, par) : new System.Collections.Generic.List<Vector3i> { par })
                {
                    TileEntityComposite vc = world.GetTileEntity(v) as TileEntityComposite;
                    TEFeatureStorage vs = vc == null ? null : vc.GetFeature<TEFeatureStorage>();
                    if (vs == null || vs.ItemGrid == null) continue;
                    for (int i = 0; i < vs.ItemGrid.Length; i++)
                    {
                        ItemStack it = vs.ItemGrid[i];
                        if (it == null || it.IsEmpty()) continue;
                        if (only.Length > 0 && (it.itemValue.ItemClass == null || it.itemValue.ItemClass.GetItemName() != only)) continue;
                        total += it.count;
                    }
                }
                return total.ToString();
            }
            TorqueNet net = Kinetic.Get(world, c);
            if (net != null) return Mathf.RoundToInt(net.RpmAt(Kinetic.NodeOf(world, c))) + " RPM  " + net.Usage + "/" + net.Capacity;
            return "--";
        }
    }

    public class DisplayVisual : MonoBehaviour
    {
        Vector3i pos;
        TextMesh text;
        float next;

        public static void Attach(BlockEntityData ebcd, Vector3i pos)
        {
            if (ebcd == null || ebcd.transform == null || GameManager.IsDedicatedServer) return;
            DisplayVisual v = ebcd.transform.GetComponent<DisplayVisual>();
            if (v == null) v = ebcd.transform.gameObject.AddComponent<DisplayVisual>();
            v.pos = pos;
            v.Make();
        }

        void Make()
        {
            if (text != null) return;
            try
            {
                GameObject go = new GameObject("FeDisplayText");
                go.transform.SetParent(transform, false);
                // the front face (model local +Z) a little out, readable from the front
                go.transform.localPosition = new Vector3(0f, 0.5f, 0.52f);
                go.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);
                text = go.AddComponent<TextMesh>();
                Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
                if (font == null) font = Resources.GetBuiltinResource<Font>("Arial.ttf");
                text.font = font;
                text.fontSize = 64;
                text.characterSize = 0.012f;
                text.anchor = TextAnchor.MiddleCenter;
                text.alignment = TextAlignment.Center;
                text.color = new Color(1f, 0.65f, 0.2f);
                MeshRenderer r = go.GetComponent<MeshRenderer>();
                if (r != null && font != null) r.material = font.material;
            }
            catch (System.Exception e)
            {
                Log.Warning(ForgedInAshesMod.LogPrefix + "display text: " + e.Message);
            }
        }

        void Update()
        {
            if (text == null || Time.time < next) return;
            next = Time.time + 0.5f;
            World w = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (w == null) return;
            try { text.text = Display.Text(w, pos, w.GetBlock(pos)); }
            catch (System.Exception) { text.text = "--"; }
        }
    }

    [UnityEngine.Scripting.Preserve]
    public class BlockFeDisplay : Block
    {
        public override void OnBlockEntityTransformAfterActivated(WorldBase _world, Vector3i _blockPos, BlockValue _blockValue, BlockEntityData _ebcd)
        {
            base.OnBlockEntityTransformAfterActivated(_world, _blockPos, _blockValue, _ebcd);
            DisplayVisual.Attach(_ebcd, _blockPos);
        }

        public override bool HasBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            return true;
        }

        public override BlockActivationCommand[] GetBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            return new BlockActivationCommand[]
            {
                new BlockActivationCommand(FeUi.ConfigCommand, "tool", true, false, null),
                new BlockActivationCommand("take", "hand", Pickup.CanBuildHere(_world, _blockPos), false, null)
            };
        }

        public override bool OnBlockActivated(string _commandName, WorldBase _world, Vector3i _blockPos, BlockValue _blockValue, EntityPlayerLocal _player)
        {
            World w = _world as World;
            if (w != null && FeUi.HandleCommand(_commandName, w, _blockPos, _blockValue, _player)) return true;
            if (_commandName != "take") return false;
            takeItemWithTimer(_blockPos, _blockValue, _player, 1f);
            return true;
        }

        public override string GetActivationText(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            World w = _world as World;
            if (w == null) return "";
            return KineticLookController.Escape(GetLocalizedBlockName() + ": " + Display.Text(w, _blockPos, _blockValue) + "\n"
                   + Kinetic.Text("feDisplayInfo", "Shows what the block behind it reads (gauge, tank, counter, crate, machine, shaft)"))
                   + "\n" + Kinetic.Text("feHintConfig", "{0} settings - hold {0}: take");
        }
    }
}
