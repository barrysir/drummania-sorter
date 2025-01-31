# drummania-sorter

Since DTXMania doesn't support sorting very well, create copies of a song folder sorted in different ways. Currently supported is alphabetically and by difficulty.

It does this by making symlinks to the original files -- see [[#How it works]] for a greater description of what this implies.

## Installation

 * Python 3.9+
 * If you want japanese text processing (for alphabetical sort -- see below) then you will have to install dependencies.
   * `pip install .`
 * You will probably run into [[#OSError: [WinError 1314] ]] -- you will need to enable Developer Mode to run this script.
 * `python dtx_symlink.py (input song folder) (output song folder)`
   * e.g. `python dtx_symlink.py DTXFiles/DTXFiles.Gitadora DTXFiles/DTXFiles.Gitadora_sorted`
   * The sorted "Alphabetical" and "Difficulty" folders will be placed within `DTXFiles/DTXFiles.Gitadora_sorted`.

### Alphabetical sort method

A big problem is sorting japanese titles since kanji are difficult to read. (This program does implement reading and sorting by japanese but it might not always be correct.) However sometimes song folders are labelled with romanized titles, so those could be used for song sorting.

The program leaves it to you to decide which sorting method to use, one might be better than the other depending on the files you want to sort.

 * By song title:
   * need to sort japanese titles/kanji
   * have to install dependencies
 * By folder names:
   * folder names aren't necessarily the song title - could have stuff like "30. Yuusha"
   * folder names not required to be in english, although more likely they are

## How it works

The script works by making symlinks to the original files, so they just look like separate song packs to DTXMania. The advantages and disadvantages are below:

 + + Since DTXMania keeps score files in the song folder, this also retains leaderboards between the copies of songs. (Although when you run DTXMania, the leaderboards won't update until you restart.)
 -  - Each copy of the song has to be individually processed, so loading will take 3 times longer.

There might be better methods to achieving some kind of sorting but I'm not sure.

## Errors

### OSError: [WinError 1314] A required privilege is not held by the client

Solution: https://stackoverflow.com/a/76292992

> These days, the easiest way to make it possible to create Symbolic Links is to enable Developer Mode.
> Go to Settings > Update & Security > For Developers and turn Developer Mode to on. Immediately, it should be possible to create symbolic links.
> (on Windows 11, it's under Settings > System > For Developers).