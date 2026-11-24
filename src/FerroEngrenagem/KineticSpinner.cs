// D8: spin animation contract for 3D models of the torque network (user, 2026-11-22: "the items must receive the
// events the 3D asset needs to animate the spin, including speed").
//
// Attached to the model of every ModelEntity torque block (BlockFeKinetic, Electric Motor via BlockPowered) and of
// every power-gated machine (BlockWorkstation). Every 0.25 s it reads the network (Kinetic.Get) and every frame:
//
// 1. Turns child transforms whose name starts with "FeSpin" around THEIR OWN local +Z axis (Unity; = Blender +Y
//    after the usual FBX export, like the crank's rotor), at the node's RPM (1 RPM = 6 deg/s), in the real
//    direction of the network (right-hand rule against the part's +Z). Name tokens, separated by '_':
//      FeSpin            the node's speed and direction
//      FeSpinIn/FeSpinOut  speed box: input / output side (output x ratio); inverter: the output side turns the
//                        other way; for other blocks both are the node's speed
//      ..._Rev           reversed (e.g. the second gear of a pair)
//      ..._x2, _x0.5     speed multiplier (gear ratios inside the model)
//    Example: "FeSpinOut_x0.5_Rev".
// 2. Sets Animator parameters when the model has an Animator with them (all optional):
//      float FeRpm        signed RPM against the block's own +Z (negative = turning the other way)
//      float FeSpeed      |RPM| / 32 (1 = base speed; use it as a state speed multiplier)
//      bool  FeRunning    the network turns (source, no overload, not locked)
//      bool  FeOverloaded, FeLocked, FeWrongSpin (machine fed the wrong way round)
// Speed changes are smoothed (spin up / coast down), like a real flywheel.
// Placeholders (vanilla prefabs without FeSpin parts) can set <property name="FeSpinWhole" value="true"/> to turn
// the model's first child instead, so the events can be seen in game.
//
// Client-side visual only; on a pure multiplayer client the network is computed from the synced blocks.
//
// C# 5 only.

