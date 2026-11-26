// Conveyor Stand (feConveyorStand, user 2026-11-24: "o suporte de esteira precisa tambem da forma com curva").
// One block high trestle (Art/feConveyor/build_feConveyor.py, "feConveyorStand") whose shape follows the belt on
// top of it: FeStand_Straight (straight belt, ramp, or nothing above), FeStand_Curve_L/R, FeStand_Junction, and
// FeStand_Duct (deck + cradle lips, with the straight one) under a Conveyor Duct. The parts are built in the belt's
// frame and turned to the belt's rotation, so the stand can be placed facing any way.
// No logic: client-side visual only (and the placement preview, BeltPreviewPatch in Belt.cs).
//
// C# 5 only.

using UnityEngine;

namespace ForgedInAshes
{
    [UnityEngine.Scripting.Preserve]
    public class BlockFeConveyorStand : Block
    {
        public override void OnBlockEntityTransformAfterActivated(WorldBase _world, Vector3i _blockPos,
                                                                  BlockValue _blockValue, BlockEntityData _ebcd)
        {
            base.OnBlockEntityTransformAfterActivated(_world, _blockPos, _blockValue, _ebcd);
            if (_ebcd == null || _ebcd.transform == null || GameManager.IsDedicatedServer) return;
            StandShape s = _ebcd.transform.GetComponent<StandShape>();
            if (s == null) s = _ebcd.transform.gameObject.AddComponent<StandShape>();
            s.Init(_blockPos, StandParts.Of(_ebcd.transform));
        }
    }

    public class StandParts
    {
        class Part
        {
            public Transform T;
            public Vector3 Pos;
            public Quaternion Rot;
        }

        Part straight, curveL, curveR, junction, duct;

        static Part P(Transform root, string name)
        {
            Transform t = Find(root, name);
            if (t == null) return null;
            Part p = new Part();
            p.T = t;
            p.Pos = t.localPosition;
            p.Rot = t.localRotation;
            return p;
        }

        public static StandParts Of(Transform t)
        {
            StandParts s = new StandParts();
            s.straight = P(t, "FeStand_Straight");
            s.curveL = P(t, "FeStand_Curve_L");
            s.curveR = P(t, "FeStand_Curve_R");
            s.junction = P(t, "FeStand_Junction");
            s.duct = P(t, "FeStand_Duct");
            return s;
        }

        /// <summary>Shape for the block at `above` (the cell over the stand); standBv gives the stand's rotation.</summary>
        public void Apply(World world, Vector3i above, BlockValue standBv)
        {
            BlockValue bv = world.GetBlock(above);
            int shape = 0;                                   // 0 straight, 1 curve L, 2 curve R, 3 junction, 4 duct
            Quaternion turn = Quaternion.identity;
            if (Belt.Is(bv.Block))
            {
                if (Belt.IsClosed(bv.Block)) shape = 4;
                else if (!Belt.IsRamp(bv.Block))
                {
                    BeltLook k = BeltLook.Evaluate(world, above, bv);
                    shape = k.Mode;
                }
                Quaternion standRot = standBv.Block.shape.GetRotation(standBv);
                Quaternion beltRot = bv.Block.shape.GetRotation(bv);
                turn = Quaternion.Inverse(standRot) * beltRot;
            }
            Set(straight, shape == 0 || shape == 4, turn);
            Set(curveL, shape == 1, turn);
            Set(curveR, shape == 2, turn);
            Set(junction, shape == 3, turn);
            Set(duct, shape == 4, turn);
        }

        static void Set(Part p, bool on, Quaternion turn)
        {
            if (p == null) return;
            if (p.T.gameObject.activeSelf != on) p.T.gameObject.SetActive(on);
            if (!on) return;
            // turn about the vertical axis through the block's floor centre (the model's origin)
            p.T.localPosition = turn * p.Pos;
            p.T.localRotation = turn * p.Rot;
        }

        static Transform Find(Transform t, string n)
        {
            if (t.name == n || t.name.StartsWith(n + ".", System.StringComparison.Ordinal)) return t;
            for (int i = 0; i < t.childCount; i++)
            {
                Transform r = Find(t.GetChild(i), n);
                if (r != null) return r;
            }
            return null;
        }
    }

    public class StandShape : MonoBehaviour
    {
        Vector3i pos;
        StandParts parts;
        float next;

        public void Init(Vector3i _pos, StandParts _parts)
        {
            pos = _pos;
            parts = _parts;
            next = 0f;
        }

        void Update()
        {
            if (Time.time < next || parts == null) return;
            next = Time.time + 0.5f;
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (world == null) return;
            BlockValue me = world.GetBlock(pos);
            if (!(me.Block is BlockFeConveyorStand)) return;
            parts.Apply(world, new Vector3i(pos.x, pos.y + 1, pos.z), me);
        }
    }
}
