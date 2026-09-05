import os.path
from enum import Enum, auto
from dataclasses import dataclass
from generalsmodbuilder.data.common import FinalizeParsedData, ParsedData
from generalsmodbuilder.util import JsonContext, JsonFile
from generalsmodbuilder import util


class Sort(Enum):
    Zero = auto()
    Ascending = auto()
    Descending = auto()


@dataclass(init=False)
class SortDefinition(ParsedData):
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

    def VerifyValues(self) -> None:
        util.Verify(self.IsDateSort() or self.IsLabelSort(), "changelog.records.sortList entry is neither a date nor a label sort")


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
        for definition in self.sortDefinitions:
            definition.VerifyValues()


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


def __MakeSortFromStr(jStr: str) -> Sort:
    jStrLower: str = jStr.lower()
    if jStrLower == Sort.Ascending.name.lower():
        return Sort.Ascending
    if jStrLower == Sort.Descending.name.lower():
        return Sort.Descending
    return Sort.Zero


def __MakeSortDefinitionsFromList(ctx: JsonContext, jSortList: list) -> list[SortDefinition]:
    definitions = list[SortDefinition]()
    jSortLabel: dict

    for index, jSortLabel in enumerate(jSortList):
        sortCtx: JsonContext = ctx.At(index)

        jDate: str = sortCtx.GetOptional(jSortLabel, "date", str)
        if jDate:
            definition = SortDefinition()
            definition.isDate = True
            definition.sort = __MakeSortFromStr(jDate)
            definitions.append(definition)
            continue

        jLabel: str = sortCtx.GetOptional(jSortLabel, "label", str)
        if jLabel:
            definition = SortDefinition()
            definition.label = jLabel
            definitions.append(definition)

    return definitions


def __MakeAbsFilesFromList(jFileList: list, jsonDir: str) -> list[str]:
    return [os.path.join(jsonDir, jFile) for jFile in jFileList]


def __MakeChangeConfigRecordFromDict(ctx: JsonContext, jRecord: dict, jsonDir: str) -> ChangeConfigRecord:
    record = ChangeConfigRecord()

    record.absSourceFiles = __MakeAbsFilesFromList(
        ctx.GetMandatory(jRecord, "sourceList", list, elementType=str), jsonDir)
    record.absTargetFiles = __MakeAbsFilesFromList(
        ctx.GetMandatory(jRecord, "targetList", list, elementType=str), jsonDir)

    jSortList: list = ctx.GetOptional(jRecord, "sortList", list, default=[], elementType=dict)
    record.sortDefinitions = __MakeSortDefinitionsFromList(ctx.Sub("sortList"), jSortList)

    record.includeLabels = ctx.GetOptional(jRecord, "includeLabelList", list, record.includeLabels, elementType=str)
    record.excludeLabels = ctx.GetOptional(jRecord, "excludeLabelList", list, record.excludeLabels, elementType=str)

    return record


def MakeChangeConfigFromJsons(jsonFiles: list[JsonFile]) -> ChangeConfig:
    config = ChangeConfig()

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsFileDir(jsonFile.path)
        root = util.JsonContext(jsonFile.path)
        jChangelog: dict = root.GetOptional(jsonFile.data, "changelog", dict)

        if jChangelog:
            ctx = root.Sub("changelog")
            jRecords: list = ctx.GetOptional(jChangelog, "records", list, default=[], elementType=dict)
            jRecord: dict
            for index, jRecord in enumerate(jRecords):
                config.records.append(
                    __MakeChangeConfigRecordFromDict(ctx.Sub("records").At(index), jRecord, jsonDir))

    FinalizeParsedData(config)
    return config
