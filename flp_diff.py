############################################
# flp_diff.py - diff and merge parsed FLP projects
# Feb 2022, Sam Boyer
# Part of the FLPX project
############################################


from typing import Any, Callable, Optional
from flp_read import loadFLP
import sys
import fl_helpers
from collections import defaultdict


class ArrangementChange:
    state: str  # 'added|deleted|modified|moved' (modified takes priority over moved)
    index: Optional[int] = None
    data: Optional[dict[str, Any]] = None


def diff_arrangement(
    arr1: dict[str, Any], arr2: dict[str, Any]
) -> list[ArrangementChange]:
    """Returns information about the differences between two versions of an
    arrangement.

    Limitations/assumptions:
    - assumes pattern/channel indexes between the two channels are identical.
        TODO detect changes in pattern/channel indexes, resolve in an earlier function
    - moving a clip slightly sideways counts as deletion and reinsertion
    - assumes time resolution is the same
    - ignores changes to track names/states
    Returns: a list of changes. changes are of the form

    {
      state: 'added|deleted|modified|moved' (modified takes priority over moved)
      index: int  (the index of this item in arr1. None if it's a new item)
      data: PlaylistItem (optional)
    }s
    TODO consider making 'muted/unmuted' a state type rather than just modified?
    """

    items2Dict = defaultdict(list)  # keyed on clipID and start time.
    # values are arrays of hits (bc same clip can be on same tick multiple times)

    for item in arr2["items"]:
        key = (item["type"], item["clipIndex"], item["start"])
        items2Dict[key].append(item)

    changes = []

    for i in range(len(arr1["items"])):
        item = arr1["items"][i]
        key = (item["type"], item["clipIndex"], item["start"])

        if key in items2Dict:
            matches = items2Dict[key]
            if len(matches) > 1:
                # find the closest one in y coordinates(for more accurate linking)
                dists = [abs(item["track"] - i2["track"]) for i2 in matches]
                matchI = dists.index(min(dists))
            else:
                matchI = 0
            match = matches[matchI]

            del items2Dict[key][matchI]  # so it's no longer 'added'

            # now determine if it's changed
            # (we already checked start, type, index. leaves length, track, clip start,end, status)
            clipStartA = fl_helpers.normalise_clip_start(item["clipStart"])
            clipStartB = fl_helpers.normalise_clip_start(match["clipStart"])

            hasMoved = item["track"] != match["track"]
            isModified = (
                item["length"] != match["length"]
                or clipStartA
                != clipStartB  # i dont think clipEnd can change while clipStart/length stay the same
                or item["muted"] != match["muted"]
            )
            if isModified or hasMoved:
                changes.append(
                    ArrangementChange(
                        state="modified" if isModified else "moved",
                        index=i,
                        data=match,
                    )
                )
        else:  # item doesn't appear in arr2
            changes.append(
                ArrangementChange(
                    state="deleted",
                    index=i,
                )
            )

    # add remaining arr2 items as added
    for items in items2Dict.values():
        for item in items:  # remember the dict contains lists!
            changes.append(ArrangementChange(state="added", data=item))

    return changes


def debug_describe_arrangement_diff_verbose(
    project, arrangement, changes: list[ArrangementChange]
):
    for change in changes:
        # TODO handle ghost patterns
        if "index" in change:
            item = arrangement["items"][change.index]
            name = (
                fl_helpers.getNameOfPattern(project, item["clipIndex"])
                if item["type"] == "pattern"
                else fl_helpers.channel_i_name(project, item["clipIndex"])
            )
        elif "data" in change:
            name = (
                fl_helpers.getNameOfPattern(project, change.data["clipIndex"])
                if change.data["type"] == "pattern"
                else fl_helpers.channel_i_name(project, change.data["clipIndex"])
            )

        if change.state == "added":
            print(
                "{} added at {}".format(
                    name, fl_helpers.ticks_to_BST(project, change.data["start"])
                )
            )
        elif change.state == "deleted":
            print(
                "{} at {} deleted".format(
                    name, fl_helpers.ticks_to_BST(project, item["start"])
                )
            )
            pass
        elif change.state == "modified":
            print(
                "{} at {} modified".format(
                    name, fl_helpers.ticks_to_BST(project, change.data["start"])
                )
            )
        elif change.state == "moved":
            print(
                "{} at {} moved from track {} to track {}".format(
                    name,
                    fl_helpers.ticks_to_BST(project, item["start"]),
                    item["track"],
                    change.data["track"],
                )
            )


