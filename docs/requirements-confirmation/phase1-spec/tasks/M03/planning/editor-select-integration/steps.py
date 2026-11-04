"""Pending native automation; never counts as executable BDD acceptance."""
def given_fixture(context, fixture_id):
 raise NotImplementedError("Native fixture runner pending")
def when_select(context):
 raise NotImplementedError("Native command adapter pending")
def then_expected(context):
 raise NotImplementedError("Independent native assertions pending")
