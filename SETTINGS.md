## Configuration settings

### Bundle Items

| Setting                                           | Mandatory | Default | Description                                                                                                         |
|---------------------------------------------------|-----------|---------|---------------------------------------------------------------------------------------------------------------------|
| bundles.version                                   | no        | 1       | json Format version                                                                                                 |
| bundles.itemsPrefix                               | no        |         | A prefix added to all generated .big file names                                                                     |
| bundles.itemsSuffix                               | no        |         | A suffix added to all generated .big file names                                                                     |
| bundles.items                                     | no        |         | Item list                                                                                                           |
| bundles.items[].name                              | yes       |         | Item name                                                                                                           |
| bundles.items[].big                               | no        | True    | Item is a .big file?                                                                                                |
| bundles.items[].files                             | no        |         | Item file list                                                                                                      |
| bundles.items[].files[].sourceParent              | no        |         | Source file(s) parent folder                                                                                        |
| bundles.items[].files[].parent                    | no        |         | Legacy name of 'sourceParent'                                                                                       |
| bundles.items[].files[].source                    | no        |         | Source file(s), accepts wild cards \*.\* or A.\* or \*.B                                                            |
| bundles.items[].files[].target                    | no        |         | Target file(s), accepts wild cards \*.\* or A.\* or \*.B                                                            |
| bundles.items[].files[].params                    | no        |         | File params, see Sample Project for examples                                                                        |
| bundles.items[].files[].sourceList                | no        |         | List of source file(s), target file is automatic, alternative to 'source', accepts wild cards \*.\* or A.\* or \*.B |
| bundles.items[].files[].sourceTargetList          | no        |         | List of source and target file(s), alternative to 'source' and 'target', accepts wild cards \*.\* or A.\* or \*.B   |
| bundles.items[].files[].sourceTargetList[].source | yes       |         | Source file as part of the list                                                                                     |
| bundles.items[].files[].sourceTargetList[].target | yes       |         | Target file as part of the list                                                                                     |
| bundles.items[].files[].sourceTargetList[].params | no        |         | Not implemented                                                                                                     |
| bundles.items[].files[].multiSource                    | no  |         | List of source files that build one 'target' file together, accepts wild cards \*.\* or A.\* or \*.B, see Multi Source Files |
| bundles.items[].files[].multiSourceTargetList          | no  |         | List of multi source and target file(s), alternative to 'multiSource' and 'target'                                  |
| bundles.items[].files[].multiSourceTargetList[].multiSource | yes |    | List of source files that build one target file together, accepts wild cards \*.\* or A.\* or \*.B                  |
| bundles.items[].files[].multiSourceTargetList[].target      | yes |    | Target file built from all source files of this list entry                                                          |
| bundles.items[].onPreBuild                        | no        |         | Special callback event that is executed before build. Used to inject custom script logic                            |
| bundles.items[].onPreBuild.script                 | yes       |         | Python script called on event                                                                                       |
| bundles.items[].onPreBuild.function               | no        | OnEvent | Python script function called                                                                                       |
| bundles.items[].onPreBuild.kwargs                 | no        |         | Arbitrary keyword arguments passed to Python script function                                                        |

### Multi Source Files

A regular `source` builds one target file per source file. A wild card in it does not change
that, it simply produces more source and target file pairs.

A `multiSource` does the opposite and builds a single target file from all of its source files.
This is useful to keep game data in several small files that are easier to maintain, and still
ship them as the one file that the game expects. A wild card in a `multiSource` entry adds all
of its matches to the same target file. Matches of a wild card are sorted alphabetically, so
that the resulting file is the same on every machine. Files that are listed without wild card
keep the order they are listed in.

Because there is no single source file name to derive a target file name from, `target` is
mandatory with `multiSource` and cannot contain a wild card.

```json
{
    "sourceParent": "GameFilesEdited",
    "multiSource": [
        "Data/INI/Weapon_Base.ini",
        "Data/INI/Weapon_USA.ini",
        "Data/INI/WeaponOverrides/*.ini"
    ],
    "target": "Data/INI/Weapon.ini"
}
```

The supported file types and the way that they are combined are:

| Target file | Source files | Combined by                                                                   |
|-------------|--------------|-------------------------------------------------------------------------------|
| ini, wnd    | Same type    | Appending the text of each source file in the listed order                     |
| str         | str          | Appending the text of each source file in the listed order                     |
| str, csf    | str, csf     | Merging the string labels, where a label of a later file overwrites an earlier one |

All `params` of the bundle file apply to the combined result. For a merged str or csf file the
text params are applied to each source file before they are merged.

Any other target file type is rejected, because there is no meaningful way to combine
multiple source files into it.

### Bundle Packs

| Setting                             | Mandatory | Default | Description                                                                              |
|-------------------------------------|-----------|---------|------------------------------------------------------------------------------------------|
| bundles.version                     | no        | 1       | json Format version                                                                      |
| bundles.packsPrefix                 | no        |         | A prefix added to all generated .zip file names                                          |
| bundles.packsSuffix                 | no        |         | A suffix added to all generated .zip file names                                          |
| bundles.packs                       | no        |         | Pack list                                                                                |
| bundles.packs[].install             | no        | False   | Pack is installed by Mod Builder for testing?                                            |
| bundles.packs[].name                | yes       |         | Pack name                                                                                |
| bundles.packs[].itemNames           | yes       |         | Item name list                                                                           |
| bundles.packs[].onPreBuild          | no        |         | Special callback event that is executed before build. Used to inject custom script logic |
| bundles.items[].onPreBuild.script   | yes       |         | Python script called on event                                                            |
| bundles.items[].onPreBuild.function | no        | OnEvent | Python script function called                                                            |
| bundles.items[].onPreBuild.kwargs   | no        |         | Arbitrary keyword arguments passed to Python script function                             |

### Unique Names

Names that end up as a file or a directory must be unique, so that one build step cannot
silently overwrite the result of another one. Names are compared case insensitively, because
file names are case insensitive on Windows and in big archives, therefore two names that
differ in upper and lower case only name the same file.

The build rejects a configuration when

- an item builds the same target file more than once,
- two items have the same name, or build a big file of the same name,
- two packs have the same name, or build a release .zip file of the same name,
- a pack lists the same item more than once,
- two items of the same pack build a file of the same name into that pack.
