// F8.1: the Casting Table's model shows its state (host / single player, from FluidStore):
//   FeCastMetal  pivot at the bottom of the mold cavity; local Y scale = metal in the mold / one cast; hidden empty
//   FeCastReady  a stack of casts, shown while casts wait to leave
//
// C# 5 only.

using UnityEngine;

namespace FerroEngrenagem
{
    public class CasterVisual : MonoBehaviour
    {
        Vector3i pos;
        Transform metal, ready;
        Vector3 metalScale;
        float now, goal, next;

        public static void Attach(BlockEntityData ebcd, Vector3i pos)
        {
            if (ebcd == null || ebcd.transform == null || GameManager.IsDedicatedServer) return;
            CasterVisual v = ebcd.transform.GetComponent<CasterVisual>();
            if (v == null) v = ebcd.transform.gameObject.AddComponent<CasterVisual>();
            v.pos = pos;
            v.metal = Find(ebcd.transform, "FeCastMetal");
            v.ready = Find(ebcd.transform, "FeCastReady");
            if (v.metal != null) v.metalScale = v.metal.localScale;
            v.now = v.goal = 0f;
            v.next = 0f;
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

        void Update()
        {
            if (Time.time >= next)
            {
                next = Time.time + 0.5f;
                FluidStore.EnsureLoaded();
                FluidState s = FluidStore.Get(pos);
                float dose = 0f;
                foreach (Process p in Processes.For("feCaster"))
                    if (p.Kind == "cast" && p.Mold == s.Mold && p.FluidIn == s.Fluid) { dose = p.Liters; break; }
                goal = dose > 0f ? Mathf.Clamp01(s.Amount / dose) : 0f;
                if (ready != null && ready.gameObject.activeSelf != (s.Count > 0)) ready.gameObject.SetActive(s.Count > 0);
            }
            now = Mathf.MoveTowards(now, goal, Time.deltaTime);
            if (metal == null) return;
            bool show = now > 0.02f;
            if (metal.gameObject.activeSelf != show) metal.gameObject.SetActive(show);
            if (show) metal.localScale = new Vector3(metalScale.x, metalScale.y * now, metalScale.z);
        }
    }
}
