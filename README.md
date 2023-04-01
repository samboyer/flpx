# [EXPERIMENTAL] FLPX - Read, write, edit & merge .flp files

Primarily, FLPX attempts to give developers an easy interface to read and write Image Line's FLP files for FL Studio. Eventually, the tool will also support diffing and merging FLPs, allowing for version control via git etc.

## Module breakdown

- flp_read.py - .flp reading - 80% complete
  - Currently supports:
    - playlist/arrangement decoding
  - Missing features/functions:
    - mixer channels/effects parsing
    - automation clips
    - missing event handlers for events (166, 165, 236 - possibly playlist item-specific) and (143,144,155,221,226,228,229,32,36,97 - unknown)
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
   - Use custom classes/enums to store parsed project data instead of dicts, put them all in a _defs.py file
     - better for API inputs/outputs, and type checking 
     - harder to (de)serialize?
   - Add type signatures to all functions
     - need a type for `project`...
  - move inline notes to...somewhere else
  - move all __name__ == 'main' bits of code to a seperate script 
  - decide on a single name for various FLP things
    - Clip vs Pattern vs playlist item
  - move debug print functions to debug.py(?)
- MVP FLP write-back / round-trip
  -  fill in the gaps in write_FLP
- Finish reader
  - ???
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


## Terminology

- Ghost pattern: patterns can be added to the Playlist that don't actually exist yet - this is most easily observed by srolling down the Current Pattern dropdown, which lets you go well past your last pattern. 