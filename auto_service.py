import os
import tempfile
import shutil
import xbmc
import xbmcvfs
import xbmcaddon

from resources.lib.dualsubs import mergesubs

class KodiPlayer(xbmc.Player):

    def onAVStarted(self):
        try:
            initial_sub_streams = self.getAvailableSubtitleStreams()
            if not initial_sub_streams or not all(sub in initial_sub_streams for sub in ["del (External)", "gle"]):
                return
        except:
            return

        substemp = []
        try:
            vid_basename = os.path.splitext(self.getPlayingFile())[0]

            subs = [vid_basename + ".del.srt", vid_basename + ".gle.srt"]
            for sub in subs:
                subtemp = tempfile.mktemp(suffix=".srt", dir=__temp__)
                xbmcvfs.copy(sub, subtemp)
                if not os.path.exists(subtemp):
                    return
                substemp.append(subtemp)

            finalfile = mergesubs(substemp)

            self.setSubtitles(finalfile)
            self.setSubtitleStream(len(initial_sub_streams) - 1)
        finally:
            for subtemp in substemp:
                try:
                    xbmcvfs.delete(subtemp)
                except:
                    pass


if __name__ == "__main__":
    __profile__ = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
    __temp__    = xbmcvfs.translatePath(os.path.join(__profile__, 'temp', ''))
    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    player = KodiPlayer()
    xbmc.Monitor().waitForAbort()
