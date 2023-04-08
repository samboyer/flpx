############################################
# flp_write.py - write project data back to FLP file
# Feb 2022, Sam Boyer
# Part of the FLPX project
############################################


from typing import BinaryIO, Union

from flp_read import eid_to_ename, ename_to_eid
from _types import *


# CONSTANTS
HEADERCHUNKID = b"FLhd"
DATACHUNKID = b"FLdt"


# UTIL FUNCTIONS
def itob(x: int, length: int, endianness="little") -> bytes:
    """Convert an integer to a bytes object, padded to `length`"""
    return int.to_bytes(x, length, endianness)


def _str_to_UTF16(s: str) -> bytes:
    """Convert UTF-16-encoded strings to python strings"""
    # return codecs.utf_16_encode(str)[0] #might need to re-add a null byte?
    return s.encode("UTF-16-LE")


def _event_size_to_bytes(s: int) -> bytes:
    """Convert integer byte length to TEXT event size, using gol's funky encoding"""
    out = b""
    while s != 0:
        # little endian
        nextByte = s & 127
        s = s >> 7
        if s != 0:
            # all bytes except the last one have bit 7 enabled
            nextByte = nextByte | 128
        out += itob(nextByte, 1)
    return out


def _write_event(
    f: BinaryIO, eventId: Union[int, str], data: Union[int, bytes]
) -> None:
    if isinstance(eventId, str):
        eventId = ename_to_eid(eventId)
    f.write(itob(eventId, 1))
    # content is either int or bytes, depending on eventID
    if eventId < 64:
        f.write(itob(data, 1))
    elif eventId < 128:
        f.write(itob(data, 2))
    elif eventId < 192:
        f.write(itob(data, 4))
    else:
        eventSize = len(data)
        f.write(_event_size_to_bytes(eventSize))  # size of event
        f.write(data)

    if DEBUG:
        fd.write(f"{eventId} {eid_to_ename(eventId)}\n{data}\n")


def _make_arrangement_data(arrangement: PlaylistArrangement) -> bytes:
    size = 32 * len(arrangement.items)
    out = b""
    for item in arrangement.items:
        item_bytes = (
            itob(item.start, 4)  # 0-4
            + item.misc_4_6  # 4,5
            + itob(
                item.clipIndex + 20481
                if item.itemType == "pattern"
                else item.clipIndex,
                2,
            )  # 6,7
            + itob(item.length, 4)  # 8-12
            + itob(500 - item.track, 4)  # 12-16
            + item.misc  # 16-24
            + itob(item.clipStart, 4)  # 24-28
            + itob(item.clipEnd, 4)  # 28-32
        )
        assert len(item_bytes) == 32
        out += item_bytes
        # TODO handle muted, selected members (edit .misc?)
    assert len(out) == size
    return out


