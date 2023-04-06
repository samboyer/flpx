############################################
# readFLP.py - FLP file parsing functions
# Feb 2021, Sam Boyer
# Part of the FLPX project
############################################

import hashlib
import sys
from dataclasses import dataclass, field

from _types import *
import fl_helpers


# define exports
__all__ = ["load_FLP"]

# OPTIONS
PRINT_EVENTS = "-events" in sys.argv
PRINT_VALUES = "-values" in sys.argv
HASH_VALUES = "-hashvalues" in sys.argv

# CONSTANTS
HEADERCHUNKID = b"FLhd"
DATACHUNKID = b"FLdt"


# UTIL FUNCTIONS
def error(msg):
    raise Exception("Error: " + msg)


def warn(msg):
    print("Warning: " + msg, file=sys.stderr)


def btoi(bytes):
    """Convert little-endian bytes to an int."""
    return int.from_bytes(bytes, "little")


# https://stackoverflow.com/a/15365026/6560491
def _length_of_file(f):
    currentPos = f.tell()
    f.seek(0, 2)  # move to end of file
    length = f.tell()  # get current position
    f.seek(currentPos, 0)  # go back to where we started
    return length


def _bytes_until_end(f, fileLength):
    return fileLength - f.tell()


# PARSING FUNCTIONS


def _read_TEXT_event_size(f):
    """Parse the size of a TEXT event, using gol's funky encoding"""
    eventSize = 0
    continueReading = True
    shiftAmnt = 0
    while continueReading:
        byte = btoi(f.read(1))
        eventSize += (byte & 127) << shiftAmnt
        continueReading = (byte & 128) == 128
        shiftAmnt += 7
    # print(eventSize)
    return eventSize


def _event_size(eventId, f):
    """Return the size of this event in bytes."""
    if eventId < 64:
        return 1
    elif eventId < 128:
        return 2
    elif eventId < 192:
        return 4
    else:
        return _read_TEXT_event_size(f)


def _decode_playlist_item(itemData: bytes) -> PlaylistItem:
    """Decode binary data for a single item in a playlist/arrangement."""
    # Notes:
    #   4-6 is always b'\x00P'
    #   20-24 is always b'@d\x80\x80'
    #  ^(should i make warnings for these?)
    #   suspect they're something to do with performance mode (out of scope for now)

    itemId = btoi(itemData[6:8])  # the identifier for this item
    if itemId > 20480:
        itemType = "pattern"
        clipIndex = itemId - 20481
    else:
        # item is instead defined by the index of the audio clip/automation clip in the Channel list
        itemType = "channel"
        clipIndex = itemId

    return PlaylistItem(
        start=btoi(itemData[0:4]),  # position in playlist, in ticks
        length=btoi(itemData[8:12]),
        track=500 - btoi(itemData[12:16]),  # ie y position
        clipStart=btoi(itemData[24:28]),  # start of the clip, in ticks
        clipEnd=btoi(itemData[28:32]),
        misc=itemData[16:20],  # contains muted bit, probs other stuff
        muted=itemData[19] & 32 != 0,
        selected=itemData[19] & 128 != 0,
        itemType=itemType,
        clipIndex=clipIndex,
    )


