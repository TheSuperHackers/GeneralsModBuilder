import functools
from copy import copy
from markdownmaker import document as md
from markdownmaker import markdownmaker as md
from generalsmodbuilder import util
from generalsmodbuilder.changelog.parser import ChangeLog, ChangeLogRecord, ChangeLogRecordEntry, ChangeLogChange
from generalsmodbuilder.data.changeconfig import ChangeConfigRecord, Sort, SortDefinition


def __AddRecordsLabelFiltersText(doc: md.Document, configRecord: ChangeConfigRecord, labelSet: set[str]) -> None:
    hasIncludeLabels = False
    hasExcludeLabels = False

    if bool(configRecord.includeLabels):
        hasIncludeLabels = True
        labelsStr = ", ".join(label for label in sorted(configRecord.includeLabels))
        doc.add(md.Paragraph(f"Includes changes with labels: {labelsStr}"))

    if bool(configRecord.excludeLabels):
        hasExcludeLabels = True
        labelsStr = ", ".join(label for label in sorted(configRecord.excludeLabels))
        doc.add(md.Paragraph(f"Excludes changes with labels: {labelsStr}"))

    if not hasIncludeLabels and not hasExcludeLabels:
        labelsStr = ", ".join(label for label in sorted(labelSet))
        doc.add(md.Paragraph(f"Includes changes with all labels: {labelsStr}"))


def __AddRecordsSortRulesText(doc: md.Document, configRecord: ChangeConfigRecord) -> None:
    sortList = []

    if bool(configRecord.sortDefinitions):
        for definition in configRecord.sortDefinitions:
            if definition.IsDateSort():
                sortList.append(f"date ({definition.sort.name.lower()})")
            elif definition.IsLabelSort():
                sortList.append(f"{definition.label} ({definition.sort.name.lower()})")

    sortStr = ", ".join(sortList)
    doc.add(md.Paragraph(f"Sorts changes by: {sortStr}"))


def __AddRecordsChangeCountsText(doc: md.Document, logRecord: ChangeLogRecord) -> None:
    entriesCount: int = len(logRecord.entries)
    majorChangeCount = 0
    minorChangeCount = 0
    majorChangeCountByType = dict[str, int]()
    minorChangeCountByType = dict[str, int]()

    for logEntry in logRecord.entries:
        for type, count in logEntry.majorTypeCounts.items():
            majorChangeCount += count
            if majorChangeCountByType.get(type):
                majorChangeCountByType[type] += count
            else:
                majorChangeCountByType[type] = count

        for type, count in logEntry.minorTypeCounts.items():
            minorChangeCount += count
            if minorChangeCountByType.get(type):
                minorChangeCountByType[type] += count
            else:
                minorChangeCountByType[type] = count

    majorChangeCountStrList = [f"{type} ({count})" for type, count in majorChangeCountByType.items()]
    minorChangeCountStrList = [f"{type} ({count})" for type, count in minorChangeCountByType.items()]
    majorChangeCountStr = ", ".join(majorChangeCountStrList)
    minorChangeCountStr = ", ".join(minorChangeCountStrList)

    doc.add(md.Paragraph(f"Contains {entriesCount} entries with "
        f"{majorChangeCount} major changes: [ {majorChangeCountStr} ] and "
        f"{minorChangeCount} minor changes: [ {minorChangeCountStr} ]."))



def __MakeRecordTitle(logEntry: ChangeLogRecordEntry) -> str:
    date: str = logEntry.date.strftime('%Y-%m-%d')
    title: str = f"{date} - {logEntry.title}"
    return title


def __MakeRecordTitleLink(logEntry: ChangeLogRecordEntry, index: int) -> str:
    name: str = util.GetFileNameNoExt(logEntry.absSourceFile)
    name = "".join(name.split())
    link: str = f"index__{index}__{name.lower()}"
    return link


def __MakeMarkdownLink(link: str) -> md.Link:
    return md.Link(label=f"{link}", url=f"{link}")


def __AddRecordsIndex(doc: md.Document, logRecord: ChangeLogRecord) -> None:
    logEntry: ChangeLogRecordEntry

    with md.HeaderSubLevel(doc):
        doc.add(md.Header(f"Index"))

        linkList = list[md.Link]()

        for i, logEntry in enumerate(logRecord.entries):
            title: str = __MakeRecordTitle(logEntry)
            titleLink: str = __MakeRecordTitleLink(logEntry, i)
            link = md.Link(label=title, url=f"#{titleLink}")
            linkList.append(link)

        doc.add(md.Paragraph(md.OrderedList(linkList)))


