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
def itob(x: int, length: int) -> bytes:
    """Convert an integer to a bytes object, padded to `length`"""
    return int.to_bytes(x, length, "little")


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


def _make_arrangement_data(arrangement: PlaylistArrangement) -> bytes:
    size = 32 * len(arrangement.items)
    out = b""
    for item in arrangement.items:
        item_bytes = (
            itob(item.start, 4)  # 0-4
            + b"\0\0"  # 4-6
            + itob(
                item.clipIndex + 20481
                if item.itemType == "channel"
                else item.clipIndex,
                2,
            )  # 6-8
            + itob(item.length, 4)  # 8-12
            + itob(500 - item.track, 4)  # 12-16
            + item.misc  # 16-20
            + b"\0\0\0\0"  # 20-24
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
        _write_event(f, 65, i + 1)
        if pattern.name:
            _write_event(f, 193, _str_to_UTF16(pattern.name))
        for miscKey in ["PatternAutomationData", "PatternData"]:
            if miscKey in pattern.misc:
                _write_event(f, miscKey, pattern.misc[miscKey])

    # 226 Unknown
    # 226 Unknown
    # 226 Unknown
    # TODO what are these events??

    # write automation clip data
    for channel in project.channels:
        # if channel.type == "automationClip":
        # _write_event(f, "AutomationClipData", None)
        # TODO need to parse it first
        pass

    # write channel data
    for i, channel in enumerate(project.channels):
        _write_event(f, "FLP_NewChan", i)
        # if "name" in channel: #(pretty sure this is mandatory)
        _write_event(f, "ChannelName", _str_to_UTF16(channel.name))

        for miscKey in [
            "FLP_NewPlugin",
            "FLP_Enabled",
            "FLP_LoopType",
            "FLP_ChanType",
            "FLP_MixSliceNum",
            "FLP_FX",
            "FLP_Fade_Stereo",
            "FLP_CutOff",
            "FLP_PreAmp",
            "FLP_Decay",
            "FLP_Attack",
            "FLP_Resonance",
            "FLP_StDel",
            "FLP_FX3",
            "FLP_ShiftDelay",
            "FLP_FXSine",
            "FLP_CutCutBy",
            "FLP_Reverb",
            "FLP_IntStretch",
            "FLP_SSNote",
            "FLP_Delay",
            "FLP_ChanParams",
            "ChannelName",
            "UNKNOWN_228",
            "ChannelEnvelopeParams",
            "ChannelParams",
            "ChannelFilterGroup",
            "UNKNOWN_234",
            "UNKNOWN_32",
            "UNKNOWN_97",
            "UNKNOWN_143",
            "UNKNOWN_144",
            "UNKNOWN_221",
            "UNKNOWN_229",
            "UNKNOWN_150",
            "UNKNOWN_157",
            "UNKNOWN_158",
            "UNKNOWN_164",
            "FLP_Text_SampleFileName",
            "UNKNOWN_142",
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
        if mixerTrack.name:
            _write_event(f, "InsertName", _str_to_UTF16(mixerTrack.name))
        for miscKey in ["PatternAutomationData", "PatternData"]:
            if miscKey in mixerTrack.misc:
                _write_event(f, miscKey, mixerTrack.misc[miscKey])
        # write mixer effect slots
        for i in range(10):
            _write_event(f, "SlotIndex", i)
            if i in mixerTrack.effects:
                effect = mixerTrack.effects[i]
                for miscKey in [
                    "FLP_Text_PlLuginName",
                    "FLP_NewPlugin",
                    "UNKNOWN_155",
                    "FLP_Color",
                    "FLP_PluginParams",
                ]:
                    if miscKey in effect.misc:
                        _write_event(f, miscKey, effect.misc[miscKey])

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
