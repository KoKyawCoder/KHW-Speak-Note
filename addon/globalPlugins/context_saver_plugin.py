# Copyright ©  2026 Ko Kyaw Htoo Win
import os
import tempfile
import json
import globalPluginHandler
import api
import ui
import speech
import gui
import wx
from logHandler import log
from scriptHandler import script
import textInfos
import config
from gui.settingsDialogs import SettingsPanel, NVDASettingsDialog

# Configuration setup for the addon settings
CONFIG_SECTION = "khwSpeakNote"
config.conf.spec[CONFIG_SECTION] = {
    "temporarySaving": "boolean(default=false)"
}

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    
    def __init__(self):
        super(GlobalPlugin, self).__init__()
        try:
            # Persistent path vs Temporary path
            self.temp_dir = tempfile.gettempdir()
            self.persistent_file = os.path.join(os.path.dirname(__file__), "..", "context_saver_data.json")
            self.temp_file = os.path.join(self.temp_dir, "nvda_temp_context.json")
            
            # Context-sensitive path selection based on configuration
            if config.conf[CONFIG_SECTION]["temporarySaving"]:
                self.file_path = self.temp_file
            else:
                self.file_path = self.persistent_file
                
            log.info(f"KHW Speak Note initializing storage path: {self.file_path}")
            
            if not os.path.exists(self.file_path):
                self.save_items([])
                
            self.current_index = -1
            
            # Register our custom settings panel into NVDA settings
            NVDASettingsDialog.categoryClasses.append(KHWSpeakNoteSettingsPanel)
        except Exception as e:
            log.error(f"KHW Speak Note initialization error: {e}", exc_info=True)

    def terminate(self):
        """Executed automatically when NVDA exits, reloads, or shutdowns."""
        try:
            if config.conf[CONFIG_SECTION]["temporarySaving"]:
                self.clear_all_items()
                log.info("KHW Speak Note cleared temporary data on shutdown.")
            NVDASettingsDialog.categoryClasses.remove(KHWSpeakNoteSettingsPanel)
        except Exception as e:
            log.error(f"KHW Speak Note termination error: {e}", exc_info=True)
        super(GlobalPlugin, self).terminate()

    def update_storage_path(self):
        """Switches paths immediately when user changes setting dynamically."""
        if config.conf[CONFIG_SECTION]["temporarySaving"]:
            self.file_path = self.temp_file
        else:
            self.file_path = self.persistent_file
        if not os.path.exists(self.file_path):
            self.save_items([])

    def get_saved_items(self):
        if not os.path.exists(self.file_path):
            return []
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log.error(f"KHW Speak Note failed to read JSON file: {e}", exc_info=True)
            return []

    def save_items(self, items):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"KHW Speak Note failed to write items to JSON file: {e}", exc_info=True)

    def clear_all_items(self):
        try:
            self.save_items([])
            self.current_index = -1
        except Exception as e:
            log.error(f"KHW Speak Note clear_all_items operation failed: {e}", exc_info=True)

    # --- SCRIPTS WITH INPUT GESTURE INTEGRATION ---
    # Default gestures can be altered cleanly from NVDA Preferences -> Input Gestures

    @script(
        description="Saves highlighted text or focused context into memory.",
        category="KHW Speak Note",
        gesture="kb:control+shift+m"
    )
    def script_save_focus_text(self, gesture):
        try:
            obj = api.getFocusObject()
            if not obj:
                ui.message("Nothing to save")
                return
            
            text = ""
            try:
                info = obj.makeTextInfo(textInfos.POSITION_SELECTION)
                if info and info.text:
                    text = info.text.strip()
            except Exception:
                pass
            
            if not text:
                try:
                    info = obj.makeTextInfo(textInfos.POSITION_CARET)
                    if info:
                        info.expand(textInfos.UNIT_LINE)
                        text = info.text.strip()
                except Exception:
                    pass

            if not text:
                text = obj.name

            if not text or text.strip() == "":
                ui.message("No text found to save")
                return

            items = self.get_saved_items()
            items.append(text)
            self.save_items(items)
            self.current_index = len(items) - 1
            ui.message(f"Saved text: {text[:20]}")
            
        except Exception as e:
            log.error(f"KHW Speak Note failed to save focus text: {e}", exc_info=True)
            ui.message("Error saving text context")

    @script(
        description="Speaks the currently active context item.",
        category="KHW Speak Note",
        gesture="kb:control+shift+r"
    )
    def script_read_current(self, gesture):
        try:
            items = self.get_saved_items()
            if not items:
                ui.message("No items saved")
                return
            if self.current_index < 0 or self.current_index >= len(items):
                self.current_index = len(items) - 1
            speech.speakText(items[self.current_index])
        except Exception as e:
            log.error(f"KHW Speak Note error in script_read_current: {e}", exc_info=True)

    @script(
        description="Navigates forward to the next saved item.",
        category="KHW Speak Note",
        gesture="kb:control+shift+3"
    )
    def script_read_next(self, gesture):
        try:
            items = self.get_saved_items()
            if not items:
                ui.message("No items saved")
                return
            
            if self.current_index < len(items) - 1:
                self.current_index += 1
                speech.speakText(items[self.current_index])
            else:
                ui.message("End of list")
        except Exception as e:
            log.error(f"KHW Speak Note error in script_read_next: {e}", exc_info=True)

    @script(
        description="Navigates backward to the previous saved item.",
        category="KHW Speak Note",
        gesture="kb:control+shift+2"
    )
    def script_read_previous(self, gesture):
        try:
            items = self.get_saved_items()
            if not items:
                ui.message("No items saved")
                return
            
            if self.current_index > 0:
                self.current_index -= 1
                speech.speakText(items[self.current_index])
            else:
                ui.message("Start of list")
        except Exception as e:
            log.error(f"KHW Speak Note error in script_read_previous: {e}", exc_info=True)

    @script(
        description="Opens the dialog history panel to view or delete context logs.",
        category="KHW Speak Note",
        gesture="kb:control+shift+h"
    )
    def script_open_history_dialog(self, gesture):
        try:
            gui.mainFrame.prePopup()
            d = ContextHistoryDialog(gui.mainFrame, self)
            d.Show()
            gui.mainFrame.postPopup()
        except Exception as e:
            log.error(f"KHW Speak Note failed to run history dialog window: {e}", exc_info=True)