def write_FLP(filepath: str, project: Project) -> None:
    f = open(filepath, "wb")

    # write header
    f.write(HEADERCHUNKID)  # file header
    f.write(itob(6, 4))  # header length
    f.write(itob(0, 2))  # header format
    f.write(itob(4, 2))  # 'not really used'
    f.write(itob(96, 2))  # 'not really used'
    f.write(DATACHUNKID)

    # come back here to write dataLength here at the end
    dataLengthPosition = f.tell()
    f.write(b"0000")  # make space to write the size later

    # write global project vars
    def writeGenericProjectEvent(eventId):
        name = eid_to_ename(eventId)  # the name I've given to this event
        _write_event(f, eventId, project.projectInfo[name])

    # (see FLP layout grammar for an explanation of these event IDs)
    for eventId in [
        199,
        159,
        28,
        37,
        200,
        156,
        67,
        9,
        11,
        80,
        17,
        18,
        35,
        23,
        30,
        10,
        194,
        206,
        207,
        202,
        195,
        197,
        237,
    ]:
        writeGenericProjectEvent(eventId)

    # write channel group names
    for channelGroup in project.channelFilterGroups:
        _write_event(f, 231, _str_to_UTF16(channelGroup["name"]))

    # 146 CurrentChannelFilterGroup, 216 unknown
    writeGenericProjectEvent(146)
    writeGenericProjectEvent(216)

    # write pattern data
    for i, pattern in enumerate(project.patterns):
        _write_event(f, "FLP_NewPat", i + 1)
        if pattern.name:
            _write_event(f, "FLP_Text_PatName", _str_to_UTF16(pattern.name))
        for miscKey in ["PatternAutomationData", "PatternData"]:
            if miscKey in pattern.misc:
                _write_event(f, miscKey, pattern.misc[miscKey])

    for data in project.projectInfo["UNKNOWN_226"]:
        _write_event(f, "UNKNOWN_226", data)

    # write automation clip data
    for channel in project.channels:
        if channel.type == "automation_clip":
            _write_event(f, "AutomationClipData", channel.data)

    # write channel data
    for i, channel in enumerate(project.channels):
        _write_event(f, "FLP_NewChan", i)
        # if "name" in channel: #(pretty sure this is mandatory)

        CHANNEL_TYPE_MAP = {
            "sampler": 0,
            "generator": 2,
            "audio_clip": 4,
            "automation_clip": 5,
        }
        _write_event(f, "FLP_ChanType", CHANNEL_TYPE_MAP[channel.type])

        _write_event(f, "FLP_Text_PluginName", channel.misc["FLP_Text_PluginName"])
        _write_event(f, "FLP_NewPlugin", channel.misc["FLP_NewPlugin"])

        _write_event(f, "ChannelName", _str_to_UTF16(channel.name))

        for miscKey in [
            "UNKNOWN_155",
            "FLP_Color",
            "FLP_PluginParams",
            "FLP_Enabled",
            "FLP_Delay",
            "FLP_Reverb",
            "FLP_IntStretch",
            "FLP_ShiftDelay",
            "UNKNOWN_97",
            "FLP_FX",
            "FLP_FX3",
            "FLP_CutOff",
            "FLP_Resonance",
            "FLP_PreAmp",
            "FLP_Decay",
            "FLP_Attack",
            "FLP_StDel",
            "FLP_FXSine",
            "FLP_Fade_Stereo",
            "FLP_MixSliceNum",
            "ChannelParams",
            "UNKNOWN_229",
            "UNKNOWN_221",
            "FLP_ChanParams",
            "FLP_CutCutBy",
            "UNKNOWN_144",
            "ChannelFilterGroup",
            "UNKNOWN_234",
            "UNKNOWN_32",
            "UNKNOWN_228",
            "FLP_SSNote",
            "ChannelEnvelopeParams",
            "UNKNOWN_143",
            "FLP_LoopType",
            "FLP_Text_SampleFileName",
            "UNKNOWN_142",
            "UNKNOWN_150",
            "UNKNOWN_157",
            "UNKNOWN_158",
            "UNKNOWN_164",
        ]:
            if miscKey in channel.misc:
                if isinstance(channel.misc[miscKey], list):
                    for data in channel.misc[miscKey]:
                        _write_event(f, miscKey, data)
                else:
                    _write_event(f, miscKey, channel.misc[miscKey])

        pass

    # write arrangement data
    for i, arrangement in enumerate(project.arrangements):
        _write_event(f, 99, i)
        if arrangement.name:
            _write_event(f, "ArrangementName", _str_to_UTF16(arrangement.name))
        _write_event(f, "UNKNOWN_36", arrangement.misc["UNKNOWN_36"])

        arrangement_data = _make_arrangement_data(arrangement)
        _write_event(f, 233, arrangement_data)
        for track in arrangement.tracks:
            _write_event(f, "TrackInfo", track.misc["TrackInfo"])
            if track.name:
                _write_event(f, "TrackName", _str_to_UTF16(track.name))

    # more globals, see grammar
    for eventId in [100, 29, 39, 40, 31, 38]:
        writeGenericProjectEvent(eventId)

    # write mixer data
    for mixerTrack in project.mixerTracks:
        _write_event(f, "MixerTrackInfo", mixerTrack.misc["MixerTrackInfo"])
        # write mixer effect slots
        for i in range(10):
            # if i != 0:
            _write_event(f, "SlotIndex", i)
            if i in mixerTrack.effects:
                effect = mixerTrack.effects[i]
                for miscKey in [
                    "FLP_Text_PluginName",
                    "FLP_NewPlugin",
                ]:
                    if miscKey in effect.misc:
                        _write_event(f, miscKey, effect.misc[miscKey])
                if effect.name:
                    _write_event(f, "ChannelName", _str_to_UTF16(effect.name))
                for miscKey in [
                    "UNKNOWN_155",
                    "FLP_Color",
                    "FLP_PluginParams",
                ]:
                    if miscKey in effect.misc:
                        _write_event(f, miscKey, effect.misc[miscKey])
            # if i == 0:
            #     _write_event(f, "SlotIndex", i)  # lol
        # mixer track postamble
        for miscKey in [
            "MixerTrackRouting",
            "InsertAudioInputSource",
            "InsertAudioOutputTarget",
            "MixerTrackColor",
            "MixerTrackIcon",
        ]:
            if miscKey in mixerTrack.misc:
                _write_event(f, miscKey, mixerTrack.misc[miscKey])
        if mixerTrack.name:
            _write_event(f, "InsertName", _str_to_UTF16(mixerTrack.name))

    # more globals, see grammar
    writeGenericProjectEvent(225)  # this is massive...
    writeGenericProjectEvent(133)

    # write back to the datalength
    endingPosition = f.tell()
    dataLength = (
        endingPosition - dataLengthPosition - 4
    )  # -4 because of the empty space we made for the size!
    print("{} bytes of event data".format(dataLength))
    f.seek(dataLengthPosition, 0)
    f.write(itob(dataLength, 4))


# _event_size_to_bytes test
# TODO move to a test file
def test_event_size_to_bytes():
    from flp_read import _read_TEXT_event_size
    import random
    from io import BytesIO

    for i in range(0, 100):
        size = random.randint(0, 2**128)
        sizeBytes = _event_size_to_bytes(size)
        f = BytesIO(sizeBytes)
        parsed = _read_TEXT_event_size(f)
        assert size == parsed, (
            "_event_size_to_bytes test failed: " f"{size} {parsed} {sizeBytes}"
        )


if __name__ == "__main__":
    test_event_size_to_bytes()

    from flp_read import load_FLP

    DEBUG = 1
    fd = open("test_comment_OUT_DEBUG.txt", "w")

    print("loading...")
    project = load_FLP("test/files/test_comment.flp")
    print("writing...")
    write_FLP("test_comment_OUT.flp", project)

    orig_file_len = len(open("test/files/test_comment.flp", "rb").read())
    new_file_len = len(open("test_comment_OUT.flp", "rb").read())
    print(f"Original file: {orig_file_len} bytes")
    print(
        f"New file: {new_file_len} bytes ({int(new_file_len/orig_file_len*100)}% of original file)"
    )
