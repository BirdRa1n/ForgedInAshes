// E01 Crank (feCrank): hold the Activate key (E) while looking at it to turn it.
// Replaces the F2-T04 "hit it" mechanic (buffs.xml + gameevents.xml), at the user's request.
//
// How the game handles interaction (IL of 3.4.0 b10):
//  - PlayerMoveController.HandleInteraction -> TryHandleBlock: if Block.HasBlockActivationCommands is true,
//    pressing Activate opens the radial (XUiC_Radial) and the "[E] ..." prompt comes from GetActivationText.
//    There is no vanilla "hold to keep doing" for blocks (XUiC_Timer is a one-shot bar, cancelled by pressing E).
//  - So: standing, the crank reports NO activation commands (E opens nothing) and CrankController polls
//    PlayerActionsLocal/PlayerActionsPermanent.Activate.IsPressed itself and writes its own prompt
//    (XUiC_InteractionPrompt.SetText). Crouching, it reports the vanilla commands, so crouch + E opens the
//    normal radial (Take = pick it up).
//  - XML: Class="FerroEngrenagem.FeCrank, FerroEngrenagem". ReflectionHelpers.GetTypeWithPrefix inserts "Block"
//    after the last '.', so the game creates FerroEngrenagem.BlockFeCrank. [Preserve] avoids its warning.
//  - The block's model (Art/feCrank via Resources/ferroengrenagem.unity3d) has the children feCrank_Rotor and
//    feCrank_DynamoPulley; CrankSpinner turns them around their local Z (Blender Y after the FBX/Unity
//    conversion). The spin is only seen by the player who cranks (no network sync yet).
//
// D7 step 2 (watts): the crank is a GENERATOR now (BlockGenerator -> TileEntityPowerSource + PowerGenerator).
//  - Cranking adds fuel to its PowerGenerator (FeCrankFuelPerSecond per second) and turns it on; the vanilla
//    generator converts 1 fuel into OutputPerFuel energy per power tick (PowerManager ticks every 0.16 s) and
//    sends up to MaxOutput watts through the wires. MaxOutput = OutputPerStack x Flywheels in the slots
//    (SlotItem=feFlywheel): no flywheel, no watts.
//  - Crouch + E opens the vanilla generator radial (open: insert flywheels; turn on/off; take).
//  - The vanilla "Refuel" button would pour gas cans into it: blocked in PowerPatches.cs.
//  - Single player / host only for now: on a pure multiplayer client the PowerItem lives on the server
//    (needs a net package; F2-T06).
//
// Tunables (blocks.xml, optional): FeCrankFuelPerSecond, FeCrankStaminaPerSecond, FeCrankMinStamina,
// FeCrankSpinDegPerSecond. Generator values: SlotItem, OutputPerStack, MaxPower, MaxFuel, OutputPerFuel.
//
// C# 5 only (built with the .NET Framework 4 csc.exe, see tools/build.ps1).

using System.Collections.Generic;
using UnityEngine;

namespace FerroEngrenagem
{
    [UnityEngine.Scripting.Preserve]
    public class BlockFeCrank : BlockGenerator
    {
        public float FuelPerSecond = 12.5f;       // generator fuel added per second of cranking
        public int BaseOutput = 30;               // watts without any Flywheel (PowerPatches.cs)
        public float StaminaPerSecond = 10f;      // drain while turning (regeneration still runs)
        public float MinStamina = 5f;             // below this the player is too tired to turn
        public float SpinDegPerSecond = 300f;     // rotor speed while turning

        public override void Init()
        {
            base.Init();
            ReadFloat("FeCrankFuelPerSecond", ref FuelPerSecond);
            if (Properties != null && Properties.Contains("FeCrankBaseOutput")) BaseOutput = Properties.GetInt("FeCrankBaseOutput");
            ReadFloat("FeCrankStaminaPerSecond", ref StaminaPerSecond);
            ReadFloat("FeCrankMinStamina", ref MinStamina);
            ReadFloat("FeCrankSpinDegPerSecond", ref SpinDegPerSecond);
            if (FuelPerSecond < 0.1f) FuelPerSecond = 0.1f;
            CrankController.Ensure();
            MotorSocketMarker.Ensure();
            Log.Out(FerroEngrenagemMod.LogPrefix + "BlockFeCrank (generator) ready for '" + GetBlockName() + "' ("
                    + FuelPerSecond + " fuel/s of cranking)");
        }

        // Rare-case diagnostics (e.g. a crank without a generator power item), throttled.
        static float nextDiag;
        internal static void Diag(string msg)
        {
            if (!FerroEngrenagemMod.Verbose || Time.time < nextDiag) return;
            nextDiag = Time.time + 2f;
            Log.Out(FerroEngrenagemMod.LogPrefix + "crank: " + msg);
        }

