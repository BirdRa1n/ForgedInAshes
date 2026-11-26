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
//   - 2026-11-26: the look text also vanished with no modal window open (log: "looking at feSteamEngine ... the
//     look-text window is closed"): the window had been closed while the game kept the same text cached, and the
//     game only reopens it when the text changes. The watchdog clears that cache (part 2 of Check).
//
// Client side, single player / host. C# 5 only.

using UnityEngine;

namespace FerroEngrenagem
{
    public class UiWatchdog : MonoBehaviour
    {
        static GameObject host;
        float next, radialSince = -1f, lastReport = -100f, lastRepair = -100f, lastFeLook = -100f, lastLostReport = -100f;
        string lastFeName = "";

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

            // 2. the look-text window was closed behind the game's back. PlayerMoveController.HandleInteraction only
            //    calls XUiC_InteractionPrompt.SetText when the text differs from its cache strTextLabelPointingTo
            //    (IL 3.4.0 b10), so once anything closes the window while the text stays the same (an engine that is
            //    stopped, a block whose readout does not change), it never opens again until the player looks at
            //    something with another text (user test 2026-11-26, Steam Engine). Clear the cache: the next frame
            //    the game sees a "new" text and opens the window itself.
            bool promptOpen = wm.IsWindowOpen("interactionPrompt");
            WorldRayHitInfo look = pl.HitInfo;
            bool lookFe = look != null && look.bHitValid && GameUtils.IsBlockOrTerrain(look.tag) && !look.hit.blockValue.isair
                          && look.hit.blockValue.Block.GetBlockName().StartsWith("fe", System.StringComparison.Ordinal);
            if (promptOpen && lookFe) { lastFeLook = Time.time; lastFeName = look.hit.blockValue.Block.GetBlockName(); }
            else if (!promptOpen && modal == null && Time.time - lastFeLook < 2f && Time.time - lastLostReport > 30f)
            {
                // the text was shown on an "fe" block less than 2 s ago and is gone now: what does the game see?
                lastLostReport = Time.time;
                string what = look == null ? "no hit info"
                    : "hit valid " + look.bHitValid + ", tag '" + look.tag + "', block " + (look.hit.blockValue.isair ? "air" : look.hit.blockValue.Block.GetBlockName())
                      + " at " + look.hit.blockPos + ", dist " + Mathf.Sqrt(look.hit.distanceSq).ToString("0.00");
                Log.Out(FerroEngrenagemMod.LogPrefix + "ui watchdog: look text gone right after " + lastFeName + " (" + what
                        + ", cached text " + (pl.MoveController == null || string.IsNullOrEmpty(pl.MoveController.strTextLabelPointingTo) ? "empty" : "set") + ")");
            }
            if (modal != null || promptOpen || wm.IsFullHUDDisabled() || wm.IsHUDPartialHidden()) return;
            PlayerMoveController pmc = pl.MoveController;
            if (pmc != null && !string.IsNullOrEmpty(pmc.strTextLabelPointingTo))
            {
                pmc.strTextLabelPointingTo = null;
                if (Time.time - lastRepair > 30f)
                {
                    lastRepair = Time.time;
                    Log.Out(FerroEngrenagemMod.LogPrefix + "ui watchdog: the look-text window was closed with a text cached: reopened it");
                }
                return;
            }

            // 3. diagnostic: looking at a block with a look text, no modal window, but no prompt window
            if (Time.time - lastReport < 30f) return;
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