EID_NAMES = {
    # BYTE events
    0: "FLP_Enabled",
    1: "FLP_NoteOn",
    2: "FLP_Vol",
    3: "FLP_Pan",
    4: "FLP_MIDIChan",
    5: "FLP_MIDINote",
    6: "FLP_MIDIPatch",
    7: "FLP_MIDIBank",
    9: "FLP_LoopActive",
    10: "FLP_ShowInfo",
    11: "FLP_Shuffle",
    12: "FLP_MainVol",
    13: "FLP_Stretch",
    14: "FLP_Pitchable",
    15: "FLP_Zipped",
    16: "FLP_Delay_Flags",
    17: "FLP_PatLength",
    18: "FLP_BlockLength",
    19: "FLP_UseLoopPoints",
    20: "FLP_LoopType",
    21: "FLP_ChanType",
    22: "FLP_MixSliceNum",
    # WORD events
    64: "FLP_NewChan",
    65: "FLP_NewPat",
    66: "FLP_Tempo",
    67: "FLP_CurrentPatNum",
    68: "FLP_PatData",
    69: "FLP_FX",
    70: "FLP_Fade_Stereo",
    71: "FLP_CutOff",
    72: "FLP_DotVol",
    73: "FLP_DotPan",
    74: "FLP_PreAmp",
    75: "FLP_Decay",
    76: "FLP_Attack",
    77: "FLP_DotNote",
    78: "FLP_DotPitch",
    79: "FLP_DotMix",
    80: "FLP_MainPitch",
    81: "FLP_RandChan",
    82: "FLP_MixChan",
    83: "FLP_Resonance",
    84: "FLP_LoopBar",
    85: "FLP_StDel",
    86: "FLP_FX3",
    87: "FLP_DotReso",
    88: "FLP_DotCutOff",
    89: "FLP_ShiftDelay",
    90: "FLP_LoopEndBar",
    91: "FLP_Dot",
    92: "FLP_DotShift",
    # DWORD events
    128: "FLP_Color",
    129: "FLP_PlayListItem",
    130: "FLP_Echo",
    131: "FLP_FXSine",
    132: "FLP_CutCutBy",
    133: "FLP_WindowH",
    134: "FLP_MiddleNote",
    135: "FLP_Reserved",
    136: "FLP_MainResoCutOff",
    137: "FLP_DelayReso",
    138: "FLP_Reverb",
    139: "FLP_IntStretch",
    140: "FLP_SSNote",
    141: "FLP_FineTune",
    # TEXT events
    192: "FLP_Text_ChanName",
    193: "FLP_Text_PatName",
    194: "FLP_Text_Title",
    195: "FLP_Text_Comment",
    196: "FLP_Text_SampleFileName",
    197: "FLP_Text_URL",
    198: "FLP_Text_CommentRTF",
    199: "FLP_Version",
    201: "FLP_Text_PluginName",
    208: "FLP_MIDICtrls",
    209: "FLP_Delay",
    210: "FLP_TS404Params",
    211: "FLP_DelayLine",
    212: "FLP_NewPlugin",
    213: "FLP_PluginParams",
    215: "FLP_ChanParams",
    # suspected events
    31: "IsPerformanceMode",  # 0 if off, 1 if on
    95: "MixerTrackIcon",  # TODO check this is actually true
    98: "SlotIndex",  # comes after a plugin in this slot!
    99: "ArrangementIndex",
    100: "CurrentArrangement",
    145: "ChannelFilterGroup",  # the group this channel belongs to
    146: "CurrentChannelFilterGroup",  # 4294967295 for 'All'
    147: "InsertAudioOutputTarget",  # 4294967295 if (none), index of the output target otherwise.
    149: "MixerTrackColor",
    154: "InsertAudioInputSource",  # 4294967295 if (none), index of the input source otherwise.
    156: "Tempo",
    203: "ChannelName",  # also applies to mixer slots!
    204: "InsertName",
    206: "ProjectInfoGenre",
    207: "ProjectInfoAuthor",
    218: "ChannelEnvelopeParams",  # one for each ADSR (pan,vol,x,y,pitch).
    219: "ChannelParams",  # contains channel volume, pan values
    223: "PatternAutomationData",  # only appears when a pattern contains automation curves
    224: "PatternData",
    227: "AutomationClipData",
    231: "ChannelFilterGroupName",
    233: "PlaylistData",
    235: "MixerTrackRouting",  # 1 if routes to this channel, 0 otherwise. probably deprecated cause new ones can be partial/automated?
    238: "TrackInfo",  # contains index, muted bit, not the name tho!
    239: "TrackName",
    241: "ArrangementName",
    # TODO need to confirm these
    159: "FLP_Version_Minor",  # eg 2553,
    236: "MixerTrackInfo",
    # 236 - one for each mixer channel. possibly also encodes mutedness, volume,pan,stereo,eq,
    #    b'\x00\x00\x00\x00L\x00\x00\x00\x00\x00\x00\x00'    if Insert 1-125,
    #    b'\x00\x00\x00\x00\x0c\x00\x00\x00\x00\x00\x00\x00' if master or current.
}

ENAME_IDS = {v: k for k, v in EID_NAMES.items()}


def eid_to_ename(id: int) -> str:
    if id in EID_NAMES:
        return EID_NAMES[id]
    else:
        return "UNKNOWN_" + str(id)


def ename_to_eid(event_name: str) -> int:
    if event_name.startswith("UNKNOWN_"):
        return int(event_name[8:])
    else:
        return ENAME_IDS[event_name]


# STATEFUL FILE PARSER


