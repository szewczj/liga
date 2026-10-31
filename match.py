class Match():

    _id = None

    def __init__(self, match_id=None):
        self._id = match_id
        self._read_from_db()

    @staticmethod
    def create(self, teams=None):
        if teams is not None and len(teams) == 2:
            print("Create new match, teams are:")
            for team in teams:
                print(team)
        else:
            print("Cannot create new match, teams are not defined or number of teams is different than 2")

    @staticmethod
    def delete(self):
        print("deleting match")

    def get_id(self):
        pass

    def _read_from_db(self):
        pass

    def _delete_from_db(self):
        pass




