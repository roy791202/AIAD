"""Document-review step stubs. Not executable product RED and not native ACK proof."""


def given_yellow_parent_and_preserved_packets(context):
    raise NotImplementedError("PENDING: bind read-only preserved M04 packets and Yellow parent")


def given_write_atomic_path_receipt(context):
    raise NotImplementedError("PENDING M04-ACK-1: HOST FileSystemPort.write_atomic path is not ACK")


def given_four_field_commit_receipt(context):
    raise NotImplementedError("PENDING M04-ACK-2: CommitReceipt four fields are not semantic ACK")


def given_missing_issuer(context):
    raise NotImplementedError("PENDING M04-ACK-3: authenticated M05 issuer receipt required")


def given_replayed_receipt_or_ack(context):
    raise NotImplementedError("PENDING M04-ACK-4: replay of consumed receipt/ACK")


def given_newer_formal_revision(context):
    raise NotImplementedError("PENDING M04-ACK-5: captured revision older than formal baseline")


def given_false_adoption_claim(context):
    raise NotImplementedError("PENDING M04-ACK-6: Owner-selected or ACK-adopted mutation")


def given_m05_eligible_for_cleanup(context):
    raise NotImplementedError("PENDING M04-ACK-7: retention eligibility is not delete authorization")


def given_pending_bridge_mapping(context):
    raise NotImplementedError("PENDING M04-ACK-8: three bridges remain selected=null")


def when_evaluate_document_mapping(context):
    raise NotImplementedError("PENDING: independent document oracle; no product execution")


def then_observe_document_outcome(context):
    raise NotImplementedError("PENDING: observable document classification only")