@dataclass
class ParserContext:
    currentArrangement: int = -1
    currentArrangementTrack: int = -1
    currentPattern: int = -1
    currentChannel: int = -1
    currentMixerTrack: int = -1
    currentMixerTrackEffectSlot: int = -1
    isMixerEffect: bool = False
    project: Project = field(default_factory=Project)


def _default_project_info():
    """return a projectInfo dict with some sane defaults."""
    return {
        "FLP_PatLength": 4,
        "FLP_BlockLength": 4,
        "NBeatDiv": 96,
    }


def _handle_flp_event(ctx: ParserContext, eventId: int, contents: bytes):
    eventName = eid_to_ename(eventId)
    project = ctx.project
    # convert numeric events into ints, otherwise leave as bytes
    if eventId < 192:
        contents = btoi(contents)

    # event handlers

    def genericProject():
        project.projectInfo[eventName] = contents

    def genericChannel():
        project.channels[ctx.currentChannel].misc[eventName] = contents

    def genericChannelAppend():
        if eventName not in project.channels[ctx.currentChannel].misc:
            project.channels[ctx.currentChannel].misc[eventName] = []
        project.channels[ctx.currentChannel].misc[eventName].append(contents)

    def genericArrangement():
        project.arrangements[ctx.currentArrangement].misc[eventName] = contents

    def genericPattern():
        project.patterns[ctx.currentPattern].misc[eventName] = contents

    def genericMixerTrack():
        project.mixerTracks[ctx.currentMixerTrack].misc[eventName] = contents

    def genericMixerEffect():
        effects = project.mixerTracks[ctx.currentMixerTrack].effects
        if ctx.currentMixerTrackEffectSlot not in effects:
            effects[ctx.currentMixerTrackEffectSlot] = MixerEffect()
        effects[ctx.currentMixerTrackEffectSlot].misc[eventName] = contents

    def genericChannelOrMixerEffect():
        if ctx.isMixerEffect:
            genericMixerEffect()
        else:
            genericChannel()

    def patternName():
        project.patterns[ctx.currentPattern].name = contents.decode("UTF-16-LE")

    def channelName():
        if ctx.isMixerEffect:
            project.mixerTracks[ctx.currentMixerTrack].effects[
                ctx.currentMixerTrackEffectSlot
            ].name = contents.decode("UTF-16-LE")
        else:
            project.channels[ctx.currentChannel].name = contents.decode("UTF-16-LE")

    def arrangementName():
        project.arrangements[ctx.currentArrangement].name = contents.decode("UTF-16-LE")

    def arrangementTrackName():
        project.arrangements[ctx.currentArrangement].tracks[
            ctx.currentArrangementTrack
        ].name = contents.decode("UTF-16-LE")

    def mixerTrackName():
        project.mixerTracks[ctx.currentMixerTrack].name = contents.decode("UTF-16-LE")

    def newChannel():
        ctx.currentChannel = contents
        ctx.isMixerEffect = False
        if ctx.currentChannel >= len(project.channels):
            project.channels.append(Channel())

    def newPattern():
        index = contents - 1
        ctx.currentPattern = index
        if ctx.currentPattern >= len(project.patterns):
            project.patterns.append(Pattern())

    def newArrangement():
        ctx.currentArrangement = contents
        project.arrangements.append(PlaylistArrangement())

    def newMixerTrack():
        ctx.currentMixerTrack = len(project.mixerTracks)
        project.mixerTracks.append(MixerTrack(misc={eventName: contents}))

    def newArrangementTrack():
        ctx.currentArrangementTrack = len(
            project.arrangements[ctx.currentArrangement].tracks
        )
        project.arrangements[ctx.currentArrangement].tracks.append(
            ArrangementTrack(misc={eventName: contents})
        )

    def newChannelFilterGroup():
        project.channelFilterGroups.append({"name": contents.decode("UTF-16-LE")})

    def parsePlaylistData():
        bytesPerItem = 32
        numItems = len(contents) // bytesPerItem
        for item in range(numItems):
            itemData = contents[item * bytesPerItem : (item + 1) * bytesPerItem]
            item = _decode_playlist_item(itemData)
            project.arrangements[ctx.currentArrangement].items.append(item)
        # print(len(project.arrangements[ctx.currentArrangement].items))

    def setCtxSlotIndex():
        ctx.currentMixerTrackEffectSlot = contents
        ctx.isMixerEffect = True

    handlerLUT = {
        # per-project
        "FLP_ShowInfo": genericProject,
        "FLP_Shuffle": genericProject,
        "FLP_PatLength": genericProject,
        "FLP_BlockLength": genericProject,
        "FLP_CurrentPatNum": genericProject,
        "FLP_MainPitch": genericProject,
        "FLP_WindowH": genericProject,
        "FLP_Text_Title": genericProject,
        "FLP_Text_Comment": genericProject,
        "FLP_Text_URL": genericProject,
        "FLP_Text_CommentRTF": genericProject,
        "FLP_Version": genericProject,
        "IsPerformanceMode": genericProject,
        "CurrentArrangement": genericProject,
        "CurrentChannelFilterGroup": genericProject,
        "Tempo": genericProject,
        "ProjectInfoGenre": genericProject,
        "ProjectInfoAuthor": genericProject,
        "FLP_Version_Minor": genericProject,
        "FLP_LoopActive": genericProject,
        "UNKNOWN_28": genericProject,
        "UNKNOWN_37": genericProject,
        "UNKNOWN_200": genericProject,
        "UNKNOWN_35": genericProject,
        "UNKNOWN_23": genericProject,
        "UNKNOWN_30": genericProject,
        "UNKNOWN_202": genericProject,
        "UNKNOWN_237": genericProject,
        "UNKNOWN_216": genericProject,
        "UNKNOWN_29": genericProject,
        "UNKNOWN_39": genericProject,
        "UNKNOWN_40": genericProject,
        "UNKNOWN_38": genericProject,
        "UNKNOWN_225": genericProject,
        # per-channel
        "FLP_NewChan": newChannel,
        "FLP_Enabled": genericChannel,
        "FLP_LoopType": genericChannel,
        "FLP_ChanType": genericChannel,
        "FLP_MixSliceNum": genericChannel,
        "FLP_FX": genericChannel,
        "FLP_Text_SampleFileName": genericChannel,
        "FLP_Fade_Stereo": genericChannel,
        "FLP_CutOff": genericChannel,
        "FLP_PreAmp": genericChannel,
        "FLP_Decay": genericChannel,
        "FLP_Attack": genericChannel,
        "FLP_Resonance": genericChannel,
        "FLP_StDel": genericChannel,
        "FLP_FX3": genericChannel,
        "FLP_ShiftDelay": genericChannel,
        "FLP_FXSine": genericChannel,
        "FLP_CutCutBy": genericChannel,
        "FLP_Reverb": genericChannel,
        "FLP_IntStretch": genericChannel,
        "FLP_SSNote": genericChannel,
        "FLP_Delay": genericChannel,
        "FLP_ChanParams": genericChannel,
        "ChannelName": channelName,
        "ChannelEnvelopeParams": genericChannelAppend,
        "ChannelParams": genericChannel,
        "ChannelFilterGroup": genericChannel,
        "UNKNOWN_32": genericChannel,
        "UNKNOWN_97": genericChannel,
        "UNKNOWN_143": genericChannel,
        "UNKNOWN_144": genericChannel,
        "UNKNOWN_221": genericChannel,
        "UNKNOWN_229": genericChannel,
        "UNKNOWN_228": genericChannelAppend,
        "UNKNOWN_234": genericChannel,
        # less confident about these, they only come up on one channel in the test file...
        "UNKNOWN_150": genericChannel,
        "UNKNOWN_157": genericChannel,
        "UNKNOWN_158": genericChannel,
        "UNKNOWN_164": genericChannel,
        "UNKNOWN_142": genericChannel,
        # per-pattern
        "FLP_NewPat": newPattern,
        "FLP_Text_PatName": patternName,
        "PatternAutomationData": genericPattern,
        "PatternData": genericPattern,
        # context-aware (target changes based on position)
        "FLP_Color": genericChannelOrMixerEffect,
        "FLP_Text_PluginName": genericChannelOrMixerEffect,
        "FLP_NewPlugin": genericChannelOrMixerEffect,
        "FLP_PluginParams": genericChannelOrMixerEffect,
        "UNKNOWN_155": genericChannelOrMixerEffect,
        # per-mixer track
        "MixerTrackInfo": newMixerTrack,
        "InsertAudioOutputTarget": genericMixerTrack,
        "InsertAudioInputSource": genericMixerTrack,
        "InsertName": mixerTrackName,
        "MixerTrackRouting": genericMixerTrack,
        "MixerTrackColor": genericMixerTrack,
        "MixerTrackIcon": genericMixerTrack,
        # per-mixer effect
        "SlotIndex": setCtxSlotIndex,
        # per-arrangement
        "ArrangementIndex": newArrangement,
        "ArrangementName": arrangementName,
        "PlaylistData": parsePlaylistData,
        "UNKNOWN_36": genericArrangement,
        # per-track-per-arrangement
        "TrackInfo": newArrangementTrack,
        "TrackName": arrangementTrackName,
        # other
        "AutomationClipData": None,  # TODO what.how.
        "ChannelFilterGroupName": newChannelFilterGroup,
    }

    if eventName not in handlerLUT:
        warn("Missing event handler for event " + eventName)
        return

    if handlerLUT[eventName] != None:
        handlerLUT[eventName]()


