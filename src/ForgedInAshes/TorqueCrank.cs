// D7: Torque Crank (feTorqueCrank). User, 2026-11-22: "the motor makes torque from the electric energy the
// crank makes; we also need a crank that makes PURE torque, plugged in the same place as the Electric Motor".
//
// It is a plain block (no tile entity, no wires) placed in a machine's motor socket (PowerGate.SocketPos).
// While the local player holds Activate (E) on it, it spins (stamina cost) and the machine counts as driven
// with FeTorqueOutput watts of shaft power; after letting go it coasts for FeTorqueCoastSeconds. Nothing is
// stored: no turning, no crafting.
//
// The spin state lives in memory on the machine that runs the power gate (single player / host). Like the
// generator crank, a pure multiplayer client cannot drive it yet (needs a net package; F2-T06).
// Model: the crank's prefab for now (CrankSpinner turns its rotor; the battery parts stay hidden).
//
// C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace ForgedInAshes
{
    [UnityEngine.Scripting.Preserve]
    public class BlockFeTorqueCrank : Block
    {
        public int Output = 64;                   // UT while spinning (D8)
        public float CoastSeconds = 1.5f;         // keeps driving this long after the player stops
        public float StaminaPerSecond = 30f;
        public float MinStamina = 5f;
        public float SpinDegPerSecond = 300f;

        public override void Init()
        {
            base.Init();
            if (Properties != null && Properties.Contains("FeTorqueOutput")) Output = Properties.GetInt("FeTorqueOutput");
            ReadFloat("FeTorqueCoastSeconds", ref CoastSeconds);
            ReadFloat("FeTorqueStaminaPerSecond", ref StaminaPerSecond);
            ReadFloat("FeTorqueMinStamina", ref MinStamina);
            ReadFloat("FeTorqueSpinDegPerSecond", ref SpinDegPerSecond);
            TorqueCrankController.Ensure();
            MotorSocketMarker.Ensure();
            Log.Out(ForgedInAshesMod.LogPrefix + "BlockFeTorqueCrank ready for '" + GetBlockName() + "' (" + Output
                    + " UT while turning)");
        }

        void ReadFloat(string name, ref float value)
        {
            if (Properties != null && Properties.Contains(name)) value = Properties.GetFloat(name);
        }

        // Standing: no commands (E is "hold to turn"). Crouching: vanilla commands (pick up).
        // Not the vanilla CanPickup: with it a plain E press picks the crank up and its "press E to pick up"
        // prompt hides ours (user test, 2026-11-23). Crouch + E opens an own radial with "take".
        public override bool HasBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos,
                                                        EntityAlive _entityFocusing)
        {
            return _entityFocusing != null && _entityFocusing.IsCrouching;
        }

        public override BlockActivationCommand[] GetBlockActivationCommands(WorldBase _world, BlockValue _blockValue,
                                                                           Vector3i _blockPos,
                                                                           EntityAlive _entityFocusing)
        {
            return new BlockActivationCommand[]
            {
                new BlockActivationCommand("take", "hand", Pickup.CanBuildHere(_world, _blockPos), false, null)
            };
        }

        public override bool OnBlockActivated(string _commandName, WorldBase _world, Vector3i _blockPos,
                                              BlockValue _blockValue, EntityPlayerLocal _player)
        {
            if (_commandName != "take") return false;
            float delay = Properties != null && Properties.Contains("TakeDelay") ? Properties.GetFloat("TakeDelay") : 3f;
            takeItemWithTimer(_blockPos, _blockValue, _player, delay);
            return true;
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

        public override void OnBlockRemoved(WorldBase world, Chunk _chunk, Vector3i _blockPos, BlockValue _blockValue)
        {
            base.OnBlockRemoved(world, _chunk, _blockPos, _blockValue);
            TorqueState.Stop(_blockPos);
        }
    }

    /// <summary>Which torque cranks are turning right now (position -> time until which they drive).</summary>
    public static class TorqueState
    {
        static readonly Dictionary<Vector3i, float> until = new Dictionary<Vector3i, float>();

        public static void Spin(Vector3i pos, float seconds)
        {
            until[pos] = Time.time + seconds;
        }

        public static void Stop(Vector3i pos)
        {
            until.Remove(pos);
        }

        public static bool IsSpinning(Vector3i pos)
        {
            float t;
            return until.TryGetValue(pos, out t) && Time.time < t;
        }
    }

    // One per game client: reads "hold E" while the local player looks at a torque crank.
    public class TorqueCrankController : MonoBehaviour
    {
        static GameObject host;
        string prompt;
        LocalPlayerUI promptUi;

        public static void Ensure()
        {
            if (host != null || GameManager.IsDedicatedServer) return;
            host = new GameObject("ForgedInAshes.TorqueCrankController");
            Object.DontDestroyOnLoad(host);
            host.AddComponent<TorqueCrankController>();
        }

        void Update()
        {
            prompt = null;
            promptUi = null;
            GameManager gm = GameManager.Instance;
            if (gm == null || gm.World == null) return;
            EntityPlayerLocal player = gm.World.GetPrimaryPlayer();
            if (player == null || player.IsDead()) return;

            WorldRayHitInfo hit = player.HitInfo;
            if (hit == null || !hit.bHitValid || !GameUtils.IsBlockOrTerrain(hit.tag)) return;
            BlockFeTorqueCrank crank = hit.hit.blockValue.Block as BlockFeTorqueCrank;
            if (crank == null || hit.hit.distanceSq > crank.GetActivationDistanceSq()) return;
            Vector3i pos = hit.hit.blockPos;

            LocalPlayerUI ui = player.PlayerUI;
            if (ui == null || ui.windowManager == null) return;
            if (ui.windowManager.IsModalWindowOpen() || ui.windowManager.IsCursorWindowOpen()) return;
            if (player.IsCrouching) return;   // crouch + E: vanilla radial (pick up)
            promptUi = ui;

            if (!IsActivateHeld(player))
            {
                prompt = string.Format(Text("feTorqueHold", "Hold {0} to turn the Torque Crank"), KeyName(player)) +
                         "\n" + KineticLookController.Status(Kinetic.Get(gm.World, pos), pos);
                return;
            }
            Stat stamina = player.Stats.Stamina;
            if (stamina.Value <= crank.MinStamina)
            {
                prompt = Text("feCrankTired", "Too tired to turn the Crank");
                return;
            }
            stamina.Value = Mathf.Max(0f, stamina.Value - crank.StaminaPerSecond * Time.deltaTime);
            TorqueState.Spin(pos, crank.CoastSeconds);
            CrankSpinner spinner = CrankSpinner.At(pos);
            if (spinner != null) spinner.Drive(crank.SpinDegPerSecond);
            prompt = Text("feTorqueTurning", "Turning the Torque Crank...") + "\n" +
                     KineticLookController.Status(Kinetic.Get(gm.World, pos), pos);
        }

        void LateUpdate()
        {
            if (prompt != null && promptUi != null) XUiC_InteractionPrompt.SetText(promptUi, prompt);
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
