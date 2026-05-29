# C:\KHW Speak Note\context_saver\addon\globalPlugins\context_saver_plugin.py
import os
import tempfile
import json
import codecs
import globalPluginHandler
import api
import ui
import speech
import gui
import wx
import textInfos
from logHandler import log
from scriptHandler import script

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    
    def __init__(self):
        super(GlobalPlugin, self).__init__()
        try:
            self.temp_dir = tempfile.gettempdir()
            self.file_path = os.path.join(self.temp_dir, "nvda_temp_context.json")
            log.info(f"Context Saver initializing temp storage path: {self.file_path}")
            
            if not os.path.exists(self.file_path):
                self.save_items([])
                
            self.current_index = -1
        except Exception as e:
            log.error(f"Context Saver initialization error: {e}", exc_info=True)

    def get_saved_items(self):
        if not os.path.exists(self.file_path):
            return []
        try:
            with codecs.open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Context Saver failed to read or parse JSON file: {e}", exc_info=True)
            return []

    def save_items(self, items):
        try:
            with codecs.open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"Context Saver failed to write items to JSON file: {e}", exc_info=True)

    def clear_all_items(self):
        try:
            self.save_items([])
            self.current_index = -1
        except Exception as e:
            log.error(f"Context Saver clear_all_items operation failed: {e}", exc_info=True)

    # --- SCRIPT DECORATORS ---

    @script(gesture="kb:control+shift+m")
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
            except Exception as e:
                log.debug(f"Context Saver selection capture fallback triggered: {e}")
            
            if not text:
                try:
                    info = obj.makeTextInfo(position=textInfos.POSITION_SELECTION)
                    if info and info.text:
                        text = info.text.strip()
                except Exception as e:
                    log.debug(f"Context Saver secondary selection dropped: {e}")

            if not text:
                try:
                    info = obj.makeTextInfo(textInfos.POSITION_CARET)
                    if info:
                        info.expand(textInfos.UNIT_LINE)
                        text = info.text.strip()
                except Exception as e:
                    log.debug(f"Context Saver caret navigation dropped: {e}")

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
            log.error(f"Context Saver failed during script_save_focus_text execution: {e}", exc_info=True)
            ui.message("Error saving text context")

    @script(gesture="kb:control+shift+r")
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
            log.error(f"Context Saver error in script_read_current: {e}", exc_info=True)

    # UPDATED: Assigned to Ctrl+Shift+3 and its shifted symbol format
    @script(gestures=["kb:control+shift+3", "kb:control+shift+numrow3", "kb:control+shift+#"])
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
            log.error(f"Context Saver error in script_read_next: {e}", exc_info=True)

    # RESTORED: Assigned back to your preferred Ctrl+Shift+2 configuration
    @script(gestures=["kb:control+shift+2", "kb:control+shift+numrow2", "kb:control+shift+@"])
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
            log.error(f"Context Saver error in script_read_previous: {e}", exc_info=True)

    @script(gesture="kb:control+shift+h")
    def script_open_history_dialog(self, gesture):
        try:
            gui.mainFrame.prePopup()
            d = ContextHistoryDialog(gui.mainFrame, self)
            d.Show()
            gui.mainFrame.postPopup()
        except Exception as e:
            log.error(f"Context Saver failed to run history UI popup: {e}", exc_info=True)


# --- DIALOG UI MANAGEMENT ---

class ContextHistoryDialog(wx.Dialog):
    def __init__(self, parent, plugin):
        try:
            super(ContextHistoryDialog, self).__init__(parent, title="Saved Context Information", size=(450, 350))
            self.plugin = plugin
            
            mainSizer = wx.BoxSizer(wx.VERTICAL)
            self.listBox = wx.ListBox(self, choices=[])
            mainSizer.Add(self.listBox, 1, wx.EXPAND | wx.ALL, 10)
            self.update_list()
            
            self.listBox.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
            
            clearBtn = wx.Button(self, label="&Clear All")
            clearBtn.Bind(wx.EVT_BUTTON, self.on_clear_all)
            mainSizer.Add(clearBtn, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)
            
            closeBtn = wx.Button(self, wx.ID_CLOSE, label="&Close")
            closeBtn.Bind(wx.EVT_BUTTON, lambda e: self.Destroy())
            mainSizer.Add(closeBtn, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)
            
            self.SetSizer(mainSizer)
            self.listBox.SetFocus()
        except Exception as e:
            log.error(f"ContextHistoryDialog initialization broke: {e}", exc_info=True)

    def update_list(self):
        try:
            self.listBox.Clear()
            items = self.plugin.get_saved_items()
            for item in items:
                display_text = item if len(item) < 50 else item[:47] + "..."
                self.listBox.Append(display_text)
        except Exception as e:
            log.error(f"ContextHistoryDialog UI failed to refresh items list: {e}", exc_info=True)

    def on_key_down(self, event):
        try:
            keycode = event.GetKeyCode()
            if keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                selection = self.listBox.GetSelection()
                if selection != wx.NOT_FOUND:
                    items = self.plugin.get_saved_items()
                    items.pop(selection)
                    self.plugin.save_items(items)
                    self.update_list()
                    ui.message("Item deleted")
                    if self.plugin.current_index >= len(items):
                        self.plugin.current_index = len(items) - 1
                return
            event.Skip()
        except Exception as e:
            log.error(f"ContextHistoryDialog keydown controller failed: {e}", exc_info=True)
            event.Skip()

    def on_clear_all(self, event):
        try:
            self.plugin.clear_all_items()
            self.update_list()
            ui.message("All items cleared")
        except Exception as e:
            log.error(f"ContextHistoryDialog clear interaction crashed: {e}", exc_info=True)