# --- DIALOG UI MANAGEMENT ---

class ContextHistoryDialog(wx.Dialog):
    def __init__(self, parent, plugin):
        try:
            super(ContextHistoryDialog, self).__init__(parent, title="Saved Context Information", size=(500, 400))
            self.plugin = plugin
            
            mainSizer = wx.BoxSizer(wx.VERTICAL)
            
            self.listBox = wx.ListBox(self, choices=[])
            mainSizer.Add(self.listBox, 1, wx.EXPAND | wx.ALL, 10)
            self.update_list()
            
            self.listBox.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
            
            # Button layouts
            btnSizer = wx.BoxSizer(wx.HORIZONTAL)
            
            removeBtn = wx.Button(self, label="&Remove Item")
            removeBtn.Bind(wx.EVT_BUTTON, self.on_remove_item)
            btnSizer.Add(removeBtn, 0, wx.RIGHT, 5)
            
            clearBtn = wx.Button(self, label="&Clear All")
            clearBtn.Bind(wx.EVT_BUTTON, self.on_clear_all)
            btnSizer.Add(clearBtn, 0, wx.RIGHT, 5)
            
            closeBtn = wx.Button(self, wx.ID_CLOSE, label="&Close")
            closeBtn.Bind(wx.EVT_BUTTON, lambda e: self.Destroy())
            btnSizer.Add(closeBtn, 0)
            
            mainSizer.Add(btnSizer, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)
            
            self.SetSizer(mainSizer)
            self.listBox.SetFocus()
        except Exception as e:
            log.error(f"ContextHistoryDialog initialization failed: {e}", exc_info=True)

    def update_list(self):
        try:
            self.listBox.Clear()
            items = self.plugin.get_saved_items()
            for item in items:
                display_text = item if len(item) < 50 else item[:47] + "..."
                self.listBox.Append(display_text)
        except Exception as e:
            log.error(f"ContextHistoryDialog failed to refresh elements: {e}", exc_info=True)

    def remove_selected_item(self):
        selection = self.listBox.GetSelection()
        if selection != wx.NOT_FOUND:
            items = self.plugin.get_saved_items()
            items.pop(selection)
            self.plugin.save_items(items)
            self.update_list()
            ui.message("Item removed")
            if self.plugin.current_index >= len(items):
                self.plugin.current_index = len(items) - 1
            if len(items) > 0:
                new_selection = min(selection, len(items) - 1)
                self.listBox.SetSelection(new_selection)

    def on_remove_item(self, event):
        self.remove_selected_item()

    def on_key_down(self, event):
        try:
            keycode = event.GetKeyCode()
            # Pressing DELETE key breaks away individual elements directly
            if keycode in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
                self.remove_selected_item()
                return
            event.Skip()
        except Exception as e:
            log.error(f"ContextHistoryDialog key control crashed: {e}", exc_info=True)
            event.Skip()

    def on_clear_all(self, event):
        try:
            self.plugin.clear_all_items()
            self.update_list()
            ui.message("All items cleared")
        except Exception as e:
            log.error(f"ContextHistoryDialog interactive clearing failed: {e}", exc_info=True)


# --- SETTINGS PANEL CONFIGURATION ---

class KHWSpeakNoteSettingsPanel(SettingsPanel):
    title = "KHW Speak Note"

    def makeSettings(self, settingsSizer):
        # Create a static box sizer for the storage mode section
        storageGroupBox = wx.StaticBoxSizer(wx.VERTICAL, self, label="Storage Mode Selection")
        
        # Radio button selection to choose exclusively between temporary saving and persistent data saving
        self.tempSavingRadio = wx.RadioButton(
            self, 
            label="Temporary Saving (Wipe items automatically when computer resets or shutdowns)",
            style=wx.RB_GROUP
        )
        self.dataSavingRadio = wx.RadioButton(
            self,
            label="Data Saving Only (Keep items persistently saved across sessions)"
        )
        
        # Read the current configuration state to set the correct radio button value
        is_temp = config.conf[CONFIG_SECTION]["temporarySaving"]
        self.tempSavingRadio.SetValue(is_temp)
        self.dataSavingRadio.SetValue(not is_temp)
        
        # Add radio buttons to the storage group box
        storageGroupBox.Add(self.tempSavingRadio, 0, wx.ALL, 10)
        storageGroupBox.Add(self.dataSavingRadio, 0, wx.ALL, 10)
        
        # Add the storage group box to the settings sizer (passed as parameter)
        settingsSizer.Add(storageGroupBox, 0, wx.EXPAND | wx.ALL, 10)

    def onSave(self):
        # Update settings configuration target purely based on chosen storage rule option
        config.conf[CONFIG_SECTION]["temporarySaving"] = self.tempSavingRadio.GetValue()
        
        # Dynamically alert active instance if storage migration changes context files
        try:
            import globalPluginHandler
            for p in globalPluginHandler.runningPlugins:
                if isinstance(p, GlobalPlugin):
                    p.update_storage_path()
                    break
        except Exception as e:
            log.error(f"Failed updating runtime path changes: {e}", exc_info=True)