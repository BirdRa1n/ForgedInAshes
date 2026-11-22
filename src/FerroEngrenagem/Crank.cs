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
// Tunables (blocks.xml, optional): FeCrankChargeSeconds, FeCrankStaminaPerSecond, FeCrankMinStamina,
// FeCrankSpinDegPerSecond.
//
// C# 5 only (built with the .NET Framework 4 csc.exe, see tools/build.ps1).

using System.Collections.Generic;
using UnityEngine;

namespace FerroEngrenagem
{
    [UnityEngine.Scripting.Preserve]
    public class BlockFeCrank : Block
    {
        public float ChargeSeconds = 2.5f;        // seconds of cranking per Charge (old balance: ~4 per 10 s)
        public float StaminaPerSecond = 10f;      // drain while turning (regeneration still runs)
        public float MinStamina = 5f;             // below this the player is too tired to turn
        public float SpinDegPerSecond = 300f;     // rotor speed while turning

        public override void Init()
        {
            base.Init();
            ReadFloat("FeCrankChargeSeconds", ref ChargeSeconds);
            ReadFloat("FeCrankStaminaPerSecond", ref StaminaPerSecond);
            ReadFloat("FeCrankMinStamina", ref MinStamina);
            ReadFloat("FeCrankSpinDegPerSecond", ref SpinDegPerSecond);
            if (ChargeSeconds < 0.1f) ChargeSeconds = 0.1f;
            CrankController.Ensure();
            Log.Out(FerroEngrenagemMod.LogPrefix + "BlockFeCrank ready for '" + GetBlockName() + "' (Charge every "
                    + ChargeSeconds + " s)");
        }

        // Diagnostics while the hold-E crank is being tested in game (throttled).
        static float nextDiag;
        internal static void Diag(string msg)
        {
            if (Time.time < nextDiag) return;
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
            bool result = crouch && base.HasBlockActivationCommands(_world, _blockValue, _blockPos, _entityFocusing);
            Diag("HasBlockActivationCommands crouch=" + crouch + " -> " + result);
            return result;
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

        Vector3i pos;
        bool registered;
        Transform rotor, pulley;
        float speed, target, drivenUntil;

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
            if (rotor == null) Log.Warning(FerroEngrenagemMod.LogPrefix + "crank model has no " + RotorName);
        }

        public void Drive(float degPerSecond)
        {
            target = degPerSecond;
            drivenUntil = Time.time + 0.15f;
        }

        void Update()
        {
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

        float progress;          // seconds of cranking toward the next Charge (kept between pushes)
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
            BlockFeCrank.Diag("controller sees crank at " + pos + " held=" + IsActivateHeld(player)
                              + " crouch=" + player.IsCrouching);

            LocalPlayerUI ui = player.PlayerUI;
            if (ui == null || ui.windowManager == null) return;
            if (ui.windowManager.IsModalWindowOpen() || ui.windowManager.IsCursorWindowOpen()) return;
            if (player.IsCrouching) return;   // crouch + E is the vanilla radial (Take)

            promptUi = ui;
            Stat stamina = player.Stats.Stamina;
            if (!IsActivateHeld(player))
            {
                prompt = string.Format(Text("feCrankHold", "Hold {0} to turn the Crank"), KeyName(player));
                return;
            }
            if (stamina.Value <= crank.MinStamina)
            {
                prompt = Text("feCrankTired", "Too tired to turn the Crank");
                return;
            }

            float dt = Time.deltaTime;
            stamina.Value = Mathf.Max(0f, stamina.Value - crank.StaminaPerSecond * dt);
            CrankSpinner spinner = CrankSpinner.At(pos);
            if (spinner != null) spinner.Drive(crank.SpinDegPerSecond);

            progress += dt;
            if (progress >= crank.ChargeSeconds)
            {
                progress -= crank.ChargeSeconds;
                GiveCharge(gm, player);
            }
            int pct = Mathf.Clamp(Mathf.FloorToInt(100f * progress / crank.ChargeSeconds), 0, 99);
            prompt = string.Format(Text("feCrankTurning", "Turning the Crank... {0}%"), pct);
        }

        // After the game's own Update, so our prompt is the one shown this frame.
        void LateUpdate()
        {
            if (prompt != null && promptUi != null) XUiC_InteractionPrompt.SetText(promptUi, prompt);
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

        static void GiveCharge(GameManager gm, EntityPlayerLocal player)
        {
            ItemValue iv = ItemClass.GetItem(ChargeFuel.ChargeItemName, false);
            if (iv == null || iv.IsEmpty()) return;
            ItemStack stack = new ItemStack(iv, 1);
            XUiM_PlayerInventory inv = player.PlayerUI.xui.PlayerInventory;
            if (inv != null && inv.AddItem(stack, true)) return;
            // Inventory full: drop it at the player's feet, like vanilla does with harvested items.
            gm.ItemDropServer(new ItemStack(iv, 1), player.GetPosition(), Vector3.zero, player.entityId, 60f, false);
        }
    }
}