        void ReadFloat(string name, ref float value)
        {
            if (Properties != null && Properties.Contains(name)) value = Properties.GetFloat(name);
        }

        // Standing: no commands, so Activate does not open the radial (CrankController handles "hold E").
        // Crouching: vanilla commands, so crouch + E opens the radial with Take.
        public override bool HasBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos,
                                                        EntityAlive _entityFocusing)
        {
            bool crouch = _entityFocusing != null && _entityFocusing.IsCrouching;
            return crouch && base.HasBlockActivationCommands(_world, _blockValue, _blockPos, _entityFocusing);
        }

        // Crouch radial (user, 2026-11-22): only "open" (Flywheel slots) and "take". No on/off: cranking turns it
        // on and the generator turns itself off when the cranked fuel runs out.
        // Vanilla BlockPowerSource enables "take" only inside the player's OWN land claim (IsMyLandProtectedBlock,
        // IL 3.4.0 b10) and with TakeDelay > 0; the crank can be taken anywhere the player could build
        // (CanPlaceBlockAt: not inside someone else's claim).
        public override BlockActivationCommand[] GetBlockActivationCommands(WorldBase _world, BlockValue _blockValue,
                                                                           Vector3i _blockPos,
                                                                           EntityAlive _entityFocusing)
        {
            BlockActivationCommand[] vanilla = base.GetBlockActivationCommands(_world, _blockValue, _blockPos,
                                                                              _entityFocusing);
            if (vanilla == null || vanilla.Length < 3) return vanilla;   // no tile entity: Empty
            TileEntityPowerSource te = _world.GetTileEntity(_blockPos) as TileEntityPowerSource;
            bool canBuild = _world.CanPlaceBlockAt(_blockPos, _world.GetGameManager().GetPersistentLocalPlayer(), false);
            BlockActivationCommand open = vanilla[0];
            BlockActivationCommand take = vanilla[2];
            take.enabled = te != null && te.IsPlayerPlaced && canBuild && TakeDelay > 0f;
            return new BlockActivationCommand[] { open, take };
        }

