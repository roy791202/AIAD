"""Pending native oracles. Document recipe only. Do not execute destructive FS experiments."""

NOT_RUN = "NOT RUN: host_is_not_windows11_x64"


def given_task_yellow_pending_win11(context):
    raise NotImplementedError("PENDING IO-FX: retain Yellow lightReason Win11/reparse/8.3 missing")


def given_win10_19045_evidence_unchanged(context):
    raise NotImplementedError("PENDING IO-FX: do not rewrite existing Win10 19045 evidence")


def when_evaluate_os_identity(context):
    raise NotImplementedError(f"PENDING IO-FX-01: {NOT_RUN}; commands in candidate.json identity[]")


def then_win11_x64_or_not_run(context):
    raise NotImplementedError("PENDING IO-FX-01: SUCCESS only ProductName Windows 11, build>=22000, 64-bit")


def when_create_junction_in_temp(context):
    raise NotImplementedError(
        "PENDING IO-FX-02: document mklink /J in %TEMP%\\io-fx-reparse-*; do not run outside disposable temp"
    )


def then_live_reparse_tag(context):
    raise NotImplementedError("PENDING IO-FX-02: SUCCESS only if fsutil reparsepoint query shows a Reparse Tag")


def when_query_eight_dot_three(context):
    raise NotImplementedError("PENDING IO-FX-03: fsutil 8dot3name query + dir /x on disposable temp file")


def then_short_name_alias_observed(context):
    raise NotImplementedError("PENDING IO-FX-03: SUCCESS only if a distinct 8.3 alias is observed")


def then_combined_gate(context):
    raise NotImplementedError("PENDING IO-FX-04: SUCCESS iff IO-FX-01 and IO-FX-02 and IO-FX-03 actually passed")


def then_reject_win10_labeled_win11(context):
    raise NotImplementedError("PENDING IO-FX-05: Windows 10 19045 labeled as Windows 11 PASS => REJECT")


def then_linux_records_not_run(context):
    raise NotImplementedError("PENDING IO-FX-06: Linux authoring host must record explicit NOT RUN, never platform PASS")
