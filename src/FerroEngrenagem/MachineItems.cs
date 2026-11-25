// D13 (Create look: you see what a machine works on): every process machine shows, on top of it (or at the empty
// "FeItemAnchor" of its model), the ingredient it is working on, or the product waiting to leave. Parts of the model
// named "FeHead_*" press down and come back up while it works (in-line press, inserter, crimper: down onto the item
// under the station). The Deployer shows the block it holds at "FeItemAnchor" (or in front).
// Client side, near the player only. C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace FerroEngrenagem
{
    public class MachineItems : MonoBehaviour
    {
        Vector3i pos;
        Transform anchor;
        readonly List<Transform> heads = new List<Transform>();
        readonly List<Vector3> headRest = new List<Vector3>();
        BeltRenderer.Shown shown;
        string shownItem = "";
        float next, phase;
        bool working;

        public static void Attach(BlockEntityData ebcd, Vector3i pos, Block b)
        {
            if (ebcd == null || ebcd.transform == null || GameManager.IsDedicatedServer) return;
            if (!ProcessMachine.Is(b) && WorldMachines.Kind(b) != "deployer") return;
            MachineItems m = ebcd.transform.GetComponent<MachineItems>();
            if (m == null) m = ebcd.transform.gameObject.AddComponent<MachineItems>();
            m.pos = pos;
            m.anchor = Find(ebcd.transform, "FeItemAnchor");
            m.heads.Clear();
            m.headRest.Clear();
            Collect(ebcd.transform, m.heads);
            foreach (Transform h in m.heads) m.headRest.Add(h.localPosition);
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

        static void Collect(Transform t, List<Transform> l)
        {
            if (t.name.StartsWith("FeHead_", System.StringComparison.Ordinal)) l.Add(t);
            for (int i = 0; i < t.childCount; i++) Collect(t.GetChild(i), l);
        }

        string WhatToShow(World w, out bool work)
        {
            work = false;
            BlockValue bv = w.GetBlock(pos);
            if (WorldMachines.Kind(bv.Block) == "deployer")
            {
                ItemStack h = WorldMachines.Held(pos);
                return h == null ? "" : h.itemValue.ItemClass.GetItemName();
            }
            FluidState s = FluidStore.Get(pos);
            work = s.Steam > 0f && s.Note.Length == 0;
            if (ProcessMachine.IsInline(bv.Block)) return "";   // the item is on the belt under it, already drawn
            foreach (KeyValuePair<string, int> kv in ProcessMachine.Map(s.Stock)) return kv.Key;
            foreach (KeyValuePair<string, int> kv in ProcessMachine.Outs(s)) return kv.Key;
            return "";
        }

        void Update()
        {
            World w = GameManager.Instance == null ? null : GameManager.Instance.World;
            EntityPlayerLocal pl = w == null ? null : w.GetPrimaryPlayer();
            if (pl == null) return;
            bool near = (pos.ToVector3() - pl.position).sqrMagnitude < 40f * 40f;
            if (Time.time >= next)
            {
                next = Time.time + 0.4f;
                string item = near ? WhatToShow(w, out working) : "";
                if (item != shownItem)
                {
                    if (shown != null) { BeltRenderer.Kill(shown); shown = null; }
                    shownItem = item;
                    ItemValue iv = item.Length == 0 ? null : ItemClass.GetItem(item, false);
                    if (iv != null && !iv.IsEmpty())
                    {
                        shown = BeltRenderer.Make(new ItemStack(iv, 1));
                        if (shown.Go != null) shown.Go.transform.localScale = Vector3.one * 0.8f;
                    }
                }
            }
            if (shown != null && shown.Go != null)
            {
                Vector3 at = anchor != null ? anchor.position : transform.position + transform.up * 1.02f;
                shown.Go.transform.position = at + Vector3.up * (working ? 0.02f * Mathf.Sin(Time.time * 12f) : 0f);
                shown.Go.transform.rotation = Quaternion.Euler(0f, Time.time * (working ? 90f : 20f), 0f);
            }
            if (heads.Count > 0)
            {
                phase = working ? phase + Time.deltaTime * 1.6f : Mathf.MoveTowards(phase, Mathf.Round(phase), Time.deltaTime);
                float down = 0.5f - 0.5f * Mathf.Cos(phase * Mathf.PI * 2f);
                for (int i = 0; i < heads.Count; i++)
                    if (heads[i] != null) heads[i].localPosition = headRest[i] + Vector3.down * 0.18f * down;
            }
        }

        void OnDestroy()
        {
            if (shown != null) BeltRenderer.Kill(shown);
        }

        void OnDisable()
        {
            if (shown != null) { BeltRenderer.Kill(shown); shown = null; shownItem = ""; }
        }
    }
}
