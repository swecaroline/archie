
class ServerRecord():

    def __init__(
        self,
        id,
        archiveCategoryName,
        timeToArchive,
        permanentCategories,
        permanentChannels,
        timeToDeletion
    ):
        self.id = id
        self.archiveCategoryName = archiveCategoryName
        self.timeToArchive = timeToArchive
        self.permanentCategories = permanentCategories
        self.permanentChannels = permanentChannels
        self.timeToDeletion = timeToDeletion