def load_FLP(filepath):
    f = open(filepath, "rb")
    # 'state' of the parser - e.g. which channel/arrangement/patter we're currently populating
    ctx = ParserContext()

    headerChunkID = f.read(4)
    if headerChunkID != HEADERCHUNKID:
        error("This isn't an FLP file")

    headerLength = btoi(f.read(4))
    if headerLength != 6:
        error("invalid header length")

    headerFormat = btoi(f.read(2))
    if headerFormat != 0:
        warn("header format not 0")

    headerNChannels = btoi(f.read(2))  #'not really used'
    headerBeatDiv = btoi(
        f.read(2)
    )  # 'Pulses per quarter of the song.' (eg resolution) (mine is 96)

    dataChunkId = f.read(4)
    if dataChunkId != DATACHUNKID:
        error("incorrect data chunk ID")

    dataLength = btoi(f.read(4))  # number of remaining bytes
    fileLength = _length_of_file(f)
    actualDataLength = _bytes_until_end(f, fileLength)

    if dataLength != actualDataLength:
        error("file truncation error (DATA length incorrect)")

    # 'The whole data chunk is a succession of EVENTS'
    while _bytes_until_end(f, fileLength) != 0:
        eventId = btoi(f.read(1))
        contents = f.read(_event_size(eventId, f))

        _handle_flp_event(ctx, eventId, contents)
        debug_print_flp_event(eventId, contents)

    return ctx.project