def __AddRecordsDetails(doc: md.Document, logRecord: ChangeLogRecord) -> None:
    logEntry: ChangeLogRecordEntry

    with md.HeaderSubLevel(doc):
        with md.HeaderSubLevel(doc):
            for i, logEntry in enumerate(logRecord.entries):
                fileName: str = util.GetFileName(logEntry.absSourceFile)
                title: str = __MakeRecordTitle(logEntry)
                titleLink: str = __MakeRecordTitleLink(logEntry, i)
                majorList = [f"{change.typeName}: {change.text}" for change in logEntry.majorChanges]
                minorList = [f"{change.typeName}: {change.text}" for change in logEntry.minorChanges]
                labelsStr = ", ".join(label for label in logEntry.labels)
                authorsStr = ", ".join(author for author in logEntry.authors)
                linkList = [__MakeMarkdownLink(link) for link in logEntry.links]

                doc.add(md.HorizontalRule())
                doc.add(md.Header(f"{title} <a name='{titleLink}'></a>"))
                if bool(majorList):
                    doc.add(md.Paragraph(md.Bold("Changes")))
                    doc.add(md.UnorderedList(majorList))
                if bool(minorList):
                    doc.add(md.Paragraph(md.Bold("Subchanges")))
                    doc.add(md.UnorderedList(minorList))
                if bool(logEntry.links):
                    doc.add(md.Paragraph(md.Bold("Links")))
                    doc.add(md.UnorderedList(linkList))
                if labelsStr:
                    doc.add(md.Paragraph(f"{md.Bold('Labels:')} {labelsStr}"))
                if authorsStr:
                    doc.add(md.Paragraph(f"{md.Bold('Authors:')} {authorsStr}"))
                doc.add(md.Paragraph(f"{md.Bold('Source:')} {fileName}"))


def GenerateChangeLogMarkdown(logRecord: ChangeLogRecord, absTarget: str) -> None:
    if not bool(logRecord.entries):
        return

    timer = util.Timer()
    print(f"Generate change log at {absTarget}")

    labelSet = set[str]()
    logEntry: ChangeLogRecordEntry
    for logEntry in logRecord.entries:
        for label in logEntry.labels:
            labelSet.add(label)

    doc = md.Document()

    fileStr: str = util.GetFileNameNoExt(absTarget)
    doc.add(md.Header(f"Auto Generated Change Log '{fileStr}'"))

    __AddRecordsLabelFiltersText(doc, logRecord.configRecord, labelSet)
    __AddRecordsSortRulesText(doc, logRecord.configRecord)
    __AddRecordsChangeCountsText(doc, logRecord)
    __AddRecordsIndex(doc, logRecord)
    __AddRecordsDetails(doc, logRecord)

    text: str = doc.write()
    with open(absTarget, "w", encoding='utf-8') as targetFile:
        targetFile.write(text)

    if timer.GetElapsedSeconds() > util.PERFORMANCE_TIMER_THRESHOLD:
        print(f"Generate change log completed in {timer.GetElapsedSecondsString()} s")


def GenerateChangeLogDocuments(changeLog: ChangeLog) -> None:
    logRecord: ChangeLogRecord
    absTarget: str

    for logRecord in changeLog.records:
        for absTarget in logRecord.configRecord.absTargetFiles:
            if util.HasFileExt(absTarget, "md"):
                GenerateChangeLogMarkdown(logRecord, absTarget)


def __ChangeLogRecordCompare(a: ChangeLogRecordEntry, b: ChangeLogRecordEntry, definitions: list[SortDefinition]) -> int:
    # The sort definition list can contain multiple entries, where earlier entries have higher sort priority.
    # This algoritm adds to return value if a > b and subtracts if a < b, and vice versa if the sort is descending.
    # The higher the sort definition priority, the higher the value to add or subtract.
    value = 0
    weight = len(definitions)

    for i, definition in enumerate(definitions):
        less = False
        greater = False
        if definition.IsDateSort():
            if definition.sort == Sort.Ascending:
                less = a.date < b.date
                greater = a.date > b.date
            elif definition.sort == Sort.Descending:
                less = a.date > b.date
                greater = a.date < b.date
        elif definition.IsLabelSort():
            if definition.sort == Sort.Ascending:
                less = (definition.label in a.labels) and (not definition.label in b.labels)
                greater = (not definition.label in a.labels) and (definition.label in b.labels)
            elif definition.sort == Sort.Descending:
                less = (not definition.label in a.labels) and (definition.label in b.labels)
                greater = (definition.label in a.labels) and (not definition.label in b.labels)
        if less:
            value -= (weight - i) ** 2
        if greater:
            value += (weight - i) ** 2

    return value


def SortChangeList(changeLog: ChangeLog) -> ChangeLog:
    logRecord: ChangeLogRecord
    newChangeLog = ChangeLog()

    for logRecord in changeLog.records:
        newLogRecord = ChangeLogRecord()
        newLogRecord.configRecord = logRecord.configRecord
        newLogRecord.entries = copy(logRecord.entries)
        fnc = lambda a, b: __ChangeLogRecordCompare(a, b, logRecord.configRecord.sortDefinitions)
        cmp = functools.cmp_to_key(fnc)
        newLogRecord.entries.sort(key=cmp)
        newChangeLog.records.append(newLogRecord)

    return newChangeLog


def FilterChangeLog(changeLog: ChangeLog) -> ChangeLog:
    logRecord: ChangeLogRecord
    logEntry: ChangeLogRecordEntry
    newChangeLog = ChangeLog()

    for logRecord in changeLog.records:
        newLogRecord = ChangeLogRecord()
        newLogRecord.configRecord = logRecord.configRecord
        newLogRecord.entries = list[ChangeLogRecordEntry]()

        includeLabels: list[str] = logRecord.configRecord.includeLabels
        excludeLabels: list[str] = logRecord.configRecord.excludeLabels

        for logEntry in logRecord.entries:
            if bool(includeLabels):
                if set(includeLabels).isdisjoint(set(logEntry.labels)):
                    continue
            if bool(excludeLabels):
                if not set(excludeLabels).isdisjoint(set(logEntry.labels)):
                    continue
            newLogRecord.entries.append(logEntry)

        newChangeLog.records.append(newLogRecord)

    return newChangeLog