        public override void OnBlockEntityTransformAfterActivated(WorldBase _world, Vector3i _blockPos,
                                                                  BlockValue _blockValue, BlockEntityData _ebcd)
        {
            base.OnBlockEntityTransformAfterActivated(_world, _blockPos, _blockValue, _ebcd);
            if (_ebcd == null || _ebcd.transform == null) return;
            CrankSpinner spinner = _ebcd.transform.GetComponent<CrankSpinner>();
            if (spinner == null) spinner = _ebcd.transform.gameObject.AddComponent<CrankSpinner>();
            spinner.Setup(_blockPos);
        }
    }

    // Lives on the crank's model; turns the rotor and the dynamo pulley with some inertia.
    public class CrankSpinner : MonoBehaviour
    {
        const string RotorName = "feCrank_Rotor";
        const string PulleyName = "feCrank_DynamoPulley";
        const float PulleyRatio = 0.10f / 0.045f;   // belt: big pulley 0.10 m, dynamo pulley 0.045 m
        const float SpinUp = 600f;                 // deg/s^2 while driven
        const float SpinDown = 150f;               // deg/s^2 coasting (flywheel inertia)

        static readonly Dictionary<Vector3i, CrankSpinner> byPos = new Dictionary<Vector3i, CrankSpinner>();

        const string ModuleName = "feCrank_Module";     // battery compartment: shown when the module is in slot 1
        const string BatteryName = "feCrank_Battery";   // the car battery: shown when a battery is in slot 2

        Vector3i pos;
        bool registered;
        Transform rotor, pulley, moduleObj, batteryObj;
        float speed, target, drivenUntil, nextSlotCheck;

        public static CrankSpinner At(Vector3i pos)
        {
            CrankSpinner s;
            return byPos.TryGetValue(pos, out s) && s != null ? s : null;
        }

        public void Setup(Vector3i blockPos)
        {
            // Model instances are pooled and reused for other blocks: re-register and reset every time.
            Unregister();
            pos = blockPos;
            byPos[pos] = this;
            registered = true;
            speed = 0f;
            target = 0f;
            rotor = FindDeep(transform, RotorName);
            pulley = FindDeep(transform, PulleyName);
            moduleObj = FindDeep(transform, ModuleName);
            batteryObj = FindDeep(transform, BatteryName);
            nextSlotCheck = 0f;
            UpdateSlotParts();
            if (rotor == null) Log.Warning(FerroEngrenagemMod.LogPrefix + "crank model has no " + RotorName);
        }

        // Shows the compartment / battery only when they are in the crank's slots (CrankSlots.cs). Reads the
        // client copy of the slots (TileEntityPowerSource.ItemSlots), so every player sees the same.
        void UpdateSlotParts()
        {
            if (moduleObj == null && batteryObj == null) return;
            GameManager gm = GameManager.Instance;
            TileEntityPowerSource te = gm == null || gm.World == null ? null
                : gm.World.GetTileEntity(pos) as TileEntityPowerSource;
            ItemStack[] slots = te == null ? null : te.ItemSlots;
            if (moduleObj != null) moduleObj.gameObject.SetActive(CrankSlots.HasModule(slots));
            if (batteryObj != null) batteryObj.gameObject.SetActive(CrankSlots.HasBatteryItem(slots));
        }

        public void Drive(float degPerSecond)
        {
            Drive(degPerSecond, 0.15f);
        }

        // hold: how long it keeps being driven without a new call (network spins arrive every ~0.2 s).
        public void Drive(float degPerSecond, float hold)
        {
            target = degPerSecond;
            drivenUntil = Mathf.Max(drivenUntil, Time.time + hold);
        }

        void Update()
        {
            if (Time.time >= nextSlotCheck)
            {
                nextSlotCheck = Time.time + 0.5f;
                UpdateSlotParts();
            }
            float goal = Time.time < drivenUntil ? target : 0f;
            speed = Mathf.MoveTowards(speed, goal, (goal > speed ? SpinUp : SpinDown) * Time.deltaTime);
            if (speed <= 0.01f) return;
            float step = speed * Time.deltaTime;
            if (rotor != null) rotor.Rotate(Vector3.forward, step, Space.Self);
            if (pulley != null) pulley.Rotate(Vector3.forward, step * PulleyRatio, Space.Self);
        }

        void OnDestroy()
        {
            Unregister();
        }

        void Unregister()
        {
            CrankSpinner cur;
            if (registered && byPos.TryGetValue(pos, out cur) && cur == this) byPos.Remove(pos);
            registered = false;
        }

        static Transform FindDeep(Transform t, string name)
        {
            if (t.name == name) return t;
            for (int i = 0; i < t.childCount; i++)
            {
                Transform r = FindDeep(t.GetChild(i), name);
                if (r != null) return r;
            }
            return null;
        }
    }

    // One per game client (not on a dedicated server): reads "hold E" while the local player looks at a crank.
    public class CrankController : MonoBehaviour
    {
        static GameObject host;

        const float SendInterval = 0.2f;   // seconds of cranking batched per CrankNet.Turn call
        float sendSeconds;                 // cranking time not yet sent
        Vector3i lastPos;
        string prompt;
        LocalPlayerUI promptUi;

        public static void Ensure()
        {
            if (host != null || GameManager.IsDedicatedServer) return;
            host = new GameObject("FerroEngrenagem.CrankController");
            Object.DontDestroyOnLoad(host);
            host.AddComponent<CrankController>();
        }

        void Update()
        {
            prompt = null;
            promptUi = null;
            GameManager gm = GameManager.Instance;
            if (gm == null || gm.World == null) return;
            EntityPlayerLocal player = gm.World.GetPrimaryPlayer();
            if (player == null || player.IsDead()) return;

            BlockFeCrank crank;
            Vector3i pos;
            if (!LookingAtCrank(player, out crank, out pos)) return;

            LocalPlayerUI ui = player.PlayerUI;
            if (ui == null || ui.windowManager == null) return;
            if (ui.windowManager.IsModalWindowOpen() || ui.windowManager.IsCursorWindowOpen()) return;
            if (player.IsCrouching) return;   // crouch + E is the vanilla radial (Take)

            promptUi = ui;
            TileEntityPowerSource te = gm.World.GetTileEntity(pos) as TileEntityPowerSource;
            if (te == null) return;
            // Fuel: on the server read the generator itself (TileEntityPowerSource.get_MaxFuel casts the raw
            // PowerItem field to PowerGenerator and throws when it is null or not a generator, IL 3.4.0 b10);
            // on a client the getters read the synced ClientData, which is safe.
            int curFuel, maxFuel;
            ReadFuel(te, out curFuel, out maxFuel);
            int pct = maxFuel == 0 ? 0 : Mathf.Clamp(100 * curFuel / maxFuel, 0, 100);
            ItemStack battery = CrankSlots.ActiveBattery(te.ItemSlots);
            int batPct = battery == null || battery.itemValue.MaxUseTimes <= 0 ? -1
                : Mathf.Clamp(100 * CrankSlots.Charge(battery) / battery.itemValue.MaxUseTimes, 0, 100);
            Stat stamina = player.Stats.Stamina;
            if (!IsActivateHeld(player))
            {
                prompt = batPct < 0
                    ? string.Format(Text("feCrankHold", "Hold {0} to turn the Crank ({1}% stored)"), KeyName(player), pct)
                    : string.Format(Text("feCrankHoldBattery", "Hold {0} to turn the Crank ({1}% stored, battery {2}%)"),
                                    KeyName(player), pct, batPct);
                return;
            }
            if (stamina.Value <= crank.MinStamina)
            {
                prompt = Text("feCrankTired", "Too tired to turn the Crank");
                return;
            }
            ConnectionManager cm = SingletonMonoBehaviour<ConnectionManager>.Instance;
            if (cm != null && cm.IsServer && !(te.GetPowerItem() is PowerGenerator))
            {
                // A crank placed by an older build whose saved power item is not a generator.
                PowerItem item = te.GetPowerItem();
                BlockFeCrank.Diag("no PowerGenerator at " + pos + " (power item: "
                                  + (item == null ? "none" : item.GetType().Name) + ")");
                prompt = Text("feCrankReplace", "Old Crank: pick it up (crouch + E) and place it again");
                return;
            }

            float dt = Time.deltaTime;
            stamina.Value = Mathf.Max(0f, stamina.Value - crank.StaminaPerSecond * dt);
            CrankSpinner spinner = CrankSpinner.At(pos);
            if (spinner != null) spinner.Drive(crank.SpinDegPerSecond);

            // The energy is added on the server (CrankNet.cs): directly when this game is the server, by a
            // net package from a multiplayer client. Batched every ~0.2 s.
            if (pos != lastPos) { sendSeconds = 0f; lastPos = pos; }
            sendSeconds += dt;
            if (sendSeconds >= SendInterval)
            {
                CrankNet.Turn(pos, sendSeconds);
                sendSeconds = 0f;
            }
            prompt = batPct < 0
                ? string.Format(Text("feCrankTurning", "Turning the Crank... {0}% stored"), pct)
                : string.Format(Text("feCrankTurningBattery", "Turning the Crank... {0}% stored, battery {1}%"),
                                pct, batPct);
        }

        // After the game's own Update, so our prompt is the one shown this frame.
        void LateUpdate()
        {
            if (prompt != null && promptUi != null) XUiC_InteractionPrompt.SetText(promptUi, prompt);
        }

        static void ReadFuel(TileEntityPowerSource te, out int cur, out int max)
        {
            cur = 0;
            max = 0;
            ConnectionManager cm = SingletonMonoBehaviour<ConnectionManager>.Instance;
            if (cm != null && cm.IsServer)
            {
                PowerGenerator gen = te.GetPowerItem() as PowerGenerator;
                if (gen == null) return;
                cur = gen.CurrentFuel;
                max = gen.MaxFuel;
                return;
            }
            cur = te.CurrentFuel;
            max = te.MaxFuel;
        }

        static bool LookingAtCrank(EntityPlayerLocal player, out BlockFeCrank crank, out Vector3i pos)
        {
            crank = null;
            pos = Vector3i.zero;
            WorldRayHitInfo hit = player.HitInfo;
            if (hit == null || !hit.bHitValid || !GameUtils.IsBlockOrTerrain(hit.tag)) return false;
            BlockValue bv = hit.hit.blockValue;
            crank = bv.Block as BlockFeCrank;
            if (crank == null) return false;
            if (hit.hit.distanceSq > crank.GetActivationDistanceSq()) return false;
            pos = hit.hit.blockPos;
            if (bv.ischild && crank.multiBlockPos != null) pos = crank.multiBlockPos.GetParentPos(pos, bv);
            return true;
        }

        static bool IsActivateHeld(EntityPlayerLocal player)
        {
            PlayerActionsLocal input = player.playerInput;
            if (input == null) return false;
            if (input.Activate != null && input.Activate.IsPressed) return true;
            PlayerActionsPermanent perm = input.PermanentActions;
            return perm != null && perm.Activate != null && perm.Activate.IsPressed;
        }

        static string KeyName(EntityPlayerLocal player)
        {
            PlayerActionsLocal input = player.playerInput;
            if (input == null || input.PermanentActions == null) return "[E]";
            return XUiUtils.GetBindingXuiMarkupString(input.PermanentActions.Activate,
                XUiUtils.EmptyBindingStyle.EmptyString, XUiUtils.DisplayStyle.Plain, null);
        }

        static string Text(string key, string fallback)
        {
            string s;
            return Localization.TryGet(key, out s) && !string.IsNullOrEmpty(s) ? s : fallback;
        }

    }
}
