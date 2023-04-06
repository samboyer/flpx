![FLPx banner](docs/banner.jpg)
# [EXPERIMENTAL] FLPx - Read, write, edit & merge .flp files


Primarily, FLPx attempts to give developers an easy interface to read and write Image Line's FLP files for FL Studio. Eventually, the tool will also support diffing and merging FLPs, allowing for version control via git etc.

## Module breakdown

- flp_read.py - .flp reading - 80% complete
  - Currently supports:
    - playlist/arrangement decoding
  - Missing features/functions:
    - automation clip curve decoding
- flp_write.py - .flp writing - 10% complete
  - Currently supports:
    - write generic project events
  - Missing features/functions:
    - writing pattern data
    - writing automation clip data
    - writing arrangement data
    - writing mixer data

- flp_diff.py - three-way merge for FLPs - 15% complete
  - Currently supports:
    - three-way-merge on playlist arrangements
  - Missing features/functions:
    - arrangement track name/colour changes are ignored
    - three-way merge for patterns
    - three-way merge for generators
    - three-way merge for mixer channels
    - three-way merge for mixer effects


- fl_helpers.py - helper functions for FL Studio variables/reprs 
- **TODO** util.py - generic util/helper functions (logging, inupt/output etc)
- **TODO** \_\_main.py\_\_ - CLI for reading/writing/merging

## To-do:
- Clean-up code
  - Add type signatures to all functions
  - Add/move to_bytes methods to their respective classses
  - move inline notes to...somewhere else
  - decide on a single name for various FLP things
    - playlist clip vs playlist item
    - playlist vs arrangement
    - channel vs generator
    - mixer track vs mixer insert vs mixer channel
  - move debug print functions to debug.py(?)
  - move all __name__ == 'main' bits of code to a seperate script 
- FLP write-back / round-trip
  - fill in read_FLP gaps 
    - Automation clip data
    - 'Missing event handler for event ___'
  - fill in the gaps in write_FLP
- Actually parse Pattern data
- Actually parse Channel data (FLP_ChanParams)
- FL 21.0 support
  - AudioClip fade in/out, volume, blending
- Work out how demo/paid file checking/DRM works & how to maintain it 
- MVP CLI
  - FLP to JSON, JSON to FLP
- Testing
  - reader: pairs of FLPs and expected object subsets
  - writer: pairs of full track objects and expected FLPs
  - integration test: reading->writing should produce the same FLP.

## Roadmap
### Short-term
- Working reader/writer functions
- Simple API to read/write files
- CLI to read/write files
- Three-way merge via API & CLI
- Git merge driver

### Long-term/'nice to have'
- clean_project(): deselect all playlist items, unmute all mixer channels & playlist tracks, set position to 0, etc. (essentially just normalise the file a little)
- make_empty_project(): return a Project with sane projectInfo values set

## Terminology

- *Ghost pattern*: patterns can be added to the Playlist that don't actually exist yet - this is most easily observed by srolling down the Current Pattern dropdown, which lets you go well past your last pattern. 