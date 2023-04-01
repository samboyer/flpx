############################################
# flp_write.py - write project data back to FLP file
# Feb 2022, Sam Boyer
# Part of the FLPX project
############################################


from typing import BinaryIO, Union
from flp_read import eventIdToName


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


def _write_event(f: BinaryIO, eventId: int, data: Union[int, bytes]) -> None:
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


def write_FLP(filepath, project):
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
        name = eventIdToName(eventId)  # the name I've given to this event
        _write_event(f, eventId, project["projectInfo"][name])

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
    for channelGroup in project["channelGroups"]:
        _write_event(f, 231, _str_to_UTF16(channelGroup["name"]))

    # 146 CurrentChannelFilterGroup, 216 unknown
    writeGenericProjectEvent(146)
    writeGenericProjectEvent(216)

    # write pattern data
    for pattern in project["patterns"]:
        # TODO next:)
        pass

    # 226 Unknown
    # 226 Unknown
    # 226 Unknown
    # TODO what are these events??

    # write automation clip data
    # TODO idek how to represent this yet...

    # write channel data
    for channel in project["channels"]:
        # TODO
        pass

    # write arrangement data
    for arrangement in project["arrangements"]:
        # TODO
        for trackIndex in range(0, 501):
            # TODO
            pass

    # more globals, see grammar
    for eventId in [100, 29, 39, 40, 31, 38]:
        writeGenericProjectEvent(eventId)

    # write mixer data
    for i in range(0, 128):
        # TODO
        pass

    # more globals, see grammar
    writeGenericProjectEvent(225)
    writeGenericProjectEvent(133)

    # write back to the datalength
    endingPosition = f.tell()
    dataLength = (
        endingPosition - dataLengthPosition - 4
    )  # -4 because of the empty space we made for the size!
    print("{} bytes of event data".format(dataLength))
    f.seek(dataLengthPosition, 0)
    f.write(itob(dataLength, 4))


if __name__ == "__main__":
    # _event_size_to_bytes test
    # TODO move to a test file
    from flp_read import readTEXTEventSize
    import random
    import io

    for i in range(0, 100):
        size = random.randint(0, 2**128)
        sizeBytes = _event_size_to_bytes(size)
        f = io.BytesIO(sizeBytes)
        parsed = readTEXTEventSize(f)
        assert size == parsed, (
            "_event_size_to_bytes test failed: " f"{size} {parsed} {sizeBytes}"
        )

    from flp_read import loadFLP

    print("loading...")
    project = loadFLP("test comment.flp")
    print("writing...")
    write_FLP("testWrite.flp", project)
