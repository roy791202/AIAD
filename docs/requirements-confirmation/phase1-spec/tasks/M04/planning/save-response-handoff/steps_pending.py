# Deliberately non-executable native BDD stubs; document model is not acceptance.
def given_capture(context):
    raise NotImplementedError("Owner-approved capture fixture/provider required")
def when_reconcile(context):
    raise NotImplementedError("Approved native orchestration required")
def then_observe(context):
    raise NotImplementedError("Independent native verifier required")