using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace FerroEngrenagem
{
    public class KineticSpinner : MonoBehaviour
    {
        const float QuerySeconds = 0.25f;
        const float DegPerRpmSecond = 6f;

        class Part
        {
            public Transform T;
            public float Mult = 1f;
            public bool Rev;
            public int Side;   // 0 node, 1 in, 2 out
        }

        static readonly int HRpm = Animator.StringToHash("FeRpm");
        static readonly int HSpeed = Animator.StringToHash("FeSpeed");
        static readonly int HRunning = Animator.StringToHash("FeRunning");
        static readonly int HOverloaded = Animator.StringToHash("FeOverloaded");
        static readonly int HLocked = Animator.StringToHash("FeLocked");
        static readonly int HWrong = Animator.StringToHash("FeWrongSpin");

        Vector3i pos;
        bool machine;
        readonly List<Part> parts = new List<Part>();
        Animator anim;
        readonly HashSet<int> animParams = new HashSet<int>();

        float targetRpm, rpm, ratio = 1f, nextQuery, angle;

        // FePiston* parts: slide back and forth along their own local Z with the spin (two-cylinder engine)
        class Piston
        {
            public Transform T;
            public Vector3 Base;
            public float Phase;
            public float Amp = 0.12f;
        }
        readonly List<Piston> pistons = new List<Piston>();

        // Slider-crank (Steam Engine HD, 2026-11-24): FeCrankPin_<n> (empty at the crank pin, built pose) rides on the
        // crank (the FeSpin part named *Flywheel* / *Crank*); FeCrosshead_<n> slides on the line from the crank axis
        // through its built position; FeConrod_<n> (pivot at the crosshead pin) turns to point at the pin. Solved
        // from the crank's real angle every frame, in the model root's space (floating origin safe). Captured once,
        // from the pristine model (the component stays on the pooled instance).
        class Linkage
        {
            public Transform Cross, Rod;
            public Vector3 PinInCrank, C, D, Cross0, Dir0;
            public Quaternion Rod0;
            public float L;
        }
        readonly List<Linkage> links = new List<Linkage>();
        Transform crank;
        bool linksCaptured, linksSolved;
        Vector3 omega = Vector3.forward;
        bool running, overloaded, locked, wrong, inverter;
        string lastLog;

        public static void Attach(BlockEntityData ebcd, Vector3i pos, Block block)
        {
            Setup(ebcd, pos, block, false);
        }

        public static void AttachMachine(BlockEntityData ebcd, Vector3i pos, Block block)
        {
            Setup(ebcd, pos, block, true);
        }

        static void Setup(BlockEntityData ebcd, Vector3i pos, Block block, bool machine)
        {
            if (ebcd == null || ebcd.transform == null || GameManager.IsDedicatedServer) return;
            KineticSpinner s = ebcd.transform.GetComponent<KineticSpinner>();
            if (s == null) s = ebcd.transform.gameObject.AddComponent<KineticSpinner>();
            s.Init(pos, block, machine);
        }

        // Model instances are pooled and reused: reset everything on every activation.
        void Init(Vector3i blockPos, Block block, bool isMachine)
        {
            pos = blockPos;
            machine = isMachine;
            rpm = targetRpm = 0f;
            nextQuery = 0f;
            lastLog = null;
            inverter = Kinetic.Kind(block) == KineticKind.Inverter;
            parts.Clear();
            pistons.Clear();
            angle = 0f;
            linkParts.Clear();
            Collect(transform);
            CaptureLinks();
            linksSolved = false;
            if (parts.Count == 0 && block.Properties != null && block.Properties.Contains("FeSpinWhole") &&
                block.Properties.GetBool("FeSpinWhole") && transform.childCount > 0)
            {
                Part p = new Part();
                p.T = transform.GetChild(0);
                parts.Add(p);
            }
            anim = GetComponentInChildren<Animator>();
            animParams.Clear();
            if (anim != null)
                foreach (AnimatorControllerParameter ap in anim.parameters) animParams.Add(ap.nameHash);
        }

        void Collect(Transform t)
        {
            for (int i = 0; i < t.childCount; i++)
            {
                Transform c = t.GetChild(i);
                // case-sensitive: the Spin Inverter model itself is named "feSpinInverter" and must not spin as a whole
                if (c.name.StartsWith("FeSpin", System.StringComparison.Ordinal)) parts.Add(Parse(c));
                else if (c.name.StartsWith("FeCrosshead_", System.StringComparison.Ordinal) ||
                         c.name.StartsWith("FeConrod_", System.StringComparison.Ordinal) ||
                         c.name.StartsWith("FeCrankPin_", System.StringComparison.Ordinal))
                    linkParts[c.name] = c;
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

        readonly Dictionary<string, Transform> linkParts = new Dictionary<string, Transform>();

        /// <summary>Pairs FeCrosshead_n / FeConrod_n / FeCrankPin_n with the crank. Only on the pristine model.</summary>
        void CaptureLinks()
        {
            if (linksCaptured) return;
            linksCaptured = true;
            links.Clear();
            crank = null;
            foreach (Part p in parts)
                if (p.T != null && (p.T.name.Contains("Flywheel") || p.T.name.Contains("Crank"))) { crank = p.T; break; }
            if (crank == null) return;
            Vector3 o = transform.InverseTransformPoint(crank.position);
            Vector3 a = transform.InverseTransformDirection(crank.forward).normalized;   // spin axis = local +Z
            for (int n = 1; n <= 8; n++)
            {
                Transform cross, rod, pin;
                if (!linkParts.TryGetValue("FeCrosshead_" + n, out cross) | !linkParts.TryGetValue("FeConrod_" + n, out rod) |
                    !linkParts.TryGetValue("FeCrankPin_" + n, out pin)) continue;
                Linkage l = new Linkage();
                l.Cross = cross;
                l.Rod = rod;
                l.PinInCrank = crank.InverseTransformPoint(pin.position);
                l.Cross0 = transform.InverseTransformPoint(cross.position);
                l.C = o + a * Vector3.Dot(l.Cross0 - o, a);
                l.D = (l.Cross0 - l.C).normalized;
                Vector3 p0 = transform.InverseTransformPoint(pin.position);
                l.L = (l.Cross0 - p0).magnitude;
                l.Dir0 = (p0 - l.Cross0).normalized;
                l.Rod0 = Quaternion.Inverse(transform.rotation) * rod.rotation;
                links.Add(l);
            }
        }

        void SolveLinks()
        {
            if (crank == null) return;
            foreach (Linkage l in links)
            {
                if (l.Cross == null || l.Rod == null) continue;
                Vector3 pin = transform.InverseTransformPoint(crank.TransformPoint(l.PinInCrank));
                Vector3 v = pin - l.C;
                float along = Vector3.Dot(v, l.D);
                float perp = (v - l.D * along).magnitude;
                float s = along + Mathf.Sqrt(Mathf.Max(0f, l.L * l.L - perp * perp));
                Vector3 x = l.C + l.D * s;
                l.Cross.position = transform.TransformPoint(x);
                l.Rod.position = l.Cross.position;
                Vector3 dir = (pin - x).normalized;
                l.Rod.rotation = transform.rotation * (Quaternion.FromToRotation(l.Dir0, dir) * l.Rod0);
            }
        }

        static Part Parse(Transform t)
        {
            Part p = new Part();
            p.T = t;
            string[] tok = t.name.Split('_');
            string head = tok[0].ToLowerInvariant();
            if (head == "fespinin") p.Side = 1;
            else if (head == "fespinout") p.Side = 2;
            for (int i = 1; i < tok.Length; i++)
            {
                string k = tok[i].ToLowerInvariant();
                if (k == "rev") p.Rev = true;
                else if (k.Length > 1 && k[0] == 'x')
                {
                    float m;
                    if (float.TryParse(k.Substring(1), System.Globalization.NumberStyles.Float,
                                       System.Globalization.CultureInfo.InvariantCulture, out m)) p.Mult = m;
                }
            }
            return p;
        }

        void Query()
        {
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (world == null) return;
            targetRpm = 0f;
            running = overloaded = locked = wrong = false;
            ratio = 1f;
            Vector3i node = pos;
            TorqueNet net;
            if (machine)
            {
                node = PowerGate.SocketPos(world.GetBlock(pos), pos);
                net = Kinetic.Get(world, node);
                if (net == null) return;
                wrong = net.WrongSpin.ContainsKey(pos);
                running = net.Running && net.Machines.ContainsKey(pos);
                if (running) targetRpm = net.MachineSpeed(pos) * Kinetic.BaseRpm;
            }
            else
            {
                node = Kinetic.NodeOf(world, pos);
                net = Kinetic.Get(world, node);
                if (net == null) return;
                running = net.Running;
                if (running) targetRpm = Kinetic.IsMultiEngine(world.GetBlock(pos).Block) || net.Factor.ContainsKey(node)
                    ? net.RpmAt(node) : 0f;
                BlockValue bv = world.GetBlock(pos);
                if (Kinetic.Kind(bv.Block) == KineticKind.SpeedBox) ratio = BlockFeKinetic.Ratio(bv);
            }
            overloaded = net.Overloaded;
            locked = net.Locked;
            Vector3i o;
            if (net.Omega.TryGetValue(node, out o)) omega = o.ToVector3();

            string key = running + "|" + Mathf.RoundToInt(targetRpm) + "|" + omega + "|" + overloaded + "|" + locked + "|" + wrong;
            if (key != lastLog && FerroEngrenagemMod.Verbose)
            {
                lastLog = key;
                Log.Out(FerroEngrenagemMod.LogPrefix + "spin " + (machine ? "machine " : "") +
                        world.GetBlock(pos).Block.GetBlockName() + " at " + pos + ": rpm=" + Mathf.RoundToInt(targetRpm) +
                        " omega=" + o + " running=" + running + (overloaded ? " overloaded" : "") +
                        (locked ? " locked" : "") + (wrong ? " wrongSpin" : "") + " parts=" + parts.Count +
                        " animator=" + (anim != null));
            }
        }

        void Update()
        {
            if (Time.time >= nextQuery)
            {
                nextQuery = Time.time + QuerySeconds;
                Query();
            }
            float accel = Mathf.Max(40f, Mathf.Abs(targetRpm) * 1.5f);   // RPM per second
            rpm = Mathf.MoveTowards(rpm, targetRpm, accel * Time.deltaTime);

            if (rpm > 0.01f)
            {
                for (int i = 0; i < parts.Count; i++)
                {
                    Part p = parts[i];
                    if (p.T == null) continue;
                    Vector3 w = omega;
                    float r = rpm * p.Mult;
                    if (p.Side == 2)
                    {
                        r *= ratio;
                        if (inverter) w = -w;
                    }
                    float dir = Vector3.Dot(w, p.T.forward) < 0f ? -1f : 1f;
                    if (p.Rev) dir = -dir;
                    p.T.Rotate(Vector3.forward, dir * r * DegPerRpmSecond * Time.deltaTime, Space.Self);
                }
            }

            if (links.Count > 0 && (rpm > 0.01f || !linksSolved)) { SolveLinks(); linksSolved = true; }

            if (pistons.Count > 0)
            {
                angle += rpm * DegPerRpmSecond * Time.deltaTime * Mathf.Deg2Rad;
                foreach (Piston p in pistons)
                {
                    if (p.T == null) continue;
                    float off = p.Amp * Mathf.Sin(angle + p.Phase);
                    p.T.localPosition = p.Base + p.T.localRotation * Vector3.forward * off;
                }
            }

            if (anim != null && animParams.Count > 0)
            {
                float signed = (Vector3.Dot(omega, transform.forward) < 0f ? -1f : 1f) * rpm;
                SetF(HRpm, signed);
                SetF(HSpeed, rpm / Kinetic.BaseRpm);
                SetB(HRunning, running);
                SetB(HOverloaded, overloaded);
                SetB(HLocked, locked);
                SetB(HWrong, wrong);
            }
        }

        void SetF(int h, float v)
        {
            if (animParams.Contains(h)) anim.SetFloat(h, v);
        }

        void SetB(int h, bool v)
        {
            if (animParams.Contains(h)) anim.SetBool(h, v);
        }
    }

    // Electric Motor (vanilla Class="Powered" + FeMotor): attach the spinner to its model.
    [HarmonyPatch(typeof(BlockPowered), "OnBlockEntityTransformAfterActivated")]
    public static class Patch_BlockPowered_KineticSpinner
    {
        public static void Postfix(BlockPowered __instance, Vector3i _blockPos, BlockEntityData _ebcd)
        {
            if (PowerGate.IsMotor(__instance)) KineticSpinner.Attach(_ebcd, _blockPos, __instance);
        }
    }

    // Power-gated machines: their models get FeRpm / FeRunning ... and FeSpin parts too.
    [HarmonyPatch(typeof(BlockWorkstation), "OnBlockEntityTransformBeforeActivated")]
    public static class Patch_BlockWorkstation_KineticSpinner
    {
        public static void Postfix(BlockWorkstation __instance, Vector3i _blockPos, BlockEntityData _ebcd)
        {
            if (PowerGate.MinPower(__instance) > 0) KineticSpinner.AttachMachine(_ebcd, _blockPos, __instance);
        }
    }
}
