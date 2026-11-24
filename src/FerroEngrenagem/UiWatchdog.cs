// Bug (user, 2026-11-24): "after a while the E prompt and the look texts are gone on every block, and E takes the
// item". The game shows the look text (XUiC_InteractionPrompt) only while no modal window is open
// (PlayerMoveController.Update: guiOpenThisUpdate = IsModalWindowOpen). The E radial is a modal window. The mod opens
// its own windows (Recipes, Machine Panel, Picker, Settings, Network, Guide) right after a radial command: when the
// radial had not finished closing, the radial could stay registered as open but hidden - from then on every look
// text was suppressed and a tap of E ran the first command (Take) of what was looked at.
//
// The fix has two parts:
//   - the mod's windows wait until no modal window is open (up to 5 s) and give up instead of forcing it
//     (FeUi.OpenWhenFree, RecipeBook.OpenWhenFree);
//   - this watchdog: a radial "open" while E is not held for more than 1.5 s is stuck: close it (and log it).
//     It also logs, once per 30 s, when the player looks at a block that has a look text but the prompt window is
//     not open, with the window state (diagnostic for any other cause).
//
// Client side, single player / host. C# 5 only.

using UnityEngine;

namespace FerroEngrenagem
{
    public class UiWatchdog : MonoBehaviour
    {
        static GameObject host;
        float next, radialSince = -1f, lastReport = -100f;

        public static void Ensure()
        {
            if (host != null || GameManager.IsDedicatedServer) return;
            host = new GameObject("FerroEngrenagem.UiWatchdog");
            Object.DontDestroyOnLoad(host);
            host.AddComponent<UiWatchdog>();
        }

        static bool ActivateHeld(EntityPlayerLocal pl)
        {
            PlayerActionsLocal input = pl.playerInput;
            if (input == null) return false;
            if (input.Activate != null && input.Activate.IsPressed) return true;
            return input.PermanentActions != null && input.PermanentActions.Activate != null && input.PermanentActions.Activate.IsPressed;
        }

        void Update()
        {
            if (Time.time < next) return;
            next = Time.time + 0.25f;
            try { Check(); }
            catch (System.Exception e)
            {
                if (Time.time - lastReport > 30f) { lastReport = Time.time; Log.Warning(FerroEngrenagemMod.LogPrefix + "ui watchdog: " + e.Message); }
            }
        }

        void Check()
        {
            GameManager gm = GameManager.Instance;
            if (gm == null || gm.World == null) return;
            LocalPlayerUI ui = LocalPlayerUI.GetUIForPrimaryPlayer();
            if (ui == null || ui.windowManager == null || ui.xui == null) return;
            EntityPlayerLocal pl = ui.entityPlayer;
            if (pl == null) return;
            GUIWindowManager wm = ui.windowManager;

            // 1. a radial that stays open without E held is stuck
            GUIWindow modal = wm.IsModalWindowOpen() ? wm.GetModalWindow() : null;
            bool radial = modal != null && modal.Id == "radial";
            // a radial the player is really using is shown on screen (hold R, hold E...): only a hidden one is stuck
            bool hidden = radial && (!modal.isShowing || (ui.xui.RadialWindow != null && ui.xui.RadialWindow.ViewComponent != null
                                                          && !ui.xui.RadialWindow.ViewComponent.IsVisible));
            if (radial && hidden && !ActivateHeld(pl))
            {
                if (radialSince < 0f) radialSince = Time.time;
                else if (Time.time - radialSince > 1.5f)
                {
                    Log.Warning(FerroEngrenagemMod.LogPrefix + "ui watchdog: the E radial was stuck open (hidden: " + !modal.isShowing
                                + ") without E held for " + (Time.time - radialSince).ToString("0.0") + " s: closed it (look texts were suppressed)");
                    try { if (ui.xui.RadialWindow != null) ui.xui.RadialWindow.Close(); } catch (System.Exception) { }
                    if (wm.IsWindowOpen("radial")) wm.Close("radial");
                    radialSince = -1f;
                }
            }
            else if (modal != null && !ActivateHeld(pl) && modal.Id != null && !modal.isShowing && Time.time - lastReport > 30f)
            {
                // some other modal window registered as open but not shown: also suppresses every look text
                lastReport = Time.time;
                Log.Warning(FerroEngrenagemMod.LogPrefix + "ui watchdog: modal window '" + modal.Id + "' is open but not shown: look texts are suppressed");
                radialSince = -1f;
            }
            else radialSince = -1f;

            // 2. diagnostic: looking at a block with a look text, no modal window, but no prompt window
            if (modal != null || Time.time - lastReport < 30f || wm.IsWindowOpen("interactionPrompt")) return;
            WorldRayHitInfo hit = pl.HitInfo;
            if (hit == null || !hit.bHitValid || !GameUtils.IsBlockOrTerrain(hit.tag)) return;
            BlockValue bv = hit.hit.blockValue;
            if (bv.isair || !bv.Block.GetBlockName().StartsWith("fe", System.StringComparison.Ordinal)) return;
            if (hit.hit.distanceSq > bv.Block.GetActivationDistanceSq()) return;
            lastReport = Time.time;
            Log.Warning(FerroEngrenagemMod.LogPrefix + "ui watchdog: looking at " + bv.Block.GetBlockName() + " at " + hit.hit.blockPos
                        + " but the look-text window is closed (HUD full off: " + wm.IsFullHUDDisabled() + ", HUD partial: "
                        + wm.IsHUDPartialHidden() + ")");
        }
    }
}
