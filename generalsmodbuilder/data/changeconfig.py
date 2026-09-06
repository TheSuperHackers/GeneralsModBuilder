import os.path
from enum import Enum, auto
from dataclasses import dataclass
from generalsmodbuilder.data.common import FinalizeParsedData, ParsedData, VerifyFormatVersion
from generalsmodbuilder.util import JsonNode, JsonFile
from generalsmodbuilder import util


LATEST_CHANGELOG_VERSION = 1

CHANGELOG_KEYS = {
    "version",
    "records"
}

CHANGELOG_RECORD_KEYS = {
    "sourceList",
    "targetList",
    "sortList",
    "includeLabelList",
    "excludeLabelList"
}

CHANGELOG_SORT_KEYS = {
    "date",
    "label"
}


class Sort(Enum):
    Ascending = auto()
    Descending = auto()


@dataclass(init=False)
class SortDefinition:
    isDate: bool
    label: str
    sort: Sort

    def __init__(self):
        self.isDate = False
        self.label = ""
        self.sort = Sort.Ascending

    def IsDateSort(self) -> bool:
        return self.isDate and not bool(self.label)

    def IsLabelSort(self) -> bool:
        return not self.isDate and bool(self.label)


@dataclass(init=False)
class ChangeConfigRecord(ParsedData):
    absSourceFiles: list[str]
    absTargetFiles: list[str]
    sortDefinitions: list[SortDefinition]
    includeLabels: list[str]
    excludeLabels: list[str]

    def __init__(self):
        self.absSourceFiles = list[str]()
        self.absTargetFiles = list[str]()
        self.sortDefinitions = list[SortDefinition]()
        self.includeLabels = list[str]()
        self.excludeLabels = list[str]()

    def Normalize(self) -> None:
        for i, file in enumerate(self.absSourceFiles):
            self.absSourceFiles[i] = os.path.normpath(file)
        for i, file in enumerate(self.absTargetFiles):
            self.absTargetFiles[i] = os.path.normpath(file)

    def ResolveWildcards(self) -> None:
        self.absSourceFiles = util.ResolveFileWildcards(self.absSourceFiles)

    def VerifyValues(self) -> None:
        # The source files are already verified while their wildcards are resolved.
        for file in self.absTargetFiles:
            util.Verify(util.IsValidPathName(file), f"changelog.records.targetList '{file}' is not a valid file name")


@dataclass(init=False)
class ChangeConfig(ParsedData):
    records: list[ChangeConfigRecord]

    def __init__(self):
        self.records = list[ChangeConfigRecord]()

    def Normalize(self) -> None:
        for record in self.records:
            record.Normalize()

    def ResolveWildcards(self) -> None:
        for record in self.records:
            record.ResolveWildcards()

    def VerifyValues(self) -> None:
        for record in self.records:
            record.VerifyValues()


def __MakeSortFromStr(node: JsonNode, jStr: str) -> Sort:
    for sort in Sort:
        if jStr.lower() == sort.name.lower():
            return sort

    validNames: str = " or ".join(f"'{sort.name.lower()}'" for sort in Sort)
    raise AssertionError(f"{node.Name('date')} is '{jStr}', but must be {validNames}")


def __MakeSortDefinitionsFromList(sortNodes: list[JsonNode]) -> list[SortDefinition]:
    definitions = list[SortDefinition]()
    sortNode: JsonNode

    for sortNode in sortNodes:
        sortNode.VerifyKnownKeys(CHANGELOG_SORT_KEYS)

        jDate: str = sortNode.GetOptional("date", str)
        jLabel: str = sortNode.GetOptional("label", str)

        # An entry that names neither sorts by nothing and used to be dropped in silence.
        # An entry that names both is ambiguous, because only the date would be used.
        sortNode.Verify(bool(jDate) != bool(jLabel), "must name exactly one of 'date' or 'label'")

        definition = SortDefinition()
        if jDate:
            definition.isDate = True
            definition.sort = __MakeSortFromStr(sortNode, jDate)
        else:
            definition.label = jLabel
        definitions.append(definition)

    return definitions


def __MakeAbsFilesFromList(jFileList: list, jsonDir: str) -> list[str]:
    return [os.path.join(jsonDir, jFile) for jFile in jFileList]


def __MakeChangeConfigRecordFromDict(node: JsonNode, jsonDir: str) -> ChangeConfigRecord:
    record = ChangeConfigRecord()
    node.VerifyKnownKeys(CHANGELOG_RECORD_KEYS)

    record.absSourceFiles = __MakeAbsFilesFromList(
        node.GetMandatory("sourceList", list, elementType=str), jsonDir)
    record.absTargetFiles = __MakeAbsFilesFromList(
        node.GetMandatory("targetList", list, elementType=str), jsonDir)

    record.sortDefinitions = __MakeSortDefinitionsFromList(node.Elements("sortList", dict))

    record.includeLabels = node.GetOptional("includeLabelList", list, record.includeLabels, elementType=str)
    record.excludeLabels = node.GetOptional("excludeLabelList", list, record.excludeLabels, elementType=str)

    return record


def MakeChangeConfigFromJsons(jsonFiles: list[JsonFile]) -> ChangeConfig:
    config = ChangeConfig()

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsFileDir(jsonFile.path)
        root = util.JsonNode(jsonFile.path, jsonFile.data)

        if node := root.SubOptional("changelog"):
            node.VerifyKnownKeys(CHANGELOG_KEYS)
            VerifyFormatVersion(node, LATEST_CHANGELOG_VERSION)

            recordNode: JsonNode
            for recordNode in node.Elements("records", dict):
                config.records.append(__MakeChangeConfigRecordFromDict(recordNode, jsonDir))

    FinalizeParsedData(config)
    return config
