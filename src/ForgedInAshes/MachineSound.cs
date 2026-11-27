// Machine sounds (user 2026-11-27: "go after sounds for the mod"). A running machine plays a looping sound at its
// block through the game's own audio system, so the game's volume options, distance roll-off and voice limits apply.
//
// Who says "running": KineticSpinner (the shaft of a torque block turns) and FxVisual (fire, work or steam of a
// fluid / process block). Both call MachineSound.Report every time they sample the state; the component keeps the
// loop on while any report said "on" in the last RunWindow seconds, and plays it only within HearRange of the
// player (the game stops looping positional sounds beyond the AudioSource's maxDistance on its own:
// Audio.Manager.StopDistantLoopingPositionalSounds, IL 3.4.0 b10, so we stop first and restart when near again).
//
// The loop is Audio.Manager.Play(blockPos, group) / Audio.Manager.Stop(blockPos, group), the same calls the Blade
// Trap uses for its running sound (BlockBladeTrap.OnBlockUnloaded, IL 3.4.0 b10). Groups are SoundDataNodes in
// Config/sounds.xml (our clips in the asset bundle, made by Art/feSounds/make_sounds.py) or vanilla groups by name
// (fire, the gas generator); nothing of the game is copied.
//
// Which sound a block plays: its property FeLoopSound (a group name, or "none"), else the table below by name prefix.
// Client-side only. C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace ForgedInAshes
{
    public class MachineSound : MonoBehaviour
    {
        const float RunWindow = 1.2f;      // a report keeps the sound on this long
        const float HearRange = 24f;       // metres; the loop starts / stops at this distance from the player
        const float CheckSeconds = 0.5f;

        // block name prefix -> sound group (first match wins; longer prefixes first where they overlap)
        static readonly string[,] Table =
        {
            { "feSteamTurbine", "fe_turbine_lp" },
            { "feSteamEngine", "fe_engine_lp" }, { "feCoalEngine", "fe_engine_lp" },
            { "feGasEngine", "generator_run" }, { "feGasMotor", "generator_run" },
            { "feElectricMotor", "fe_motor_lp" }, { "feDynamo", "fe_motor_lp" }, { "feCentrifuge", "fe_motor_lp" },
            { "feGearbox", "fe_gear_lp" }, { "feSpeedBox", "fe_gear_lp" }, { "feSpinInverter", "fe_gear_lp" },
            { "feCogwheel", "fe_gear_lp" }, { "feTorqueRegulator", "fe_gear_lp" }, { "feLathe", "fe_gear_lp" },
            { "feSpringCoiler", "fe_gear_lp" }, { "feWireDrawer", "fe_gear_lp" }, { "feCalender", "fe_gear_lp" },
            { "feSpinner", "fe_gear_lp" }, { "feChemMixer", "fe_gear_lp" }, { "feWasher", "fe_gear_lp" },
            { "feSteamDryer", "fe_gear_lp" }, { "feMechHarvester", "fe_gear_lp" }, { "feDeployer", "fe_gear_lp" },
            { "feCrusher", "fe_crusher_lp" }, { "feMill", "fe_crusher_lp" }, { "feGrinder", "fe_crusher_lp" },
            { "feMiningRig", "fe_drill_lp" }, { "feOilExtractor", "fe_pump_lp" },
            { "feMechDrill", "fe_drill_lp" }, { "feMechSaw", "fe_saw_lp" }, { "feSawmill", "fe_saw_lp" },
            { "feFan", "fe_fan_lp" },
            { "feMechPump", "fe_pump_lp" }, { "feElecPump", "fe_pump_lp" }, { "feCompressor", "fe_pump_lp" },
            { "feHosePulley", "fe_pump_lp" },
            { "fePress", "fe_press_lp" }, { "feInlinePress", "fe_press_lp" }, { "feVulcanizer", "fe_press_lp" },
            { "feBender", "fe_press_lp" }, { "feCrimper", "fe_press_lp" }, { "feAmmoPress", "fe_press_lp" },
            { "feJuicePress", "fe_press_lp" }, { "feMechPiston", "fe_press_lp" },
            { "feConveyorDuct", "none" }, { "feConveyorStand", "none" },
            { "feConveyor", "fe_belt_lp" }, { "feBelt", "fe_belt_lp" },
            { "feBoilerFirebox", "FireMediumLoop" }, { "feGasBurner", "FireSmallLoop" }, { "feFoundry", "FireMediumLoop" },
            { "feRetortKiln", "FireSmallLoop" }, { "feShaleRetort", "FireSmallLoop" }, { "feTemperFurnace", "FireSmallLoop" },
            { "feSteelConverter", "FireMediumLoop" }, { "feDistillTower", "FireSmallLoop" },
            { "feBoilerDrum", "fe_steam_hiss_lp" }, { "feValveRelief", "fe_steam_hiss_lp" },
            { "feBiodigester", "fe_bubble_lp" }, { "feHydroTower", "fe_bubble_lp" }, { "feFermenter", "fe_bubble_lp" },
            { "feInductionFurnace", "fe_buzz_lp" }, { "feWelder", "fe_buzz_lp" }, { "feReflowOven", "fe_buzz_lp" },
            { "feCracker", "fe_buzz_lp" }, { "fePolymerReactor", "fe_buzz_lp" }, { "feCasterElectric", "fe_buzz_lp" },
        };

        static readonly Dictionary<int, string> cache = new Dictionary<int, string>();

        Vector3i pos;
        string group;
        float lastOn = -100f, next;
        bool playing;

        /// <summary>The sound group a block plays while it runs, or null (silent).</summary>
        public static string GroupOf(Block b)
        {
            if (b == null) return null;
            string g;
            if (cache.TryGetValue(b.blockID, out g)) return g;
            g = null;
            if (b.Properties != null && b.Properties.Contains("FeLoopSound")) g = b.Properties.GetString("FeLoopSound");
            else
            {
                string n = b.GetBlockName();
                for (int i = 0; i < Table.GetLength(0); i++)
                    if (n.StartsWith(Table[i, 0], System.StringComparison.Ordinal)) { g = Table[i, 1]; break; }
            }
            if (g == "none" || g == "") g = null;
            cache[b.blockID] = g;
            return g;
        }

        /// <summary>Called by the visuals each time they sample a machine: on = it runs now.</summary>
        public static void Report(Transform t, Vector3i blockPos, Block b, bool on)
        {
            if (t == null || GameManager.IsDedicatedServer) return;
            string g = GroupOf(b);
            if (g == null) return;
            MachineSound m = t.GetComponent<MachineSound>();
            if (m == null) m = t.gameObject.AddComponent<MachineSound>();
            if (m.group != g || m.pos != blockPos)
            {
                m.StopNow();                      // a pooled model reused for another block
                m.group = g;
                m.pos = blockPos;
                m.lastOn = -100f;
            }
            if (on) m.lastOn = Time.time;
        }

        void Update()
        {
            if (Time.time < next || group == null) return;
            next = Time.time + CheckSeconds;
            bool want = Time.time - lastOn < RunWindow && Near();
            if (want == playing) return;
            if (want) Audio.Manager.Play(pos.ToVector3(), group, -1, false, 1f);
            else Audio.Manager.Stop(pos.ToVector3(), group);
            playing = want;
        }

        bool Near()
        {
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            EntityPlayerLocal p = world == null ? null : world.GetPrimaryPlayer();
            if (p == null) return false;
            return (p.position - pos.ToVector3()).sqrMagnitude < HearRange * HearRange;
        }

        void StopNow()
        {
            if (playing && group != null) Audio.Manager.Stop(pos.ToVector3(), group);
            playing = false;
        }

        void OnDisable()
        {
            StopNow();
        }
    }
}
