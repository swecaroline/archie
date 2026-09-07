
class ServerRecord():

    def __init__(
        self,
        id,
        archiveId,
        timeToArchive,
        timeToDelete
    ):
        self.id = id
        self.archiveId = archiveId
        self.timeToArchive = timeToArchive
        self.timeToDelete = timeToDelete