def debug_print_flp_event(eventId, contents):
    if eventId not in EID_NAMES:
        # warn("Unknown Event ID " + str(eventId) + ", skipping")
        if PRINT_EVENTS:
            print(eventId, "Unknown")

        if PRINT_VALUES:
            if eventId < 192:
                print(btoi(contents))
            else:
                if HASH_VALUES:
                    print(hashlib.md5(contents).digest().hex())
                else:
                    print(contents)

    else:  # event known
        eventName = EID_NAMES[eventId]

        if PRINT_EVENTS:
            print(eventId, eventName)
        if PRINT_VALUES:
            if eventId < 192:
                print(btoi(contents))
            else:
                try:
                    # print(contents.decode('UTF-16-LE'))
                    print(contents)
                except:
                    if HASH_VALUES:
                        print(hashlib.md5(contents).digest().hex())
                    else:
                        print(contents)


def debug_print_main_playlist(project: Project):
    for item in project.arrangements[0].items:
        name = ""
        if item.itemType == "channel":
            name = project.channels[item.clipIndex].name
        else:  # pattern
            if item.clipIndex >= len(project.patterns):  # ghost pattern
                name = "Pattern {} (ghost)".format(item.clipIndex + 1)
            elif project.patterns[item.clipIndex].name:
                name = project.patterns[item.clipIndex].name
            else:
                name = "Pattern {}".format(item.clipIndex + 1)
        print(
            "{} at Track {}, {}".format(
                name, item.track, fl_helpers.ticks_to_BST(project, item.start)
            )
        )


if __name__ == "__main__":
    PRINT_EVENTS = "-events" in sys.argv
    PRINT_VALUES = "-values" in sys.argv
    HASH_VALUES = "-hashvalues" in sys.argv

    if len(sys.argv) < 2:
        print("Usage: flp_read.py path_to_flp")
        exit(1)

    INPUTFILE = sys.argv[-1]

    project = load_FLP(INPUTFILE)

    debug_print_main_playlist(project)


"""
interesting notes

when FLP_Text_PluginName == b'\x00\x00', the plugin is either a Sampler or an Automation Clip. mb other things too

vst plugins have FLP_Text_PluginName 'Fruity Wrapper', builtin ones have proper names

mixer channel indexes: master is 0, insert 125 are as usual, Current is 126
"""