def debug_describe_arrangement_diff_summary(arrangement, changes):
    numAdded = numDeleted = numModified = numMoved = 0
    numItems = len(arrangement["items"])
    print(numItems)
    for change in changes:
        if change.state == "added":
            numAdded += 1
        elif change.state == "deleted":
            numDeleted += 1
        elif change.state == "modified":
            numModified += 1
        elif change.state == "moved":
            numMoved += 1
    print("{} clips ({}%) added".format(numAdded, round((numAdded / numItems * 100))))
    print(
        "{} clips ({}%) deleted".format(
            numDeleted, round((numDeleted / numItems * 100))
        )
    )
    print(
        "{} clips ({}%) modified".format(
            numModified, round((numModified / numItems * 100))
        )
    )
    print("{} clips ({}%) moved".format(numMoved, round((numMoved / numItems * 100))))


def resolve_conflict_default(
    arrangement, changeA: ArrangementChange, changeB: ArrangementChange
) -> list[dict[str, Any]]:
    """Resolve two conflicting actions, without user interaction."""

    # table of what actions to take based on which conflicts
    actionTable = {
        "added": {
            "added": "maybeAddBoth",
            "deleted": "error",
            "modified": "error",
            "moved": "error",
        },
        "deleted": {
            "added": "error",
            "deleted": "delete",
            "modified": "delete",  # TODO is this always wanted?
            "moved": "delete",  # ^
        },
        "modified": {
            "added": "error",
            "deleted": "delete",
            "modified": "twoModify",
            "moved": "maybeMoveAndModify",
        },
        "moved": {
            "added": "error",
            "deleted": "delete",
            "modified": "maybeMoveAndModify",
            "moved": "A",
        },
    }
    action = actionTable[changeA.state][changeB.state]

    if action == "error":
        raise Exception("invalid item change comparison")
    elif action == "delete":
        return []
    elif action == "maybeAddBoth":
        # if clips are identical, add only one, otherwise add both
        # (start/clipID already checked)
        itemA = changeA.data
        itemB = changeB.data
        clipsIdentical = (itemA["length"] == itemB["length"]) and (
            fl_helpers.normalise_clip_start(itemA["clipStart"])
            == fl_helpers.normalise_clip_start(itemB["clipStart"])
        )
        if clipsIdentical:
            return [itemA]
        else:
            return [itemA, itemB]  # TODO make this configurable (ie add both or prompt)
    elif action == "A":
        return [changeA.data]
    elif action == "maybeMoveAndModify":
        # if the modify doesn't move the clip, apply both and move it
        theMove = changeA if changeA.state == "moved" else changeB
        theModify = changeA if changeA.state == "modified" else changeB
        theOriginal = arrangement["items"][theModify["index"]]

        if theModify["data"]["track"] == theOriginal["track"]:
            # apply the move to the modified version
            theModify["data"]["track"] = theMove["data"]["track"]
        # (if both have moved, just use theModify)
        return [theModify["data"]]
    elif action == "twoModify":
        theOriginal = arrangement["items"][changeA.index]
        # merge the changes into changeA
        # attributes that may have changed
        clipAttribs = [
            "start",
            "length",
            "track",
            "clipStart",
            "clipEnd",
            "muted",
            "selected",
        ]

        def handleClipAttrib(attrib):
            orig = theOriginal[attrib]
            a = changeA.data[attrib]
            b = changeB.data[attrib]
            aChanged = a == orig
            bChanged = b == orig
            if a == b:
                return  # both versions have the same attrib; do nothing
            elif aChanged and bChanged:
                # UH OH both clips have been changed in a non-mergeable way. just use A's attrib for now
                return [changeA.data]
            elif bChanged:
                # B changed and A didn't; replace A's attrib
                changeA.data[attrib] = b
            else:
                return  # only A changed, do nothing

        for attrib in clipAttribs:
            handleClipAttrib(attrib)
        return [changeA.data]


