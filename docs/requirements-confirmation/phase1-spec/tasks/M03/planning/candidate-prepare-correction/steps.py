"""Future native step definitions; deliberately not a product harness."""
def given_fixture(case_id):
    raise NotImplementedError("Adopted native fixture/provider required")
def when_prepare(request):
    raise NotImplementedError("Approved input Port required")
def then_observe(expected):
    raise NotImplementedError("Independent native verification required")
