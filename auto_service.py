import os
import json
import xbmc
import xbmcvfs
import xbmcaddon


class KodiPlayer(xbmc.Player):

    @staticmethod
    def is_logging_enabled():
        resp = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"debug.showloginfo"},"id":null}')
        return not (resp and resp.startswith('{"error":'))

    ENABLE_LOG = is_logging_enabled.__func__() # remove this dumb shit when Kodi finally upgrades its Python

    def __init__(self):
        super().__init__()
        self.create_and_clean_temp()
        if KodiPlayer.is_ass_override_style_not_positions():
            KodiPlayer.set_ass_override_style(False)
        self.position_override_disabled = False
        if KodiPlayer.is_sub_border_background_not_none():
            KodiPlayer.set_sub_border_background(False)
        self.border_override_enabled = False

    def create_and_clean_temp(self):
        __profile__ = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
        self.__temp__ = xbmcvfs.translatePath(os.path.join(__profile__, 'temp', ''))
        if xbmcvfs.exists(self.__temp__):
            from shutil import rmtree
            rmtree(self.__temp__)
        xbmcvfs.mkdirs(self.__temp__)

    @staticmethod
    def set_ass_override_style(disabled: bool):
        if disabled:
            xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","params":{"setting":"subtitles.overridestyles","value":0},"id":null}') # OverrideStyles::DISABLED
        else:
            xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","params":{"setting":"subtitles.overridestyles","value":1},"id":null}') # OverrideStyles::POSITIONS

    @staticmethod
    def is_ass_override_style_not_positions():
        try:
            return json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"subtitles.overridestyles"},"id":null}'))["result"]["value"] != 1
        except Exception:
            return True

    @staticmethod
    def set_sub_border_background(enabled: bool):
        if enabled:
            xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","params":{"setting":"subtitles.backgroundtype","value":3},"id":null}') # BackgroundType::SQUAREBOX
        else:
            xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","params":{"setting":"subtitles.backgroundtype","value":0},"id":null}') # BackgroundType::NONE

    @staticmethod
    def is_sub_border_background_not_none():
        try:
            return json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"subtitles.backgroundtype"},"id":null}'))["result"]["value"] != 0
        except Exception:
            return True

    def end(self):
        if self.position_override_disabled:
            KodiPlayer.set_ass_override_style(False)
            self.position_override_disabled = False
        if self.border_override_enabled:
            KodiPlayer.set_sub_border_background(False)
            self.border_override_enabled = False

    def onPlayBackEnded(self):
        if not self.isPlaying(): # not xbmc.getCondVisibility("Player.HasMedia")
            self.end()

    def onPlayBackError(self):
        self.end()

    def onPlayBackStopped(self):
        self.end()

    #def onPlayBackStarted(self):
    #    self.end()

    def onAVStarted(self):
        xbmc.sleep(500)

        try:
            initial_sub_streams = self.getAvailableSubtitleStreams()
        except Exception:
            return

        if not initial_sub_streams:
            return

        initial_sub_streams_len = len(initial_sub_streams)
        if initial_sub_streams_len == 0:
            return

        if KodiPlayer.ENABLE_LOG: xbmc.log(" | ".join(f"{i}={sub}" for i, sub in enumerate(initial_sub_streams)), xbmc.LOGERROR)

        if initial_sub_streams_len == 1:
            self.showSubtitles(True)
            return

        new_idx = None
        del_idx = None
        gle_idx = None
        eng_count = 0
        bor_on = False
        straight_ext_found = False

        for i, sub in enumerate(initial_sub_streams):
            if not straight_ext_found and sub == "(External)":
                straight_ext_found = True
                if bor_on:
                    break
            elif not bor_on and sub == "bor":
                bor_on = True
                if straight_ext_found:
                    break
            elif (del_idx is None) and (sub == "del" or sub == "del (External)"):
                del_idx = i
            elif gle_idx is None and sub == "gle":
                gle_idx = i
            elif not straight_ext_found and sub.lower().startswith("eng"):
                eng_count += 1

        if bor_on:
            if not self.border_override_enabled:
                KodiPlayer.set_sub_border_background(True)
                self.border_override_enabled = True

        if straight_ext_found:
            return

        if del_idx is not None and gle_idx is not None:
            new_idx = self.handle_dual_subs(initial_sub_streams_len)
        elif eng_count > 1:
            new_idx = KodiPlayer.find_sdh()
        elif del_idx is not None:
            new_idx = del_idx
        elif gle_idx is not None:
            new_idx = gle_idx
        elif bor_on and player.getSubtitles() == "bor":
            new_idx = KodiPlayer.find_sdh(True)

        if new_idx is not None:
            self.setSubtitleStream(new_idx)

    def handle_dual_subs(self, initial_sub_streams_len):
        substemp = []
        try:
            from tempfile import mktemp
            import resources.lib.dualsubs

            vid_basename = os.path.splitext(self.getPlayingFile())[0]

            subs = [vid_basename + ".del.srt", vid_basename + ".gle.srt"]
            for sub in subs:
                subtemp = mktemp(suffix=".srt", dir=self.__temp__)
                if not xbmcvfs.copy(sub, subtemp):
                    return None
                substemp.append(subtemp)

            if resources.lib.dualsubs.__addon__.getSetting('bottom_background') == 'true':
                finalfile = resources.lib.dualsubs.mergesubs(substemp)
            elif not xbmcvfs.exists(vid_basename + ".bor.srt"):
                finalfile = resources.lib.dualsubs.mergesubs(substemp)
            else:
                try:
                    original_addon_instance = resources.lib.dualsubs.__addon__
                    class AddonWrapper:
                        def getSetting(self, id: str) -> str:
                            if id != "bottom_background":
                                return original_addon_instance.getSetting(id)
                            return "true"

                        def __getattr__(self, name):
                            return getattr(original_addon_instance, name)

                    resources.lib.dualsubs.__addon__ = AddonWrapper()
                    finalfile = resources.lib.dualsubs.mergesubs(substemp)
                finally:
                    if original_addon_instance:
                        resources.lib.dualsubs.__addon__ = original_addon_instance

            if not self.position_override_disabled:
                KodiPlayer.set_ass_override_style(True)
                self.position_override_disabled = True
            self.setSubtitles(finalfile)
            return initial_sub_streams_len - 1
        finally:
            for subtemp in substemp:
                try:
                    xbmcvfs.delete(subtemp)
                except Exception:
                    pass

    @staticmethod
    def find_sdh(fuck_it=False):
        json_response = KodiPlayer.query_available_subs()
        eng_sdh_idx = next((sub["index"] for sub in json_response["subtitles"] if sub["name"] == "(External)" and sub["language"] == "eng"), None)

        if eng_sdh_idx is None:
            eng_sdh_idx = next((sub["index"] for sub in json_response["subtitles"] if sub["name"] == "(External)" and not sub.get("language")), None)

        if eng_sdh_idx is None:
            eng_sdh_idx = next((sub["index"] for sub in json_response["subtitles"] if sub["name"] == "(External)" and sub["language"] == "hin"), None)

        if eng_sdh_idx is None:
            is_sdh = lambda sub: (((sub["language"] == "eng"))) and (((sub["isimpaired"])) or (("SDH" in sub["name"] or sub["name"] == "HI") and not "dub" in sub["name"].lower()))

            if is_sdh(json_response["currentsubtitle"]):
                return None

            eng_sdh_idx = next((sub["index"] for sub in reversed(json_response["subtitles"]) if is_sdh(sub)), None)

        if (eng_sdh_idx is None) and (json_response["currentsubtitle"]["isforced"] or json_response["currentsubtitle"]["name"].lower() == "forced"):
            eng_sdh_idx = next((sub["index"] for sub in json_response["subtitles"] if sub["language"] == "eng" and not sub["isforced"] and not "forced" in sub["name"].lower()), None)

        if fuck_it and eng_sdh_idx is None:
            eng_sdh_idx = next((sub["index"] for sub in json_response["subtitles"] if sub["name"] == "(External)" and sub["language"] != "bor"), None)

        return eng_sdh_idx

    @staticmethod
    def query_available_subs():
        # https://github.com/rockrider69/service.LanguagePreferenceManager/blob/V1.0.4/resources/lib/prefutils.py#L391
        activePlayerID = 1 #json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.GetActivePlayers","id":null}'))["result"][0]["playerid"]
        details_query_dict = { "jsonrpc": "2.0",
                               "method":  "Player.GetProperties",
                               "params":  { "properties": ["currentsubtitle", "subtitles"],  # "subtitleenabled",
                                            "playerid":   activePlayerID },
                               "id": None }
        json_response = xbmc.executeJSONRPC(json.dumps(details_query_dict))
        if KodiPlayer.ENABLE_LOG: xbmc.log(json_response, xbmc.LOGERROR)
        return json.loads(json_response)["result"]

if __name__ == "__main__":
    player = KodiPlayer()
    xbmc.Monitor().waitForAbort()