def merge_arrangement_changes(
    arrangement: dict[str, Any],
    changesA: list[ArrangementChange],
    changesB: list[ArrangementChange],
    resolveConflict: Callable[
        [ArrangementChange, ArrangementChange], list[dict[str, Any]]
    ],
) -> dict[str, Any]:
    """Returns a new arrangement incorporating both sets of changes.
    Does ??? upon merge conflicts
    Limitations:
      - discards playlist track names/customisation
    Inputs:
      resolveConflict :: (Change, Change) => [PlaylistItem]
    """

    # annotate arrangement with changesA
    # (also collect added clips)
    addedA = defaultdict(list)
    for change in changesA:
        if change.state == "added":
            item = change.data
            key = (item["type"], item["clipIndex"], item["start"])
            addedA[key].append(change)
        else:
            arrangement["items"][change.index]["change"] = change

    # loop over changesB, look for conflicts
    newItems = []
    for change in changesB:
        if change.state == "added":
            item = change.data
            key = (item["type"], item["clipIndex"], item["start"])
            if key in addedA:
                # if new item is identical (same start pl start/length, startPos)
                newItems += resolveConflict(arrangement, addedA[key][0], change)
                del addedA[key][0]
                pass
            else:
                newItems.append(item)
        else:
            # if the item has already been changed, use the precedence table
            if "change" in arrangement["items"][change.index]:
                newItems += resolveConflict(
                    arrangement, arrangement["items"][change.index]["change"], change
                )
                arrangement["items"][change.index]["deleted"] = True

    # finally loop over the arrangement and apply pending changes
    for item in arrangement["items"]:
        if "deleted" in item:
            continue
        if "change" in item:
            if item["change"]["state"] == "deleted":
                continue
            else:
                # state is moved or modified - just replace with the new data
                newItems.append(item["change"]["data"])
        else:  # item is unchanged
            newItems.append(item)
    # add new items from A and B
    newItems += [change.data for changes in addedA.values() for change in changes]

    return {
        "items": newItems,
        "tracks": arrangement["tracks"],  # TODO actually merge tracks
    }


if __name__ == "__main__":
    # file1 = sys.argv[-2]
    # file2 = sys.argv[-1]
    # project1 = loadFLP(file1)
    # project2 = loadFLP(file2)
    # changes = diff_arrangement(project1['arrangements'][0], project2['arrangements'][0])
    # debug_describe_arrangement_diff_verbose(project1, project1['arrangements'][0], changes)
    # debug_describe_arrangement_diff_summary(project1['arrangements'][0], changes)

    # usage: python flp_diff.py [...] original.flp edited_a.flp edited_b.flp
    projO = loadFLP(sys.argv[-3])
    projA = loadFLP(sys.argv[-2])
    projB = loadFLP(sys.argv[-1])
    changesA = diff_arrangement(projO["arrangements"][0], projA["arrangements"][0])
    changesB = diff_arrangement(projO["arrangements"][0], projB["arrangements"][0])
    print("======")
    print(len(projO["arrangements"][0]["items"]))
    print("======")

    # for c in changesA:
    #   if 'index' in c: print(c['index'])
    # for c in changesB:
    #   if 'index' in c: print(c['index'])
    newArrangement = merge_arrangement_changes(
        projO["arrangements"][0], changesA, changesB, resolve_conflict_default
    )

    for item in newArrangement["items"]:
        print(item)
