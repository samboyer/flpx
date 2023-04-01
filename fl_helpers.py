############################################
# fl_helpers.py - Helper functions for FL Studio variables/quirks
# Feb 2022, Sam Boyer
# Part of the FLPX project
############################################


def pattern_i_name(project, i: int) -> str:
    if i >= len(project["patterns"]):  # ghost pattern
        return "Pattern {} (ghost)".format(i + 1)
    elif "FLP_Text_PatName" in project["patterns"][i]:
        return project["patterns"][i]["FLP_Text_PatName"].decode("UTF-16-LE")
    else:
        return "Pattern {}".format(i + 1)


def channel_i_name(project, i: int) -> str:
    return project["channels"][i]["name"]


def normalise_clip_start(s: int) -> int:
    """If a playlist item has never been shifted, the starting tick is
    inexplicably written as 3212836864 - map this to 0."""
    return s if s != 3212836864 else 0


def ticks_to_BST(project, ticks):
    numerator = project["projectInfo"]["FLP_PatLength"]
    denominator = project["projectInfo"]["FLP_BlockLength"]
    timebase = project["projectInfo"]["NBeatDiv"]
    ticksPerStep = timebase // 4
    stepsPerBar = numerator * (16 // denominator)
    bar = ticks // (stepsPerBar * ticksPerStep) + 1
    step = (ticks // ticksPerStep) % stepsPerBar + 1
    tick = ticks % ticksPerStep

    return "{}:{:02d}:{:02d}".format(bar, step, tick)
