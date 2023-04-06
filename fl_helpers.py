############################################
# fl_helpers.py - Helper functions for FL Studio variables/quirks
# Feb 2022, Sam Boyer
# Part of the FLPX project
############################################

from _types import *


def pattern_i_name(project, i: int) -> str:
    if i >= len(project.patterns):  # ghost pattern
        return "Pattern {} (ghost)".format(i + 1)
    elif "FLP_Text_PatName" in project.patterns[i]:
        return project.patterns[i]["FLP_Text_PatName"].decode("UTF-16-LE")
    else:
        return "Pattern {}".format(i + 1)


def channel_i_name(project, i: int) -> str:
    return project.channels[i]["name"]


def normalise_clip_start(s: int) -> int:
    """If a playlist item has never been shifted, the starting tick is
    inexplicably written as 3212836864 - map this to 0."""
    return s if s != 3212836864 else 0


DEFAULT_BEATDIV = 96
DEFAULT_BLOCKLENGTH = 4
DEFAULT_PATLENGTH = 4


def ticks_to_BST(project: Project, ticks: int) -> str:
    numerator = (
        project.projectInfo["FLP_PatLength"]
        if "FLP_PatLength" in project.projectInfo
        else DEFAULT_PATLENGTH
    )
    denominator = (
        project.projectInfo["FLP_BlockLength"]
        if "FLP_BlockLength" in project.projectInfo
        else DEFAULT_BLOCKLENGTH
    )
    timebase = (
        project.projectInfo["NBeatDiv"]
        if "NBeatDiv" in project.projectInfo
        else DEFAULT_BEATDIV
    )
    ticksPerStep = timebase // 4
    stepsPerBar = numerator * (16 // denominator)
    bar = ticks // (stepsPerBar * ticksPerStep) + 1
    step = (ticks // ticksPerStep) % stepsPerBar + 1
    tick = ticks % ticksPerStep

    return "{}:{:02d}:{:02d}".format(bar, step, tick)
