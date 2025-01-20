import os
import json
import xbmc
import xbmcvfs
import xbmcaddon


class KodiPlayer(xbmc.Player):

    def __init__(self):
        super().__init__()
        self.create_and_clean_temp()
        if KodiPlayer.is_ass_override_style_not_positions():
            KodiPlayer.set_ass_override_style(False)
        self.position_override_disabled = False

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

    def end(self):
        if self.position_override_disabled:
            KodiPlayer.set_ass_override_style(False)
            self.position_override_disabled = False

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
        try:
            initial_sub_streams = self.getAvailableSubtitleStreams()
        except Exception:
            return

        if not initial_sub_streams:
            return

        initial_sub_streams_len = len(initial_sub_streams)
        if initial_sub_streams_len == 0:
            return

        #xbmc.log(";".join(initial_sub_streams) + ";", xbmc.LOGERROR)

        if initial_sub_streams_len == 1:
            self.showSubtitles(True)
            return

        del_idx = -1
        gle_idx = -1
        eng_count = 0

        for i, sub in enumerate(initial_sub_streams):
            if sub == "(External)":
                return
            elif (del_idx == -1) and (sub == "del" or sub == "del (External)"):
                del_idx = i
            elif gle_idx == -1 and sub == "gle":
                gle_idx = i
            elif sub.lower().startswith("eng"):
                eng_count += 1

        if del_idx != -1 and gle_idx != -1:
            self.handle_dual_subs(initial_sub_streams_len)
        elif eng_count > 1:
            self.find_sdh()
        elif del_idx != -1:
            self.setSubtitleStream(del_idx)
        elif gle_idx != -1:
            self.setSubtitleStream(gle_idx)

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
                    return
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
                    resources.lib.dualsubs.__addon__ = original_addon_instance

            if not self.position_override_disabled:
                KodiPlayer.set_ass_override_style(True)
                self.position_override_disabled = True
            self.setSubtitles(finalfile)
            self.setSubtitleStream(initial_sub_streams_len - 1)
        finally:
            for subtemp in substemp:
                try:
                    xbmcvfs.delete(subtemp)
                except Exception:
                    pass

    def find_sdh(self):
        # https://github.com/rockrider69/service.LanguagePreferenceManager/blob/V1.0.4/resources/lib/prefutils.py#L391
        activePlayerID = json.loads(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": null}'))['result'][0]['playerid']
        details_query_dict = {  "jsonrpc": "2.0",
                                "method": "Player.GetProperties",
                                "params": { "properties": 
                                            ["currentsubtitle", "subtitles" ], # "subtitleenabled",
                                            "playerid": activePlayerID },
                                "id": None}
        json_query = xbmc.executeJSONRPC(json.dumps(details_query_dict))
        #xbmc.log(json_query, xbmc.LOGERROR)
        json_response = json.loads(json_query)["result"]

        is_sdh = lambda sub: ((sub["language"] == "eng")) and ((sub["isimpaired"]) or ("SDH" in sub["name"] and not "dub" in sub["name"].lower()))

        if is_sdh(json_response["currentsubtitle"]):
            return

        eng_sdh_idx = next((sub["index"] for sub in reversed(json_response["subtitles"]) if is_sdh(sub)), None)

        if eng_sdh_idx is None and json_response["currentsubtitle"]["name"].lower() == "forced":
            eng_sdh_idx = next((sub["index"] for sub in json_response["subtitles"] if sub["language"] == "eng" and not "forced" in sub["name"].lower()), None)

        if eng_sdh_idx is not None:
            self.setSubtitleStream(eng_sdh_idx)


if __name__ == "__main__":
    player = KodiPlayer()
    xbmc.Monitor().waitForAbort()
