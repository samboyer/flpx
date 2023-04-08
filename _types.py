############################################
# _types.py - Class definitions for FLP items
# Apr 2023, Sam Boyer
# Part of the FLPX project
############################################

from dataclasses import dataclass, field
from typing import Any, Optional, Union


@dataclass
class PlaylistItem:
    start: int  # position in playlist, in ticks
    length: int  # length of item, in ticks
    track: int  # which track this item is on (i.e. 'y coordinate')
    clipStart: int  # position in the Pattern where this clip starts, in ticks. # TODO rename to clipOffset
    clipEnd: int  # position in the Pattern wehre this clip ends, in ticks. # TODO isn't this always clipStart+length
    muted: bool  # is this clip muted?
    selected: bool  # is this clip currently selected in the playlist?
    itemType: str  # type of tis clip. allowed values are 'pattern', 'channel' (audio clip or automation)
    # TODO make PatternItem, AutomationClipItem, AudioClipItem subclasses when doing 21.0 support, so they can have extra parameters
    clipIndex: int  # index of this item's Pattern or Audio CLip/Automation Clip generator, depending on its type.

    misc_4_6: bytes
    misc: bytes
    """Additional unknown bytes."""
    # TODO should this class have a reference to the Pattern/AudioClip/AutomationClip generator object?


@dataclass
class PlaylistArrangement:
    name: Optional[str] = None  # if none, show as 'Arrangement i' etc (I think)
    items: list[PlaylistItem] = field(default_factory=list)
    tracks: list[Any] = field(default_factory=list)

    misc: dict[str, Union[int, bytes]] = field(default_factory=dict)
    """Dictionary of data we don't currently know how to handle.
    Keys are Event names, values are either ints or bytes depending on event type."""


@dataclass
class Pattern:
    name: Optional[str] = None  # if none, show as 'Pattern i' etc (I think)

    misc: dict[str, Union[int, bytes]] = field(default_factory=dict)
    """Dictionary of data we don't currently know how to handle.
    Keys are Event names, values are either ints or bytes depending on event type."""


@dataclass
class Channel:
    """Object representing a Generator (synth, audioclip, automation clip etc)"""

    name: str = ""

    type: str = ""  # TODO make this an enum 'generator, audio_clip, automation_clip'

    data: Optional[bytes] = None

    misc: dict[str, Union[int, bytes]] = field(default_factory=dict)
    """Dictionary of data we don't currently know how to handle.
    Keys are Event names, values are either ints or bytes depending on event type."""

    # TODO subclass this and store automationclip data here?
    # TODO expand misc (muted, FLP_ChanParams)


@dataclass
class ArrangementTrack:
    """Object representing a track (row) in the arrangement."""

    name: Optional[str] = None  # if None, shown as 'Track i'

    misc: dict[str, Union[int, bytes]] = field(default_factory=dict)
    """Dictionary of data we don't currently know how to handle.
    Keys are Event names, values are either ints or bytes depending on event type."""

    # TODO decode TrackInfo event (is it a child, is it muted, etc.)


@dataclass
class MixerEffect:
    """Object representing a mixer track in the Mixer."""

    # TODO make this a subclass of Channel?

    name: str = ""
    misc: dict[str, Union[int, bytes]] = field(default_factory=dict)
    """Dictionary of data we don't currently know how to handle.
    Keys are Event names, values are either ints or bytes depending on event type."""


@dataclass
class MixerTrack:
    """Object representing a mixer track in the Mixer."""

    name: Optional[str] = None  # if None, shown as 'Insert i'

    effects: dict[int, MixerEffect] = field(default_factory=dict)
    """Collection of mixer effects, keyed on their slot index (starting at 0!)"""

    misc: dict[str, Union[int, bytes]] = field(default_factory=dict)
    """Dictionary of data we don't currently know how to handle.
    Keys are Event names, values are either ints or bytes depending on event type."""


@dataclass
class Project:
    """Object representing an FL Studio project (.flp file)."""

    projectInfo: dict[str, Any] = field(default_factory=dict)
    """Miscellaneous info about this project."""

    arrangements: list[PlaylistArrangement] = field(default_factory=list)
    channels: list[Channel] = field(default_factory=list)
    patterns: list[Pattern] = field(default_factory=list)
    channelFilterGroups: list[dict[str, Any]] = field(default_factory=list)
    mixerTracks: list[MixerTrack] = field(default_factory=list)
    """List of mixer tracks. Currently includes Master & Current."""  # TODO move master & current to their own members
